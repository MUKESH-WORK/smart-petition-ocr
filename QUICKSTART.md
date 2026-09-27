# 🚀 GDP Assistant — Quickstart & Developer Guide

> This guide provides step-by-step instructions for getting the platform up and running on any machine, whether you prefer 1-click launchers, manual terminal setup, or Docker containers.

---

## 📋 Table of Contents
1. [🌟 Fresh Server Deployment (1-Command Bootstrap)](#-fresh-server-deployment-1-command-bootstrap)
2. [Prerequisites](#-prerequisites)
3. [Option A: 1-Click Automated Launch (Local Native)](#-option-a-1-click-automated-launch-local-native)
4. [Option B: Manual Step-by-Step Developer Setup](#-option-b-manual-step-by-step-developer-setup)
5. [Option C: Docker Compose Deployment](#-option-c-docker-compose-deployment)
6. [API Keys & LLM Configuration](#-api-keys--llm-configuration)
7. [Pre-Configured Officer Test Accounts](#-pre-configured-officer-test-accounts)
8. [Database Management & CLI Tools](#-database-management--cli-tools)
9. [Troubleshooting & Diagnostics](#-troubleshooting--diagnostics)

---

## 🌟 Fresh Server Deployment (1-Command Bootstrap)

> **For fresh Windows servers with only Git and Docker Desktop installed.**

If Ollama is not installed and the AI model is not downloaded on the server, run the automated bootstrap script:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_host.ps1
```

### What this script automates:
1. **Checks Docker & Docker Engine**: Verifies Docker daemon responsiveness.
2. **Detects & Installs Ollama**: Automatically installs Ollama via `winget` if missing on the host.
3. **Starts Host Ollama Server**: Starts the `ollama serve` background daemon and verifies `http://127.0.0.1:11434`.
4. **Downloads Required AI Model**: Pulls `qwen2.5:3b-instruct` automatically if not already present.
5. **Constructs Environment (`.env`)**: Generates `.env` from `.env.example` if missing without overwriting existing configs.
6. **Builds & Launches Containers**: Executes `docker compose up -d --build`.
7. **Monitors Health & Verifies Process Tree**: Waits for `http://localhost/health` and verifies Supervisor sub-processes (Nginx, FastAPI, Redis, Worker).

Once finished, open your browser at **`http://localhost`**.

---

## 🛠️ Prerequisites

Ensure you have installed:
- **Python 3.11+** ([python.org](https://www.python.org/downloads/))
- **Node.js 18+ & npm 9+** ([nodejs.org](https://nodejs.org/))
- **Git** ([git-scm.com](https://git-scm.com/))
- *(Optional for AI)* **Ollama** ([ollama.com](https://ollama.com/))
- *(Optional for Enterprise DB)* **Docker Desktop** ([docker.com](https://www.docker.com/products/docker-desktop/))

---

## ⚡ Option A: 1-Click Automated Launch (Fastest)

### Windows (1-Click)
1. **First-Time Setup**:
   - Double-click **`setup.bat`**.
   - *Automatically creates the `.venv`, installs all Python and Node dependencies, and seeds the government database.*
2. **Launch Application**:
   - Double-click **`run_all.bat`**.
   - *Starts both backend and frontend servers, and opens `http://localhost:5174` in your browser.*

### Linux / macOS (1-Click)
```bash
chmod +x setup.sh run_all.sh
./setup.sh
./run_all.sh
```

---

## 💻 Option B: Manual Step-by-Step Developer Setup

### Step 1: Clone Repository
```bash
git clone https://github.com/MUKESH-WORK/smart-petition-ocr.git
cd smart-petition-ocr
```

### Step 2: Configure Environment
```bash
# Copy template to active .env
cp .env.example .env             # Linux/macOS
Copy-Item .env.example .env      # Windows PowerShell
```

### Step 3: Setup Ollama LLM (Local Offline AI)
1. Install Ollama from [ollama.com](https://ollama.com).
2. Pull the required models:
   ```bash
   ollama run qwen2.5:3b-instruct
   ollama pull nomic-embed-text:latest
   ```

### Step 4: Choose Database
- **SQLite (Zero setup)**: Set `USE_SQLITE=true` in `.env`.
- **PostgreSQL 16 + pgvector (Docker)**:
  ```bash
  docker compose up -d postgres
  ```

### Step 5: Backend Setup & Run (Terminal 1)
```bash
cd backend

# 1. Create and activate virtual environment
py -3.11 -m venv .venv           # Windows
source .venv/bin/activate        # Linux/macOS (.venv\Scripts\activate on Windows)

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Seed database from official government taxonomy
python scripts/manage_db.py seed-fresh

# 4. Start backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 6: Frontend Setup & Run (Terminal 2)
```bash
cd frontend
npm install
npm run dev
```

Open [`http://localhost:5173`](http://localhost:5173) or [`http://localhost:5174`](http://localhost:5174) in your browser.

---

## 🐳 Option C: Docker Compose Deployment

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Launch all services
docker compose up -d

# 3. View service status
docker compose ps
```

---

## 🔑 API Keys & LLM Configuration

### Datalab Chandra OCR API Key (`DATALAB_API_KEY`)
- **Purpose**: Provides deep neural OCR specifically tuned for handwritten Tamil petitions.
- **How to Obtain**: Register for free at [https://www.datalab.to](https://www.datalab.to) and copy your API key into `.env`:
  ```env
  OCR_PROVIDER=datalab
  DATALAB_API_KEY=your_key_here
  ```
- **Fallback**: If left empty, GDP Assistant automatically uses the bundled offline **PaddleOCR** engine with zero cloud dependency.

---

## 👥 Pre-Configured Officer Test Accounts

| Officer Name | Officer ID | Role | Permissions |
| :--- | :--- | :--- | :--- |
| **District Collector** | `ADM-ERODE-001` | **District Administrator** | Full Admin, Profile Editing, Taxonomy & Hierarchy Management |
| **District Revenue Officer (DRO)** | `DRO-ERODE-001` | **District Administrator** | Full Admin, Profile Editing, Petition Approval & Dispatch |
| **Sub-Collector / RDO** | `RDO-ERODE-001` | **Department User** | Petition Review, Verification, View-Only System Data |
| **Tahsildar (Erode)** | `TAH-ERD-001` | **Field Officer** | Petition Review, Field Verification |
| **Tahsildar (Bhavani)** | `TAH-BHV-001` | **Field Officer** | Petition Review, Field Verification |

---

## 🗄️ Database Management & CLI Tools

```bash
# View active database statistics
python scripts/manage_db.py stats

# Export compressed bundle
python scripts/manage_db.py export --output gdp_database_bundle.tar.gz

# Import compressed bundle on another system
python scripts/manage_db.py import --input gdp_database_bundle.tar.gz

# Seed fresh from source government PDF
python scripts/manage_db.py seed-fresh

# Migrate SQLite database into PostgreSQL + pgvector
python scripts/manage_db.py sync-to-postgres --postgres-url "postgresql+asyncpg://dro_user:dro_password_2026@localhost:5432/dro_grievance_db"
```

---

## 🩺 Troubleshooting & Diagnostics

Run the system doctor anytime to diagnose setup issues:
```bash
python run.py --doctor
```

- **Missing `sentence_transformers`**: Run `pip install -r backend/requirements.txt` inside your virtual environment.
- **Port 8000/5174 busy**: Terminate any dangling processes or modify ports in `run.py`.
- **Ollama offline**: Ensure `ollama serve` is running or start the Ollama desktop client.
- **Docker PostgreSQL offline**: Check Docker Desktop is running, then run `docker compose up -d postgres`.
