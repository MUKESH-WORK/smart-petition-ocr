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
2. **High-Accuracy Tamil OCR**: Decipher complex handwritten and printed Tamil petitions using deep neural OCR with offline fallbacks.
3. **Automated CM Helpline Taxonomy Alignment**: Accurately classify grievances across **40 Department Groups**, **1,027 Grievance Types**, and **1,861 Sub-Types** with responsible officer designation.
4. **Authoritative Administrative Grounding**: Route petitions accurately across **6 Administrative Tiers** (Corporation Zones, Taluks, Firkas, Municipalities, Revenue Villages, and Corporation Wards) with zero hallucination.
5. **Absolute Privacy & Data Sovereignty**: Automatic client-side masking of Aadhaar numbers (`XXXX-XXXX-1234`) and zero reliance on proprietary cloud APIs for core operations.
6. **Real-Time Bilingual Interface**: Dynamic LLM-powered English ↔ Tamil translation across the entire UI — no hardcoded dictionaries.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#%EF%B8%8F-system-architecture)
- [Intake Channels (21 Sources)](#-intake-channels-21-sources)
- [Administrative Hierarchy & Taxonomy Structure](#-administrative-hierarchy--taxonomy-structure)
- [Role-Based Access Control](#-role-based-access-control)
- [Dynamic Bilingual Translation](#-dynamic-bilingual-translation)
- [Passing Database & Data to Another System](#-passing-database--data-to-another-system)
- [Quickstart: Clone & Run](#-quickstart-clone--run)
  - [Prerequisites](#prerequisites)
  - [Step 1: Clone Repository](#step-1-clone-repository)
  - [Step 2: Environment Configuration](#step-2-environment-configuration)
  - [Step 3: Launch Services](#step-3-launch-services)
- [Configuration Reference](#%EF%B8%8F-configuration-reference)
- [Project Structure](#-project-structure)
- [Production Deployment Procedures](#-production-deployment-procedures)
- [Verification & Testing](#-verification--testing)
- [Security & Governance](#-security--governance)
- [Community & Support](#-community--support)
- [License](#-license)

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
        LLM["Cognitive LLM Engine (Ollama / Gemini)\nSummarization, Verification & Translation"]
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

## 📡 Intake Channels (21 Sources)

The system supports ingestion from **21 official grievance intake channels**, aligned with the Tamil Nadu CM Helpline and District Administration workflows:

| # | Channel | Category |
| :---: | :--- | :--- |
| 1 | CM Helpline 1100 (Phone Call) | Helpline |
| 2 | CM Helpline App | Digital |
| 3 | CM Helpline Web Portal | Digital |
| 4 | CM Special Cell | Helpline |
| 5 | District Collector Petition Day (GDP) | Walk-In |
| 6 | DRO / RDO Direct Petition | Walk-In |
| 7 | Sub-Collector Office | Walk-In |
| 8 | Tahsildar Office Walk-In | Walk-In |
| 9 | MLA / MP Recommendation | Referral |
| 10 | Revenue Divisional Office (RDO) | Government |
| 11 | E-Sevai Centre (CSC) | Digital |
| 12 | Social Media (Twitter/X, Facebook) | Social Media |
| 13 | WhatsApp Official Channel | Digital |
| 14 | Email Petition | Digital |
| 15 | Post / Speed Post / Courier | Mail |
| 16 | Public Hearing (Makkal Durbar) | Walk-In |
| 17 | RTI Application (Forwarded) | Government |
| 18 | Court Order / Tribunal Directive | Legal |
| 19 | NHRC / SHRC Referral | Legal |
| 20 | Transferred from Other District | Government |
| 21 | NGO / Civil Society Referral | Referral |

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

GDP Assistant enforces strict role-based access across the application:

| Role | Profile Edit | Taxonomy Admin | Petition Processing | System Config |
| :--- | :---: | :---: | :---: | :---: |
| **District Administrator** (Admin) | ✅ | ✅ | ✅ | ✅ |
| **Department User** | ❌ (View Only) | ❌ | ✅ | ❌ |
| **Field Officer** | ❌ (View Only) | ❌ | ✅ | ❌ |

- **Admin users** can edit officer profiles, manage taxonomy mappings, and configure system settings.
- **Non-admin users** see all profile data in read-only mode with a "View Only" badge.

---

## 🌐 Dynamic Bilingual Translation

The entire UI supports real-time English ↔ Tamil translation powered by the LLM engine:

- **No hardcoded dictionaries** — all translations are generated dynamically via the `/api/v1/translate` endpoint.
- **LRU Cache** on the server side prevents redundant LLM calls for previously translated text.
- **Batch translation** support for translating multiple UI elements in a single API request.
- **Tamil text rendering** uses dedicated font stack (`Noto Sans Tamil`, `Latha`, `Tamil Sangam MN`) with proper Unicode handling to prevent alignment issues.

---

## 💾 Passing Database & Data to Another System

To migrate or share the databases and all pre-seeded records to another workstation or server **without hitting Git push limits** (since binary `.db` files are excluded by `.gitignore`):

### Option 1: Compressed Database Bundle Export / Import (Recommended)
Use the included `scripts/manage_db.py` CLI:

```bash
# Step 1: On the SOURCE machine, export a compressed bundle:
python scripts/manage_db.py export --output gdp_database_bundle.tar.gz

# Step 2: Transfer 'gdp_database_bundle.tar.gz' to the target system (via USB, SCP, S3, etc.)

# Step 3: On the TARGET machine, import the bundle:
python scripts/manage_db.py import --input gdp_database_bundle.tar.gz

# Step 4: Verify that all records and metrics are active:
python scripts/manage_db.py stats
```

### Option 2: Zero-Transfer Clean Seeding (Air-Gapped Setup)
No file transfer needed! Every clone of this repository contains the authoritative government document (`backend/data/government_taxonomy.pdf`). Any target machine can construct the complete database from scratch in seconds:

```bash
python scripts/manage_db.py seed-fresh
```

### Option 3: Direct Migration to PostgreSQL + pgvector
To transfer the active SQLite database directly into a centralized PostgreSQL server:

```bash
python scripts/manage_db.py sync-to-postgres --postgres-url "postgresql+asyncpg://postgres:password@10.0.0.5:5432/gdp_db"
```

---

## 🚀 Quickstart: Clone & Run

> For detailed step-by-step instructions with test accounts and troubleshooting, see [QUICKSTART.md](QUICKSTART.md).

### Prerequisites
- **Python**: 3.11 or higher
- **Node.js**: 18.x or higher (`npm` 9+)
- *(Optional)* **Ollama**: For local offline LLM inference (`ollama run qwen2.5:3b-instruct`)
- *(Optional)* **PostgreSQL 16**: With `pgvector` extension for enterprise multi-user mode
- *(Optional)* **Docker**: For containerized deployment (`docker compose up`)

### Step 1: Clone Repository
```bash
git clone https://github.com/MUKESH-WORK/smart-petition-ocr.git
cd smart-petition-ocr
```

### Step 2: Environment Configuration
Copy the sample environment file and customize:
```bash
# Linux / macOS
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

**Minimum required changes:**
- Set a secure `SECRET_KEY` for JWT authentication
- *(Optional)* Add your `DATALAB_API_KEY` for cloud OCR, or leave blank to use the bundled PaddleOCR engine

### Step 3: Launch Services

#### Method 1: 1-Click Setup + Launch (Recommended for First Time)
```bash
# Windows
setup.bat        # First-time setup (installs all dependencies, seeds database)
run_all.bat      # Launch backend + frontend + open browser

# Linux / macOS
chmod +x setup.sh run_all.sh
./setup.sh       # First-time setup
./run_all.sh     # Launch backend + frontend
```

#### Method 2: Python Unified Launcher
```bash
python run.py --setup     # First-time dependency installation & DB seeding
python run.py             # Launch both backend + frontend
python run.py --doctor    # Pre-flight system diagnostics
python run.py --test      # Run automated test suite
```

#### Method 3: Manual Developer Launch
```bash
# Terminal 1: Backend
cd backend
python -m venv .venv
# On Windows: .venv\Scripts\activate | On Linux: source .venv/bin/activate
pip install -r requirements.txt
python scripts/manage_db.py seed-fresh    # Initializes databases if not present
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

#### Method 4: Docker Compose (Containerized)
```bash
docker compose up -d
```
This launches PostgreSQL 16 + pgvector, the FastAPI backend, and the Nginx-served frontend.

### 🌐 Application URLs

| Service | URL |
| :--- | :--- |
| **Civil Desk Workspace** | [`http://localhost:5174`](http://localhost:5174) |
| **FastAPI Interactive Docs** | [`http://127.0.0.1:8000/api/v1/docs`](http://127.0.0.1:8000/api/v1/docs) |
| **Database Health Telemetry** | [`http://127.0.0.1:8000/api/v1/health`](http://127.0.0.1:8000/api/v1/health) |

---

## ⚙️ Configuration Reference

All environment variables are documented in [`.env.example`](.env.example). Key variables:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite+aiosqlite:///...` | User & grievance database connection URL |
| `ADMIN_DATABASE_URL` | `sqlite+aiosqlite:///...` | Administrative & taxonomy database URL |
| `SECRET_KEY` | *(must be set)* | JWT signing secret for officer sessions |
| `LLM_PROVIDER` | `ollama` | LLM backend (`ollama` / `llama_cpp` / `openai_compat`) |
| `LLM_MODEL_NAME` | `qwen2.5:3b-instruct` | Default LLM model for analysis & translation |
| `OCR_PROVIDER` | `datalab` | OCR engine (`datalab` / `chandra_cloud` / `chandra_local`) |
| `DATALAB_API_KEY` | `""` | Optional Datalab Chandra OCR key for Tamil handwriting |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint for offline LLM inference |
| `SEMANTIC_CACHE_ENABLED` | `true` | Enable LLM response deduplication cache |
| `ALLOWED_ORIGINS` | `localhost:5173,5174` | CORS allowed origins for frontend |
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
│   │   └── routers/            # Router modules (translate, admin, etc.)
│   ├── core/                   # Core utilities (security, LLM client)
│   ├── models/                 # SQLAlchemy ORM models
│   ├── services/               # Business logic (OCR, RAG, cache, etc.)
│   ├── scripts/                # DB management, data ingestion scripts
│   ├── tests/                  # pytest test suites
│   ├── alembic/                # Database migration scripts
│   ├── Dockerfile              # Production container image
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
│   │   ├── utils/              # Translation engine, helpers
│   │   └── data/               # Mock data, intake channel definitions
│   ├── public/                 # Static assets (favicon, emblem)
│   ├── Dockerfile              # Nginx-served production image
│   └── package.json            # Node dependencies
│
├── scripts/                    # Root-level CLI utilities
│   └── manage_db.py            # Database export / import / seed / migrate
│
├── docker-compose.yml          # Full-stack Docker orchestration
├── run.py                      # Unified Python launcher & diagnostics
├── setup.bat / setup.sh        # 1-click environment setup
├── run_all.bat / run_all.sh    # 1-click full system launcher
├── .env.example                # Environment configuration template
├── .gitignore                  # Strict PII & binary exclusion rules
│
├── README.md                   # ← You are here
├── QUICKSTART.md               # Detailed setup & test accounts guide
├── DEPLOYMENT.md               # Production deployment procedures
├── CONTRIBUTING.md             # Developer contribution guidelines
├── SECURITY.md                 # Security policy & vulnerability disclosure
├── CODE_OF_CONDUCT.md          # Contributor Covenant v2.1
└── LICENSE                     # Apache License 2.0
```

---

## 🚢 Production Deployment Procedures

For comprehensive production deployment principles, platform-specific steps (Docker, systemd, reverse proxies), zero-downtime procedures, and rollback runbooks, see [DEPLOYMENT.md](DEPLOYMENT.md).

**Supported Deployment Models:**
1. **Single-Node Offline Workstation** — SQLite + CPU-only inference (Taluk / Remote Desks)
2. **District Intranet Server** — PostgreSQL 16 + pgvector behind Nginx (Multi-Officer)
3. **Containerized Enterprise** — Docker Compose / Kubernetes (State Data Center)

---

## 🧪 Verification & Testing

### Backend Automated Tests
```bash
cd backend
pytest tests/ -v
```

### Frontend Build Validation
```bash
cd frontend
npm run build
npm run lint
```

### System Diagnostics
```bash
python run.py --doctor
```

### Database Health Check
```bash
python scripts/manage_db.py stats
```

### Production Verification (Post-Deploy)
```bash
# API & database health
curl -s http://127.0.0.1:8000/api/v1/health | python -m json.tool

# Hierarchy stats
curl -s -H "X-Officer-Id: ADM-ERODE-001" http://127.0.0.1:8000/api/v1/admin/hierarchy/stats

# Taxonomy stats
curl -s -H "X-Officer-Id: ADM-ERODE-001" http://127.0.0.1:8000/api/v1/admin/taxonomy/stats
```

---

## 🛡️ Security & Governance

- **Aadhaar Protection**: Automatic regex-based client and server redaction to `XXXX-XXXX-1234`.
- **Zero Citizen PII in Logs**: Strict logging policy preventing citizen names, addresses, or contact information from writing to stdout.
- **Air-Gapped Security**: Core OCR, vector indexing, and entity validation execute 100% locally.
- **Role-Based Access**: Administrative endpoints require verified officer JWT with `is_admin: true`.
- **Database Isolation**: SQLite databases reside in `temp_cache/` excluded from Git; PostgreSQL connections require SSL in production.
- For vulnerability disclosure instructions and policies, review [SECURITY.md](SECURITY.md).

---

## 🤝 Community & Contributing

We welcome contributions from developers, civic technologists, and revenue administrators!

- Please read our [Contributing Guidelines](CONTRIBUTING.md) to understand our coding standards, branch conventions, and PR workflow.
- All participants must adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).
- To report a bug or request a feature, use our [GitHub Issue Templates](.github/ISSUE_TEMPLATE/).
- For a detailed quickstart and test accounts, see [QUICKSTART.md](QUICKSTART.md).

---

## 📄 License

This project is licensed under the **Apache License, Version 2.0**. See the [LICENSE](LICENSE) file for complete terms.
