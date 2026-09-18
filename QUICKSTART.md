# 🚀 GDP Assistant — Quickstart & Installation Guide

> Whether you are an **evaluator/tester** looking to test Tamil petition OCR in 60 seconds, or a **software developer** building new AI features, this guide will get you up and running effortlessly.

---

## 🎯 Option A: For Testers & Evaluators (1-Click Launch)

You do **not** need Docker, PostgreSQL, or cloud API keys to run and evaluate GDP Assistant. The platform runs in offline-capable embedded mode.

### Windows (1-Click)
1. **First-Time Setup**:
   - Double-click **`setup.bat`** (or run `.\setup.bat` in PowerShell/CMD).
   - *This automatically creates the virtual environment, installs Python/Node dependencies, and seeds the authoritative government database.*
2. **Launch Application**:
   - Double-click **`run_all.bat`**.
   - *This launches the backend and frontend servers, and automatically opens your browser to `http://localhost:5174`.*

### Linux / macOS (1-Click)
```bash
# 1. First-time setup
chmod +x setup.sh run_all.sh
./setup.sh

# 2. Launch application
./run_all.sh
```

---

## 💻 Option B: For Developers

### 1. Environment Doctor (Pre-Flight Diagnostics)
Check your environment readiness at any time:
```bash
python run.py --doctor
```
*Outputs a clear health check for Python 3.11+, Node.js, npm, database files, port availability, and taxonomy assets.*

---

### 2. Manual Developer Setup

#### Step 1: Clone Repository
```bash
git clone https://github.com/MUKESH-WORK/smart-petition-ocr.git
cd smart-petition-ocr
```

#### Step 2: Automated Dependency & Database Setup
```bash
python run.py --setup
```
*(Or activate manually from the root: `activate.bat` on Windows or `source backend/.venv/bin/activate` on Linux).*

#### Step 3: Run in Development Mode (Hot-Reloading)
```bash
# Terminal 1: Backend (FastAPI with Uvicorn Reload)
python run.py --reload --backend-only

# Terminal 2: Frontend (Vite Dev Server)
cd frontend
npm run dev
```

---

## 🔑 Pre-Configured Test Accounts

The local database is pre-seeded with authoritative officer roles for testing:

| Officer Name | Officer ID | Role | Default Jurisdiction |
| :--- | :--- | :--- | :--- |
| **District Collector** | `ADM-ERODE-001` | **District Administrator** | Erode District Collectorate |
| **District Revenue Officer (DRO)** | `DRO-ERODE-001` | **District Administrator** | Revenue Administration |
| **Sub-Collector / RDO** | `RDO-ERODE-001` | **Department User** | Erode Revenue Division |
| **Tahsildar (Erode)** | `TAH-ERD-001` | **Field Officer** | Erode Taluk Desk |
| **Tahsildar (Bhavani)** | `TAH-BHV-001` | **Field Officer** | Bhavani Taluk Desk |

---

## 🗄️ Database Management Quick Reference

Use the root CLI utility `python scripts/manage_db.py` to inspect, export, import, or migrate data:

```bash
# View active database counts and table statistics
python scripts/manage_db.py stats

# Export database bundle (to send to another developer or machine)
python scripts/manage_db.py export --output gdp_database_bundle.tar.gz

# Import a database bundle onto a new system
python scripts/manage_db.py import --input gdp_database_bundle.tar.gz

# Re-seed fresh from source government PDF (zero external files required)
python scripts/manage_db.py seed-fresh

# Migrate local SQLite data into enterprise PostgreSQL + pgvector
python scripts/manage_db.py sync-to-postgres --postgres-url "postgresql+asyncpg://user:pass@host:5432/gdp_db"
```

---

## 🧪 Running Automated Tests

Verify backend pipeline integrity and OCR fallback logic:
```bash
python run.py --test
```
*(Or run `pytest backend/tests/ -v` directly).*

---

## 🌐 Key Application URLs

Once running:
- **Civil Desk Workspace**: [`http://localhost:5174`](http://localhost:5174)
- **FastAPI OpenAPI Interactive Docs**: [`http://127.0.0.1:8000/api/v1/docs`](http://127.0.0.1:8000/api/v1/docs)
- **Database & Health Telemetry**: [`http://127.0.0.1:8000/api/v1/health`](http://127.0.0.1:8000/api/v1/health)
- **Mobile QR Capture Bridge**: Built into the frontend header for scanning physical petitions with any mobile device camera.
