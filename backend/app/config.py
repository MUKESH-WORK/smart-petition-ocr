import os
from typing import Optional
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    try:
        from pydantic import BaseSettings
        SettingsConfigDict = None
    except ImportError:
        class BaseSettings:
            def __init__(self, **kwargs):
                for k, v in self.__class__.__dict__.items():
                    if not k.startswith("_") and not callable(v):
                        env_val = os.getenv(k)
                        setattr(self, k, env_val if env_val is not None else v)
        SettingsConfigDict = None


class Settings(BaseSettings):
    # App info
    PROJECT_NAME: str = "DRO Grievance AI Module"
    API_V1_STR: str = "/api/v1"
    
    # Database Settings
    USE_SQLITE: bool = True
    POSTGRES_USER: str = "dro_user"
    POSTGRES_PASSWORD: str = os.environ.get("POSTGRES_PASSWORD", "")
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "dro_grievance_db"
    
    DATABASE_URL: str = ""
    DATABASE_SYNC_URL: str = ""
    
    # Security
    SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175,http://127.0.0.1:5176"
    SEED_DEMO_DATA: bool = False
    
    # NLP & Embeddings
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIM: int = 384
    
    # LLM Engine (ollama, llama_cpp, openai_compat)
    LLM_PROVIDER: str = "ollama"
    LLM_API_BASE_URL: str = "http://localhost:11434/v1"
    LLM_MODEL_NAME: str = "qwen2.5:3b-instruct"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1024
    
    # DRO External Portal Bridge
    DRO_PORTAL_BASE_URL: str = "http://localhost:9000"
    
    # File Storage
    UPLOAD_DIR: str = "uploads"
    STATIC_MEDIA_DIR: str = "static/media"
    STORE_FILE_BYTEA: bool = False
    
    # OCR Engine (chandra_cloud / chandra_local / datalab)
    OCR_PROVIDER: str = "datalab"
    DATALAB_API_KEY: str = ""
    DATALAB_API_URL: str = "https://www.datalab.to/api/v1/convert"
    DATALAB_MODE: str = "accurate"             # Default to high-accuracy Chandra OCR
    DATALAB_FALLBACK_MODE: str = "balanced"    # Fallback to balanced mode on timeout
    DATALAB_TIMEOUT: int = 45                  # Accurate mode timeout
    DATALAB_FALLBACK_TIMEOUT: int = 25         # Balanced fallback timeout
    
    # Local Chandra OCR V2 5.6B Engine (Local Inference Runner)
    LOCAL_CHANDRA_ENABLED: bool = False
    LOCAL_CHANDRA_URL: str = "http://127.0.0.1:8088/v1"
    LOCAL_CHANDRA_TIMEOUT: float = 30.0
    LOCAL_CHANDRA_BATCH_SIZE: int = 8
    LOCAL_CHANDRA_TARGET_FPS: float = 12.0

    # Production Performance, Workers & Concurrency
    OCR_MAX_IMAGE_DIMENSION: int = 1500      # Max long-edge px (up from 1100 for enhanced Tamil separation)
    OCR_DPI: int = 200                        # PDF render DPI (optimal balance for Tamil OCR)
    OCR_PREPROCESSING_ENABLED: bool = True     # Adaptive binarization, deskew, denoise
    
    # Multi-User Concurrency & Queue Workers (10 simultaneous users)
    WORKER_CONCURRENCY: int = 4               # Number of concurrent async workers
    WORKER_POLL_INTERVAL: float = 0.8         # Worker polling frequency (sub-second responsiveness)
    JOB_MAX_RETRIES: int = 3                  # Max job retries on transient failures
    JOB_STUCK_TIMEOUT_MINUTES: int = 5        # Auto-recover stuck processing jobs
    
    # Database Connection Pool
    DB_POOL_SIZE: int = 25
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    
    # LLM Concurrency, Warmup & Output Preservation
    LLM_FAST_TIMEOUT: float = 75.0            # Fast timeout with entity-grounded fallback
    LLM_FULL_TIMEOUT: float = 120.0           # Full timeout for LLM
    LLM_MAX_CONCURRENCY: int = 4              # Semaphore to prevent GPU bottleneck / OOM
    LLM_KEEP_ALIVE_INTERVAL: int = 120        # Heartbeat ping every 2 minutes
    LLM_KEEP_ALIVE_ENABLED: bool = True       # Keep LLM resident in VRAM
    
    # AI Semantic Cache
    SEMANTIC_CACHE_ENABLED: bool = True
    SEMANTIC_CACHE_THRESHOLD: float = 0.92    # Vector cosine similarity threshold for cache hit
    SEMANTIC_CACHE_TTL_DAYS: int = 30         # Cache TTL in days
    
    # Deduplication & Perceptual Hashing
    DEDUP_EXACT_HASH_ENABLED: bool = True
    DEDUP_PHASH_ENABLED: bool = True
    DEDUP_PHASH_THRESHOLD: int = 4            # Max Hamming distance for image perceptual similarity

    if SettingsConfigDict is not None:
        _env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        model_config = SettingsConfigDict(
            env_file=_env_path if os.path.exists(_env_path) else ".env",
            env_file_encoding="utf-8",
            extra="ignore"
        )


settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.STATIC_MEDIA_DIR, exist_ok=True)
