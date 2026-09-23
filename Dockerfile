# ==============================================================================
# All-In-One Production Dockerfile for GDP Assistant
# Bundles React Frontend + FastAPI AI Backend into a single deployable container
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build React Frontend
# ------------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /build

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Python 3.11 AI Backend Runtime
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
    PORT=8000

WORKDIR /app

# Install system dependencies for OpenCV, PDF rendering, and health probes
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create application directories
RUN mkdir -p /app/temp_cache /app/uploads /app/backend/data /app/model_cache

# Install lightweight CPU PyTorch and requirements
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r /app/requirements.txt

# Pre-download and bake the multilingual SentenceTransformer embedding model into the image
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

# Copy backend source code
COPY backend /app/backend

# Copy built frontend distribution from Stage 1
COPY --from=frontend-builder /build/dist /app/frontend/dist

# Set Python path
ENV PYTHONPATH=/app/backend:/app

EXPOSE 8000

# Health check
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
