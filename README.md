# 🏛️ GDP Assistant: AI-Powered Grievance Redressal & Digitization Platform

<div align="center">

![GDP Assistant Banner](assets/banner.jpg)

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=for-the-badge&logo=apache)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI: Modern](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React: 19](https://img.shields.io/badge/React-19.0-61DAFB.svg?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL: 16 + pgvector](https://img.shields.io/badge/PostgreSQL-16_%7C_pgvector-4169E1.svg?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Ollama: Local LLM](https://img.shields.io/badge/Ollama-Qwen_2.5-black.svg?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.ai)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg?style=for-the-badge)](CONTRIBUTING.md)

</div>

<p align="center">
  <strong>An enterprise-grade, offline-capable civic intelligence system engineered for District Revenue Officers (DRO) to digitize, verify, classify, and route handwritten and printed Tamil grievance petitions in seconds on consumer CPU hardware.</strong>
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [System Architecture & The Postgres-First Law](#-system-architecture--the-postgres-first-law)
- [Key Features](#-key-features)
- [Deep Dive: Processing Pipeline](#-deep-dive-processing-pipeline)
- [Tech Stack](#%EF%B8%8F-tech-stack)
- [Project Structure](#-project-structure)
- [Prerequisites & Models Setup](#-prerequisites--models-setup)
- [Getting Started](#-getting-started)
  - [System Requirements](#system-requirements)
  - [One-Click Startup](#one-click-startup-windows)
  - [Manual Step-by-Step Setup](#manual-step-by-step-setup)
- [API Reference & Endpoints](#-api-reference--endpoints)
- [Security, Anti-Hallucination & Governance](#-security-anti-hallucination--governance)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 💡 Overview

In district administration across Tamil Nadu, thousands of citizens submit handwritten and printed petitions during weekly **Grievance Day Petition (GDP)** collectorate sessions. Revenue officers previously faced manual data entry bottlenecks, lost tracking metadata, and delays in routing grievances to responsible taluk and firka officers.

**GDP Assistant** modernizes this civic workflow into an automated, fault-tolerant, and zero-cloud-dependency pipeline:
1. **Wireless Mobile Intake**: Officers or intake staff scan petitions directly via phone cameras using local Wi-Fi QR pairing.
2. **Deep Optical Recognition**: PaddleOCR (PP-OCRv5) extracts complex bilingual Tamil and English typography with bounding boxes.
3. **Deterministic Entity Extraction & PII Redaction**: Automatically extracts petitioner names, mobile numbers, door numbers, revenue taluks, and survey numbers while masking Aadhaar numbers (`XXXX-XXXX-1234`).
4. **Local LLM Intelligence with Grounding Verification**: Qwen 2.5 synthesizes bilingual summaries and auto-suggests government departments, while an anti-hallucination verification barrier cross-references claims against source document pages.
5. **Direct DRO Portal Bridge**: Once verified by an officer, petitions are formatted and dispatched directly into the state grievance redressal system.

---

## 🏗️ System Architecture & The Postgres-First Law

GDP Assistant is architected under the **Postgres-First Law**: **Zero Redis, Zero RabbitMQ, Zero Kafka, Zero Pinecone, Zero Chroma, and Zero MongoDB**. A single, hardened PostgreSQL 16 instance satisfies the entire platform's persistence, vector indexing, full-text search, and task orchestration needs.

```mermaid
flowchart TB
    subgraph ClientLayer ["Client & Ingestion Layer"]
        Desktop["Desktop Admin Portal\n(React 19 + Vite)"]
        Mobile["Mobile Camera Intake\n(WebRTC / Local QR Bridge)"]
    end

    subgraph APILayer ["FastAPI Async Gateway (Port 8000)"]
        Auth["JWT & Officer Session Guard"]
        Upload["/api/v1/grievance/upload"]
        RAGChat["/api/v1/grievance/{id}/chat"]
        AdminAPI["/api/v1/admin & /history"]
    end

    subgraph ProcessingPipeline ["Processing Engine (CPU Hardware)"]
        OCR["PaddleOCR (PP-OCRv5)\nBilingual Tamil + English"]
        Chunker["Tamil Semantic Chunker\nSentence Boundaries"]
        Embedder["SentenceTransformer\nparaphrase-multilingual-MiniLM-L12-v2"]
        NER["Hybrid Entity Extractor\nRegex + Revenue Master Validator"]
        LLM["Local Qwen 2.5 (Ollama)\nSummarization & Claim Verification"]
    end

    subgraph PostgresStore ["PostgreSQL 16 Enterprise Core (Single Source of Truth)"]
        Relational["Relational Tables\nsources, officers, master_locations"]
        Vector["pgvector (HNSW Index)\ndocument_chunks (384-dim cosine)"]
        FTS["tsvector + GIN Index\nTamil & English Full-Text Search"]
        DocStore["JSONB Documents\nextracted_entities, ai_analysis, draft"]
        Queue["SKIP LOCKED ACID Queue\njob_queue (ocr, vector, ner, ai)"]
        Audit["Partitioned Table\naudit_log (Monthly Partitions)"]
    end

    Desktop --> Upload
    Mobile --> Upload
    Desktop --> RAGChat
    Upload --> Queue
    Queue --> OCR --> Chunker --> Embedder --> Vector
    OCR --> NER --> DocStore
    NER --> LLM --> DocStore
    RAGChat --> Vector
    RAGChat --> FTS
```

### Why Postgres-First?
* **Zero Distributed State Headaches**: No synchronization lag between databases, search engines, and vector stores.
* **ACID Task Queuing**: `SELECT ... FOR UPDATE SKIP LOCKED` guarantees reliable, crash-safe asynchronous background jobs with zero separate queue infrastructure.
* **Hybrid Reciprocal Rank Fusion (RRF)**: Combines dense semantic vectors (`pgvector`) with sparse lexical tokens (`tsvector`) in a single unified SQL query.

---

## ✨ Key Features

* **Tamil-First Optical Character Recognition (OCR)**
  * Optimized PaddleOCR PP-OCRv5 detection and recognition models tuned for Tamil script and cursive signatures.
  * Preserves page numbers, block coordinates, bounding polygons, and confidence scores.

* **Anti-Hallucination Claim Grounding Barrier**
  * Evaluates every extracted grievance claim against raw OCR text.
  * Assigns quantitative `hallucination_score` and `grounding_score` metrics.
  * Enforces Section Officer override if the hallucination risk exceeds `0.20`.

* **Automated DRO Portal Draft Generation**
  * Automatically categorizes grievance types (*Patta Transfer, Encroachment, Road Infrastructure, Old Age Pension, Electricity*).
  * Resolves jurisdictional routing to the exact Block Development Officer (BDO), Tahsildar, or Revenue Divisional Officer (RDO).

* **Air-Gapped & Offline Ready**
  * Fully operational without public internet connectivity.
  * Uses quantized local LLMs (Qwen 2.5 3B / 1.5B via Ollama) and local sentence transformers.

* **Privacy & Statutory Compliance**
  * Automatic regex Aadhaar detection and masking (`XXXX-XXXX-1234`).
  * Immutable, monthly partitioned audit trails recording every officer interaction, query, update, and API dispatch.

* **Wireless QR Mobile Intake**
  * Dynamic, self-expiring session QR codes allow intake staff to photograph physical petitions with a smartphone and stream them directly to the active desktop session via local network WebSocket/HTTP.

* **Interactive RAG Document Chat**
  * Grounded question-answering assistant citing specific page numbers and textual snippets for verification.

---

## 🔬 Deep Dive: Processing Pipeline

When a petition document is submitted, it flows through a five-stage processing pipeline:

```text
[Petition Upload] (PDF / PNG / JPG)
        │
        ├──► 1. Save to FileStore & Compute SHA-256 Hash
        ├──► 2. Insert into `sources` (status: 'uploaded', BYTEA archive)
        │
   [Postgres Queue: FOR UPDATE SKIP LOCKED]
        │
        ├──► Stage A: OCR Router (PP-OCRv5 Tamil Det + Rec)
        │        └── Writes text blocks & tables to `ocr_results`
        │
        ├──► Stage B: Vector Indexing & Semantic Chunking
        │        └── Chunks on Tamil boundaries (கொண்டு, எனவே, ஆகிய)
        │        └── Encodes 384-dim embeddings via MiniLM-L12-v2 into `pgvector`
        │
        ├──► Stage C: Entity Extraction & Validation
        │        └── Extracts: Petitioner, Phone, Address, Survey No, Village
        │        └── Validates against `master_locations` table
        │        └── Redacts PII (Aadhaar masking)
        │
        ├──► Stage D: AI Analysis & Claim Verification
        │        └── Executes Qwen 2.5 with structured JSON schema
        │        └── Computes Hallucination / Grounding scores
        │        └── Auto-populates `grievance_drafts`
        │
        └──► Ready for Officer Inspection & 1-Click DRO Dispatch
```

---

## 🛠️ Tech Stack

### Backend
* **Runtime**: Python 3.11+
* **Framework**: FastAPI (Asynchronous ASGI)
* **ORM & Migrations**: SQLAlchemy 2.0 (AsyncIO), Alembic
* **OCR Engines**: PaddlePaddle PP-OCRv5 (Tamil + English), Surya OCR
* **Embeddings**: HuggingFace `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
* **Local LLM Engine**: Ollama (`qwen2.5:3b`, `qwen2.5:1.5b`)

### Database & Storage
* **Primary Database**: PostgreSQL 16
* **Vector Engine**: `pgvector` extension (HNSW index, Cosine distance)
* **Text Search**: PostgreSQL Full-Text Search (`tsvector`, `tsquery`, GIN indexing)
* **Document & Queue Store**: Native PostgreSQL `JSONB` + `FOR UPDATE SKIP LOCKED`

### Frontend
* **Core**: React 19, JavaScript (ESNext)
* **Build Tool**: Vite 8.2 (Fast Hot Module Replacement & production bundling)
* **Design & Styling**: Tailored Modern Vanilla CSS Design Tokens (Glassmorphism, High-DPI typography, dark-mode ready)
* **Icons**: Lucide React

---

## 📂 Project Structure

```text
GDP_Assistant/
├── assets/
│   └── banner.jpg                     # Platform header banner
├── backend/
│   ├── alembic/
│   │   ├── versions/
│   │   │   └── 001_initial_schema.py  # DDL with pgvector, JSONB, tsvector, partitions
│   │   └── env.py
│   ├── app/
│   │   ├── config.py                  # Pydantic Settings & environment schemas
│   │   ├── dependencies.py            # Session management, JWT auth, audit logging
│   │   ├── main.py                    # FastAPI application initialization & lifecycle
│   │   └── routers/
│   │       ├── grievance.py           # /api/v1/grievance (upload, ocr, draft, push, chat)
│   │       ├── search.py              # /api/v1/search (vector, fulltext, hybrid RRF)
│   │       └── admin.py               # /api/v1/admin (queue status, metrics, master data)
│   ├── core/
│   │   ├── llm_client.py              # Local Ollama / Qwen 2.5 client interface
│   │   └── security.py                # Password hashing, JWT creation & verification
│   ├── models/
│   │   ├── database.py                # Async engine & connection pool
│   │   ├── orm.py                     # SQLAlchemy 2.0 ORM database schema
│   │   └── schemas.py                 # Pydantic v2 validation models
│   ├── services/
│   │   ├── ai_analyzer.py             # Qwen 2.5 summary, classification & claim verification
│   │   ├── dro_bridge.py              # External DRO portal API integration
│   │   ├── entity_extractor.py        # Regex + AI NER + Aadhaar masking + Master DB check
│   │   ├── file_store.py              # Binary file & rendered page storage
│   │   ├── job_queue.py               # PostgreSQL SKIP LOCKED worker implementation
│   │   ├── ocr_router.py              # Hybrid Paddle PP-OCRv5 router
│   │   ├── tamil_chunker.py           # Semantic chunking on Tamil syntactic boundaries
│   │   └── vector_store.py            # pgvector embedding indexing & hybrid RRF search
│   ├── docker-compose.yml             # PostgreSQL 16 + pgvector container definition
│   └── requirements.txt               # Backend Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── audit/                 # Full-page Audit Logs & historical records
│   │   │   ├── layout/                # AppHeader, Sidebar, Modals, Breadcrumbs
│   │   │   ├── upload/                # UploadLanding, ProcessingOverlay, MobileQrModal
│   │   │   └── workspace/             # SummaryChatView, DocumentViewer, FullDetailsForm
│   │   ├── data/                      # Master schemas & fallback definitions
│   │   ├── services/
│   │   │   └── apiService.js          # REST client connecting Frontend to FastAPI
│   │   ├── App.jsx                    # Top-level state machine & view router
│   │   └── index.css                  # Global design system & typography tokens
│   ├── package.json                   # Frontend dependencies
│   └── vite.config.js                 # Vite server, proxy configuration & QR bridge plugin
├── CONTRIBUTING.md                    # Contributor guide & coding standards
├── LICENSE                            # Apache License, Version 2.0
├── run_all.bat                        # Unified launch script (Backend + Frontend)
├── run_backend.bat                    # Standalone FastAPI launcher
└── run_frontend.bat                   # Standalone Vite launcher
```

---

## 📦 Prerequisites & Models Setup

Before launching GDP Assistant, ensure your environment meets the system dependencies and has the required local models installed.

### 1. System Dependencies

| Dependency | Required Version | Verification Command | Purpose |
| :--- | :--- | :--- | :--- |
| **Python** | `3.11.x` – `3.12.x` | `python --version` | Backend API, OCR & ML Pipeline |
| **Node.js** | `18.x` or `20.x` LTS | `node -v` | Frontend Dev Server & Build Tool |
| **npm** | `9.x` or `10.x` | `npm -v` | Package Manager |
| **Docker** | `24.x+` & Compose v2 | `docker compose version` | Containerized PostgreSQL 16 + pgvector |
| **Poppler** | Latest | `pdftoppm -v` | High-fidelity PDF-to-image rasterization |
| **Ollama** | Latest | `ollama --version` | Local Quantized LLM Inference Server |

> [!TIP]
> **Installing Poppler Safely:**
> * **Windows**: Run in PowerShell: `winget install -e --id OSGeo.Poppler` or `choco install poppler`. Ensure the `bin/` directory is added to your System `PATH`.
> * **Ubuntu / Debian**: `sudo apt-get update && sudo apt-get install -y poppler-utils`
> * **macOS**: `brew install poppler`

---

### 2. Required AI / ML Models

GDP Assistant operates with zero reliance on external paid APIs. All models run locally on consumer CPU hardware.

#### A. Large Language Model (Ollama)
The platform uses **Qwen 2.5** for bilingual Tamil/English summarization, entity extraction, and RAG document QA.

1. Install [Ollama](https://ollama.ai) for your operating system.
2. Pull the recommended model (requires ~2.2 GB disk space):
   ```bash
   # Recommended default (Optimal balance of speed & Tamil syntactic accuracy)
   ollama pull qwen2.5:3b

   # Alternative for ultra-lightweight systems (< 8 GB RAM):
   ollama pull qwen2.5:1.5b
   ```
3. Test that Ollama is responding locally:
   ```bash
   curl http://localhost:11434/api/tags
   ```

#### B. Multilingual Semantic Embedding Model
* **Model**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384-dimensional vectors).
* **Download**: Automatically fetched from Hugging Face on the first run and cached locally in `~/.cache/huggingface/hub/`.
* **Offline Pre-Cache Script** *(Optional, for air-gapped environments)*:
  ```bash
  python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"
  ```

#### C. Optical Character Recognition (OCR) Weights
* **Engine**: PaddlePaddle PP-OCRv5 (Text Detection & Tamil Recognition).
* **Weights**: `PP-OCRv5_server_det` + `ta_PP-OCRv5_mobile_rec` + `en_PP-OCRv5_mobile_rec`.
* **Download**: Downloaded automatically by the OCR router on initial petition upload and cached in `~/.paddlex/official_models/`.

---

## 🚀 Getting Started

### System Requirements

* **Operating System**: Windows 10/11, Ubuntu 22.04+, or macOS
* **RAM**: 8 GB minimum (16 GB recommended for concurrent OCR + LLM inference)
* **CPU**: 4 cores minimum (runs purely on CPU without requiring an expensive GPU)

---

### One-Click Startup (Windows)

To start both the FastAPI backend and Vite frontend simultaneously:

```bat
run_all.bat
```

* **Frontend Portal**: Open `http://localhost:5174`
* **FastAPI Backend**: Running at `http://127.0.0.1:8000`
* **API Documentation**: Open `http://127.0.0.1:8000/api/v1/docs`

---

### Manual Step-by-Step Setup

#### Step 1: Start PostgreSQL 16 + pgvector

Start the isolated database container:

```bash
cd backend
docker compose up -d
```

Verify that the database is healthy:
```bash
docker compose ps
```

#### Step 2: Configure Environment Variables

Create your local `.env` file from the provided template:

```bash
cp .env.example .env
```

Default configuration in `.env`:
```ini
# PostgreSQL 16 connection URL
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/gdp_db

# Local Ollama LLM endpoint
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:3b

# Multilingual Sentence Transformer
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# Security & Session
SECRET_KEY=your-secure-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

#### Step 3: Install Backend Packages in a Safe Virtual Environment

Always use an isolated virtual environment to prevent package version conflicts with system Python:

```bash
cd backend

# Create isolated virtual environment
python -m venv .venv

# Activate the virtual environment:
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Windows (Command Prompt):
.venv\Scripts\activate.bat
# On Linux / macOS:
source .venv/bin/activate

# Upgrade pip to latest version
python -m pip install --upgrade pip

# Install pinned dependencies
pip install -r requirements.txt
```

> [!NOTE]
> **CPU vs GPU PyTorch**: `requirements.txt` installs standard PyTorch. For strictly CPU-only production environments to save disk space, install PyTorch with:
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cpu
> ```

#### Step 4: Run Database Migrations & Seed Revenue Master Data

```bash
# Apply Alembic schema migrations (DDL, pgvector extension, HNSW indexes)
alembic upgrade head

# Seed master revenue locations (Erode district taluks, firkas, villages)
python init_db.py
```

#### Step 5: Start the FastAPI Backend Server

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
API Documentation will be live at `http://127.0.0.1:8000/api/v1/docs`.

#### Step 6: Install & Start Frontend

In a separate terminal:

```bash
cd frontend

# Install clean Node dependencies
npm install

# Start Vite development server
npm run dev
```

Open **`http://localhost:5174/`** to access the GDP Assistant dashboard.

---

## 📡 API Reference & Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/grievance/upload` | Uploads PDF/image petition; saves file and enqueues processing pipeline |
| `GET` | `/api/v1/grievance/{id}/status` | Checks pipeline progress (OCR, Chunks, Entities, AI status) |
| `GET` | `/api/v1/grievance/{id}/ocr` | Retrieves all OCR pages, bounding polygons, confidence scores, and tables |
| `GET` | `/api/v1/grievance/{id}/analysis` | Retrieves AI summaries, suggested departments, and hallucination scores |
| `GET` | `/api/v1/grievance/{id}/draft` | Retrieves pre-populated DRO portal draft entry |
| `PUT` | `/api/v1/grievance/draft/{id}` | Updates draft fields following officer review |
| `POST` | `/api/v1/grievance/draft/{id}/approve` | Digitally signs and approves draft with officer credentials |
| `POST` | `/api/v1/grievance/draft/{id}/push-to-dro`| Dispatches approved grievance to the external state DRO portal |
| `POST` | `/api/v1/grievance/{id}/chat` | RAG document chat endpoint with page citation snippets |
| `GET` | `/api/v1/grievance/history` | Lists processed petitions and audit summaries |
| `GET` | `/api/v1/admin/queue-status` | Returns pending, active, and completed task queue counts |

Access full interactive Swagger documentation at **`http://127.0.0.1:8000/api/v1/docs`**.

---

## 🛡️ Security, Anti-Hallucination & Governance

1. **Deterministic Verification Gate**: AI cannot directly write to the live government database. Every draft requires explicit officer review and approval before being pushed to the DRO bridge.
2. **Audit Trail Immutability**: All upload events, officer modifications, queries, and dispatches are logged in the partitioned `audit_log` with timestamps, IP addresses, and officer IDs.
3. **Statutory Aadhaar Protection**: Regex sanitizers redact 12-digit Aadhaar numbers at the memory extraction boundary prior to database storage.
4. **Jurisdictional Master Tables**: Master location records for Erode District (`master_locations`) validate revenue divisions, taluks, and village panchayats to prevent misdirection of public grievances.

---

## 🗺️ Roadmap

- [x] High-accuracy Tamil OCR pipeline (Paddle PP-OCRv5)
- [x] Single-database Postgres-First architecture (`pgvector`, `tsvector`, `JSONB`, `SKIP LOCKED`)
- [x] Local LLM integration with quantitative anti-hallucination verification
- [x] Responsive React dashboard with split-view document inspection
- [x] Real-time wireless mobile camera scan bridge
- [ ] Multi-district location master database expansion (all 38 districts of Tamil Nadu)
- [ ] Automated SMS & WhatsApp status tracking dispatch to citizen petitioners
- [ ] Offline voice-to-text intake for visually challenged petitioners

---

## 🤝 Contributing

Contributions are welcome! Please read our **[CONTRIBUTING.md](CONTRIBUTING.md)** for details on our code of conduct, development setup, and pull request workflow.

1. Fork the project repository.
2. Create a feature branch: `git checkout -b feat/YourFeatureName`
3. Commit your changes: `git commit -m 'feat(component): descriptive commit message'`
4. Push to the branch: `git push origin feat/YourFeatureName`
5. Open a Pull Request.

---

## 📄 License

This project is licensed under the **Apache License, Version 2.0**. See the [LICENSE](LICENSE) file for full license text.

```text
Copyright 2026 GDP Assistant Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
