import os
import re
import json
import sqlite3
import socket
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import event, text
from app.config import settings

logger = logging.getLogger(__name__)

# Register standard adapters for SQLite
sqlite3.register_adapter(list, lambda l: json.dumps(l))
sqlite3.register_adapter(dict, lambda d: json.dumps(d))

# SQLAlchemy Bases
Base = declarative_base()
UserBase = Base
AdminBase = Base


def _is_postgres_available(url: str) -> bool:
    """Fast probe to check if PostgreSQL is reachable before asyncpg fails in worker loops."""
    if not url or not ("postgres" in url or "asyncpg" in url):
        return False
    try:
        host = getattr(settings, "POSTGRES_HOST", "localhost")
        port = int(getattr(settings, "POSTGRES_PORT", 5432))
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except Exception:
        return False


# Helper to locate existing SQLite DB files across cwd/backend
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_repo_root = os.path.dirname(_backend_dir)

def _find_sqlite_path(db_name: str) -> str:
    for candidate in [
        os.path.join(_backend_dir, "temp_cache", db_name),
        os.path.join(_repo_root, "temp_cache", db_name),
        os.path.join(os.getcwd(), "temp_cache", db_name),
        os.path.join(os.getcwd(), "backend", "temp_cache", db_name),
    ]:
        if os.path.isfile(candidate) and os.path.getsize(candidate) > 0:
            return os.path.abspath(candidate).replace("\\", "/")
    return os.path.abspath(os.path.join(_backend_dir, "temp_cache", db_name)).replace("\\", "/")

# Determine database URLs with automatic SQLite fallback
use_sqlite = getattr(settings, "USE_SQLITE", True) or os.getenv("USE_SQLITE", "true").lower() in ("true", "1", "yes")
pg_configured = not use_sqlite and bool(settings.DATABASE_URL and ("postgres" in settings.DATABASE_URL or "asyncpg" in settings.DATABASE_URL))
pg_online = _is_postgres_available(settings.DATABASE_URL) if pg_configured else False

if pg_configured and pg_online:
    user_db_url = settings.DATABASE_URL
    admin_db_url = getattr(settings, "ADMIN_DATABASE_URL", None) or settings.DATABASE_URL
    is_sqlite = False
    is_admin_sqlite = False
    logger.info("Connected to PostgreSQL as primary database.")
else:
    if pg_configured and not pg_online:
        logger.warning("PostgreSQL (port 5432) is offline or unreachable. Seamlessly activating high-performance SQLite dual databases.")
    user_sqlite_path = _find_sqlite_path("dro_user.db")
    admin_sqlite_path = _find_sqlite_path("dro_admin.db")
    user_db_url = f"sqlite+aiosqlite:///{user_sqlite_path}"
    admin_db_url = f"sqlite+aiosqlite:///{admin_sqlite_path}"
    is_sqlite = True
    is_admin_sqlite = True
    logger.info(f"Active SQLite dual databases: user={user_sqlite_path}, admin={admin_sqlite_path}")

effective_db_url = user_db_url


def _get_engine_kwargs(sqlite_flag: bool) -> dict:
    kwargs = {"echo": False, "future": True}
    if sqlite_flag:
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = getattr(settings, "DB_POOL_SIZE", 25)
        kwargs["max_overflow"] = getattr(settings, "DB_MAX_OVERFLOW", 20)
        kwargs["pool_timeout"] = getattr(settings, "DB_POOL_TIMEOUT", 30)
        kwargs["pool_pre_ping"] = True
    return kwargs


# Dual Engines
user_engine = create_async_engine(user_db_url, **_get_engine_kwargs(is_sqlite))
admin_engine = create_async_engine(admin_db_url, **_get_engine_kwargs(is_admin_sqlite))
engine = user_engine  # Backwards compatibility


def _attach_sqlite_compat(target_engine):
    @event.listens_for(target_engine.sync_engine, "before_cursor_execute", retval=True)
    def _sqlite_compat_listener(conn, cursor, statement, parameters, context, executemany):
        s = statement
        s = re.sub(r"CAST\s*\(\s*(\?|:\w+|[^\)]+)\s+AS\s+UUID\s*\)", r"\1", s, flags=re.IGNORECASE)
        s = re.sub(r"CAST\s*\(\s*(\?|:\w+|[^\)]+)\s+AS\s+INET\s*\)", r"\1", s, flags=re.IGNORECASE)
        s = re.sub(r"\bFOR\s+UPDATE\s+SKIP\s+LOCKED\b", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\bILIKE\b", "LIKE", s, flags=re.IGNORECASE)
        s = re.sub(r"\bNOW\(\)", "CURRENT_TIMESTAMP", s, flags=re.IGNORECASE)
        return s, parameters


if is_sqlite:
    _attach_sqlite_compat(user_engine)
if is_admin_sqlite:
    _attach_sqlite_compat(admin_engine)

# Async Session Factories
UserAsyncSessionLocal = async_sessionmaker(
    bind=user_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)
AsyncSessionLocal = UserAsyncSessionLocal  # Backwards compatibility

AdminAsyncSessionLocal = async_sessionmaker(
    bind=admin_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_user_db():
    async with UserAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


get_db = get_user_db  # Backwards compatibility


async def get_admin_db():
    async with AdminAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def _ensure_sqlite_dir(url: str):
    db_path = url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
    if db_path and not db_path.startswith(":memory:"):
        dirname = os.path.dirname(os.path.abspath(db_path))
        if dirname:
            os.makedirs(dirname, exist_ok=True)


async def init_db_schema():
    """Idempotently create tables for both User DB and Admin DB."""
    if is_sqlite:
        _ensure_sqlite_dir(user_db_url)
    if is_admin_sqlite:
        _ensure_sqlite_dir(admin_db_url)

    import models.orm  # noqa: F401

    # 1. Initialize User Database
    async with user_engine.begin() as conn:
        await conn.run_sync(UserBase.metadata.create_all)
        if not is_sqlite:
            try:
                await conn.execute(text("ALTER TABLE extracted_entities DROP CONSTRAINT IF EXISTS extracted_entities_extracted_by_check;"))
            except Exception as e:
                logger.debug(f"User DB constraint note: {e}")
            try:
                await conn.execute(text("ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_status_check;"))
                await conn.execute(text("""
                    ALTER TABLE sources ADD CONSTRAINT sources_status_check 
                    CHECK (status IN (
                        'uploaded', 'pending', 'processing', 'ocr_processing', 'ocr_complete',
                        'ocr_review', 'vector_indexing', 'vector_indexed', 'entity_extracting',
                        'entity_extracted', 'ai_analyzing', 'draft_ready', 'officer_approved',
                        'pushed_to_dro', 'flagged_for_review', 'rejected', 'completed', 'failed'
                    ));
                """))
            except Exception as e:
                logger.debug(f"Could not update sources_status_check constraint: {e}")
            try:
                await conn.execute(text("ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS complainant_signatory VARCHAR(200);"))
            except Exception as e:
                logger.debug(f"Could not add complainant_signatory column: {e}")

        # Ensure dynamic officer columns & sources.phash exist across SQLite and Postgres
        for col_sql in [
            "ALTER TABLE officers ADD COLUMN name VARCHAR(100);",
            "ALTER TABLE officers ADD COLUMN email VARCHAR(150);",
            "ALTER TABLE officers ADD COLUMN mobile VARCHAR(20);",
            "ALTER TABLE officers ADD COLUMN is_admin BOOLEAN DEFAULT 0;",
            "ALTER TABLE officers ADD COLUMN status VARCHAR(20) DEFAULT 'Inactive';",
            "ALTER TABLE officers ADD COLUMN last_login TIMESTAMP;",
            "ALTER TABLE officers ADD COLUMN designation VARCHAR(100);",
            "ALTER TABLE officers ADD COLUMN department VARCHAR(100);",
            "ALTER TABLE sources ADD COLUMN phash VARCHAR(64);",
            "ALTER TABLE semantic_cache ADD COLUMN expires_at TIMESTAMP;",
            "ALTER TABLE semantic_cache ADD COLUMN prompt_text TEXT;"
        ]:
            try:
                await conn.execute(text(col_sql))
            except Exception:
                pass

        # Ensure AI Semantic Cache table exists in User DB
        if is_sqlite:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS semantic_cache (
                    id VARCHAR(50) PRIMARY KEY,
                    prompt_hash VARCHAR(64) NOT NULL,
                    prompt_text TEXT NOT NULL,
                    embedding JSON,
                    response_json TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                );
            """))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sem_cache_hash ON semantic_cache(prompt_hash);"))
        else:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS semantic_cache (
                    id VARCHAR(50) PRIMARY KEY,
                    prompt_hash VARCHAR(64) NOT NULL,
                    prompt_text TEXT NOT NULL,
                    embedding vector(384),
                    response_json JSONB NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                );
            """))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sem_cache_hash ON semantic_cache(prompt_hash);"))

    # 2. Initialize Admin Database
    if not is_admin_sqlite:
        try:
            async with admin_engine.connect() as conn:
                await conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        except Exception as e:
            logger.debug(f"Could not enable pgvector on admin db: {e}")

    async with admin_engine.begin() as conn:

        # Ensure admin tables exist
        if is_admin_sqlite:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS admin_users (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    name_tamil VARCHAR(100),
                    mobile VARCHAR(20),
                    email VARCHAR(150),
                    password_hash VARCHAR(255),
                    is_admin BOOLEAN DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'Active',
                    last_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS admin_activity_log (
                    id VARCHAR(50) PRIMARY KEY,
                    type VARCHAR(50) NOT NULL,
                    detail TEXT NOT NULL,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    officer_id VARCHAR(50)
                );
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS system_backups (
                    id VARCHAR(50) PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    size_bytes BIGINT,
                    record_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(50)
                );
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS master_locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    district_code VARCHAR(10),
                    district_name_tamil VARCHAR(100),
                    district_name_en VARCHAR(100),
                    division_code VARCHAR(10),
                    division_name_tamil VARCHAR(100),
                    division_name_en VARCHAR(100),
                    taluk_code VARCHAR(10),
                    taluk_name_tamil VARCHAR(100),
                    taluk_name_en VARCHAR(100),
                    firka_code VARCHAR(10),
                    firka_name_tamil VARCHAR(100),
                    firka_name_en VARCHAR(100),
                    block_code VARCHAR(10),
                    block_name_tamil VARCHAR(100),
                    block_name_en VARCHAR(100),
                    village_code VARCHAR(10),
                    village_name_tamil VARCHAR(100),
                    village_name_en VARCHAR(100),
                    local_body_type VARCHAR(100),
                    ward_no INTEGER,
                    ward_name_tamil VARCHAR(200),
                    ward_name_en VARCHAR(200),
                    pincode VARCHAR(10),
                    search_text TEXT,
                    embedding JSON,
                    sub_departments VARCHAR(255)
                );
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cm_taxonomy_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    department VARCHAR(200) NOT NULL,
                    department_code VARCHAR(50),
                    sub_department VARCHAR(200),
                    grievance_type VARCHAR(255) NOT NULL,
                    grievance_sub_type VARCHAR(255) NOT NULL,
                    responsible_officer VARCHAR(255),
                    search_text TEXT,
                    embedding JSON
                );
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cm_grievance_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category VARCHAR(100) NOT NULL,
                    channel_name VARCHAR(255) NOT NULL,
                    channel_code VARCHAR(50) UNIQUE,
                    is_active BOOLEAN DEFAULT 1,
                    description TEXT
                );
            """))
            # Ensure sub_departments, department, role and password_hash exist on existing sqlite db
            for col_stmt in [
                "ALTER TABLE master_locations ADD COLUMN sub_departments VARCHAR(255);",
                "ALTER TABLE admin_users ADD COLUMN password_hash VARCHAR(255);",
                "ALTER TABLE admin_users ADD COLUMN department VARCHAR(100);",
                "ALTER TABLE admin_users ADD COLUMN role VARCHAR(50);",
            ]:
                try:
                    await conn.execute(text(col_stmt))
                except Exception:
                    pass
        else:
            # PostgreSQL schema creation with pgvector support
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS admin_users (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    name_tamil VARCHAR(100),
                    mobile VARCHAR(20),
                    email VARCHAR(150),
                    password_hash VARCHAR(255),
                    department VARCHAR(100),
                    role VARCHAR(50),
                    is_admin BOOLEAN DEFAULT FALSE,
                    status VARCHAR(20) DEFAULT 'Active',
                    last_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS admin_activity_log (
                    id VARCHAR(50) PRIMARY KEY,
                    type VARCHAR(50) NOT NULL,
                    detail TEXT NOT NULL,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    officer_id VARCHAR(50)
                );
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS system_backups (
                    id VARCHAR(50) PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    size_bytes BIGINT,
                    record_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(50)
                );
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS master_locations (
                    id SERIAL PRIMARY KEY,
                    district_code VARCHAR(10),
                    district_name_tamil VARCHAR(100),
                    district_name_en VARCHAR(100),
                    division_code VARCHAR(10),
                    division_name_tamil VARCHAR(100),
                    division_name_en VARCHAR(100),
                    taluk_code VARCHAR(10),
                    taluk_name_tamil VARCHAR(100),
                    taluk_name_en VARCHAR(100),
                    firka_code VARCHAR(10),
                    firka_name_tamil VARCHAR(100),
                    firka_name_en VARCHAR(100),
                    block_code VARCHAR(10),
                    block_name_tamil VARCHAR(100),
                    block_name_en VARCHAR(100),
                    village_code VARCHAR(10),
                    village_name_tamil VARCHAR(100),
                    village_name_en VARCHAR(100),
                    local_body_type VARCHAR(100),
                    ward_no INTEGER,
                    ward_name_tamil VARCHAR(200),
                    ward_name_en VARCHAR(200),
                    pincode VARCHAR(10),
                    search_text TEXT,
                    embedding vector(384),
                    sub_departments VARCHAR(255)
                );
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cm_taxonomy_mappings (
                    id SERIAL PRIMARY KEY,
                    department VARCHAR(200) NOT NULL,
                    department_code VARCHAR(50),
                    sub_department VARCHAR(200),
                    grievance_type VARCHAR(255) NOT NULL,
                    grievance_sub_type VARCHAR(255) NOT NULL,
                    responsible_officer VARCHAR(255),
                    search_text TEXT,
                    embedding vector(384)
                );
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cm_grievance_channels (
                    id SERIAL PRIMARY KEY,
                    category VARCHAR(100) NOT NULL,
                    channel_name VARCHAR(255) NOT NULL,
                    channel_code VARCHAR(50) UNIQUE,
                    is_active BOOLEAN DEFAULT TRUE,
                    description TEXT
                );
            """))
            for col_stmt in [
                "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS sub_departments VARCHAR(255);",
                "ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);",
                "ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS department VARCHAR(100);",
                "ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS role VARCHAR(50);",
            ]:
                try:
                    await conn.execute(text(col_stmt))
                except Exception:
                    pass

    logger.info(f"Database schemas initialized successfully (User DB: {'SQLite' if is_sqlite else 'PostgreSQL'}, Admin DB: {'SQLite' if is_admin_sqlite else 'PostgreSQL'}).")


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
