import os
import re
import json
import sqlite3
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from app.config import settings

logger = logging.getLogger(__name__)

# Register standard adapters for SQLite
sqlite3.register_adapter(list, lambda l: json.dumps(l))
sqlite3.register_adapter(dict, lambda d: json.dumps(d))

# SQLAlchemy Base
Base = declarative_base()

# Database URL resolution with safe fallback
effective_db_url = settings.DATABASE_URL if settings.DATABASE_URL else "sqlite+aiosqlite:///temp_cache/dro_local.db"

# Dialect detection
is_sqlite = effective_db_url.startswith("sqlite")

# Engine options
engine_kwargs = {
    "echo": False,
    "future": True,
}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 10
    engine_kwargs["pool_pre_ping"] = True

# Async Engine
engine = create_async_engine(effective_db_url, **engine_kwargs)

# For SQLite: attach compatibility listener to dynamically translate PostgreSQL-specific idioms
if is_sqlite:
    @event.listens_for(engine.sync_engine, "before_cursor_execute", retval=True)
    def _sqlite_compat_listener(conn, cursor, statement, parameters, context, executemany):
        s = statement
        s = re.sub(r"CAST\s*\(\s*(\?|:\w+|[^\)]+)\s+AS\s+UUID\s*\)", r"\1", s, flags=re.IGNORECASE)
        s = re.sub(r"CAST\s*\(\s*(\?|:\w+|[^\)]+)\s+AS\s+INET\s*\)", r"\1", s, flags=re.IGNORECASE)
        s = re.sub(r"\bFOR\s+UPDATE\s+SKIP\s+LOCKED\b", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\bILIKE\b", "LIKE", s, flags=re.IGNORECASE)
        s = re.sub(r"\bNOW\(\)", "CURRENT_TIMESTAMP", s, flags=re.IGNORECASE)
        return s, parameters

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db_schema():
    """Idempotently create all tables if they do not exist."""
    # Ensure any SQLite directory exists
    if is_sqlite:
        db_path = effective_db_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
        if db_path and not db_path.startswith(":memory:"):
            dirname = os.path.dirname(os.path.abspath(db_path))
            if dirname:
                os.makedirs(dirname, exist_ok=True)

    # Import models so Base has all tables registered
    import models.orm  # noqa: F401
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if not is_sqlite:
            try:
                await conn.execute(text("ALTER TABLE extracted_entities DROP CONSTRAINT IF EXISTS extracted_entities_extracted_by_check;"))
            except Exception as e:
                logger.debug(f"Could not drop check constraint: {e}")
    logger.info(f"Database schema initialized successfully ({'SQLite' if is_sqlite else 'PostgreSQL'}).")


async def get_asyncpg_pool():
    """Raw connection pool for PostgreSQL bulk operations; returns None in SQLite mode."""
    if is_sqlite:
        return None
    try:
        import asyncpg
        return await asyncpg.create_pool(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            min_size=5,
            max_size=20
        )
    except Exception as e:
        logger.warning(f"PostgreSQL pool unavailable: {e}")
        return None

