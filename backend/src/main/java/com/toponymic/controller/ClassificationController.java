package com.toponymic.controller;

import com.toponymic.model.ClassificationResult;
import com.toponymic.model.ClassificationResult.ClassificationType;
import com.toponymic.model.PlacenameRecord;
import com.toponymic.repository.ClassificationResultRepository;
import com.toponymic.repository.PlacenameRecordRepository;
import com.toponymic.service.LlmClassifierService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST controller for classification operations.
 */
@RestController
@RequestMapping("/api/classification")
public class ClassificationController {

    @Autowired
    private LlmClassifierService llmClassifierService;

    @Autowired
    private PlacenameRecordRepository placenameRecordRepository;

    @Autowired
    private ClassificationResultRepository classificationResultRepository;

    /**
     * Trigger classification of all pending records.
     * POST /api/classification/run
     */
    @PostMapping("/run")
    public ResponseEntity<Map<String, Long>> runClassification() {
        Map<String, Long> result = llmClassifierService.classifyAllPending();
        return ResponseEntity.ok(result);
    }

    /**
     * Classify a single record by ID.
     * POST /api/classification/record/{id}
     */
    @PostMapping("/record/{id}")
    public ResponseEntity<?> classifyRecord(@PathVariable Long id) {
        return placenameRecordRepository.findById(id)
            .map(record -> ResponseEntity.ok(llmClassifierService.classifyRecord(record)))
            .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Get classification statistics.
     * GET /api/classification/stats
     */
    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getStats() {
        return ResponseEntity.ok(llmClassifierService.getClassificationStats());
    }

    /**
     * Get all classification results.
     * GET /api/classification/results
     */
    @GetMapping("/results")
    public ResponseEntity<List<ClassificationResult>> getAllResults() {
        return ResponseEntity.ok(classificationResultRepository.findAll());
    }

    /**
     * Get classification results by type (STRONG/WEAK/NONE).
     * GET /api/classification/results/{type}
     */
    @GetMapping("/results/{type}")
    public ResponseEntity<List<ClassificationResult>> getResultsByType(
            @PathVariable String type) {
        try {
            ClassificationType classificationType = ClassificationType.valueOf(type.toUpperCase());
            return ResponseEntity.ok(classificationResultRepository.findByClassification(classificationType));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().build();
        }
    }
}
