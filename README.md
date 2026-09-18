# 🏛️ GDP Assistant: AI-Powered Grievance Redressal & Digitization Platform

<div align="center">

![GDP Assistant Banner](assets/banner.jpg)

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=for-the-badge&logo=apache)](LICENSE)
[![Code of Conduct](https://img.shields.io/badge/Contributor-Covenant_v2.1-4baaaa.svg?style=for-the-badge)](CODE_OF_CONDUCT.md)
[![Contributing](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg?style=for-the-badge)](CONTRIBUTING.md)
[![Security Policy](https://img.shields.io/badge/Security-Policy-red.svg?style=for-the-badge)](SECURITY.md)
[![Deployment Guide](https://img.shields.io/badge/Deployment-Procedures-orange.svg?style=for-the-badge)](DEPLOYMENT.md)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI: Modern](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
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

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#%EF%B8%8F-system-architecture)
- [Administrative Hierarchy & Taxonomy Structure](#-administrative-hierarchy--taxonomy-structure)
- [Passing Database & Data to Another System](#-passing-database--data-to-another-system)
- [Quickstart: Clone & Run](#-quickstart-clone--run)
  - [Prerequisites](#prerequisites)
  - [Step 1: Clone Repository](#step-1-clone-repository)
  - [Step 2: Environment Configuration](#step-2-environment-configuration)
  - [Step 3: Launch Services](#step-3-launch-services)
- [Configuration Reference](#%EF%B8%8F-configuration-reference)
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

---

## ✨ Key Features

- **Split Dual-Panel Workspace**: View the high-resolution scanned petition on the left alongside the AI-assisted draft form, metadata editor, and interactive chat on the right.
- **Cognitive Document Chat**: Ask questions in Tamil or English grounded strictly in petition text with instant answer verification.
- **Mobile QR Capture**: Intake staff scan a QR code on their smartphone to upload multi-page petitions directly to the desktop workspace.
- **Authoritative Taxonomy Management**: Search, filter, add, edit, and delete mappings across all 40 official government departments with real-time vector indexing.
- **Administrative Hierarchy Overview**: Real-time management across all district tiers (Zones, Taluks, Firkas, Municipalities, Villages, and Wards).
- **Dual Database Architecture with Real-Time Telemetry**: Seamlessly switches between embedded SQLite (offline desktop mode) and PostgreSQL 16 with `pgvector` (intranet/cloud mode) with live latency monitoring.
- **Anti-Hallucination Barrier**: Automatically cross-references extracted claims against raw OCR text chunks and flags unverified information.
- **Formal Administrative Tamil Summaries**: Enforces standard third-person administrative Tamil summaries (`மனுதாரர் [பெயர்] ... கோரியுள்ளார்`) adhering to official collectorate conventions.

---

## 🏗️ System Architecture

GDP Assistant operates with a decoupled, resilient architecture supporting both offline single-node setups and enterprise clustered deployments:

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
        AdminAPI["Admin & Taxonomy Services"]
        Telemetry["Database Health Telemetry"]
    end

    subgraph ProcessingPipeline ["Processing Engine"]
        OCR["Hybrid OCR Router\nChandra OCRv2 / PaddleOCR"]
        Chunker["Tamil Semantic Chunker\nSentence Boundaries"]
        Embedder["SentenceTransformer\nparaphrase-multilingual-MiniLM-L12-v2"]
        NER["Hybrid Entity Extractor\nRegex + Revenue Master Validator"]
        LLM["Cognitive LLM Engine (Ollama / Gemini)\nSummarization & Claim Verification"]
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

### Prerequisites
- **Python**: 3.11 or higher
- **Node.js**: 18.x or higher (`npm` 9+)
- *(Optional)* **Ollama**: For local offline LLM inference (`ollama run qwen2.5:3b`)

### Step 1: Clone Repository
```bash
git clone https://github.com/MUKESH-WORK/smart-petition-ocr.git
cd smart-petition-ocr
```

### Step 2: Environment Configuration
Copy the sample environment file:
```bash
cp .env.example .env
```
*(Optionally provide your `CHANDRA_API_KEY` for cloud handwriting OCR, or leave blank to utilize the bundled local OCR engine).*

### Step 3: Launch Services

#### Method 1: All-in-One Launcher (Recommended)
```bash
# Windows
run_all.bat

# Linux / macOS
chmod +x run_all.sh && ./run_all.sh
```

#### Method 2: Manual Developer Launch
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

Open your browser at **`http://localhost:5174`** (or `http://localhost:5173`).

---

## ⚙️ Configuration Reference

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite+aiosqlite:///temp_cache/dro_user.db` | User & grievance database connection URL |
| `ADMIN_DATABASE_URL` | `sqlite+aiosqlite:///temp_cache/dro_admin.db` | Administrative & taxonomy database connection URL |
| `CHANDRA_API_KEY` | `""` | Optional Datalab Chandra OCR key for enhanced Tamil handwriting |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint for offline LLM inference |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Default Ollama model name |
| `JWT_SECRET` | *(Auto-generated)* | Signing secret for officer session tokens |
| `UPLOAD_DIR` | `uploads` | Directory for temporary petition scan storage |

---

## 🚢 Production Deployment Procedures

For comprehensive production deployment principles, platform-specific steps (Docker, systemd, reverse proxies), zero-downtime procedures, and rollback runbooks, see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## 🧪 Verification & Testing

Execute the backend automated test suite:
```bash
cd backend
pytest tests/ -v
```

Verify database health and record counts:
```bash
python scripts/manage_db.py stats
```

Validate frontend production build:
```bash
cd frontend
npm run build
```

---

## 🛡️ Security & Governance

- **Aadhaar Protection**: Automatic regex-based client and server redaction to `XXXX-XXXX-1234`.
- **Zero Citizen PII in Logs**: Strict logging policy preventing citizen names, addresses, or contact information from writing to stdout.
- **Air-Gapped Security**: Core OCR, vector indexing, and entity validation execute 100% locally.
- For vulnerability disclosure instructions and policies, review [SECURITY.md](SECURITY.md).

---

## 🤝 Community & Contributing

We welcome contributions from developers, civic technologists, and revenue administrators!
- Please read our [Contributing Guidelines](CONTRIBUTING.md) to understand our coding standards, branch conventions, and PR workflow.
- All participants must adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).
- To report a bug or request a feature, use our [GitHub Issue Templates](.github/ISSUE_TEMPLATE/).

---

## 📄 License

This project is licensed under the **Apache License, Version 2.0**. See the [LICENSE](LICENSE) file for complete terms.
