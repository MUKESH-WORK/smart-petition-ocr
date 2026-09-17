# 🏛️ GDP Assistant: AI-Powered Grievance Redressal & Digitization Platform

<div align="center">

![GDP Assistant Banner](assets/banner.jpg)

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=for-the-badge&logo=apache)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI: Modern](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React: 19](https://img.shields.io/badge/React-19.0-61DAFB.svg?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL: 16 + pgvector](https://img.shields.io/badge/PostgreSQL-16_%7C_pgvector-4169E1.svg?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Ollama: Local LLM](https://img.shields.io/badge/Ollama-Qwen_2.5-black.svg?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.ai)

</div>

<p align="center">
  <strong>An enterprise-grade, offline-capable civic intelligence system engineered for District Revenue Officers (DRO) to digitize, verify, classify, and route handwritten and printed Tamil grievance petitions in seconds on consumer hardware.</strong>
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#%EF%B8%8F-system-architecture)
- [Tech Stack](#%EF%B8%8F-tech-stack)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Quickstart: Clone & Run](#-quickstart-clone--run)
  - [Step 1: Clone the Repository](#step-1-clone-the-repository)
  - [Step 2: Setup Environment Configuration](#step-2-setup-environment-configuration)
  - [Step 3: Launch Application](#step-3-launch-application)
    - [Method 1: One-Click Native Launch (Recommended)](#method-1-one-click-native-launch-recommended)
    - [Method 2: Docker Compose (All-in-One)](#method-2-docker-compose-all-in-one)
    - [Method 3: Manual Developer Setup](#method-3-manual-developer-setup)
- [Configuration Reference](#%EF%B8%8F-configuration-reference)
- [Verification & Testing](#-verification--testing)
- [Security & Governance](#-security--governance)
- [License](#-license)

---

## 💡 Overview

During weekly **Grievance Day Petition (GDP)** sessions at district collectorates across Tamil Nadu, thousands of citizens submit handwritten and printed petitions. Revenue officers typically face data entry bottlenecks, lost tracking metadata, and delays in routing grievances to the appropriate taluks, firkas, and departments.

**GDP Assistant** transforms this process into an automated, fault-tolerant workflow:
1. **Wireless Mobile Intake**: Scan multi-page petitions directly using a mobile phone camera paired via local Wi-Fi QR bridge.
2. **Deep Optical Character Recognition (OCR)**: Extracts complex handwritten Tamil typography using Datalab Chandra OCRv2 with local PaddleOCR and OpenCV adaptive filters as offline fallback.
3. **Deterministic Entity Extraction & PII Redaction**: Extracts petitioner names, phone numbers, door numbers, revenue villages, and survey numbers while automatically redacting Aadhaar numbers (`XXXX-XXXX-1234`).
4. **Cognitive Multi-Page Analysis**: Analyzes multi-page petitions (header, body narrative, prayer, and signatures) without dropping critical details.
5. **CM Helpline Taxonomy Alignment**: Matches grievances dynamically against 40 official departments and 1,862 sub-types from the Tamil Nadu CM Helpline taxonomy.
6. **Direct DRO Portal Bridge**: Enables revenue officers to review, edit, approve, and dispatch petitions directly to the state grievance redressal system.

---

## ✨ Key Features

- **Split Dual-Panel Workspace**: View the high-resolution scanned petition on the left alongside the AI-assisted draft form, metadata editor, and interactive chat on the right.
- **Cognitive Document Chat**: Ask questions in Tamil or English grounded strictly in petition text with instant answer verification.
- **Mobile QR Capture**: Intake staff scan a QR code on their smartphone to upload multi-page petitions directly to the desktop workspace.
- **Editable Officer Profile**: Revenue officers can manage their identity, designation, department, and taluk jurisdictions directly from the navigation bar.
- **Anti-Hallucination Barrier**: Automatically cross-references extracted claims against raw OCR text chunks and flags unverified information.
- **Formal Administrative Tamil Summaries**: Enforces standard third-person administrative Tamil summaries (`மனுதாரர் [பெயர்] ... கோரியுள்ளார்`) adhering to official collectorate conventions.

---

## 🏗️ System Architecture

GDP Assistant is architected under the **Postgres-First Principle**: A single, hardened PostgreSQL 16 instance satisfies all persistence, vector indexing, full-text search, and queue management requirements.

```mermaid
flowchart TB
    subgraph ClientLayer ["Client & Ingestion Layer"]
        Desktop["Desktop Admin Portal\n(React 19 + Vite)"]
        Mobile["Mobile Camera Intake\n(WebRTC / Local QR Bridge)"]
    end

    subgraph APILayer ["FastAPI Async Gateway (Port 8000)"]
        Auth["JWT & Officer Session Guard"]
        Upload["Grievance Ingestion API"]
        RAGChat["Cognitive RAG Document Chat"]
        AdminAPI["Admin & Audit Services"]
    end

    subgraph ProcessingPipeline ["Processing Engine"]
        OCR["Hybrid OCR Router\nChandra OCRv2 / PaddleOCR"]
        Chunker["Tamil Semantic Chunker\nSentence Boundaries"]
        Embedder["SentenceTransformer\nparaphrase-multilingual-MiniLM-L12-v2"]
        NER["Hybrid Entity Extractor\nRegex + Revenue Master Validator"]
        LLM["Cognitive LLM Engine (Ollama / Gemini)\nSummarization & Claim Verification"]
    end

    subgraph PostgresStore ["PostgreSQL 16 Enterprise Core"]
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

---

## 🛠️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | React 19, Vite, Lucide Icons, Vanilla CSS | Officer workspace with live OCR preview and draft editor |
| **Backend** | FastAPI, Pydantic v2, Python 3.11+ | Asynchronous REST gateway and queue orchestration |
| **Database** | PostgreSQL 16 + pgvector *(or Embedded SQLite)* | Relational storage, vector search, and queue tables |
| **Primary OCR** | Datalab Chandra OCRv2 | High-accuracy Tamil handwriting transcription |
| **Offline OCR** | PaddleOCR (PP-OCRv5) + OpenCV | Offline local fallback for printed & scanned text |
| **Embeddings** | `paraphrase-multilingual-MiniLM-L12-v2` | 384-dimensional dense multilingual embeddings |
| **Cognitive LLM** | Qwen 2.5 (via Ollama) or Gemini API | Local or cloud-assisted administrative reasoning |

---

## 📂 Project Structure

```
smart-petition-ocr/
├── backend/                    # FastAPI backend service
│   ├── alembic/                # Database migrations
│   ├── app/                    # Application factories, routers, config
│   ├── core/                   # Security, LLM client interfaces
│   ├── data/                   # CM Helpline taxonomy & reference data
│   ├── models/                 # SQLAlchemy ORM models & Pydantic schemas
│   ├── services/               # OCR, NER, chunking, vector store, AI analysis
│   ├── tests/                  # Pytest automated test suites
│   ├── requirements.txt        # Python package dependencies
│   └── Dockerfile              # Backend container definition
├── frontend/                   # React 19 single-page application
│   ├── src/                    # Components, state management, styles
│   ├── package.json            # Node.js dependencies
│   └── Dockerfile              # Frontend container definition
├── assets/                     # Platform banners and UI assets
├── docker-compose.yml          # Unified container configuration
├── run_all.bat                 # Windows one-click start script
├── run_all.sh                  # Linux / macOS start script
├── .env.example                # Unified environment configuration template
└── README.md                   # Project documentation
```

---

## 📦 Prerequisites

Ensure you have the following installed on your system:

1. **Python 3.11+** ([Download Python](https://python.org))
2. **Node.js 18+ LTS** ([Download Node.js](https://nodejs.org))
3. **Local LLM via Ollama** *(Optional if using Gemini API)*:
   ```bash
   ollama pull qwen2.5:3b
   ```
4. **Docker Desktop** *(Optional, for containerized execution)*

---

## 🚀 Quickstart: Clone & Run

### Step 1: Clone the Repository

```bash
git clone https://github.com/MUKESH-WORK/smart-petition-ocr.git
cd smart-petition-ocr
```

### Step 2: Setup Environment Configuration

Copy the example environment file:

```bash
# Windows (PowerShell / Command Prompt)
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Edit `.env` to configure your preferred settings:
- Set `CHANDRA_API_KEY` if using Datalab Chandra OCR API.
- Set `GEMINI_API_KEY` or configure local `OLLAMA_BASE_URL` (default: `http://localhost:11434`).

---

### Step 3: Launch Application

Choose any of the following methods to run the platform:

#### Method 1: One-Click Native Launch (Recommended)

**On Windows:**
```bat
run_all.bat
```

**On Linux / macOS:**
```bash
chmod +x run_all.sh run_backend.sh run_frontend.sh
./run_all.sh
```

---

#### Method 2: Docker Compose (All-in-One)

Start all services (PostgreSQL with pgvector, FastAPI Backend, and React Frontend) with a single command:

```bash
docker compose up --build -d
```

---

#### Method 3: Manual Developer Setup

If you prefer to run backend and frontend in separate terminals:

**Terminal 1 — Backend:**
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv

# Windows activation:
.venv\Scripts\activate
# Linux/macOS activation:
source .venv/bin/activate

# Install dependencies and initialize database
pip install -r requirements.txt
python init_db.py

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend

# Install Node.js dependencies
npm install

# Start Vite development server
npm run dev
```

---

### 🌐 Accessing the Platform

Once launched, open your web browser:
- **Frontend Portal**: `http://localhost:5174` (or `http://localhost:3000` via Docker)
- **Backend Service**: `http://localhost:8000`
- **Interactive Documentation**: `http://localhost:8000/docs`

---

## ⚙️ Configuration Reference

Key environment variables available in `.env`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/dro_grievance` | PostgreSQL database connection string |
| `CHANDRA_API_KEY` | `""` | Datalab Chandra OCR API key for Tamil handwriting recognition |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama service endpoint for local LLM inference |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Default Ollama model name |
| `GEMINI_API_KEY` | `""` | Optional Google Gemini API key |
| `JWT_SECRET` | *(Auto-generated)* | Secret key for officer session tokens |
| `UPLOAD_DIR` | `uploads` | Directory for temporary petition image storage |

---

## 🧪 Verification & Testing

Execute the backend automated test suite:

```bash
cd backend
pytest tests/test_production_pipeline.py -v
```

Validate frontend production build:

```bash
cd frontend
npm run build
```

---

## 🛡️ Security & Governance

- **Automatic PII Redaction**: All 12-digit Aadhaar numbers are masked to `XXXX-XXXX-1234` prior to database persistence.
- **Anti-Hallucination Claim Grounding**: All LLM claims are verified against raw OCR text chunks. Unverified items are highlighted for officer review.
- **Master Location Validation**: Geographic entities (Village, Firka, Taluk, District) are validated against official revenue administration records.
- **Officer-in-the-Loop Redressal**: Petitions cannot be pushed to the state DRO system without digital officer approval (`officer_approved == True`).
- **Immutable Audit Logging**: Every transaction, edit, and dispatch event is logged in partitioned audit tables.

---

## 📄 License

This project is licensed under the **Apache License, Version 2.0**. See the [LICENSE](LICENSE) file for complete details.
