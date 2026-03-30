package com.toponymic.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.toponymic.config.AppConfig;
import com.toponymic.model.ClassificationResult;
import com.toponymic.repository.ClassificationResultRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.*;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.stream.Collectors;

/**
 * Service for Retrieval-Augmented Generation (RAG) based semantic search and Q&A.
 * Mirrors the functionality of Python's rag_agent.py.
 *
 * Note: conversationHistory is shared across all requests. For multi-user production use,
 * replace with a session-scoped or per-user conversation store.
 */
@Service
public class RagService {

    private static final Logger log = LoggerFactory.getLogger(RagService.class);

    private static final String RAG_SYSTEM_PROMPT =
        "你是一个专业的古代地名研究助手，专门分析历史文献中的地名命名解释。\n" +
        "请基于提供的文档，准确、客观地回答关于地名命名历史的问题。\n" +
        "如果文档中没有相关信息，请说明无法从现有数据中找到答案。";

    @Autowired
    private AppConfig appConfig;

    @Autowired
    private ClassificationResultRepository classificationResultRepository;

    @Autowired
    private RestTemplate restTemplate;

    private final ObjectMapper objectMapper = new ObjectMapper();

    // Thread-safe conversation history for multi-turn Q&A (single-session design)
    private final List<Map<String, String>> conversationHistory = new CopyOnWriteArrayList<>();

    /**
     * Search for relevant records using keyword matching (BM25-like retrieval).
     *
     * @param query the user's search query
     * @param topK  number of results to return
     * @return list of matching ClassificationResult records
     */
    public List<ClassificationResult> retrieveRelevantDocs(String query, int topK) {
        // Extract potential place names or keywords from the query
        List<ClassificationResult> candidates = new ArrayList<>();

        // Search by keyword in context text
        candidates.addAll(classificationResultRepository.searchByKeyword(query));

        // Search by placename
        if (query.length() >= 2) {
            // Try to find place name mentions in query (look for place suffix)
            for (String suffix : AppConfig.PLACE_SUFFIXES) {
                if (query.contains(suffix)) {
                    int idx = query.indexOf(suffix);
                    int start = Math.max(0, idx - 3);
                    String potentialName = query.substring(start, idx + suffix.length());
                    candidates.addAll(classificationResultRepository.findByPlacenameContaining(potentialName));
                }
            }
        }

        // Deduplicate and limit to topK
        return candidates.stream()
            .distinct()
            .limit(topK)
            .collect(Collectors.toList());
    }

    /**
     * Answer a user query using RAG: retrieve relevant documents and generate answer.
     *
     * @param userQuery the user's question
     * @return generated answer with context
     */
    public Map<String, Object> query(String userQuery) {
        // Retrieve relevant documents
        List<ClassificationResult> docs = retrieveRelevantDocs(userQuery, 5);

        // Build context from retrieved documents
        String context = docs.stream()
            .map(doc -> String.format(
                "地名：%s\n文本：%s\n分类：%s\n证据：%s",
                doc.getPlacenameRecord().getPlacename(),
                doc.getPlacenameRecord().getContextText(),
                doc.getClassification().name(),
                Optional.ofNullable(doc.getEvidenceSpan()).orElse("")
            ))
            .collect(Collectors.joining("\n\n---\n\n"));

        // Build prompt with context
        String prompt = context.isEmpty()
            ? userQuery
            : String.format("根据以下参考文献回答问题：\n\n%s\n\n问题：%s", context, userQuery);

        // Add to conversation history
        conversationHistory.add(Map.of("role", "user", "content", prompt));

        // Generate answer via LLM
        String answer;
        try {
            answer = callRagLlm(new ArrayList<>(conversationHistory));
        } catch (Exception e) {
            log.error("RAG LLM call failed: {}", e.getMessage());
            answer = "抱歉，无法生成回答。请检查API配置。";
        }

        // Add assistant response to history
        conversationHistory.add(Map.of("role", "assistant", "content", answer));

        // Limit history to last 20 entries (10 turns)
        synchronized (conversationHistory) {
            while (conversationHistory.size() > 20) {
                conversationHistory.remove(0);
            }
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("query", userQuery);
        result.put("answer", answer);
        result.put("retrievedDocs", docs.size());
        result.put("sources", docs.stream()
            .map(d -> d.getPlacenameRecord().getPlacename())
            .collect(Collectors.toList()));
        return result;
    }

    /**
     * Clear conversation history.
     */
    public void clearHistory() {
        conversationHistory.clear();
        log.info("Conversation history cleared");
    }

    /**
     * Get current conversation history.
     */
    public List<Map<String, String>> getConversationHistory() {
        return Collections.unmodifiableList(conversationHistory);
    }

    private String callRagLlm(List<Map<String, String>> messages) {
        List<Map<String, String>> fullMessages = new ArrayList<>();
        fullMessages.add(Map.of("role", "system", "content", RAG_SYSTEM_PROMPT));
        fullMessages.addAll(messages);

        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("model", appConfig.getRagModel());
        requestBody.put("messages", fullMessages);
        requestBody.put("temperature", 0.3);
        requestBody.put("max_tokens", 1000);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setBearerAuth(appConfig.getApiKey());

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

        ResponseEntity<String> response = restTemplate.exchange(
            appConfig.getApiBaseUrl() + "/chat/completions",
            HttpMethod.POST,
            entity,
            String.class
        );

        try {
            JsonNode root = objectMapper.readTree(response.getBody());
            return root.path("choices").get(0).path("message").path("content").asText();
        } catch (Exception e) {
            log.error("Failed to parse RAG LLM response: {}", e.getMessage());
            return "无法解析回答，请重试。";
        }
    }
}
