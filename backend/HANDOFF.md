# 🏛️ DRO Grievance AI Module — Production Hardening Handoff Guide

## 1. System Overview & Deployment Architecture
The District Revenue Officer (DRO) Grievance AI Module is designed for air-gapped or restricted-network deployment in district collectorates (e.g., Erode Collectorate, Tamil Nadu).

- **Backend Framework**: FastAPI (Python 3.11 asynchronous ASGI)
- **Primary Database**: PostgreSQL 16 with `pgvector`, `pg_trgm`, `unaccent`, and declarative range partitioning
- **Fallback Database**: SQLite 3 with runtime PostgreSQL idiom emulation layer (`models/database.py`)
- **Cognitive Engine**: Ollama running `qwen2.5:3b-instruct` (optimized for local CPU inference, INT4/INT8 quantization)
- **OCR Engine**: Datalab Chandra API with local PaddleOCR PP-OCRv5 fallback
- **Queue / Async Engine**: In-database `job_queue` using atomic status transitions (`FOR UPDATE SKIP LOCKED` on Postgres, `UPDATE ... RETURNING` on SQLite)

---

## 2. Hardening Pass Delta (P0 → P2 Kill Points Eliminated)

### P0 Data Integrity & Anti-Hallucination
- **[K1] `datetime` Module Import**: Resolved NameError in `push_to_dro` by importing `from datetime import datetime, timezone`.
- **[K2/K7] Purged Hardcoded Names & Location Overrides**: Completely eradicated all occurrences of `"கார்னாஜ்"`, `"ந. கார்னாஜ்"`, and hardcoded `"ஈரோடு பெருந்துறை"` encroachment templates from `ai_analyzer.py`.
- **[K3/K4/K5] Null-by-Default ORM Schema**:
  - `GrievanceDraft` field defaults are now strictly `NULL`/`None` (no fabricated strings or premature `'Open'` statuses).
  - WhatsApp notification flags default to `False`.
  - `dro_grievance_id` remains `NULL` until official approval and minting.
  - Substituted deprecated `datetime.utcnow` with `lambda: datetime.now(timezone.utc)`.
- **[K8] Deterministic Embedder Gating**: Eliminated pseudo-random 384-dimensional vector fallback in `vector_store.py`. If the model is not loaded, operations fail explicitly with `RuntimeError` rather than polluting the vector index.

### P1 Security & Production Access Control
- **[K9] Secret & Credential Sanitization**: Removed all hardcoded database passwords, production secrets, and external API keys from `config.py` class defaults.
- **[K10] Insecure CORS & Auto-Seeding Guard**: Restricted CORS to explicit origins configured via `ALLOWED_ORIGINS` (disallowing wildcard credentials), and guarded all demo data seeding in `lifespan()` behind `settings.SEED_DEMO_DATA = True`.
- **[K11] Fail-Closed Officer Authentication**:
  - `get_current_officer` in `dependencies.py` now strictly fails closed, raising `HTTP 401 Unauthorized` on missing or invalid JWT tokens.
  - Attached officer authentication guards to all mutation and analytical routes (`/upload`, `/chat`, `/analyze`, `/extract-entities`, `/draft/*`, `/admin/*`).
- **[K12] Air-Gapped Zero-Cost Translation**: Disabled all external calls to Google and MyMemory cloud translation APIs in `translate.py`. Uncached strings now return untouched without leaking sensitive petition data.
- **[K13] Mass Assignment Prevention in `update_draft`**: Restricted `update_draft` strictly to `ALLOWED_UPDATE_FIELDS`, preventing tampering with `dro_status`, `officer_approved`, or `dro_grievance_id`.
- **[K14] Isolated Audit Session**: `log_audit_event` executes in its own independent database session via `AsyncSessionLocal()`, guaranteeing audit logs never inadvertently commit or revert active caller transactions.

### P2 Performance & Robustness
- **[K15] Pure Asynchronous Upload**: `/upload` exclusively enqueues jobs to `job_queue` and returns immediately without running synchronous OCR or inference in the HTTP request thread.
- **[K16] Single-Pass Multi-Page Entity Extraction**: Replaced per-page LLM extraction loops with a single structured prompt over concatenated OCR pages (`--- பக்கம் N ---`), cutting CPU inference overhead from minutes to seconds.
- **[K17] OCR Confidence Gating**: Added gating for unreadable or blank scans (average confidence < 0.50 or character count < 20), routing them to `ocr_review` status with Tamil guidance (`ஆவணத்தை தெளிவாக படிக்க முடியவில்லை. மீண்டும் ஸ்கேன் செய்யவும்.`) and stopping downstream LLM jobs.
- **[K18] Atomic Job Queue Claiming**: Implemented atomic `UPDATE job_queue ... RETURNING` in SQLite mode, eliminating concurrency race conditions.
- **[K19] Strict File Whitelist**: Whitelisted file extensions strictly to `{"pdf", "png", "jpg", "jpeg", "tiff", "tif", "bmp", "webp", "docx"}`, rejecting all others with `HTTP 422`.
- **[K20] O(1) File Storage Lookups**: Implemented an in-memory path cache and targeted path resolution in `FileStore`, eliminating `os.listdir()` directory scans. DB `BYTEA` storage is enabled only when `STORE_FILE_BYTEA=True`.
- **[K21] Code Hygiene & Externalized Taxonomy**:
  - Extracted `TAMIL_CONCEPT_MAP` to `backend/data/tamil_concept_map.json`.
  - Removed developer-specific local file paths from `scripts/build_taxonomy.py`.

---

## 3. Key Rotation & Setup Checklist

When deploying to a new collectorate server:

1. **Copy Configuration Template**:
   ```bash
   cp backend/.env.example backend/.env
   ```
2. **Generate JWT Secret Key**:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Paste the generated string into `SECRET_KEY` in `backend/.env`.
3. **Database Configuration**:
   - For PostgreSQL: Set `DATABASE_URL=postgresql+asyncpg://<user>:<pass>@<host>:5432/<db>`.
   - Run migrations:
     ```bash
     alembic upgrade head
     ```
   - For SQLite portable mode: Leave `DATABASE_URL` empty or set `sqlite+aiosqlite:///temp_cache/dro_local.db`.
4. **Configure CORS Allowed Origins**:
   Set `ALLOWED_ORIGINS` to the exact IP or domain of the frontend workstation (e.g. `http://192.168.1.50:5173`).
5. **Run Verification Test Suite**:
   ```bash
   .venv\Scripts\python.exe -m pytest tests/test_production_hardening.py -v
   ```

---

## 4. Operational Troubleshooting

| Symptom | Probable Cause | Corrective Action |
| :--- | :--- | :--- |
| `HTTP 401 Unauthorized` on upload/approve | Missing Bearer token or `X-Officer-Id` | Ensure request includes valid `Authorization: Bearer <jwt>` or configured officer header |
| Petition status stuck at `ocr_review` | Low scan quality or blank page | Have petitioner re-scan petition with higher DPI or clearer contrast |
| Vector search fails with `RuntimeError` | Embedding model not downloaded | Run `python -c "from services.vector_store import vector_store; vector_store.warmup()"` with network access once |
| Worker not processing jobs | Worker process cancelled or crashed | Ensure background worker loop (`job_queue.run_worker_loop`) is active in `lifespan` |
