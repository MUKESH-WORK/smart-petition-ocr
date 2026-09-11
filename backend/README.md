# 🏛️ DRO Grievance AI Module — Production Backend

**District Revenue Officer (DRO) Grievance Digitization & Automation Module**  
An enterprise-grade, offline-capable civic intelligence backend engineered to ingest, transcribe, verify, classify, and route handwritten and printed Tamil grievance petitions.

---

## 🏗️ Architecture & The Postgres-First Law

One database. One single source of truth. A single hardened PostgreSQL 16 instance satisfies all persistence, search, vector, and queuing requirements:

- **pgvector (HNSW Index)**: 384-dimensional multilingual vector embeddings (`document_chunks`) with sub-millisecond cosine similarity search.
- **tsvector + GIN Index**: Native full-text search across Tamil and English petition transcripts.
- **JSONB Document Store**: Stores OCR bounding boxes, polygon coordinates, recognized tables, and AI-extracted structures.
- **`FOR UPDATE SKIP LOCKED` ACID Queue**: Zero Redis / RabbitMQ / Kafka. Background workers poll concurrent processing jobs (`ocr`, `vector`, `ner`, `ai`) with zero race conditions and automatic timeout recovery.
- **Monthly Partitioned Audit Logging**: Immutable 1:1 trace of all actions (`upload`, `ocr`, `analysis`, `update`, `approve`, `push`) stored in `audit_log`.

---

## 🧠 Cognitive & Processing Engine

1. **Hybrid Optical Character Recognition (OCR)**:
   - **Primary Engine**: Datalab Chandra OCRv2 API (`https://www.datalab.to/api/v1/convert`) tailored for complex Tamil orthography, historical handwriting, and multi-column layouts.
   - **Offline Fallback**: Local PaddleOCR (PP-OCRv5) with adaptive OpenCV image preprocessing (deskewing, Otsu binarization, noise filtering).
   - **OCR Noise Filtering**: Automatically detects and cleans non-Tamil court fee stamps and OCR artifacts.
   - **Devanagari Normalization**: Converts Devanagari vowel artifacts (e.g. `\u0908` Devanagari `ई`) to Tamil (`\u0B88` `ஈ`), ensuring district names like `ஈரோடு` are always canonical.

2. **Multi-Page Context Budgeting**:
   - For multi-page petitions, dynamically budgets context across **Page 1** (salutation/applicant header), **intermediate pages** (factual dispute context), and the **Final Page** (where legal sign-offs like `இப்படிக்கு, (மனுதாரர் பெயர்)` and prayers reside).

3. **Dynamic CM Helpline Taxonomy Matching**:
   - Directly loaded from `backend/data/cm_helpline_taxonomy.json` containing **40 official Tamil Nadu Government Departments** and **1,862 sub-types**.
   - Zero hardcoded keyword dictionaries. Uses dynamic token matching, semantic concept bridging (`ஆக்கிரமிப்பு` $\rightarrow$ `encroachment`, `பட்டா` $\rightarrow$ `patta`, `முதியோர்`/`விதவை` $\rightarrow$ `pension`), and official acronym mappings (REV, RDPR, MAWS, ENERGY, SWNM).

4. **Anti-Hallucination Claim Verification Barrier**:
   - Every factual claim extracted by the LLM is verified against the raw source OCR text chunks. If ungrounded or `hallucination_score > 0.20`, officer verification is enforced.

5. **Strict Formal Administrative Tamil Summaries**:
   - Summaries strictly conform to DRO 3rd-person administrative standards (`மனுதாரர் [பெயர்] ... கோரியுள்ளார்`), completely stripping colloquial or 1st-person phrasing (`நான்`, `பிறப்பித்தேன்`).

---

## 📂 Project Structure

```
backend/
├── alembic/                    # Database migrations
│   ├── versions/
│   └── env.py
├── app/
│   ├── config.py               # Pydantic v2 settings (.env loader)
│   ├── dependencies.py         # DB session & JWT officer authentication
│   ├── main.py                 # FastAPI application factory & lifespan
│   └── routers/
│       ├── grievance.py        # /api/v1/grievance (upload, ocr, draft, chat)
│       ├── search.py           # /api/v1/search (vector, fulltext, hybrid RRF)
│       └── admin.py            # /api/v1/admin (queue status, master locations)
├── core/
│   ├── llm_client.py           # Ollama / OpenAI-compatible LLM client
│   └── security.py             # JWT token utilities
├── data/
│   └── cm_helpline_taxonomy.json # Official CM Helpline Taxonomy (1,862 records)
├── models/
│   ├── database.py             # SQLAlchemy 2.0 async engine & asyncpg pool
│   ├── orm.py                  # Tables: sources, ocr_results, grievance_drafts, etc.
│   └── schemas.py              # Pydantic schemas for requests/responses
├── services/
│   ├── ai_analyzer.py          # Cognitive summarization & multi-page context engine
│   ├── dro_bridge.py           # External state DRO portal integration
│   ├── entity_extractor.py     # LLM-first NER + Aadhaar masking (`XXXX-XXXX-1234`)
│   ├── file_store.py           # Safe document & page image persistence
│   ├── job_queue.py            # SKIP LOCKED background queue worker
│   ├── ocr_router.py           # Chandra OCRv2 + PaddleOCR hybrid router
│   ├── tamil_chunker.py        # Semantic Tamil sentence chunking
│   ├── taxonomy_matcher.py     # Dynamic CM Helpline validator
│   └── vector_store.py         # pgvector HNSW indexing & hybrid RRF search
├── tests/
│   ├── test_production_pipeline.py # Production pipeline tests
│   └── test_end_to_end.py      # End-to-end integration tests
├── Dockerfile                  # Production container image definition
├── docker-compose.yml          # Standalone PostgreSQL 16 + pgvector container
├── init_db.py                  # Master location seeder (Erode revenue hierarchy)
└── requirements.txt            # Python dependencies
```

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
- **Python**: 3.11.x – 3.12.x
- **PostgreSQL**: 16 with `pgvector` extension
- **Ollama**: Running locally with `qwen2.5:3b` or `qwen2.5:1.5b`

### 2. Start PostgreSQL 16 + pgvector
```bash
docker compose up -d
```

### 3. Install Python Dependencies
```bash
# Create and activate virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 4. Run Migrations & Seed Master Data
```bash
alembic upgrade head
python init_db.py
```

### 5. Launch FastAPI Backend
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger documentation: `http://localhost:8000/api/v1/docs`

---

## 🧪 Testing

Run the automated test suite:
```bash
pytest tests/test_production_pipeline.py tests/test_end_to_end.py -v
```
