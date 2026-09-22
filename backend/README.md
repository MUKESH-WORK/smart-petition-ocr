# GDP Assistant — Backend

> FastAPI async backend for the AI-powered grievance redressal platform.

## Tech Stack

| Technology | Version | Purpose |
| :--- | :--- | :--- |
| **FastAPI** | 0.111+ | Async API framework |
| **Uvicorn** | 0.30+ | ASGI server |
| **SQLAlchemy** | 2.0+ | ORM (async support) |
| **PostgreSQL 16** | — | Enterprise database with pgvector |
| **SQLite** | — | Offline embedded database |
| **SentenceTransformers** | 2.7+ | Multilingual vector embeddings |
| **PaddleOCR** | 2.7+ | Local offline Tamil OCR |
| **Ollama / Qwen** | — | Local LLM inference |
| **Alembic** | 1.13+ | Database migrations |
| **PyJWT** | 2.8+ | JWT authentication |

## Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux: source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database (if fresh clone)
python scripts/manage_db.py seed-fresh

# 4. Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Pydantic settings & environment loader
│   ├── dependencies.py      # Dependency injection & auth guards
│   ├── api/v1/              # Versioned API route modules
│   │   └── translate.py     # Dynamic translation API
│   └── routers/             # Router modules
│       └── translate.py     # LLM-powered translation engine
├── core/
│   ├── llm_client.py        # LLM client (Ollama/Gemini)
│   └── security_config.py   # Security configuration
├── models/                  # SQLAlchemy ORM models
├── services/
│   ├── cm_grievance_rag.py  # CM Helpline RAG engine
│   ├── local_chandra_engine.py  # Local OCR engine
│   └── semantic_cache.py    # LLM response deduplication
├── scripts/                 # Data ingestion & DB management
├── tests/                   # pytest test suites
├── alembic/                 # Database migrations
├── Dockerfile               # Production container image
└── requirements.txt         # Python dependencies
```

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Database & service health telemetry |
| `POST` | `/api/v1/translate` | Dynamic LLM-powered translation |
| `POST` | `/api/v1/grievances/upload` | Petition image upload & OCR |
| `GET` | `/api/v1/admin/taxonomy/stats` | Taxonomy statistics |
| `GET` | `/api/v1/admin/hierarchy/stats` | Administrative hierarchy stats |
| `GET` | `/api/v1/docs` | Interactive OpenAPI documentation |

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_production_edge_cases.py -v
```

## Docker

```bash
# Build image
docker build -t gdp-backend -f Dockerfile ..

# Run container
docker run -p 8000:8000 --env-file ../.env gdp-backend
```

## Environment Variables

See the comprehensive [`.env.example`](.env.example) for all available configuration options including:
- Database connections (PostgreSQL / SQLite)
- LLM engine settings (Ollama, model selection)
- OCR provider configuration (Datalab, PaddleOCR, Local Chandra)
- Performance tuning (workers, pool sizes, timeouts)
- Semantic cache and deduplication settings
