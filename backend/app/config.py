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
    POSTGRES_USER: str = "dro_user"
    POSTGRES_PASSWORD: str = ""
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
    
    # OCR Engine (datalab / paddleocr)
    OCR_PROVIDER: str = "datalab"
    DATALAB_API_KEY: str = ""
    DATALAB_API_URL: str = "https://www.datalab.to/api/v1/convert"
    DATALAB_MODE: str = "balanced"
    DATALAB_TIMEOUT: int = 60

    # Production Performance & Pipeline Tuning
    OCR_MAX_IMAGE_DIMENSION: int = 1500      # Max long-edge px (up from 1100 for enhanced Tamil separation)
    OCR_DPI: int = 200                        # PDF render DPI (optimal balance for Tamil OCR)
    OCR_PREPROCESSING_ENABLED: bool = True     # Adaptive binarization, deskew, denoise
    LLM_FAST_TIMEOUT: float = 25.0            # Fast timeout with entity-grounded fallback
    LLM_FULL_TIMEOUT: float = 45.0            # Full timeout for LLM
    JOB_MAX_RETRIES: int = 3                  # Max job retries on transient failures
    JOB_STUCK_TIMEOUT_MINUTES: int = 5        # Auto-recover stuck processing jobs
    WORKER_POLL_INTERVAL: float = 1.5         # Worker polling frequency (seconds)
    
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
