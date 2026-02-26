# Toponymic Explanation Identification System

A hybrid NLP system for extracting and classifying toponymic explanations from Classical Chinese texts, combining rule-based logic, large language models, and retrieval-augmented analysis.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

This project implements an end-to-end pipeline for identifying toponymic explanations—passages that explain why a place is named in a certain way—from historical Chinese texts. The system focuses on high-precision extraction, explainable decision logic, and scalable batch processing.

Although the case study focuses on Classical Chinese geographical records, the architecture is applicable to other low-resource, rule-sensitive information extraction tasks.

## Key Features

- **Hybrid rule-based + LLM classification** - Regex patterns for high-precision cases, LLM for ambiguous ones
- **Evidence span extraction** - Every classification decision includes supporting textual evidence
- **Cross-entry narration handling** - Resolves naming targets across multiple text entries
- **Resume-safe batch processing** - Progress saving enables processing of large corpora
- **Statistical analysis & visualization** - Post-hoc pattern mining and quantitative insights
- **RAG-based semantic retrieval** - Natural language querying over extracted records

## Classification Schema

Each placename record is classified into one of three categories:

| Category | Description | Example |
|----------|-------------|---------|
| **STRONG** | Author directly explains naming reason using causal language | "因山名之" (named because of the mountain) |
| **WEAK** | Naming explanation is present but attributed to cited sources | "《水經注》云：……" (according to Shuijingzhu...) |
| **NONE** | Descriptive geographic/administrative info without naming logic | "縣東南五十里" (50 li southeast of the county) |

This is a **logic-oriented classification task**, not topic or sentiment classification.

## System Pipeline

