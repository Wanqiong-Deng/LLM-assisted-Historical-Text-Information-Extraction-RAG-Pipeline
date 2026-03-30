package com.toponymic.controller;

import com.toponymic.service.RagService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST controller for RAG-based semantic search and Q&A.
 */
@RestController
@RequestMapping("/api/rag")
public class RagController {

    @Autowired
    private RagService ragService;

    /**
     * Query the RAG system with a natural language question.
     * POST /api/rag/query
     * Body: { "query": "..." }
     */
    @PostMapping("/query")
    public ResponseEntity<Map<String, Object>> query(@RequestBody Map<String, String> request) {
        String userQuery = request.get("query");
        if (userQuery == null || userQuery.isBlank()) {
            return ResponseEntity.badRequest()
                .body(Map.of("error", "Query cannot be empty"));
        }
        return ResponseEntity.ok(ragService.query(userQuery));
    }

    /**
     * Search for relevant documents without LLM generation.
     * GET /api/rag/search?q=...&topK=5
     */
    @GetMapping("/search")
    public ResponseEntity<?> search(
            @RequestParam("q") String query,
            @RequestParam(value = "topK", defaultValue = "5") int topK) {
        return ResponseEntity.ok(ragService.retrieveRelevantDocs(query, topK));
    }

    /**
     * Clear conversation history.
     * POST /api/rag/clear-history
     */
    @PostMapping("/clear-history")
    public ResponseEntity<Map<String, String>> clearHistory() {
        ragService.clearHistory();
        return ResponseEntity.ok(Map.of("message", "Conversation history cleared"));
    }

    /**
     * Get current conversation history.
     * GET /api/rag/history
     */
    @GetMapping("/history")
    public ResponseEntity<List<Map<String, String>>> getHistory() {
        return ResponseEntity.ok(ragService.getConversationHistory());
    }
}
