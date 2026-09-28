import os
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

logger = logging.getLogger("gdp_database")

Base = declarative_base()


def get_database_url() -> str:
    use_sqlite = os.getenv("USE_SQLITE", "false").lower() in ("true", "1", "yes")
    if use_sqlite:
        os.makedirs("data", exist_ok=True)
        return "sqlite+aiosqlite:///./data/gdp_assistant.db"

    raw_url = os.getenv("DATABASE_URL", "")
    if not raw_url:
        try:
            import asyncpg
            raw_url = "postgresql://dro_user:GDP_Pr0d_S3cur3_2026!@postgres:5432/dro_grievance_db"
        except ImportError:
            logger.info("asyncpg driver not present in environment. Defaulting to high-performance SQLite engine.")
            os.makedirs("data", exist_ok=True)
            return "sqlite+aiosqlite:///./data/gdp_assistant.db"

    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return raw_url


DATABASE_URL = get_database_url()

engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}

try:
    if "sqlite" in DATABASE_URL:
        engine = create_async_engine(DATABASE_URL, **engine_kwargs)
    else:
        engine = create_async_engine(
            DATABASE_URL,
            pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            **engine_kwargs
        )
except Exception as engine_err:
    logger.warning(f"Async engine creation for PostgreSQL failed ({engine_err}). Falling back to SQLite.")
    os.makedirs("data", exist_ok=True)
    DATABASE_URL = "sqlite+aiosqlite:///./data/gdp_assistant.db"
    engine = create_async_engine(DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.warning(f"Database initialization warning (will retry on demand): {e}")
