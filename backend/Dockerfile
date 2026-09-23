# Production Dockerfile for GDP Assistant Backend
# Multi-stage / optimized Debian-based Python 3.11 image

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TEMP=/app/temp_cache \
    TMP=/app/temp_cache \
    TMPDIR=/app/temp_cache \
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

# Create cache, upload, and database bundle directories
RUN mkdir -p /app/temp_cache /app/uploads /app/data

# 1. Install lightweight CPU PyTorch first (~180MB instead of 2.8GB CUDA wheel)
RUN pip install --upgrade pip && \
    pip install torch --index-url https://download.pytorch.org/whl/cpu

# 2. Install remaining Python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -r /app/requirements.txt

# Copy backend source code
COPY backend /app/backend

# Set Python path to find app modules
ENV PYTHONPATH=/app/backend:/app

EXPOSE 8000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
