# Production Dockerfile for GDP Assistant Backend
# Multi-stage / optimized Debian-based Python 3.11 image

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

# Install system dependencies for OpenCV, PDF processing, and health probes
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create cache, upload, model cache, and database bundle directories
RUN mkdir -p /app/temp_cache /app/uploads /app/data /app/model_cache

# 1. Install lightweight CPU PyTorch first (~180MB instead of 2.8GB CUDA wheel)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 2. Install remaining Python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r /app/requirements.txt

# 3. Pre-download and bake SentenceTransformer model into the image
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

# Copy backend source code
COPY backend /app/backend

# Set Python path to find app modules
ENV PYTHONPATH=/app/backend:/app

EXPOSE 8000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
