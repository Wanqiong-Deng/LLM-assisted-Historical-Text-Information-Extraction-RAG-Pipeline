package com.toponymic.controller;

import com.toponymic.service.HtmlConverterService;
import com.toponymic.service.PlacenameExtractorService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

/**
 * REST controller for the data ingestion pipeline (HTML conversion + placename extraction).
 */
@RestController
@RequestMapping("/api/pipeline")
public class PipelineController {

    private static final Logger log = LoggerFactory.getLogger(PipelineController.class);

    @Autowired
    private HtmlConverterService htmlConverterService;

    @Autowired
    private PlacenameExtractorService placenameExtractorService;

    /**
     * Upload and convert an HTML file, then extract placenames.
     * POST /api/pipeline/upload
     */
    @PostMapping("/upload")
    public ResponseEntity<Map<String, Object>> uploadAndProcess(
            @RequestParam("file") MultipartFile file) {
        try {
            // Save uploaded file temporarily
            Path tempDir = Files.createTempDirectory("toponymic-upload-");
            Path uploadedFile = tempDir.resolve(file.getOriginalFilename());
            file.transferTo(uploadedFile.toFile());

            // Convert HTML to text
            String text = htmlConverterService.extractCtextText(uploadedFile.toFile());

            // Save text to temp file
            Path textFile = tempDir.resolve(
                file.getOriginalFilename().replaceAll("\\.(html|htm)$", ".txt")
            );
            Files.writeString(textFile, text);

            // Extract placenames
            var records = placenameExtractorService.extractFromFile(textFile, file.getOriginalFilename());

            return ResponseEntity.ok(Map.of(
                "message", "File processed successfully",
                "sourceFile", file.getOriginalFilename(),
                "recordsExtracted", records.size(),
                "textPreview", text.length() > 500 ? text.substring(0, 500) + "..." : text
            ));

        } catch (IOException e) {
            log.error("Failed to process uploaded file: {}", e.getMessage());
            return ResponseEntity.internalServerError()
                .body(Map.of("error", "File processing failed: " + e.getMessage()));
        }
    }

    /**
     * Get pipeline status and statistics.
     * GET /api/pipeline/status
     */
    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getPipelineStatus() {
        return ResponseEntity.ok(placenameExtractorService.getStats());
    }

    /**
     * Get all extracted placename records.
     * GET /api/pipeline/records
     */
    @GetMapping("/records")
    public ResponseEntity<?> getAllRecords() {
        return ResponseEntity.ok(placenameExtractorService.getAllRecords());
    }

    /**
     * Search placename records by name.
     * GET /api/pipeline/records/search?q=...
     */
    @GetMapping("/records/search")
    public ResponseEntity<?> searchRecords(@RequestParam("q") String query) {
        return ResponseEntity.ok(placenameExtractorService.searchByPlacename(query));
    }
}
