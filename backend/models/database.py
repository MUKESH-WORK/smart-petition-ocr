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
    target_dir = os.path.join(_backend_dir, "temp_cache")
    os.makedirs(target_dir, exist_ok=True)
    
    # Check existing candidates
    for candidate in [
        os.path.join(_backend_dir, "temp_cache", db_name),
        os.path.join(_repo_root, "temp_cache", db_name),
        os.path.join(os.getcwd(), "temp_cache", db_name),
        os.path.join(os.getcwd(), "backend", "temp_cache", db_name),
    ]:
        if os.path.isfile(candidate) and os.path.getsize(candidate) > 0:
            return os.path.abspath(candidate).replace("\\", "/")
            
    # If not found or empty, check if database bundle archive is present and unpack it
    for bundle_path in [
        os.path.join(_backend_dir, "gdp_database_bundle.tar.gz"),
        os.path.join(_repo_root, "gdp_database_bundle.tar.gz"),
        os.path.join(os.getcwd(), "gdp_database_bundle.tar.gz"),
        os.path.join(os.getcwd(), "backend", "gdp_database_bundle.tar.gz"),
        "/app/gdp_database_bundle.tar.gz"
    ]:
        if os.path.isfile(bundle_path):
            try:
                import tarfile
                with tarfile.open(bundle_path, "r:gz") as tar:
                    tar.extractall(target_dir)
                logger.info(f"Automatically unpacked database bundle from {bundle_path} to {target_dir}")
                extracted_file = os.path.join(target_dir, db_name)
                if os.path.isfile(extracted_file) and os.path.getsize(extracted_file) > 0:
                    return os.path.abspath(extracted_file).replace("\\", "/")
            except Exception as e:
                logger.warning(f"Notice during automatic bundle extraction: {e}")
                
    return os.path.abspath(os.path.join(_backend_dir, "temp_cache", db_name)).replace("\\", "/")

# Determine database URLs with automatic SQLite fallback
if hasattr(settings, "USE_SQLITE"):
    if isinstance(settings.USE_SQLITE, bool):
        use_sqlite = settings.USE_SQLITE
    else:
        use_sqlite = str(settings.USE_SQLITE).lower() in ("true", "1", "yes")
else:
    use_sqlite = os.getenv("USE_SQLITE", "false").lower() in ("true", "1", "yes")

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

# Dedicated SQLite Engine for Decoupled Audit Logging & Movement History
audit_sqlite_path = _find_sqlite_path("dro_audit.db")
audit_db_url = f"sqlite+aiosqlite:///{audit_sqlite_path}"
audit_engine = create_async_engine(audit_db_url, **_get_engine_kwargs(True))
_attach_sqlite_compat(audit_engine)

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
    async with AuditAsyncSessionLocal() as session:
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

    # 1. Initialize User Database (ensure pgvector extension is ready for SafeVector columns)
    if not is_sqlite:
        try:
            async with user_engine.begin() as ext_conn:
                await ext_conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        except Exception as e:
            logger.warning(f"Vector extension note on user db: {e}")

    async with user_engine.begin() as conn:
        await conn.run_sync(UserBase.metadata.create_all)

    if not is_sqlite:
        # PostgreSQL dynamic column safety
        pg_safe_alters = [
            "ALTER TABLE extracted_entities DROP CONSTRAINT IF EXISTS extracted_entities_extracted_by_check;",
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
    else:
        # SQLite dynamic column safety
        async with user_engine.begin() as sqlite_conn:
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
                    await sqlite_conn.execute(text(col_sql))
                except Exception:
                    pass

        # Ensure AI Semantic Cache table exists in User DB with correct VARCHAR(50) schema
        async with user_engine.begin() as sem_conn:
            if is_sqlite:
                try:
                    table_check = await sem_conn.execute(text("PRAGMA table_info(semantic_cache);"))
                    cols = table_check.fetchall()
                    id_col = next((c for c in cols if c[1] == "id"), None)
                    if id_col and "INT" in id_col[2].upper():
                        logger.info("Migrating semantic_cache table to VARCHAR(50) primary key...")
                        await sem_conn.execute(text("DROP TABLE semantic_cache;"))
                except Exception as ex:
                    logger.debug(f"Semantic cache table schema inspect notice: {ex}")

                await sem_conn.execute(text("""
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
                await sem_conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sem_cache_hash ON semantic_cache(prompt_hash);"))
            else:
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

    # 2. Initialize Admin Database
    if not is_admin_sqlite:
        try:
            async with admin_engine.begin() as ext_conn:
                await ext_conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        except Exception as e:
            logger.debug(f"Vector extension note on admin db: {e}")

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
                    responsible_officer VARCHAR(255),
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
            ]:
                try:
                    await conn.execute(text(col_stmt))
                except Exception:
                    pass

    # 3. Initialize SQLite Decoupled Audit Log & Movement History
    _ensure_sqlite_dir(audit_db_url)
    async with audit_engine.begin() as a_conn:
        await a_conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_id VARCHAR(50),
                officer_id VARCHAR(50),
                action VARCHAR(100) NOT NULL,
                details TEXT,
                ip_address VARCHAR(50)
            );
        """))
        await a_conn.execute(text("""
            CREATE TABLE IF NOT EXISTS admin_activity_log (
                id VARCHAR(50) PRIMARY KEY,
                type VARCHAR(50) NOT NULL,
                detail TEXT NOT NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                officer_id VARCHAR(50)
            );
        """))
        await a_conn.execute(text("""
            CREATE TABLE IF NOT EXISTS petition_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                petition_id VARCHAR(50) NOT NULL,
                movement_type VARCHAR(50) NOT NULL,
                from_officer VARCHAR(100),
                to_officer VARCHAR(100),
                status VARCHAR(50),
                remark TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        await a_conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_officer ON audit_log(officer_id);"))
        await a_conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp);"))
        await a_conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mov_pet ON petition_movements(petition_id);"))

    logger.info(f"Database schemas initialized successfully (User DB: {'SQLite' if is_sqlite else 'PostgreSQL'}, Admin DB: {'SQLite' if is_admin_sqlite else 'PostgreSQL'}, Audit Store: SQLite).")


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
