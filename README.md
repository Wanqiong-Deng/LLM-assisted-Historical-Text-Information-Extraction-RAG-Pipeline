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

---

## 中文使用说明

### 1. 我的原始数据应该放在哪里？

本项目支持两种使用模式：

#### 方式一：Java + Angular 网页版（推荐）

**无需手动放置文件。** 直接通过网页界面上传 HTML 文件：

1. 启动后端和前端（见下方步骤）
2. 打开浏览器访问 http://localhost:4200
3. 点击 **📄 Pipeline** 标签页
4. 点击上传按钮，选择从 [ctext.org](https://ctext.org) 下载的 HTML 文件
5. 系统会自动解析并提取地名信息

#### 方式二：Python 脚本版（原始版本，`src/` 目录）

将从 ctext.org 下载的 **HTML 文件**放入以下目录：

```
src/
└── data/
    └── raw_html/    ← 把你的 .html 文件放在这里
        ├── 1.html
        ├── 2.html
        └── ...
```

> **注意**：这是 `src/data/raw_html/` 文件夹，与 `src/database/`（转换后的文本输出目录）同级。

---

### 2. 怎么跑这个项目？

#### 方式一：Java + Angular 网页版（推荐）

**第 1 步：配置 LLM API Key**

编辑 `backend/src/main/resources/application.properties`，填入你的 API Key：

```properties
llm.api.key=你的API密钥
llm.api.base-url=https://api.siliconflow.cn/v1
llm.classification.model=Qwen/Qwen2.5-7B-Instruct
llm.rag.model=Qwen/Qwen2.5-72B-Instruct
```

**第 2 步：启动后端**（需要 Java 17+ 和 Maven 3.8+）

```bash
cd backend
mvn spring-boot:run
```

后端运行在 http://localhost:8080

**第 3 步：启动前端**（需要 Node.js 18+ 和 Angular CLI）

```bash
cd frontend
npm install
npm start
```

前端运行在 http://localhost:4200

**第 4 步：使用网页界面**

浏览器打开 http://localhost:4200，依次使用以下四个功能：

| 标签页 | 功能 | 操作 |
|--------|------|------|
| 📄 Pipeline | 上传并解析 HTML 文件 | 点击上传，选择 ctext 格式 HTML 文件 |
| 🏷️ Classification | 对地名记录分类 | 点击"运行分类"按钮 |
| 📊 Analysis | 统计分析 | 点击"运行分析"按钮 |
| 💬 RAG Chat | 自然语言问答 | 直接输入问题 |

---

#### 方式二：Python 脚本版（`src/` 目录）

**前提条件：** Python 3.9+，安装依赖：

```bash
pip install beautifulsoup4 pandas langchain langchain-openai langgraph opencc-python-reimplemented jieba rank-bm25 streamlit plotly langsmith
```

**第 1 步：配置 API Key**

编辑 `src/config.py`，填入你的 API Key：

```python
API_KEY = "你的API密钥"
API_BASE_URL = "https://api.siliconflow.cn/v1"
```

**第 2 步：将 HTML 文件放入 `data/raw_html/` 目录**（见上方说明）

**第 3 步：运行完整流程**

```bash
# 进入 src 目录
cd src

# 步骤一：将 HTML 转换为纯文本（输出到 src/database/）
python conversion/html_converter.py

# 步骤二：提取地名记录
python extraction/placename_extractor.py

# 步骤三：运行分类
python classification/llm_classifier.py

# 步骤四：统计分析
python analysis/data_analyzer.py

# 步骤五：启动 RAG Agent 界面（Streamlit）
streamlit run App.py
```

RAG 界面会在浏览器中打开（通常是 http://localhost:8501）。
