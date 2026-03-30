package com.toponymic.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "placename_records")
public class PlacenameRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "placename", nullable = false, length = 100)
    private String placename;

    @Column(name = "context_text", columnDefinition = "TEXT")
    private String contextText;

    @Column(name = "source_file", length = 255)
    private String sourceFile;

    @Column(name = "line_number")
    private Integer lineNumber;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }

    // Constructors
    public PlacenameRecord() {}

    public PlacenameRecord(String placename, String contextText, String sourceFile) {
        this.placename = placename;
        this.contextText = contextText;
        this.sourceFile = sourceFile;
    }

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getPlacename() { return placename; }
    public void setPlacename(String placename) { this.placename = placename; }

    public String getContextText() { return contextText; }
    public void setContextText(String contextText) { this.contextText = contextText; }

    public String getSourceFile() { return sourceFile; }
    public void setSourceFile(String sourceFile) { this.sourceFile = sourceFile; }

    public Integer getLineNumber() { return lineNumber; }
    public void setLineNumber(Integer lineNumber) { this.lineNumber = lineNumber; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
