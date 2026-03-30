package com.toponymic.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.toponymic.model.AnalysisInsight;
import com.toponymic.model.ClassificationResult;
import com.toponymic.model.ClassificationResult.ClassificationType;
import com.toponymic.repository.AnalysisInsightRepository;
import com.toponymic.repository.ClassificationResultRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.Collections;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * Service for analyzing classification results and generating insights.
 * Mirrors the functionality of Python's data_analyzer.py.
 */
@Service
public class DataAnalyzerService {

    private static final Logger log = LoggerFactory.getLogger(DataAnalyzerService.class);

    // STRONG subtype patterns - precompiled for efficiency
    private static final Map<String, Pattern> STRONG_SUBTYPE_PATTERNS;
    static {
        Map<String, String> rawPatterns = Map.of(
            "因山水得名", ".*因.*?[山水].*?名.*",
            "因地形得名", ".*因.*?[形地峰嶺谷].*?名.*",
            "因人物得名", ".*因.*?[人氏族姓].*?名.*",
            "直接命名", ".*(故名|取.*?義|以.*?為名).*"
        );
        Map<String, Pattern> compiled = new LinkedHashMap<>();
        rawPatterns.forEach((k, v) -> compiled.put(k, Pattern.compile(v)));
        STRONG_SUBTYPE_PATTERNS = Collections.unmodifiableMap(compiled);
    }

    // WEAK source indicators
    private static final List<String> WEAK_SOURCE_INDICATORS = List.of(
        "《水經注》", "《漢書》", "《史記》", "《元和郡縣志》",
        "《太平寰宇記》", "相傳", "云", "曰"
    );

    @Autowired
    private ClassificationResultRepository classificationResultRepository;

    @Autowired
    private AnalysisInsightRepository analysisInsightRepository;

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * Run full analysis pipeline and save results to SQL database.
     */
    public List<AnalysisInsight> runFullAnalysis() {
        List<AnalysisInsight> insights = new ArrayList<>();

        insights.add(analyzeBasicDistribution());
        insights.add(analyzeStrongSubtypes());
        insights.add(analyzeWeakSources());
        insights.add(analyzeNonePatterns());

        List<AnalysisInsight> saved = analysisInsightRepository.saveAll(insights);
        log.info("Saved {} analysis insights to database", saved.size());
        return saved;
    }

    /**
     * Analyze basic distribution of STRONG/WEAK/NONE classifications.
     */
    public AnalysisInsight analyzeBasicDistribution() {
        Map<String, Long> distribution = new LinkedHashMap<>();
        distribution.put("STRONG", classificationResultRepository.countByClassification(ClassificationType.STRONG));
        distribution.put("WEAK", classificationResultRepository.countByClassification(ClassificationType.WEAK));
        distribution.put("NONE", classificationResultRepository.countByClassification(ClassificationType.NONE));

        long total = distribution.values().stream().mapToLong(Long::longValue).sum();
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("counts", distribution);
        data.put("total", total);

        // Calculate percentages
        Map<String, Double> percentages = new LinkedHashMap<>();
        distribution.forEach((k, v) -> percentages.put(k, total > 0 ? (v * 100.0 / total) : 0.0));
        data.put("percentages", percentages);

        String description = String.format(
            "总计 %d 条记录：STRONG %d 条 (%.1f%%)，WEAK %d 条 (%.1f%%)，NONE %d 条 (%.1f%%)",
            total,
            distribution.get("STRONG"), percentages.get("STRONG"),
            distribution.get("WEAK"), percentages.get("WEAK"),
            distribution.get("NONE"), percentages.get("NONE")
        );

        return new AnalysisInsight("basic_distribution", "分类分布统计", description, toJson(data));
    }

    /**
     * Analyze subtypes of STRONG classifications.
     */
    public AnalysisInsight analyzeStrongSubtypes() {
        List<ClassificationResult> strongResults = classificationResultRepository.findByClassification(ClassificationType.STRONG);
        Map<String, Integer> subtypeCounts = new LinkedHashMap<>();
        STRONG_SUBTYPE_PATTERNS.keySet().forEach(k -> subtypeCounts.put(k, 0));

        for (ClassificationResult cr : strongResults) {
            String evidence = Optional.ofNullable(cr.getEvidenceSpan()).orElse("");
            for (Map.Entry<String, Pattern> entry : STRONG_SUBTYPE_PATTERNS.entrySet()) {
                if (entry.getValue().matcher(evidence).matches()) {
                    subtypeCounts.merge(entry.getKey(), 1, Integer::sum);
                }
            }
        }

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("subtypes", subtypeCounts);
        data.put("total", strongResults.size());

        String description = "STRONG分类子类型分析：" + subtypeCounts.entrySet().stream()
            .map(e -> e.getKey() + " " + e.getValue() + "条")
            .collect(Collectors.joining("，"));

        return new AnalysisInsight("strong_subtypes", "STRONG命名类型分析", description, toJson(data));
    }

    /**
     * Analyze citation sources in WEAK classifications.
     */
    public AnalysisInsight analyzeWeakSources() {
        List<ClassificationResult> weakResults = classificationResultRepository.findByClassification(ClassificationType.WEAK);
        Map<String, Integer> sourceCounts = new LinkedHashMap<>();

        for (ClassificationResult cr : weakResults) {
            String text = Optional.ofNullable(cr.getPlacenameRecord().getContextText()).orElse("");
            for (String source : WEAK_SOURCE_INDICATORS) {
                if (text.contains(source)) {
                    sourceCounts.merge(source, 1, Integer::sum);
                }
            }
        }

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("sources", sourceCounts);
        data.put("total", weakResults.size());

        String description = "WEAK分类引用来源分析，共分析 " + weakResults.size() + " 条记录";

        return new AnalysisInsight("weak_sources", "WEAK引用来源分析", description, toJson(data));
    }

    /**
     * Analyze patterns in NONE classifications.
     */
    public AnalysisInsight analyzeNonePatterns() {
        List<ClassificationResult> noneResults = classificationResultRepository.findByClassification(ClassificationType.NONE);

        // Count geographic direction mentions
        Map<String, Integer> directionCounts = new LinkedHashMap<>();
        String[] directions = {"東", "西", "南", "北", "東南", "東北", "西南", "西北"};
        for (String dir : directions) directionCounts.put(dir, 0);

        for (ClassificationResult cr : noneResults) {
            String text = Optional.ofNullable(cr.getPlacenameRecord().getContextText()).orElse("");
            for (String dir : directions) {
                if (text.contains(dir)) {
                    directionCounts.merge(dir, 1, Integer::sum);
                }
            }
        }

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("directionMentions", directionCounts);
        data.put("total", noneResults.size());

        String description = "NONE分类描述维度分析，共 " + noneResults.size() + " 条记录";

        return new AnalysisInsight("none_patterns", "NONE描述维度分析", description, toJson(data));
    }

    /**
     * Get all analysis insights from database.
     */
    public List<AnalysisInsight> getAllInsights() {
        return analysisInsightRepository.findAll();
    }

    private String toJson(Object obj) {
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize to JSON: {}", e.getMessage());
            return "{}";
        }
    }
}
