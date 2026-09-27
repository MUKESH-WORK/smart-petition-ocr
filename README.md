# 🏛️ GDP Assistant: AI-Powered Grievance Redressal & Digitization Platform

<div align="center">

![GDP Assistant Banner](assets/banner.jpg)

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=for-the-badge&logo=apache)](LICENSE)
[![Code of Conduct](https://img.shields.io/badge/Contributor-Covenant_v2.1-4baaaa.svg?style=for-the-badge)](CODE_OF_CONDUCT.md)
[![Contributing](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg?style=for-the-badge)](CONTRIBUTING.md)
[![Security Policy](https://img.shields.io/badge/Security-Policy-red.svg?style=for-the-badge)](SECURITY.md)
[![Deployment Guide](https://img.shields.io/badge/Deployment-Procedures-orange.svg?style=for-the-badge)](DEPLOYMENT.md)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI: Modern](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React: 19](https://img.shields.io/badge/React-19.0-61DAFB.svg?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![pgvector / SQLite Vector](https://img.shields.io/badge/Vector-pgvector_%7C_SQLite-4169E1.svg?style=for-the-badge)](https://github.com/pgvector/pgvector)

</div>

<p align="center">
  <strong>An enterprise-grade, offline-capable civic intelligence system engineered for District Revenue Officers (DRO) to digitize, verify, classify, and route handwritten and printed Tamil grievance petitions in seconds on consumer hardware.</strong>
</p>

---

## 📌 Repository Description & Goals

> **Description**: *An offline-first, AI-driven grievance digitization, OCR processing, and administrative routing assistant for District Collectorates and Revenue Administration in Tamil Nadu.*

### Core Objectives
1. **Zero Citizen Bottleneck**: Eliminate long queues and hours of manual transcription during weekly Grievance Day Petition (GDP) sessions.
2. **High-Accuracy Tamil OCR**: Decipher complex handwritten and printed Tamil petitions using deep neural OCR (Datalab Chandra OCRv2) with offline PaddleOCR fallbacks.
3. **Automated CM Helpline Taxonomy Alignment**: Accurately classify grievances across **40 Department Groups**, **1,027 Grievance Types**, and **1,861 Sub-Types** with responsible officer designation.
4. **Authoritative Administrative Grounding**: Route petitions accurately across **6 Administrative Tiers** (Corporation Zones, Taluks, Firkas, Municipalities, Revenue Villages, and Corporation Wards) with zero hallucination.
5. **Absolute Privacy & Data Sovereignty**: Automatic client-side masking of Aadhaar numbers (`XXXX-XXXX-1234`) and zero reliance on proprietary cloud APIs for core operations.
6. **Real-Time Bilingual Interface**: Dynamic LLM-powered English ↔ Tamil translation across the entire UI — no hardcoded dictionaries.

---

## 📋 Table of Contents

- [🌟 Fresh Server 1-Command Deployment (Fastest)](#-fresh-server-1-command-deployment-fastest)
- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#%EF%B8%8F-system-architecture)
- [Step-by-Step Manual Setup Guide (Clone & Run)](#-step-by-step-manual-setup-guide-clone--run)
  - [Prerequisites](#1-prerequisites)
  - [Step 1: Clone Repository](#step-1-clone-repository)
  - [Step 2: Environment Configuration (.env & API Keys)](#step-2-environment-configuration-env--api-keys)
  - [Step 3: Setup Local LLM Inference (Ollama)](#step-3-setup-local-llm-inference-ollama)
  - [Step 4: Setup Database (Docker Desktop or SQLite)](#step-4-setup-database-docker-desktop-or-sqlite)
  - [Step 5: Backend Setup & Run (Terminal 1)](#step-5-backend-setup--run-terminal-1)
  - [Step 6: Frontend Setup & Run (Terminal 2)](#step-6-frontend-setup--run-terminal-2)
  - [Step 7: 1-Click Automated Launch Alternatives](#step-7-1-click-automated-launch-alternatives)
  - [Step 8: Pre-Configured Test Accounts](#step-8-pre-configured-test-accounts)
- [Intake Channels (21 Sources)](#-intake-channels-21-sources)
- [Administrative Hierarchy & Taxonomy Structure](#-administrative-hierarchy--taxonomy-structure)
- [Role-Based Access Control](#-role-based-access-control)
- [Dynamic Bilingual Translation](#-dynamic-bilingual-translation)
- [Database Management & Migration](#-database-management--migration)
- [Configuration Reference](#%EF%B8%8F-configuration-reference)
- [Project Structure](#-project-structure)
- [Troubleshooting & Diagnostics](#-troubleshooting--diagnostics)
- [Security & Governance](#-security--governance)
- [License](#-license)

---

## 🌟 Fresh Server 1-Command Deployment (Fastest)

> **For a completely fresh Windows server with only Git and Docker Desktop installed.**

If Ollama is not installed and the model is not downloaded, you can set up and start the entire GDP Assistant platform automatically:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_host.ps1
```

### What `setup_host.ps1` does automatically:
1. **Verifies Docker Desktop**: Confirms Docker Engine daemon is active and responsive.
2. **Installs Ollama**: Automatically detects and installs Ollama via `winget` if missing on the host.
3. **Starts Ollama Daemon**: Launches `ollama serve` in the background and verifies `http://127.0.0.1:11434`.
4. **Pulls AI Model**: Automatically downloads `qwen2.5:3b-instruct` (~1.9 GB) if not already installed.
5. **Generates `.env`**: Creates `.env` from `.env.example` if missing.
6. **Builds & Launches Containers**: Runs `docker compose up -d --build` (PostgreSQL 16 + All-in-One GDP Assistant).
7. **Verifies Health**: Polls `http://localhost/health` until all services are healthy and ready.

After completion, navigate to **`http://localhost`** in your browser.

---

---

## 💡 Overview

During weekly **Grievance Day Petition (GDP)** sessions at district collectorates across Tamil Nadu, thousands of citizens submit handwritten and printed petitions. Revenue officers typically face data entry bottlenecks, lost tracking metadata, and delays in routing grievances to the appropriate taluks, firkas, and departments.

**GDP Assistant** transforms this process into an automated, fault-tolerant workflow:
1. **Wireless Mobile Intake**: Scan multi-page petitions directly using a mobile phone camera paired via local Wi-Fi QR bridge.
2. **Deep Optical Character Recognition (OCR)**: Extracts complex handwritten Tamil typography using Datalab Chandra OCRv2 with local PaddleOCR and OpenCV adaptive filters as offline fallback.
3. **Deterministic Entity Extraction & PII Redaction**: Extracts petitioner names, phone numbers, door numbers, revenue villages, and survey numbers while automatically redacting Aadhaar numbers (`XXXX-XXXX-1234`).
4. **Cognitive Multi-Page Analysis**: Analyzes multi-page petitions (header, narrative, prayer, and signatures) without dropping critical details.
5. **CM Helpline Taxonomy Alignment**: Matches grievances dynamically against 40 official departments and 1,861 sub-types from the Tamil Nadu CM Helpline taxonomy with 384-dimensional vector embeddings.
6. **Direct DRO Portal Bridge**: Enables revenue officers to review, edit, approve, and dispatch petitions directly to the state grievance redressal system.
7. **Dynamic Bilingual Translation**: Real-time LLM-powered English ↔ Tamil translation for the entire interface — no hardcoded strings.

---

## ✨ Key Features

| Feature | Description |
| :--- | :--- |
| **Split Dual-Panel Workspace** | View scanned petitions alongside the AI-assisted draft form, metadata editor, and interactive chat |
| **Cognitive Document Chat** | Ask questions in Tamil or English grounded strictly in petition text with instant answer verification |
| **Mobile QR Capture** | Intake staff scan a QR code on their smartphone to upload multi-page petitions directly |
| **21 Intake Channels** | Comprehensive ingestion from CM Helpline, DRO Portal, Social Media, Public Hearing, and 17 more official sources |
| **Dynamic Translation** | Real-time LLM-based English ↔ Tamil translation across the entire UI (no hardcoded dictionaries) |
| **Role-Based Access Control** | Admin-only profile editing; department users get read-only access to system data |
| **Authoritative Taxonomy** | Search, filter, add, edit, and delete mappings across all 40 departments with real-time vector indexing |
| **Administrative Hierarchy** | Real-time management across all district tiers (Zones, Taluks, Firkas, Municipalities, Villages, Wards) |
| **Dual Database Architecture** | Seamlessly switches between SQLite (offline) and PostgreSQL 16 + pgvector (enterprise) with live telemetry |
| **Semantic Cache** | LLM response deduplication with configurable similarity threshold to reduce redundant API calls |
| **Anti-Hallucination Barrier** | Cross-references extracted claims against raw OCR text chunks and flags unverified information |
| **Formal Tamil Summaries** | Enforces standard third-person administrative Tamil (`மனுதாரர் [பெயர்] ... கோரியுள்ளார்`) |
| **Perceptual Deduplication** | Prevents duplicate petition ingestion using exact hash + perceptual hash (pHash) comparison |

---

## 🏗️ System Architecture

GDP Assistant operates with a decoupled, resilient architecture supporting both offline single-node setups and enterprise clustered deployments:

```mermaid
flowchart TB
    subgraph ClientLayer ["Client & Ingestion Layer"]
        Desktop["Desktop Admin Portal\n(React 19 + Vite)"]
        Mobile["Mobile Camera Intake\n(WebRTC / Local QR Bridge)"]
        Channels["21 Intake Channels\n(CM Helpline, DRO Portal, etc.)"]
    end

    subgraph APILayer ["FastAPI Async Gateway (Port 8000)"]
        Auth["JWT & Officer Session Guard\n(Role-Based Access)"]
        Upload["Grievance Ingestion API"]
        RAGChat["Cognitive RAG Document Chat"]
        AdminAPI["Admin & Taxonomy Services"]
        TranslateAPI["Dynamic Translation Engine"]
        Telemetry["Database Health Telemetry"]
    end

    subgraph ProcessingPipeline ["Processing Engine"]
        OCR["Hybrid OCR Router\nChandra OCRv2 / PaddleOCR"]
        Chunker["Tamil Semantic Chunker\nSentence Boundaries"]
        Embedder["SentenceTransformer\nparaphrase-multilingual-MiniLM-L12-v2"]
        NER["Hybrid Entity Extractor\nRegex + Revenue Master Validator"]
        LLM["Cognitive LLM Engine (Ollama / Qwen)\nSummarization, Verification & Translation"]
        Cache["Semantic Cache\n(LRU + Vector Similarity)"]
    end

    subgraph StorageLayer ["Dual Storage Engine (SQLite / PostgreSQL)"]
        AdminDB["Admin Database (dro_admin.db / PostgreSQL)\n40 Depts · 1,861 Taxonomy Mappings · 477 Hierarchy Units"]
        UserDB["User Database (dro_user.db / PostgreSQL)\nPetitions · OCR Chunks · Vector Index · Drafts · Audit Logs"]
    end

    ClientLayer --> APILayer
    APILayer --> ProcessingPipeline
    ProcessingPipeline --> StorageLayer
```

---

## 🚀 Step-by-Step Manual Setup Guide (Clone & Run)

Follow these manual steps to set up and run the entire platform from scratch on a new machine.

### 1. Prerequisites

Before starting, ensure you have the following installed on your machine:

| Prerequisite | Minimum Version | Purpose | Download Link |
| :--- | :--- | :--- | :--- |
| **Python** | `3.11.x` | Backend API, ML pipeline, OCR & embeddings | [python.org/downloads](https://www.python.org/downloads/) |
| **Node.js & npm** | Node `18.x+` (npm `9+`) | React 19 + Vite frontend user interface | [nodejs.org](https://nodejs.org/) |
| **Git** | `2.x+` | Source code version control | [git-scm.com](https://git-scm.com/) |
| **Ollama** *(Recommended)* | Latest | Local offline AI inference & bilingual translation | [ollama.com](https://ollama.com/) |
| **Docker Desktop** *(Optional)* | Latest | PostgreSQL 16 + pgvector containerized database | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |

> [!TIP]
> **No Docker or GPU? No problem!** The application includes an embedded SQLite vector engine and local CPU fallback modes, allowing full functionality on standard laptops without Docker or cloud keys.

---

### Step 1: Clone Repository

Open your terminal or command prompt and clone the repository:

```bash
git clone https://github.com/MUKESH-WORK/smart-petition-ocr.git
cd smart-petition-ocr
```

---

### Step 2: Environment Configuration (.env & API Keys)

Copy the provided environment template to create your local `.env` configuration file:

```bash
# On Linux / macOS:
cp .env.example .env

# On Windows (PowerShell):
Copy-Item .env.example .env

# On Windows (Command Prompt):
copy .env.example .env
```

#### Understanding & Configuring Keys in `.env`:

1. **Datalab OCR API Key (`DATALAB_API_KEY`)**:
   - **What it does**: Powers Datalab Chandra OCRv2, delivering state-of-the-art recognition for complex, cursive handwritten Tamil petitions.
   - **How to get it**:
     1. Visit [https://www.datalab.to](https://www.datalab.to) and create a free account.
     2. Open your account API Dashboard.
     3. Copy your API Key and paste it into `.env`:
        ```env
        OCR_PROVIDER=datalab
        DATALAB_API_KEY=your_actual_datalab_api_key_here
        ```
   - **Offline / Zero-Cost Fallback**: If you leave `DATALAB_API_KEY` empty or unset, the system automatically falls back to the embedded **PaddleOCR** engine with OpenCV preprocessing filters at zero cost with 100% offline capability.

2. **Security Secret (`SECRET_KEY`)**:
   - Set a custom 32+ character random string to sign JWT tokens for revenue officer sessions:
     ```env
     SECRET_KEY=my-super-secret-jwt-key-change-in-production-2026
     ```

3. **Database Selection (`USE_SQLITE` vs PostgreSQL)**:
   - **Option A (SQLite - Instant / Zero Setup)**:
     ```env
     USE_SQLITE=true
     ```
   - **Option B (PostgreSQL 16 + pgvector - Enterprise / Docker)**:
     ```env
     USE_SQLITE=false
     POSTGRES_USER=dro_user
     POSTGRES_PASSWORD=dro_password_2026
     POSTGRES_HOST=localhost
     POSTGRES_PORT=5432
     POSTGRES_DB=dro_grievance_db
     DATABASE_URL=postgresql+asyncpg://dro_user:dro_password_2026@localhost:5432/dro_grievance_db
     DATABASE_SYNC_URL=postgresql://dro_user:dro_password_2026@localhost:5432/dro_grievance_db
     ```

---

### Step 3: Setup Local LLM Inference (Ollama)

GDP Assistant uses local LLMs for cognitive document analysis, petition summarization, anti-hallucination verification, and dynamic English ↔ Tamil translation.

1. **Install Ollama**:
   - Download and install Ollama from [https://ollama.com/download](https://ollama.com/download).

2. **Start the Ollama Server**:
   ```bash
   ollama serve
   ```
   *(On Windows/macOS, Ollama runs automatically in the system tray).*

3. **Pull the Required Models**:
   Open a terminal and run:
   ```bash
   # 1. Primary Reasoning & Translation LLM (Qwen 2.5 3B Instruct)
   ollama run qwen2.5:3b-instruct

   # 2. Vector Embedding Engine
   ollama pull nomic-embed-text:latest
   ```

---

### Step 4: Setup Database (Docker Desktop or SQLite)

Choose one of the two database setup options:

#### Option A: PostgreSQL 16 + pgvector via Docker Desktop (Recommended for Production)
1. Launch **Docker Desktop** on your computer.
2. In the `smart-petition-ocr` root directory, start the PostgreSQL container:
   ```bash
   docker compose up -d postgres
   ```
3. Check that the container is healthy:
   ```bash
   docker ps
   ```

#### Option B: Offline Embedded SQLite (Zero External Software Required)
- Simply ensure `USE_SQLITE=true` in your `.env` file (or let the backend automatically activate SQLite if PostgreSQL is not running).
- Database files (`dro_admin.db` and `dro_user.db`) will be automatically initialized in `backend/temp_cache/`.

---

### Step 5: Backend Setup & Run (Terminal 1)

1. **Navigate to the `backend` directory:**
   ```bash
   cd backend
   ```

2. **Create a Python 3.11 Virtual Environment:**
   ```bash
   # Windows:
   py -3.11 -m venv .venv

   # Linux / macOS:
   python3.11 -m venv .venv
   ```

3. **Activate the Virtual Environment:**
   ```bash
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1

   # Windows (Command Prompt):
   .venv\Scripts\activate.bat

   # Linux / macOS:
   source .venv/bin/activate
   ```

4. **Install Python Dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Seed the Authoritative Government Database:**
   Construct the complete database from the official government taxonomy PDF (`backend/data/government_taxonomy.pdf`):
   ```bash
   python scripts/manage_db.py seed-fresh
   ```
   *This seeds all 40 departments, 1,861 grievance taxonomy mappings, and 477 administrative hierarchy units.*

6. **Start the FastAPI Backend Server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

7. **Verify Backend Status**:
   - Backend API Root: [`http://localhost:8000/`](http://localhost:8000/)
   - Interactive Swagger API Docs: [`http://localhost:8000/api/v1/docs`](http://localhost:8000/api/v1/docs)
   - Service Health Telemetry: [`http://localhost:8000/api/v1/health`](http://localhost:8000/api/v1/health)

---

### Step 6: Frontend Setup & Run (Terminal 2)

Open a **second terminal window** and follow these steps:

1. **Navigate to the `frontend` directory:**
   ```bash
   cd smart-petition-ocr/frontend
   ```

2. **Install Node.js Packages:**
   ```bash
   npm install
   ```

3. **Start the Frontend Development Server:**
   ```bash
   npm run dev
   ```

4. **Access the Application**:
   Open your browser and navigate to:
   - **DRO Civil Desk Portal**: [`http://localhost:5173`](http://localhost:5173) (or `http://localhost:5174`)

---

### Step 7: 1-Click Automated Launch Alternatives

For convenience, you can also use one of the automated startup scripts:

#### Windows 1-Click:
- **First-time setup**: Double-click `setup.bat`
- **Launch all services**: Double-click `run_all.bat`

#### Unified Python CLI Launcher:
```bash
# 1. Run full environment setup & dependency check:
python run.py --setup

# 2. Check system health & diagnostics:
python run.py --doctor

# 3. Launch both backend & frontend concurrently:
python run.py
```

#### Full Docker Compose (All Containers):
```bash
docker compose up -d
```

---

### Step 8: Pre-Configured Test Accounts

The platform comes pre-seeded with official revenue officer roles:

| Officer Name | Officer ID | Role | Permissions |
| :--- | :--- | :--- | :--- |
| **District Collector** | `ADM-ERODE-001` | **District Administrator** | Full Admin, Profile Editing, Taxonomy & Hierarchy Management |
| **District Revenue Officer (DRO)** | `DRO-ERODE-001` | **District Administrator** | Full Admin, Profile Editing, Petition Approval & Dispatch |
| **Sub-Collector / RDO** | `RDO-ERODE-001` | **Department User** | Petition Review, Verification, View-Only System Data |
| **Tahsildar (Erode)** | `TAH-ERD-001` | **Field Officer** | Petition Review, Field Verification |
| **Tahsildar (Bhavani)** | `TAH-BHV-001` | **Field Officer** | Petition Review, Field Verification |

---

## 📡 Intake Channels (21 Sources)

The system supports ingestion from **21 official grievance intake channels**, aligned with Tamil Nadu CM Helpline and District Administration workflows:

| # | Channel | Category | Description |
| :---: | :--- | :--- | :--- |
| 1 | CM Helpline 1100 (Phone Call) | Helpline | Voice transcriptions from the 1100 state call centre |
| 2 | CM Helpline App | Digital | Citizen mobile app submissions |
| 3 | CM Helpline Web Portal | Digital | Online state portal submissions |
| 4 | CM Special Cell | Helpline | Direct petitions addressed to the Chief Minister's Cell |
| 5 | District Collector Petition Day (GDP) | Walk-In | Weekly Monday grievance day submissions |
| 6 | DRO / RDO Direct Petition | Walk-In | Petitions submitted directly to Revenue Officers |
| 7 | Sub-Collector Office | Walk-In | Revenue division intake desks |
| 8 | Tahsildar Office Walk-In | Walk-In | Taluk-level citizen submissions |
| 9 | MLA / MP Recommendation | Referral | Formal letters and constituent grievance referrals |
| 10 | Revenue Divisional Office (RDO) | Government | Official inter-departmental transfers |
| 11 | E-Sevai Centre (CSC) | Digital | Common Service Centre kiosk submissions |
| 12 | Social Media (Twitter/X, Facebook) | Social Media | Social media grievance handles & tagging |
| 13 | WhatsApp Official Channel | Digital | Verified collectorate citizen WhatsApp channel |
| 14 | Email Petition | Digital | Official district collectorate email submissions |
| 15 | Post / Speed Post / Courier | Mail | Physical mailed grievance petitions |
| 16 | Public Hearing (Makkal Durbar) | Walk-In | Village camp & public grievance outreach sessions |
| 17 | RTI Application (Forwarded) | Government | Petitions routed through RTI channels |
| 18 | Court Order / Tribunal Directive | Legal | Judicial directives requiring administrative action |
| 19 | NHRC / SHRC Referral | Legal | Human rights commission grievance notices |
| 20 | Transferred from Other District | Government | Inter-district administrative transfers |
| 21 | NGO / Civil Society Referral | Referral | Non-governmental organization constituent cases |

---

## 🏛️ Administrative Hierarchy & Taxonomy Structure

The system is pre-grounded with the official revenue hierarchy and CM Helpline grievance taxonomy for Erode District:

### 1. Administrative Hierarchy (477 Units)
| Administrative Tier | Count | Description / Coverage |
| :--- | :---: | :--- |
| **Corporation Zones** | **4** | Zone 1 (Suriyampalayam), Zone 2 (Periyasemur), Zone 3 (Surampatti), Zone 4 (Kasipalayam) |
| **Taluks** | **9** | Erode, Kodumudi, Modakkurichi, Perundurai, Anthiyur, Bhavani, Gobichettipalayam, Sathyamangalam, Thalavadi |
| **Revenue Firkas** | **33** | Revenue firkas spanning Erode and Gobichettipalayam revenue divisions |
| **Municipalities / Corp** | **5** | Erode City Municipal Corporation, Bhavani, Gobichettipalayam, Sathyamangalam, Punjai Puliampatti |
| **Revenue Villages** | **375** | Complete official village revenue roster mapped to taluks & firkas |
| **Corporation Wards** | **60** | Wards 1 through 60 with Tamil names and localized postal codes |

### 2. CM Helpline Grievance Taxonomy (1,861 Mappings across 40 Departments)
- **Highest Volume Groups**:
  - *Health and Family Welfare (`HEALTH`)*: 114 sub-types across 58 grievance types
  - *Revenue and Disaster Management (`REV`)*: 110 sub-types across 37 grievance types
  - *Municipal Administration and Water Supply (`MAWS`)*: 92 sub-types across 36 grievance types
  - *Rural Development and Panchayat Raj (`RDPR`)*: 90 sub-types across 23 grievance types
  - *Home, Prohibition and Excise (`HOMEEXE`)*: 84 sub-types across 69 grievance types
  - *Welfare of Differently Abled Persons (`DIFFABLE`)*: 80 sub-types across 17 grievance types

---

## 🔐 Role-Based Access Control

| Role | Profile Edit | Taxonomy Admin | Petition Processing | System Config |
| :--- | :---: | :---: | :---: | :---: |
| **District Administrator** (Admin) | ✅ | ✅ | ✅ | ✅ |
| **Department User** | ❌ (View Only) | ❌ | ✅ | ❌ |
| **Field Officer** | ❌ (View Only) | ❌ | ✅ | ❌ |

---

## 🌐 Dynamic Bilingual Translation

The entire UI supports real-time English ↔ Tamil translation powered by the LLM engine:
- **No hardcoded dictionaries** — all translations are generated dynamically by the translation engine.
- **LRU Cache** on the server side prevents redundant LLM calls for previously translated text.
- **Batch translation** support for translating multiple UI elements in a single API request.
- **Tamil typography rendering** uses dedicated fonts (`Noto Sans Tamil`, `Latha`, `Tamil Sangam MN`) with proper Unicode handling.

---

## 💾 Database Management & Migration

Use the included `scripts/manage_db.py` CLI for all database operations:

```bash
# View active database counts and table statistics
python scripts/manage_db.py stats

# Export a compressed database bundle (tar.gz)
python scripts/manage_db.py export --output gdp_database_bundle.tar.gz

# Import a database bundle onto a new system
python scripts/manage_db.py import --input gdp_database_bundle.tar.gz

# Seed fresh directly from source government PDF (zero external files required)
python scripts/manage_db.py seed-fresh

# Migrate active SQLite database to PostgreSQL + pgvector
python scripts/manage_db.py sync-to-postgres --postgres-url "postgresql+asyncpg://dro_user:dro_password_2026@localhost:5432/dro_grievance_db"
```

---

## ⚙️ Configuration Reference

All environment variables are documented in [`.env.example`](.env.example):

| Variable | Default | Description |
| :--- | :--- | :--- |
| `USE_SQLITE` | `false` | `true` for offline SQLite mode; `false` for PostgreSQL 16 |
| `DATABASE_URL` | `postgresql+asyncpg://...` | User & grievance database connection URL |
| `SECRET_KEY` | *(required)* | JWT signing secret for officer sessions |
| `OCR_PROVIDER` | `datalab` | OCR engine (`datalab` for cloud Chandra / `paddleocr` for offline) |
| `DATALAB_API_KEY` | `""` | Datalab Chandra OCR key from https://www.datalab.to |
| `DATALAB_MODE` | `accurate` | OCR mode (`accurate` / `balanced` / `fast`) |
| `LLM_PROVIDER` | `ollama` | LLM backend (`ollama` / `llama_cpp` / `openai_compat`) |
| `LLM_API_BASE_URL` | `http://localhost:11434/v1` | Ollama API endpoint for local LLM inference |
| `LLM_MODEL_NAME` | `qwen2.5:3b-instruct` | LLM model for analysis, summarization & translation |
| `EMBEDDING_MODEL_NAME` | `sentence-transformers/...` | Model for 384-dimensional vector embeddings |
| `SEMANTIC_CACHE_ENABLED` | `true` | Enable LLM response deduplication cache |
| `ALLOWED_ORIGINS` | `http://localhost:5173,5174` | CORS allowed origins for frontend |
| `UPLOAD_DIR` | `uploads` | Directory for temporary petition scan storage |

---

## 📁 Project Structure

```
smart-petition-ocr/
├── backend/                    # FastAPI Backend (Python 3.11+)
│   ├── app/                    # Application core
│   │   ├── main.py             # FastAPI app entry point
│   │   ├── config.py           # Pydantic settings & env loader
│   │   ├── dependencies.py     # Dependency injection & guards
│   │   ├── api/v1/             # Versioned API route modules
│   │   └── routers/            # Router modules (translate, admin, grievance)
│   ├── core/                   # Core utilities (security, LLM client)
│   ├── models/                 # SQLAlchemy ORM models & dual-DB router
│   ├── services/               # Business logic (OCR, vector store, cache)
│   ├── scripts/                # DB management, data ingestion scripts
│   ├── tests/                  # pytest test suites
│   ├── data/                   # Authoritative government taxonomy PDF
│   ├── Dockerfile              # Production container image
│   ├── .env.example            # Backend environment template
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # React 19 Frontend (Vite)
│   ├── src/
│   │   ├── App.jsx             # Root application component
│   │   ├── components/
│   │   │   ├── admin/          # Admin workspace, taxonomy modal
│   │   │   ├── layout/         # Header, Sidebar, navigation
│   │   │   ├── profile/        # Officer profile (role-based)
│   │   │   └── workspace/      # Petition workspace, dual-panel
│   │   ├── services/           # API client (apiService.js)
│   │   ├── utils/              # Dynamic translation engine, helpers
│   │   └── data/               # Intake channel definitions
│   ├── public/                 # Static assets (emblems, logos)
│   └── package.json            # Node dependencies
│
├── scripts/                    # Root-level CLI utilities
│   └── manage_db.py            # Database export / import / seed / migrate
│
├── docker-compose.yml          # Full-stack Docker orchestration
├── run.py                      # Unified Python launcher & diagnostics
├── setup.bat                   # 1-click Windows environment setup
├── run_all.bat                 # 1-click Windows full system launcher
├── .env.example                # Root environment template
├── requirements.txt            # Root requirements pointer
├── README.md                   # ← Comprehensive Documentation
├── QUICKSTART.md               # Quick setup & test accounts guide
├── DEPLOYMENT.md               # Production deployment procedures
├── CONTRIBUTING.md             # Developer contribution guidelines
├── SECURITY.md                 # Security policy & vulnerability disclosure
└── LICENSE                     # Apache License 2.0
```

---

## 🔧 Troubleshooting & Diagnostics

### 1. Run Pre-Flight Diagnostics
Run the built-in system doctor to verify your environment:
```bash
python run.py --doctor
```

### 2. Common Issues & Solutions

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **Cannot find module `sentence_transformers`** | Package not installed in virtual environment | Run `pip install -r backend/requirements.txt` inside `.venv` |
| **Port 8000 or 5174 already in use** | Another process is occupying the port | Kill the existing process or change port in `run.py` |
| **Datalab OCR Timeout or 401 Unauthorized** | Invalid or missing `DATALAB_API_KEY` | Check your key at [datalab.to](https://www.datalab.to), or leave empty to use offline PaddleOCR |
| **Ollama connection refused (`11434`)** | Ollama service is not running | Run `ollama serve` in a terminal or launch Ollama app |
| **PostgreSQL connection refused (`5432`)** | Docker container is not started | Start PostgreSQL: `docker compose up -d postgres` or set `USE_SQLITE=true` |
| **PowerShell script execution error** | Execution policy restriction | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |

---

## 🛡️ Security & Governance

- **Aadhaar Protection**: Automatic regex-based client and server redaction to `XXXX-XXXX-1234`.
- **Zero Citizen PII in Logs**: Strict logging policy preventing citizen names, addresses, or contact information from writing to stdout.
- **Air-Gapped Security**: Core OCR, vector indexing, and entity validation execute 100% locally.
- **Role-Based Access**: Administrative operations require verified officer JWT with `is_admin: true`.
- **Database Isolation**: SQLite databases reside in `temp_cache/` excluded from Git; PostgreSQL connections require SSL in production.
- For vulnerability disclosure instructions and policies, review [SECURITY.md](SECURITY.md).

---

## 📄 License

This project is licensed under the **Apache License, Version 2.0**. See the [LICENSE](LICENSE) file for complete terms.
