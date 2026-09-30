import os
import re
import json
import socket
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Declarative Bases
Base = declarative_base()
UserBase = Base
AdminBase = Base

# Global flags (pure PostgreSQL 16 architecture)
is_sqlite: bool = False
is_admin_sqlite: bool = False


def _build_postgres_url(custom_url: Optional[str] = None) -> str:
    """Builds or validates the async PostgreSQL connection URL."""
    if custom_url and ("postgres" in custom_url or "asyncpg" in custom_url):
        return custom_url
    if getattr(settings, "DATABASE_URL", "") and ("postgres" in settings.DATABASE_URL or "asyncpg" in settings.DATABASE_URL):
        return settings.DATABASE_URL
    user = getattr(settings, "POSTGRES_USER", "dro_user") or "dro_user"
    pwd = getattr(settings, "POSTGRES_PASSWORD", "dro_password_2026") or "dro_password_2026"
    host = getattr(settings, "POSTGRES_HOST", "localhost") or "localhost"
    port = getattr(settings, "POSTGRES_PORT", 5432) or 5432
    db_name = getattr(settings, "POSTGRES_DB", "dro_grievance_db") or "dro_grievance_db"
    return f"postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{db_name}"


# Unified PostgreSQL Connection URLs
user_db_url = _build_postgres_url(settings.DATABASE_URL)
admin_db_url = _build_postgres_url(getattr(settings, "ADMIN_DATABASE_URL", None) or settings.DATABASE_URL)
audit_db_url = _build_postgres_url(getattr(settings, "AUDIT_DATABASE_URL", None) or settings.DATABASE_URL)
readonly_db_url = _build_postgres_url(getattr(settings, "DATABASE_READONLY_URL", None) or settings.DATABASE_URL)
effective_db_url = user_db_url


def _get_engine_kwargs(readonly: bool = False) -> dict:
    kwargs: Dict[str, Any] = {
        "echo": False,
        "future": True,
        "pool_size": getattr(settings, "DB_POOL_SIZE", 25),
        "max_overflow": getattr(settings, "DB_MAX_OVERFLOW", 20),
        "pool_timeout": getattr(settings, "DB_POOL_TIMEOUT", 30),
        "pool_pre_ping": True,
    }
    if readonly:
        kwargs["connect_args"] = {
            "server_settings": {
                "default_transaction_read_only": "on"
            }
        }
    return kwargs


# Dual/Multi Engines on PostgreSQL 16
user_engine = create_async_engine(user_db_url, **_get_engine_kwargs())
admin_engine = create_async_engine(admin_db_url, **_get_engine_kwargs())
audit_engine = create_async_engine(audit_db_url, **_get_engine_kwargs())
readonly_engine = create_async_engine(readonly_db_url, **_get_engine_kwargs(readonly=True))
engine = user_engine  # Backwards compatibility

logger.info(f"PostgreSQL 16 engines initialized (Primary: {user_db_url.split('@')[-1]}, Audit: {audit_db_url.split('@')[-1]}, Read-Only: {readonly_db_url.split('@')[-1]}).")

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

AuditAsyncSessionLocal = async_sessionmaker(
    bind=audit_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

ReadOnlyAsyncSessionLocal = async_sessionmaker(
    bind=readonly_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


# FastAPI Session Dependencies
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


async def get_audit_db():
    """
    Dedicated PostgreSQL Audit DB session for non-blocking, isolated audit logging.
    """
    async with AuditAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_readonly_db():
    """
    Safe Read-Only PostgreSQL session dependency for queries, analytical reports, and exports.
    Guarantees no modifications or accidental writes can occur at the database level.
    """
    async with ReadOnlyAsyncSessionLocal() as session:
        try:
            await session.execute(text("SET TRANSACTION READ ONLY;"))
            yield session
        finally:
            await session.close()


async def init_db_schema():
    """Idempotently initialize schemas, extensions, and tables in PostgreSQL 16."""
    import models.orm  # noqa: F401

    # 1. Enable pgvector extension
    try:
        async with user_engine.begin() as ext_conn:
            await ext_conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    except Exception as e:
        logger.warning(f"Vector extension check notice on primary db: {e}")

    # 2. Create User / Grievance tables
    async with user_engine.begin() as conn:
        await conn.run_sync(UserBase.metadata.create_all)

    # 3. Dynamic column safety & PostgreSQL specific constraints
    pg_safe_alters = [
        "ALTER TABLE extracted_entities DROP CONSTRAINT IF EXISTS extracted_entities_extracted_by_check;",
        "ALTER TABLE audit_log ALTER COLUMN source_id TYPE VARCHAR(100);",
        "ALTER TABLE audit_log ALTER COLUMN ip_address TYPE VARCHAR(50);",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS complainant_signatory VARCHAR(200);",
        "ALTER TABLE officers ADD COLUMN IF NOT EXISTS name VARCHAR(100);",
        "ALTER TABLE officers ADD COLUMN IF NOT EXISTS email VARCHAR(150);",
        "ALTER TABLE officers ADD COLUMN IF NOT EXISTS mobile VARCHAR(20);",
        "ALTER TABLE officers ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE officers ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'Inactive';",
        "ALTER TABLE officers ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;",
        "ALTER TABLE officers ADD COLUMN IF NOT EXISTS designation VARCHAR(100);",
        "ALTER TABLE officers ADD COLUMN IF NOT EXISTS department VARCHAR(100);",
        "ALTER TABLE sources ADD COLUMN IF NOT EXISTS phash VARCHAR(64);",
        "ALTER TABLE semantic_cache ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP;",
        "ALTER TABLE semantic_cache ADD COLUMN IF NOT EXISTS prompt_text TEXT;",
        "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS embedding JSONB;",
        "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS sub_departments VARCHAR(500);",
        "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS district_name_en VARCHAR(200);",
        "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS division_code VARCHAR(50);",
        "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS division_name_tamil VARCHAR(200);",
        "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS division_name_en VARCHAR(200);",
        "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS taluk_name_en VARCHAR(200);",
        "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS firka_name_en VARCHAR(200);",
        "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS block_name_en VARCHAR(200);",
        "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS village_name_en VARCHAR(200);",
        "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS local_body_type VARCHAR(200);",
        "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS ward_no INTEGER;",
        "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS ward_name_tamil VARCHAR(200);",
        "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS ward_name_en VARCHAR(200);",
        "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS pincode VARCHAR(20);",
        "ALTER TABLE master_locations ADD COLUMN IF NOT EXISTS search_text TEXT;"
    ]
    for alter_sql in pg_safe_alters:
        try:
            async with user_engine.begin() as alter_conn:
                await alter_conn.execute(text(alter_sql))
        except Exception as e:
            logger.debug(f"Schema alter note: {e}")

    # Ensure sources table constraints and index
    try:
        async with user_engine.begin() as alter_conn:
            await alter_conn.execute(text("""
                DO $$
                DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'sources'::regclass
                          AND contype = 'u'
                          AND (conname LIKE '%file_hash%' OR conname = 'sources_file_hash_key')
                    ) LOOP
                        EXECUTE 'ALTER TABLE sources DROP CONSTRAINT IF EXISTS ' || quote_ident(r.conname);
                    END LOOP;
                END $$;
            """))
            await alter_conn.execute(text("DROP INDEX IF EXISTS idx_sources_file_hash_unique;"))
            await alter_conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sources_file_hash ON sources(file_hash);"))
            await alter_conn.execute(text("ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_status_check;"))
            await alter_conn.execute(text("""
                ALTER TABLE sources ADD CONSTRAINT sources_status_check 
                CHECK (status IN (
                    'uploaded',
                    'pending',
                    'processing',
                    'ocr_processing',
                    'ocr_complete',
                    'ocr_review',
                    'vector_indexing',
                    'vector_indexed',
                    'entity_extracting',
                    'entity_extracted',
                    'ai_analyzing',
                    'draft_ready',
                    'officer_approved',
                    'pushed_to_dro',
                    'duplicate_found',
                    'duplicate_pending',
                    'rejected',
                    'completed',
                    'failed'
                ));
            """))
    except Exception as e:
        logger.debug(f"Sources constraint setup note: {e}")

    # 4. Ensure Semantic Cache table exists with JSONB & pgvector in PostgreSQL
    async with user_engine.begin() as sem_conn:
        await sem_conn.execute(text("""
            CREATE TABLE IF NOT EXISTS semantic_cache (
                id VARCHAR(50) PRIMARY KEY,
                prompt_hash VARCHAR(64) NOT NULL,
                prompt_text TEXT NOT NULL,
                embedding JSONB,
                response_json JSONB NOT NULL,
                hit_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            );
        """))
        await sem_conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sem_cache_hash ON semantic_cache(prompt_hash);"))

    # 5. Initialize Admin Database Tables in PostgreSQL
    try:
        async with admin_engine.begin() as ext_conn:
            await ext_conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    except Exception as e:
        logger.debug(f"Vector extension check notice on admin db: {e}")

    async with admin_engine.begin() as conn:
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
                district_code VARCHAR(50),
                district_name_tamil VARCHAR(200),
                district_name_en VARCHAR(200),
                division_code VARCHAR(50),
                division_name_tamil VARCHAR(200),
                division_name_en VARCHAR(200),
                taluk_code VARCHAR(50),
                taluk_name_tamil VARCHAR(200),
                taluk_name_en VARCHAR(200),
                firka_code VARCHAR(50),
                firka_name_tamil VARCHAR(200),
                firka_name_en VARCHAR(200),
                block_code VARCHAR(50),
                block_name_tamil VARCHAR(200),
                block_name_en VARCHAR(200),
                village_code VARCHAR(50),
                village_name_tamil VARCHAR(200),
                village_name_en VARCHAR(200),
                local_body_type VARCHAR(200),
                ward_no INTEGER,
                ward_name_tamil VARCHAR(200),
                ward_name_en VARCHAR(200),
                pincode VARCHAR(20),
                search_text TEXT,
                embedding JSONB,
                sub_departments VARCHAR(500)
            );
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cm_taxonomy_mappings (
                id SERIAL PRIMARY KEY,
                department VARCHAR(255) NOT NULL,
                department_code VARCHAR(100),
                sub_department VARCHAR(255),
                grievance_type VARCHAR(255) NOT NULL,
                grievance_sub_type VARCHAR(255) NOT NULL,
                responsible_officer TEXT,
                search_text TEXT,
                embedding JSONB
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
            "ALTER TABLE cm_taxonomy_mappings ALTER COLUMN responsible_officer TYPE TEXT;",
        ]:
            try:
                await conn.execute(text(col_stmt))
            except Exception:
                pass

    # 6. Initialize PostgreSQL Native Audit Store & Movement History
    async with audit_engine.begin() as a_conn:
        await a_conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id BIGSERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                source_id VARCHAR(50),
                officer_id VARCHAR(50),
                action VARCHAR(100) NOT NULL,
                details JSONB,
                ip_address VARCHAR(50)
            );
        """))
        await a_conn.execute(text("""
            CREATE TABLE IF NOT EXISTS admin_activity_log (
                id VARCHAR(50) PRIMARY KEY,
                type VARCHAR(50) NOT NULL,
                detail TEXT NOT NULL,
                date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                officer_id VARCHAR(50)
            );
        """))
        await a_conn.execute(text("""
            CREATE TABLE IF NOT EXISTS petition_movements (
                id BIGSERIAL PRIMARY KEY,
                petition_id VARCHAR(50) NOT NULL,
                movement_type VARCHAR(50) NOT NULL,
                from_officer VARCHAR(100),
                to_officer VARCHAR(100),
                status VARCHAR(50),
                remark TEXT,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))
        # High-performance indexes for audit trail & movements
        await a_conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_officer ON audit_log(officer_id);"))
        await a_conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp DESC);"))
        await a_conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_source ON audit_log(source_id);"))
        await a_conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);"))
        await a_conn.execute(text("CREATE INDEX IF NOT EXISTS idx_act_officer ON admin_activity_log(officer_id);"))
        await a_conn.execute(text("CREATE INDEX IF NOT EXISTS idx_act_date ON admin_activity_log(date DESC);"))
        await a_conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mov_pet ON petition_movements(petition_id);"))
        await a_conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mov_time ON petition_movements(timestamp DESC);"))

    logger.info("Database schemas initialized successfully (User DB: PostgreSQL, Admin DB: PostgreSQL, Audit Store: PostgreSQL, Read-Only Engine: Ready).")


async def get_asyncpg_pool():
    """Raw connection pool for PostgreSQL bulk operations."""
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
