# Production Dockerfile for GDP Assistant Backend & Worker
# Multi-stage optimized Debian-based Python 3.11 image

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TEMP=/app/temp_cache \
    TMP=/app/temp_cache \
    TMPDIR=/app/temp_cache \
    HF_HOME=/app/model_cache \
    SENTENCE_TRANSFORMERS_HOME=/app/model_cache \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install minimal OS dependencies for PDF, imaging, and network health probes
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create application, storage, and cache directories
RUN mkdir -p /app/temp_cache /app/uploads /app/storage/uploads /app/data /app/model_cache

# 1. Install lightweight CPU PyTorch wheel
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 2. Install application Python dependencies (leveraging Docker layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r /app/requirements.txt

# 3. Copy application codebase into image
COPY . /app

# 4. Set Python paths so both app and worker packages are discoverable
ENV PYTHONPATH=/app/backend:/app

EXPOSE 8000

# Health check
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command runs FastAPI API; overridden by worker service in docker-compose
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
