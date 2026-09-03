# 🏛️ DRO Grievance AI Module — Production Backend

**District Revenue Officer (DRO) Grievance Digitization & Automation Module**  
Automates Tamil grievance petition processing on CPU hardware (Windows / Linux / Docker, 8GB RAM) using a **Postgres-First Law** architecture with Hybrid OCR and Grounded Local LLMs.

---

## 🏗️ Architecture & The Postgres-First Law

One database. One single source of truth. PostgreSQL 16 replaces all specialized data stores:
- **pgvector (HNSW Index)**: Replaces ChromaDB / Pinecone (384-dim multilingual embeddings).
- **tsvector + GIN Index**: Replaces Elasticsearch (Tamil & English full-text search).
- **JSONB**: Replaces MongoDB (stores OCR blocks, tables, and AI action items).
- **FOR UPDATE SKIP LOCKED**: Replaces Redis / RabbitMQ / Kafka for background job execution.
- **BYTEA + Filesystem Cache**: Stores source documents & rendered page images.
- **Partitioned Tables**: Monthly partitioned `audit_log` with 1:1 event traceability.

---

## 📂 Project Structure

```
GDP_Assistant/
├── alembic/
│   ├── versions/
│   │   └── 001_initial_schema.py    # DDL with pgvector, JSONB, tsvector, and partitions
│   └── env.py
├── app/
│   ├── config.py                   # Pydantic Settings (.env configuration)
│   ├── dependencies.py             # DB sessions, JWT officer auth, and audit logger
│   ├── main.py                     # FastAPI application factory & lifespan
│   └── routers/
│       ├── grievance.py            # /api/v1/grievance (upload, ocr, extract, analyze, draft, push, chat)
│       ├── search.py               # /api/v1/search (vector, fulltext, hybrid RRF)
│       └── admin.py                # /api/v1/admin (queue status, system metrics, master locations)
├── services/
│   ├── ocr_router.py               # Hybrid PaddleOCR (PP-OCRv5) + lazy-loaded Surya
│   ├── tamil_chunker.py            # Semantic chunking on Tamil sentence boundaries
│   ├── vector_store.py             # pgvector embedding indexer & RRF hybrid search
│   ├── entity_extractor.py         # Regex + AI NER + Aadhaar masking + Master DB validation
│   ├── ai_analyzer.py              # Qwen 2.5 summary, classification & claim verification barrier
│   ├── dro_bridge.py               # External DRO portal API integration
│   ├── job_queue.py                # PostgreSQL SKIP LOCKED worker queue
│   └── file_store.py               # Document & page image storage
├── models/
│   ├── database.py                 # Async engine & session pooling
│   ├── orm.py                      # SQLAlchemy 2.0 ORM mappings
│   └── schemas.py                  # Pydantic v2 request/response schemas
├── core/
│   ├── security.py                 # JWT token encoding & verification
│   └── llm_client.py               # Local Qwen 2.5 client (Ollama / llama.cpp / OpenAI-compatible)
├── test_ui/
│   └── app.py                      # Interactive Streamlit validation console
├── tests/
│   └── test_end_to_end.py          # Unit & integration tests
├── docker-compose.yml              # PostgreSQL 16 + pgvector container
├── requirements.txt                # Python dependencies
└── alembic.ini                     # Alembic migration configuration
```

---

## 🚀 Quickstart Guide

### 1. Start PostgreSQL 16 + pgvector
```bash
docker compose up -d
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Database Migrations
```bash
alembic upgrade head
```

### 4. Start the FastAPI Backend
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive API documentation will be available at: `http://localhost:8000/api/v1/docs`.

### 5. Launch the Streamlit Validation Console
```bash
streamlit run test_ui/app.py
```

---

## 🛡️ Anti-Hallucination & Security Contract

1. **Claim Grounding Barrier**: Every claim in the AI summary must match a specific source page number and pass substring/keyword verification.
2. **Aadhaar Masking**: Aadhaar numbers are automatically masked (`XXXX-XXXX-1234`) during regex extraction before being saved to the database.
3. **Master DB Validation**: Villages and taluks are cross-validated against `master_locations`. Unmatched entries are flagged as `suspect`.
4. **Mandatory Officer Sign-Off**: The DRO Bridge rejects submissions unless `officer_approved == TRUE`. If `hallucination_score > 0.20`, a Section Officer override is enforced.
5. **Full Audit Logging**: Every upload, OCR extraction, AI analysis, update, and push action is logged in `audit_log`.
