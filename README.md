# FactGraph

## Evidence-Based Document Intelligence and Relationship Discovery

FactGraph is a document intelligence system that extracts structured facts from PDF documents, preserves verbatim evidence, normalizes comparable values, identifies related facts, and classifies relationships between them.

The system is designed to provide transparent and evidence-based fact extraction. Every extracted fact remains connected to its original document, page number, and supporting verbatim quote.

🔗 **Live Demo:** https://fact-graph.vercel.app/  
💻 **GitHub Repository:** https://github.com/khyathi-2006/FactGraph

## Overview

FactGraph processes PDF documents through an intelligent document analysis pipeline.

The complete pipeline is:

PDF Documents → Page-Aware Parsing → Page-Bounded Chunking → AI Fact Extraction → Evidence Verification → Normalization → Candidate Matching → Relationship Classification → SQLite Storage → FastAPI Inspection Interface

The system ensures that extracted information can be traced back to its original source.

Each accepted fact contains:

- Original statement
- Subject
- Predicate
- Value
- Unit
- Scope
- Time period
- Confidence score
- Supporting evidence quote
- Source page number
- Normalized values

---

## Architecture

FactGraph follows a modular architecture.

The system consists of the following stages:

### 1. PDF Parsing

PDF documents are processed using page-aware parsing.

The system extracts:

- Page text
- Page numbers
- Sections
- Character counts
- Table counts

Pages with very little extractable text are marked as low-yield pages.

---

### 2. Page-Bounded Chunking

The extracted PDF text is divided into manageable chunks.

Chunks remain connected to their original page.

This ensures that facts and evidence can always be traced back to the correct page in the document.

---

### 3. AI Fact Extraction

An OpenAI-compatible Large Language Model is used to extract structured facts.

The extraction model identifies:

- Statement
- Subject
- Predicate
- Value
- Unit
- Scope
- Period
- Supporting quote
- Confidence score
- Ambiguity information

The system extracts both numeric and non-numeric facts.

Examples include:

- Revenue values
- Growth percentages
- Employee counts
- Dates
- Policy decisions
- Appointments
- Financial information
- Business events

---

### 4. Evidence Verification

Every extracted fact must contain a supporting evidence quote.

The quote is checked against the original PDF page text.

If the quote does not exist in the original page, the fact is rejected.

This helps prevent unsupported facts from entering the database.

---

### 5. Fact Normalization

FactGraph normalizes information while preserving the original extracted value.

The system supports normalization for:

- Numbers
- Percentages
- Currency values
- Lakhs
- Crores
- Millions
- Billions
- Trillions
- Financial years
- Quarters
- Calendar years
- Reporting status
- Entity names
- Scope information

The original value is always preserved.

This ensures that normalization errors do not destroy the original information extracted from the document.

---

### 6. Candidate Matching

After facts are extracted, the system searches for potentially related facts.

Candidate matching reduces unnecessary AI classification requests.

Only facts that are likely to be related are sent for relationship classification.

---

### 7. Relationship Classification

Related facts are classified into the following categories:

- Corroborates
- Contradicts
- Reconciled
- Unrelated

Each relationship contains:

- Fact A
- Fact B
- Relationship type
- Reasoning
- Confidence score
- Candidate similarity

---

### 8. SQLite Storage

FactGraph stores all processed information using SQLite.

The database contains the following tables:

- Documents
- Pages
- Facts
- Evidence
- Relationships
- Pipeline Issues

The database structure allows facts to remain connected to their documents and evidence.

---

### 9. Pipeline Issue Tracking

If any stage fails, FactGraph records the issue.

Pipeline issues can include:

- PDF parsing errors
- AI extraction errors
- Evidence verification failures
- Relationship classification errors

Errors are displayed through the application instead of silently failing.

---

## Features

FactGraph includes the following features:

- PyMuPDF page-aware PDF parsing
- Low-yield page detection
- Page-bounded document chunking
- AI-assisted structured fact extraction
- OpenAI-compatible LLM support
- Strict verbatim evidence verification
- Numeric fact extraction
- Non-numeric fact extraction
- Currency normalization
- Percentage normalization
- Scale normalization
- Period normalization
- Entity normalization
- Reporting-status detection
- Candidate fact matching
- Relationship classification
- SQLite database storage
- FastAPI backend
- Browser-based inspection interface
- Pipeline issue tracking
- Visible ingestion errors
- Document status tracking

---

## Project Structure

```text
FactGraph/
│
├── app.py
├── run_ingestion.py
├── requirements.txt
├── README.md
│
├── factlayer/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── pdf_parsing.py
│   ├── chunking.py
│   ├── llm.py
│   ├── extraction.py
│   ├── normalization.py
│   ├── matching.py
│   ├── classification.py
│   ├── storage.py
│   └── orchestrator.py
│
├── starter-datasets/
│
└── tests/
# FactGraph

## Evidence-Based Document Intelligence and Relationship Discovery

FactGraph is an evidence-based document intelligence system that extracts structured facts from PDF documents, preserves verbatim evidence, normalizes comparable values, identifies related facts, and classifies relationships between them.

Every accepted fact remains connected to its original document, page number, and supporting evidence quote.

---

## Technologies Used

FactGraph is built using the following technologies:

### Python

Python is used as the primary programming language for the backend and document processing pipeline.

### FastAPI

FastAPI provides the web application and API interface.

### SQLite

SQLite is used to store documents, facts, evidence, relationships, and pipeline issues.

### PyMuPDF

PyMuPDF is used for extracting text and metadata from PDF documents.

### Pydantic

Pydantic is used to validate structured data models.

### OpenAI-Compatible LLM APIs

FactGraph supports OpenAI-compatible AI providers for:

- Fact extraction
- Structured output generation
- Relationship classification

---

## Installation

### Requirements

Python 3.10 or newer is recommended.

Clone the repository:

```bash
git clone https://github.com/khyathi-2006/FactGraph.git
