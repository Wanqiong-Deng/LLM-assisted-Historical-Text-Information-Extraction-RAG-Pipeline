package com.toponymic.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "classification_results")
public class ClassificationResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "placename_record_id", nullable = false)
    private PlacenameRecord placenameRecord;

    @Column(name = "classification", nullable = false, length = 10)
    @Enumerated(EnumType.STRING)
    private ClassificationType classification;

    @Column(name = "evidence_span", columnDefinition = "TEXT")
    private String evidenceSpan;

    @Column(name = "classification_method", length = 20)
    private String classificationMethod; // "REGEX" or "LLM"

    @Column(name = "confidence_score")
    private Double confidenceScore;

    @Column(name = "llm_reasoning", columnDefinition = "TEXT")
    private String llmReasoning;

    @Column(name = "classified_at")
    private LocalDateTime classifiedAt;

    @PrePersist
    protected void onCreate() {
        classifiedAt = LocalDateTime.now();
    }

    public enum ClassificationType {
        STRONG, WEAK, NONE
    }

    // Constructors
    public ClassificationResult() {}

    public ClassificationResult(PlacenameRecord placenameRecord, ClassificationType classification,
                                 String evidenceSpan, String classificationMethod) {
        this.placenameRecord = placenameRecord;
        this.classification = classification;
        this.evidenceSpan = evidenceSpan;
        this.classificationMethod = classificationMethod;
    }

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public PlacenameRecord getPlacenameRecord() { return placenameRecord; }
    public void setPlacenameRecord(PlacenameRecord placenameRecord) { this.placenameRecord = placenameRecord; }

    public ClassificationType getClassification() { return classification; }
    public void setClassification(ClassificationType classification) { this.classification = classification; }

    public String getEvidenceSpan() { return evidenceSpan; }
    public void setEvidenceSpan(String evidenceSpan) { this.evidenceSpan = evidenceSpan; }

    public String getClassificationMethod() { return classificationMethod; }
    public void setClassificationMethod(String classificationMethod) { this.classificationMethod = classificationMethod; }

    public Double getConfidenceScore() { return confidenceScore; }
    public void setConfidenceScore(Double confidenceScore) { this.confidenceScore = confidenceScore; }

    public String getLlmReasoning() { return llmReasoning; }
    public void setLlmReasoning(String llmReasoning) { this.llmReasoning = llmReasoning; }

    public LocalDateTime getClassifiedAt() { return classifiedAt; }
    public void setClassifiedAt(LocalDateTime classifiedAt) { this.classifiedAt = classifiedAt; }
}
