# FactGraph

## Evidence-Based Document Intelligence and Relationship Discovery

FactGraph is a document intelligence system that extracts structured facts from PDF documents, preserves verbatim evidence, normalizes comparable values, identifies related facts, and classifies relationships between them.

## 1. Overview

The pipeline is:

PDF Documents → Page-Aware Parsing → Page-Bounded Chunking → AI Fact Extraction → Evidence Verification → Normalization → Candidate Matching → Relationship Classification → SQLite Storage → FastAPI Inspection Interface.

Every accepted fact remains connected to its source document, page, and verbatim evidence quote.

## 2. Architecture and Features

- PyMuPDF page-aware PDF parsing
- Low-yield page flagging
- Page-bounded chunking
- AI-assisted structured fact extraction
- Strict verbatim evidence verification
- Currency, scale, percentage, period, entity, and reporting-status normalization
- Cheap candidate matching before relationship classification
- Relationship labels: corroborates, contradicts, reconciled, unrelated
- SQLite persistence for documents, pages, facts, evidence, relationships, and pipeline issues
- FastAPI API and browser inspection screen
- Visible upload and ingestion errors instead of silent failures

Project structure:

factgraph/
- app.py
- run_ingestion.py
- requirements.txt
- README.md
- factlayer/
  - config.py
  - models.py
  - pdf_parsing.py
  - chunking.py
  - llm.py
  - extraction.py
  - normalization.py
  - matching.py
  - classification.py
  - storage.py
  - orchestrator.py
- starter-datasets/
- tests/

## 3. Installation and Configuration

Requirements: Python 3.10 or newer.

Create and activate a virtual environment on Windows:

python -m venv venv
venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Configure an OpenAI-compatible LLM endpoint. For the default configuration, set:

set OPENAI_API_KEY=your_api_key_here

Optional configuration variables:

- LLM_BASE_URL (default: https://api.openai.com/v1)
- FACTLAYER_EXTRACTION_MODEL (default: gpt-4o-mini)
- FACTLAYER_CLASSIFICATION_MODEL (default: gpt-4o-mini)

If you use another OpenAI-compatible provider, set its base URL and supported model names before ingestion.

## 4. Running and Inspection

Run ingestion over starter PDFs:

python run_ingestion.py

Start the application:

uvicorn app:app --reload

Open:

http://127.0.0.1:8000

API documentation:

http://127.0.0.1:8000/docs

The inspection interface displays Documents, Facts, Relationships, and Pipeline Issues. If extraction fails, the application reports the actual error instead of incorrectly marking the document as completed.

Important: a valid AI API key and compatible model are required for AI extraction and relationship classification. Without them, documents are recorded as failed with the underlying error visible in Pipeline Issues.

## 5. Testing and Output

Run:

pytest -q

The system outputs parsed documents, page-level text, extracted facts, verbatim evidence, normalized values, candidate matches, classified relationships, and classification reasoning. Required relationship cases should be selected from actual ingestion results and supported by stored evidence.


## Deployment
This project can run on Vercel. Configure these Environment Variables in Vercel:
- `OPENAI_API_KEY` (or `AI_API_KEY`)
- `LLM_BASE_URL` (optional; defaults to OpenAI-compatible endpoint)
- `FACTLAYER_EXTRACTION_MODEL`
- `FACTLAYER_CLASSIFICATION_MODEL`

Note: Vercel runtime storage is temporary. The SQLite database is suitable for a demo but data may not persist between serverless instances. For production, use a managed database.
