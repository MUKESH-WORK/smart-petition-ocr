# ==============================================================================
# Complete All-In-One Single Production Dockerfile for GDP Assistant
# Bundles React 19 Frontend + FastAPI Backend + OCR Worker + Redis + Nginx into ONE Image
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build React 19 Frontend
# ------------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /build

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Unified Python + Nginx + Redis + Worker Runtime
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TEMP=/app/temp_cache \
    TMP=/app/temp_cache \
    TMPDIR=/app/temp_cache \
    HF_HOME=/app/model_cache \
    SENTENCE_TRANSFORMERS_HOME=/app/model_cache \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend:/app

WORKDIR /app

# Install OS packages (Nginx, Supervisor, Redis, PDF & CV libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    wget \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    poppler-utils \
    nginx \
    supervisor \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Create application, storage, media, and cache directories
RUN mkdir -p /app/temp_cache /app/uploads /app/storage/uploads /app/static/media /app/data /app/model_cache /var/log/supervisor

# 1. Install lightweight CPU PyTorch wheel
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 2. Install application Python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r /app/requirements.txt

# 3. Copy built frontend distribution to Nginx html folder
COPY --from=frontend-builder /build/dist /usr/share/nginx/html

# 4. Copy Nginx and Supervisor configs
RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/sites-available/default
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 5. Copy backend source code
COPY backend /app

EXPOSE 80

HEALTHCHECK --interval=20s --timeout=5s --retries=3 --start-period=15s \
    CMD curl -f http://localhost/health || exit 1

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
