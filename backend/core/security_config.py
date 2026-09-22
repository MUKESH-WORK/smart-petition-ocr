"""
Centralized Security Configuration Module
==========================================
All sensitive credentials are loaded exclusively from environment variables / .env file.
Zero hardcoded secrets. Validates presence on startup and provides clean accessors.
"""
import os
import logging
import secrets
from typing import Optional

logger = logging.getLogger(__name__)


def _env_required(key: str, context: str = "") -> str:
    """Get a required environment variable or raise a clear error."""
    val = os.environ.get(key, "").strip()
    if not val:
        msg = f"SECURITY: Required environment variable '{key}' is not set."
        if context:
            msg += f" Context: {context}"
        logger.error(msg)
        raise EnvironmentError(msg)
    return val


def _env_optional(key: str, default: str = "") -> str:
    """Get an optional environment variable with a safe default."""
    return os.environ.get(key, default).strip() or default


class SecurityConfig:
    """
    Centralized, secure environment credential accessor.
    All secrets come from environment variables — no hardcoded fallbacks.
    """

    def __init__(self):
        self._validated = False

    def validate_on_startup(self) -> None:
        """
        Validates critical secrets exist at application boot.
        Called once during app initialization.
        """
        warnings = []

        # Check SECRET_KEY
        secret_key = os.environ.get("SECRET_KEY", "").strip()
        if not secret_key:
            generated = secrets.token_urlsafe(48)
            os.environ["SECRET_KEY"] = generated
            warnings.append("SECRET_KEY was empty — generated ephemeral key (set in .env for persistence)")
        elif len(secret_key) < 32:
            warnings.append("SECRET_KEY is shorter than 32 characters — consider a stronger key for production")

        # Check DATALAB_API_KEY if OCR is set to datalab
        ocr_provider = os.environ.get("OCR_PROVIDER", "datalab").strip()
        if ocr_provider == "datalab":
            datalab_key = os.environ.get("DATALAB_API_KEY", "").strip()
            if not datalab_key:
                warnings.append("DATALAB_API_KEY is not set — OCR will fail for datalab provider")

        # Postgres credentials (only validate if not using SQLite)
        use_sqlite = os.environ.get("USE_SQLITE", "true").strip().lower()
        if use_sqlite not in ("true", "1", "yes"):
            pg_pass = os.environ.get("POSTGRES_PASSWORD", "").strip()
            if not pg_pass:
                warnings.append("POSTGRES_PASSWORD is empty — PostgreSQL connections will fail")
            elif pg_pass in ("postgres", "password", "123456"):
                warnings.append("POSTGRES_PASSWORD uses a trivially weak value — change for production")

        for w in warnings:
            logger.warning(f"[SECURITY] {w}")

        self._validated = True
        logger.info("[SECURITY] Startup credential validation complete.")

    # ── Accessors ──────────────────────────────────────────────

    @property
    def postgres_user(self) -> str:
        return _env_optional("POSTGRES_USER", "dro_user")

    @property
    def postgres_password(self) -> str:
        return _env_optional("POSTGRES_PASSWORD", "")

    @property
    def postgres_host(self) -> str:
        return _env_optional("POSTGRES_HOST", "localhost")

    @property
    def postgres_port(self) -> int:
        return int(_env_optional("POSTGRES_PORT", "5432"))

    @property
    def postgres_db(self) -> str:
        return _env_optional("POSTGRES_DB", "dro_grievance_db")

    @property
    def database_url(self) -> str:
        """Async PostgreSQL connection string."""
        env_url = os.environ.get("DATABASE_URL", "").strip()
        if env_url:
            return env_url
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def database_sync_url(self) -> str:
        """Sync PostgreSQL connection string."""
        env_url = os.environ.get("DATABASE_SYNC_URL", "").strip()
        if env_url:
            return env_url
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def secret_key(self) -> str:
        return _env_optional("SECRET_KEY", "")

    @property
    def datalab_api_key(self) -> str:
        return _env_optional("DATALAB_API_KEY", "")


# Singleton instance
security_config = SecurityConfig()
