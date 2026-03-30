package com.toponymic.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.toponymic.config.AppConfig;
import com.toponymic.model.ClassificationResult;
import com.toponymic.model.ClassificationResult.ClassificationType;
import com.toponymic.model.PlacenameRecord;
import com.toponymic.repository.ClassificationResultRepository;
import com.toponymic.repository.PlacenameRecordRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Service for classifying placename records as STRONG, WEAK, or NONE.
 * Uses regex patterns as a fast pre-filter, with LLM API fallback for ambiguous cases.
 * Mirrors the functionality of Python's llm_classifier.py.
 */
@Service
public class LlmClassifierService {

    private static final Logger log = LoggerFactory.getLogger(LlmClassifierService.class);

    private static final String CITATION_PATTERN = "[云曰注按謂]|《[^》]+》|相傳";
    private static final String CLASSIFICATION_PROMPT_TEMPLATE =
        "你是一个专业的古汉语文本分类专家。请判断以下文本是否包含地名命名的解释。\n\n" +
        "地名：%s\n文本：%s\n\n" +
        "分类标准：\n" +
        "- STRONG：作者直接解释命名原因，使用因果性语言（如：因...名之，故名，以...为名）\n" +
        "- WEAK：命名解释存在，但引用了其他来源（如：《水经注》云...，相传...）\n" +
        "- NONE：仅描述性地理/行政信息，无命名逻辑\n\n" +
        "请只回复分类结果（STRONG/WEAK/NONE）和证据片段，格式：\n" +
        "分类：[STRONG/WEAK/NONE]\n证据：[相关文本片段]";

    @Autowired
    private AppConfig appConfig;

    @Autowired
    private PlacenameRecordRepository placenameRecordRepository;

    @Autowired
    private ClassificationResultRepository classificationResultRepository;

    @Autowired
    private RestTemplate restTemplate;

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * Check if text matches any STRONG regex pattern.
     *
     * @return matched evidence span, or null if no match
     */
    public String checkStrongByRegex(String text) {
        for (String patternStr : AppConfig.STRONG_PATTERNS) {
            Pattern pattern = Pattern.compile(patternStr);
            Matcher matcher = pattern.matcher(text);
            if (matcher.find()) {
                int start = Math.max(0, matcher.start() - 10);
                int end = Math.min(text.length(), matcher.end() + 10);
                return text.substring(start, end);
            }
        }
        return null;
    }

    /**
     * Classify a single placename record using regex + LLM fallback.
     */
    public ClassificationResult classifyRecord(PlacenameRecord record) {
        String text = record.getContextText();

        // Stage 1: Regex pre-filter for STRONG
        String evidenceSpan = checkStrongByRegex(text);
        if (evidenceSpan != null) {
            ClassificationResult result = new ClassificationResult(
                record, ClassificationType.STRONG, evidenceSpan, "REGEX"
            );
            return classificationResultRepository.save(result);
        }

        // Stage 2: LLM fallback for WEAK/NONE
        try {
            Thread.sleep(appConfig.getApiCallIntervalMs());
            return callLlmApi(record);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Thread interrupted during API call interval");
        } catch (Exception e) {
            log.error("LLM API call failed for record {}: {}", record.getId(), e.getMessage());
        }

        // Fallback: classify as NONE if LLM fails
        ClassificationResult fallback = new ClassificationResult(
            record, ClassificationType.NONE, "", "FALLBACK"
        );
        return classificationResultRepository.save(fallback);
    }

    /**
     * Call the LLM API for classification.
     */
    private ClassificationResult callLlmApi(PlacenameRecord record) {
        String prompt = String.format(CLASSIFICATION_PROMPT_TEMPLATE,
            record.getPlacename(), record.getContextText());

        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("model", appConfig.getClassificationModel());
        requestBody.put("messages", List.of(Map.of("role", "user", "content", prompt)));
        requestBody.put("temperature", 0.1);
        requestBody.put("max_tokens", 200);

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

        return parseClassificationResponse(record, response.getBody());
    }

    /**
     * Parse the LLM API response and create a ClassificationResult.
     */
    private ClassificationResult parseClassificationResponse(PlacenameRecord record, String responseBody) {
        try {
            JsonNode root = objectMapper.readTree(responseBody);
            String content = root.path("choices").get(0).path("message").path("content").asText();

            ClassificationType classification = ClassificationType.NONE;
            String evidenceSpan = "";

            // Parse classification from response
            if (content.contains("STRONG")) {
                classification = ClassificationType.STRONG;
            } else if (content.contains("WEAK")) {
                classification = ClassificationType.WEAK;
            }

            // Parse evidence span
            int evidenceIndex = content.indexOf("证据：");
            if (evidenceIndex >= 0) {
                evidenceSpan = content.substring(evidenceIndex + 3).trim();
            }

            ClassificationResult result = new ClassificationResult(
                record, classification, evidenceSpan, "LLM"
            );
            result.setLlmReasoning(content);
            return classificationResultRepository.save(result);

        } catch (Exception e) {
            log.error("Failed to parse LLM response: {}", e.getMessage());
            return classificationResultRepository.save(
                new ClassificationResult(record, ClassificationType.NONE, "", "LLM_PARSE_ERROR")
            );
        }
    }

    /**
     * Classify all unclassified records in the database.
     */
    public Map<String, Long> classifyAllPending() {
        List<PlacenameRecord> allRecords = placenameRecordRepository.findAll();
        Set<Long> classifiedIds = new HashSet<>();
        classificationResultRepository.findAll()
            .forEach(cr -> classifiedIds.add(cr.getPlacenameRecord().getId()));

        List<PlacenameRecord> pending = allRecords.stream()
            .filter(r -> !classifiedIds.contains(r.getId()))
            .toList();

        log.info("Classifying {} pending records", pending.size());

        for (PlacenameRecord record : pending) {
            classifyRecord(record);
        }

        Map<String, Long> counts = new LinkedHashMap<>();
        counts.put("STRONG", classificationResultRepository.countByClassification(ClassificationType.STRONG));
        counts.put("WEAK", classificationResultRepository.countByClassification(ClassificationType.WEAK));
        counts.put("NONE", classificationResultRepository.countByClassification(ClassificationType.NONE));
        return counts;
    }

    /**
     * Get classification statistics.
     */
    public Map<String, Object> getClassificationStats() {
        Map<String, Object> stats = new LinkedHashMap<>();
        List<Object[]> counts = classificationResultRepository.countByClassification();
        Map<String, Long> distribution = new LinkedHashMap<>();
        for (Object[] row : counts) {
            distribution.put(row[0].toString(), (Long) row[1]);
        }
        stats.put("distribution", distribution);
        stats.put("total", classificationResultRepository.count());
        stats.put("regexClassified", classificationResultRepository.findByClassificationMethod("REGEX").size());
        stats.put("llmClassified", classificationResultRepository.findByClassificationMethod("LLM").size());
        return stats;
    }
}
