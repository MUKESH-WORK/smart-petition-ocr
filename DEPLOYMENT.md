# Production Deployment Procedures & Operations Guide

> **Guiding Principle**: Every deployment is an operational event. Minimize risk through strict preparation, automated verification, safe backups, and tested rollback procedures. Learn to **think through the process**, not just run commands.

---

## 1. Architectural Deployment Models

GDP Assistant supports three deployment topologies depending on administrative infrastructure:

```
Deployment Topology Decision Tree
│
├── [Model 1] Single-Node Offline Workstation (Recommended for Taluk / Remote Desks)
│   ├── Storage: Dual embedded SQLite (dro_admin.db + dro_user.db)
│   ├── AI/OCR: Local Chandra OCRv2 + PaddleOCR + SentenceTransformers (CPU)
│   └── Network: Air-gapped / Local Wi-Fi (for Mobile QR Bridge)
│
├── [Model 2] District Collectorate Intranet Server (Multi-Officer / Multi-Desk)
│   ├── Storage: PostgreSQL 16 + pgvector (HNSW Indexing)
│   ├── Backend: FastAPI Uvicorn ASGI cluster behind Nginx / Caddy reverse proxy
│   └── Frontend: Static production build served over HTTPS / Intranet TLS
│
└── [Model 3] Containerized Enterprise Cloud / State Data Center
    ├── Orchestration: Docker Compose / Kubernetes
    ├── Database: Managed PostgreSQL 16 with pgvector extension
    └── LLM Service: Dedicated Ollama / vLLM cluster
```

---

## 2. Passing & Transferring Databases Across Systems

To deploy or replicate databases on another workstation without committing large binary files to Git:

### Method A: Portable Compressed Archive (Fastest & Simplest)
Use the included `scripts/manage_db.py` tool.

1. **On the Source Machine (Export)**:
   ```bash
   python scripts/manage_db.py export --output gdp_database_bundle.tar.gz
   ```
   *Creates an integrity-checked, compressed `.tar.gz` bundle containing both `dro_admin.db` and `dro_user.db` along with a SHA-256 manifest.*

2. **Transfer the Bundle**:
   *Copy `gdp_database_bundle.tar.gz` (or your chosen bundle name) to the target system via USB drive, secure SCP, S3 bucket, or local network share.*

3. **On the Target Machine (Import)**:
   ```bash
   python scripts/manage_db.py import --input gdp_database_bundle.tar.gz
   ```
   *Automatically verifies SHA-256 checksums, backs up any existing local database, and installs the active databases.*

4. **Verify Target Database State**:
   ```bash
   python scripts/manage_db.py stats
   ```

---

### Method B: Zero-Transfer Re-Seeding (Air-Gapped Clean Setup)
You do not need to transfer database files at all if you have the repository! The system includes an automated seeder that extracts all **477 administrative locations** and **1,861 CM Helpline taxonomy mappings** directly from the included authoritative government document (`backend/data/government_taxonomy.pdf`):

```bash
# On any fresh system:
python scripts/manage_db.py seed-fresh
```

---

### Method C: Migrating SQLite Data to PostgreSQL + pgvector
When transitioning from local developer testing to enterprise PostgreSQL with `pgvector`:

1. Configure your target PostgreSQL connection string in `.env` (or pass it directly):
   ```bash
   export DATABASE_URL="postgresql+asyncpg://postgres:secret@10.0.0.5:5432/gdp_db"
   ```
2. Run the migration bridge:
   ```bash
   python scripts/manage_db.py sync-to-postgres --postgres-url "postgresql+asyncpg://postgres:secret@10.0.0.5:5432/gdp_db"
   ```
   *Enables the `pgvector` extension, creates relational and vector schemas, and syncs all users, locations, and taxonomy mappings.*

---

## 3. The 5-Phase Deployment Workflow

Follow this strict lifecycle for every release:

```
1. PREPARE ────► 2. BACKUP ────► 3. DEPLOY ────► 4. VERIFY ────► 5. CONFIRM / ROLLBACK
```

### Phase 1: Preparation (Pre-Flight Checks)
- [ ] Automated tests passing: `pytest backend/tests/`
- [ ] No uncommitted modifications or un-ignored model weights (`git status`).
- [ ] Frontend builds without syntax errors: `cd frontend && npm run build`.
- [ ] Environment variables verified in `.env` (JWT secrets, CORS origins, model flags).
- [ ] Database migration ready or verified via `python scripts/manage_db.py stats`.

### Phase 2: Backup (Never Deploy Without a Rollback Source)
Before pulling new code or restarting services:
```bash
# Snapshot existing databases
python scripts/manage_db.py export --output /var/backups/gdp/backup_$(date +%Y%m%d_%H%M%S).tar.gz
```

### Phase 3: Deployment Execution
1. Pull verified release branch:
   ```bash
   git pull origin main
   ```
2. Install dependencies:
   ```bash
   # Backend
   pip install -r backend/requirements.txt
   
   # Frontend
   cd frontend && npm ci && npm run build && cd ..
   ```
3. Restart services (via systemd, PM2, or Docker):
   ```bash
   # Systemd example
   sudo systemctl restart gdp-backend
   sudo systemctl restart nginx
   ```

### Phase 4: Post-Deployment Verification (First 5 Minutes)
Execute health telemetry probes immediately:
```bash
# 1. API & Database Health Check
curl -s http://127.0.0.1:8000/api/v1/health | jq .

# 2. Hierarchy Stats Endpoint
curl -s -H "X-Officer-Id: ADM-ERODE-001" http://127.0.0.1:8000/api/v1/admin/hierarchy/stats | jq .

# 3. Taxonomy Stats Endpoint
curl -s -H "X-Officer-Id: ADM-ERODE-001" http://127.0.0.1:8000/api/v1/admin/taxonomy/stats | jq .

# 4. Dynamic Translation Service (verify LLM connectivity)
curl -s -X POST http://127.0.0.1:8000/api/v1/translate \
  -H "Content-Type: application/json" \
  -d '{"texts": ["System health check"], "target_language": "ta"}' | jq .
```
Verify that:
- `admin_db.status` is `"connected"`.
- `user_db.status` is `"connected"`.
- Hierarchy counts reflect active district figures (Zones: 4, Taluks: 9, Firkas: 33, Municipalities: 5, Villages: 375, Wards: 60).
- Total taxonomy mappings reflect `1,861`.
- Translation API returns a valid Tamil translation (confirms LLM engine is operational).

### Phase 5: Rollback Strategy (If Critical Anomalies Occur)
If the service fails to start or database connectivity is lost:
1. **Immediately restore previous application state**:
   ```bash
   git checkout HEAD~1
   ```
2. **Restore previous database snapshot**:
   ```bash
   python scripts/manage_db.py import --input /var/backups/gdp/pre_deploy_backup.tar.gz
   ```
3. **Restart services and alert administrative team**:
   ```bash
   sudo systemctl restart gdp-backend
   ```
   *Rule: Rollback first to preserve civic service continuity; debug root cause offline.*

---

## 4. Docker Deployment Models

GDP Assistant offers two container deployment workflows:

---

### Option A: All-in-One Standalone Container (Simplest - Zero Dependencies)
Run the entire application (React Frontend + FastAPI AI Backend + SQLite DB) in a single portable container image on any system:

```bash
# 1. Build the unified Docker image
docker build -t gdp-assistant:latest .

# 2. Run the container
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/backend/data:/app/backend/data \
  -v $(pwd)/uploads:/app/uploads \
  --name gdp_assistant \
  gdp-assistant:latest

# 3. Access in your browser:
#    👉 Web Application: http://localhost:8000/
#    👉 API Documentation: http://localhost:8000/api/v1/docs
#    👉 Health Diagnostics: http://localhost:8000/api/v1/health
```

---

### Option B: Docker Compose Multi-Service Stack (Production Intranet / Cloud)
For multi-user deployments requiring PostgreSQL 16 + pgvector and Nginx reverse proxying:

```bash
# 1. Prepare environment
cp .env.example .env
# Edit .env with your environment configuration

# 2. Build and launch all services
docker compose up -d --build

# 3. Verify container health
docker compose ps

# 4. View live logs
docker compose logs -f
```

#### Service Topography:
```
docker compose up -d
├── gdp_postgres   (pgvector/pgvector:pg16)  → Port 5432
├── gdp_backend    (Python 3.11 + FastAPI)   → Port 8000
└── gdp_frontend   (Node 20 + Nginx)         → Port 5174 / 80
```

#### Stopping & Lifecycle:
```bash
docker compose down          # Gracefully stop containers
docker compose down -v       # Stop and purge volumes (⚠️ deletes database data)
```

---

## 5. Operational Maintenance & Monitoring

- **Log Inspections**: `journalctl -u gdp-backend -f -n 100` (ensure zero citizen PII).
- **Docker Logs**: `docker compose logs -f --tail=100 backend`.
- **Disk Usage**: Keep `temp_cache/` and `uploads/` monitored to ensure storage doesn't exceed workstation capacity.
- **Scheduled Backups**: Set up a weekly cron job on the production server:
  ```cron
  0 2 * * 0 /usr/bin/python3 /opt/smart-petition-ocr/scripts/manage_db.py export --output /var/backups/gdp/weekly_$(date +\%Y\%m\%d).tar.gz
  ```
- **Translation Cache**: The LLM translation engine uses an LRU cache. No manual cache management needed, but restart the backend to clear the cache if translations seem stale.
