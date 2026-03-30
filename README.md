# Toponymic Explanation Identification System

A hybrid NLP system for extracting and classifying toponymic explanations from Classical Chinese texts, combining rule-based logic, large language models, and retrieval-augmented analysis.

[![Java 17+](https://img.shields.io/badge/java-17+-orange.svg)](https://adoptium.net/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.2-brightgreen.svg)](https://spring.io/projects/spring-boot)
[![Angular](https://img.shields.io/badge/Angular-17-red.svg)](https://angular.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

This project implements an end-to-end pipeline for identifying toponymic explanations—passages that explain why a place is named in a certain way—from historical Chinese texts. The system focuses on high-precision extraction, explainable decision logic, and scalable batch processing.

The project is built with:
- **Java 17 + Spring Boot 3** backend — REST API, business logic, LLM integration
- **Angular 17** frontend — interactive web UI replacing the original Streamlit app
- **SQL (H2 embedded)** data persistence — all records stored in a relational database via JPA/Hibernate

Although the case study focuses on Classical Chinese geographical records, the architecture is applicable to other low-resource, rule-sensitive information extraction tasks.

## Key Features

- **Hybrid rule-based + LLM classification** — Regex patterns for high-precision STRONG cases, LLM API fallback for WEAK/NONE
- **Evidence span extraction** — Every classification decision includes supporting textual evidence
- **SQL-backed persistence** — All extracted records and results stored in H2 (swappable with PostgreSQL/MySQL)
- **Statistical analysis** — Post-hoc pattern mining stored as JSON insights in the database
- **RAG-based semantic retrieval** — Natural language Q&A over extracted records with multi-turn conversation
- **Angular SPA** — Responsive web interface with four workflow tabs

## Classification Schema

Each placename record is classified into one of three categories:

| Category | Description | Example |
|----------|-------------|---------|
| **STRONG** | Author directly explains naming reason using causal language | "因山名之" (named because of the mountain) |
| **WEAK** | Naming explanation is present but attributed to cited sources | "《水經注》云：……" (according to Shuijingzhu...) |
| **NONE** | Descriptive geographic/administrative info without naming logic | "縣東南五十里" (50 li southeast of the county) |

This is a **logic-oriented classification task**, not topic or sentiment classification.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Angular 17 Frontend  (http://localhost:4200)               │
│  ├── 📄 Pipeline Tab    — upload HTML, view records         │
│  ├── 🏷️ Classification Tab — run & filter STRONG/WEAK/NONE  │
│  ├── 📊 Analysis Tab    — distribution charts & insights    │
│  └── 💬 RAG Chat Tab   — multi-turn Q&A                     │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST (CORS-enabled)
┌──────────────────────▼──────────────────────────────────────┐
│  Spring Boot 3 Backend  (http://localhost:8080)             │
│  ├── PipelineController    /api/pipeline/**                  │
│  ├── ClassificationController  /api/classification/**        │
│  ├── AnalysisController    /api/analysis/**                  │
│  └── RagController         /api/rag/**                       │
│                                                              │
│  Services:                                                   │
│  ├── HtmlConverterService  (Jsoup HTML → text)              │
│  ├── PlacenameExtractorService  (regex NLP extraction)       │
│  ├── LlmClassifierService  (regex pre-filter + LLM API)     │
│  ├── DataAnalyzerService   (statistical insights)            │
│  └── RagService            (BM25 retrieval + LLM Q&A)       │
└──────────────────────┬──────────────────────────────────────┘
                       │ JPA / Hibernate
┌──────────────────────▼──────────────────────────────────────┐
│  H2 SQL Database  (./backend/data/toponymic-db)             │
│  ├── placename_records      — extracted toponyms             │
│  ├── classification_results — STRONG/WEAK/NONE decisions     │
│  └── analysis_insights      — JSON insight objects           │
└─────────────────────────────────────────────────────────────┘
                       │ REST API (OpenAI-compatible)
┌──────────────────────▼──────────────────────────────────────┐
│  LLM API  (SiliconFlow / OpenAI-compatible)                 │
│  ├── Classification: Qwen/Qwen2.5-7B-Instruct               │
│  └── RAG Q&A:        Qwen/Qwen2.5-72B-Instruct              │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
├── backend/                          # Java Spring Boot backend
│   ├── pom.xml
│   └── src/main/java/com/toponymic/
│       ├── ToponymicApplication.java
│       ├── config/AppConfig.java
│       ├── model/
│       │   ├── PlacenameRecord.java
│       │   ├── ClassificationResult.java
│       │   └── AnalysisInsight.java
│       ├── repository/
│       │   ├── PlacenameRecordRepository.java
│       │   ├── ClassificationResultRepository.java
│       │   └── AnalysisInsightRepository.java
│       ├── service/
│       │   ├── HtmlConverterService.java
│       │   ├── PlacenameExtractorService.java
│       │   ├── LlmClassifierService.java
│       │   ├── DataAnalyzerService.java
│       │   └── RagService.java
│       └── controller/
│           ├── PipelineController.java
│           ├── ClassificationController.java
│           ├── AnalysisController.java
│           └── RagController.java
│
├── frontend/                         # Angular 17 frontend
│   ├── package.json
│   ├── angular.json
│   └── src/app/
│       ├── app.component.{ts,html}
│       ├── app.config.ts
│       ├── app.routes.ts
│       ├── models/
│       │   ├── placename-record.model.ts
│       │   ├── classification-result.model.ts
│       │   └── analysis-insight.model.ts
│       ├── services/api.service.ts
│       └── components/
│           ├── pipeline/
│           ├── classification/
│           ├── analysis/
│           └── rag-chat/
│
└── src/                              # Original Python source (preserved for reference)
```

## Getting Started

### Prerequisites

- Java 17+
- Maven 3.8+
- Node.js 18+ and npm
- Angular CLI 17+ (`npm install -g @angular/cli`)

### 1. Configure the LLM API

Edit `backend/src/main/resources/application.properties`:

```properties
llm.api.key=your-api-key-here
llm.api.base-url=https://api.siliconflow.cn/v1
llm.classification.model=Qwen/Qwen2.5-7B-Instruct
llm.rag.model=Qwen/Qwen2.5-72B-Instruct
```

### 2. Start the Backend

```bash
cd backend
mvn spring-boot:run
```

The API will be available at http://localhost:8080. The H2 console is at http://localhost:8080/h2-console.

### 3. Start the Frontend

```bash
cd frontend
npm install
npm start
```

The web UI will be available at http://localhost:4200.

### 4. Using the Application

1. **📄 Pipeline** — Upload a classical Chinese HTML file (ctext format). The system will extract place names and save them to the SQL database.
2. **🏷️ Classification** — Click "运行分类" to classify all unclassified records using regex + LLM pipeline. Filter results by STRONG/WEAK/NONE.
3. **📊 Analysis** — Click "运行分析" to generate statistical insights from the classification results.
4. **💬 RAG Chat** — Ask natural language questions about the historical place name data.

### Running Tests (Backend)

```bash
cd backend
mvn test
```
