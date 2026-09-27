# 🏛️ GDP Assistant — Backend API & Processing Engine

> High-performance FastAPI asynchronous backend powering deep Tamil optical character recognition (OCR), entity extraction, CM Helpline taxonomy classification, and dynamic bilingual translation.

---

## 🛠️ Tech Stack & Dependencies

| Category | Technology | Purpose |
| :--- | :--- | :--- |
| **Framework** | FastAPI 0.141+ | High-throughput asynchronous ASGI web framework |
| **ASGI Server** | Uvicorn 0.53+ | Production ASGI server with uvloop / watchfiles |
| **ORM & Database** | SQLAlchemy 2.0+ & AsyncPG | Dual-engine support for PostgreSQL 16 + pgvector and SQLite |
| **OCR Engines** | Datalab Chandra API & PaddleOCR 3.7+ | Cloud neural handwriting OCR with local offline CPU fallback |
| **NLP & Vectors** | SentenceTransformers 6.1+ | 384-dimensional multilingual embeddings (`paraphrase-multilingual-MiniLM-L12-v2`) |
| **LLM Inference** | Ollama / Qwen 2.5 3B | Local offline summarization, verification, and dynamic translation |
| **Security & Auth** | PyJWT 2.14+ & Cryptography | Role-based access control and JWT officer sessions |
| **Document Processing** | PyMuPDF, PyPDFium2, Pillow, OpenCV | High-speed PDF rasterization and adaptive image binarization |

---

## 🚀 Manual Step-by-Step Backend Setup

### 1. Create Virtual Environment
```bash
# Windows
py -3.11 -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3.11 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` from the root or backend directory:
```bash
cp .env.example .env
```

Configure key variables:
- `DATALAB_API_KEY`: Obtain from [https://www.datalab.to](https://www.datalab.to) for deep Tamil handwriting OCR (or leave empty for offline PaddleOCR fallback).
- `SECRET_KEY`: 32+ character JWT signing key.
- `USE_SQLITE`: Set to `true` for offline embedded SQLite, or `false` for PostgreSQL 16 + pgvector.

### 4. Seed Database
Construct the complete government taxonomy and administrative hierarchy from the included PDF:
```bash
python scripts/manage_db.py seed-fresh
```

### 5. Launch Backend Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📡 API Endpoints Reference

| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/` | API status and greeting |
| `GET` | `/api/v1/health` | Live database telemetry and service diagnostics |
| `POST` | `/api/v1/translate` | Dynamic LLM-powered English ↔ Tamil translation |
| `POST` | `/api/v1/grievances/upload` | Multi-page petition upload, OCR, and classification |
| `GET` | `/api/v1/admin/taxonomy/stats` | CM Helpline taxonomy metrics across 40 departments |
| `GET` | `/api/v1/admin/hierarchy/stats` | Administrative hierarchy unit statistics |
| `GET` | `/api/v1/docs` | Interactive Swagger API documentation |

---

## 🧪 Testing

```bash
# Run full pytest suite
pytest tests/ -v
```
