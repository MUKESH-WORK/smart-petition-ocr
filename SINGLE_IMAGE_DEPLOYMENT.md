# GDP Assistant — Single Docker Image Deployment Guide

This guide explains how to build, export, and run the **GDP Assistant Complete Single Image** on **any system** (Windows, Linux, macOS) using an `.env` file.

---

## 1. What the Single Image Bundles

The single image (`gdp-assistant:latest`) contains the complete full-stack system in **one container**:

| Component | Port | Description |
| :--- | :--- | :--- |
| **Nginx Web Server** | `80` | High-performance static web server & reverse proxy for the React 19 UI |
| **FastAPI Backend** | `8000` *(internal)* | REST API, Administrative Engine, RAG Search & Taxonomies |
| **OCR Worker** | Background | Asynchronous queue consumer for background document ingestion |
| **Embedded Redis** | `6379` *(internal)* | Fast in-memory job broker |
| **Supervisord** | PID 1 | Process manager coordinating all 4 services |

---

## 2. Running on Any System

### Option A: Quick Run with Default Configuration (Port 80)
```bash
docker run -d \
  --name gdp_assistant \
  -p 80:80 \
  --restart unless-stopped \
  -v gdp_storage:/app/storage \
  gdp-assistant:latest
```
Access the application immediately at: **`http://localhost`**

---

### Option B: Running with an `.env` File (Custom Configuration)
To configure database connections (e.g. PostgreSQL with pgvector), external OCR API keys, or Ollama/LLM endpoints:

```bash
docker run -d \
  --name gdp_assistant \
  -p 80:80 \
  --env-file .env \
  --restart unless-stopped \
  -v gdp_storage:/app/storage \
  --add-host host.docker.internal:host-gateway \
  gdp-assistant:latest
```

> [!TIP]
> `--add-host host.docker.internal:host-gateway` allows the container to communicate with services running directly on the host machine (like local Ollama on port `11434` or local PostgreSQL on port `5432`).

---

## 3. How to Transfer & Run on Another Machine (Offline / Air-Gapped)

You can save the single image into a portable `.tar` file and load it onto any computer without rebuilding or copying source code:

### Step 1: Export Image (On Current PC)
```bash
docker save -o gdp-assistant-latest.tar gdp-assistant:latest
```

### Step 2: Copy to Target PC
Transfer `gdp-assistant-latest.tar` and your `.env` file to the new PC (via USB drive, SCP, or network share).

### Step 3: Load Image (On Target PC)
```bash
docker load -i gdp-assistant-latest.tar
```

### Step 4: Run Container (On Target PC)
```bash
docker run -d \
  --name gdp_assistant \
  -p 80:80 \
  --env-file .env \
  --restart unless-stopped \
  -v gdp_storage:/app/storage \
  --add-host host.docker.internal:host-gateway \
  gdp-assistant:latest
```

---

## 4. Useful Management Commands

| Action | Command |
| :--- | :--- |
| **View Live Container Logs** | `docker logs -f gdp_assistant` |
| **Check Process Health** | `curl http://localhost/health` |
| **Check Supervisor Services** | `docker exec -it gdp_assistant supervisorctl status` |
| **Restart Application** | `docker restart gdp_assistant` |
| **Stop & Remove Container** | `docker stop gdp_assistant && docker rm gdp_assistant` |
| **Enter Container Shell** | `docker exec -it gdp_assistant bash` |

---

## 5. Key Environment Variables Reference (`.env`)

| Variable | Default / Example | Purpose |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/db` | PostgreSQL connection (falls back to SQLite if omitted) |
| `SECRET_KEY` | *(Random 32-byte string)* | JWT authentication signing key |
| `LLM_PROVIDER` | `ollama` | LLM backend (`ollama`, `openai`, `sarvam`) |
| `LLM_API_BASE_URL` | `http://host.docker.internal:11434/v1` | LLM inference endpoint |
| `LLM_MODEL_NAME` | `qwen2.5:3b-instruct` | LLM model identifier |
| `OCR_PROVIDER` | `datalab` | External OCR engine (`datalab` / offline fallback) |
| `DATALAB_API_KEY` | *(Your Datalab Key)* | Cloud OCR authentication |
| `WORKER_CONCURRENCY`| `4` | Parallel OCR extraction worker count |
