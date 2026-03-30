package com.toponymic.controller;

import com.toponymic.model.AnalysisInsight;
import com.toponymic.service.DataAnalyzerService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * REST controller for data analysis operations.
 */
@RestController
@RequestMapping("/api/analysis")
public class AnalysisController {

    @Autowired
    private DataAnalyzerService dataAnalyzerService;

    /**
     * Run full analysis pipeline.
     * POST /api/analysis/run
     */
    @PostMapping("/run")
    public ResponseEntity<List<AnalysisInsight>> runAnalysis() {
        return ResponseEntity.ok(dataAnalyzerService.runFullAnalysis());
    }

    /**
     * Get all analysis insights.
     * GET /api/analysis/insights
     */
    @GetMapping("/insights")
    public ResponseEntity<List<AnalysisInsight>> getAllInsights() {
        return ResponseEntity.ok(dataAnalyzerService.getAllInsights());
    }

    /**
     * Get basic distribution analysis.
     * GET /api/analysis/distribution
     */
    @GetMapping("/distribution")
    public ResponseEntity<AnalysisInsight> getDistribution() {
        return ResponseEntity.ok(dataAnalyzerService.analyzeBasicDistribution());
    }

    /**
     * Get STRONG subtype analysis.
     * GET /api/analysis/strong-subtypes
     */
    @GetMapping("/strong-subtypes")
    public ResponseEntity<AnalysisInsight> getStrongSubtypes() {
        return ResponseEntity.ok(dataAnalyzerService.analyzeStrongSubtypes());
    }

    /**
     * Get WEAK source analysis.
     * GET /api/analysis/weak-sources
     */
    @GetMapping("/weak-sources")
    public ResponseEntity<AnalysisInsight> getWeakSources() {
        return ResponseEntity.ok(dataAnalyzerService.analyzeWeakSources());
    }
}
