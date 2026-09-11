import os
import sys
import io
import json
import uuid
import pytest
from PIL import Image, ImageDraw

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from models.orm import Base, Officer, Source, OCRResult, DocumentChunk, ExtractedEntity, AIAnalysis, GrievanceDraft, JobQueue, AuditLog
from services.vector_store import PGVectorStore
from services.job_queue import PostgresJobQueue
from app.main import app


@pytest.fixture
def sqlite_test_engine(tmp_path):
    """Creates an isolated temporary SQLite database for testing portable execution."""
    import re
    import asyncio
    from sqlalchemy import event

    db_file = str(tmp_path / "test_dro.db")
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file}",
        connect_args={"check_same_thread": False},
        echo=False
    )

    @event.listens_for(engine.sync_engine, "before_cursor_execute", retval=True)
    def _sqlite_compat(conn, cursor, statement, parameters, context, executemany):
        s = statement
        s = re.sub(r"CAST\s*\(\s*(\?|:\w+|[^\)]+)\s+AS\s+UUID\s*\)", r"\1", s, flags=re.IGNORECASE)
        s = re.sub(r"CAST\s*\(\s*(\?|:\w+|[^\)]+)\s+AS\s+INET\s*\)", r"\1", s, flags=re.IGNORECASE)
        s = re.sub(r"\bFOR\s+UPDATE\s+SKIP\s+LOCKED\b", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\bILIKE\b", "LIKE", s, flags=re.IGNORECASE)
        s = re.sub(r"\bNOW\(\)", "CURRENT_TIMESTAMP", s, flags=re.IGNORECASE)
        return s, parameters

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())
    yield engine, db_file

    asyncio.run(engine.dispose())



@pytest.mark.asyncio
async def test_sqlite_schema_creation_and_tables(sqlite_test_engine):
    """Verifies that all tables are created cleanly on SQLite without dialect errors."""
    engine, _ = sqlite_test_engine

    # Verify table existence in sqlite_master
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = set(r[0] for r in res.fetchall())


    expected_tables = {
        "sources", "ocr_results", "document_chunks", "extracted_entities",
        "ai_analysis", "grievance_drafts", "job_queue", "audit_log",
        "officers", "master_locations"
    }
    for table in expected_tables:
        assert table in tables, f"Expected table '{table}' missing from SQLite schema"


@pytest.mark.asyncio
async def test_sqlite_job_queue_lifecycle(sqlite_test_engine):
    """Verifies queue enqueue, dequeue, recovery, and completion on SQLite without FOR UPDATE SKIP LOCKED."""
    engine, _ = sqlite_test_engine
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    queue = PostgresJobQueue()

    test_source_id = str(uuid.uuid4())

    async with session_maker() as db:
        # 1. Enqueue job
        job_id = await queue.enqueue(db, "ocr", test_source_id, {"test": True})
        assert job_id is not None
        assert job_id > 0

        # 2. Dequeue job
        dequeued = await queue.dequeue(db, worker_id="test-worker", job_types=["ocr"])
        assert dequeued is not None
        assert dequeued["id"] == job_id
        assert dequeued["job_type"] == "ocr"

        # 3. Complete job
        await queue.complete(db, job_id, success=True)

        # 4. Verify completed state in DB
        res = await db.execute(text("SELECT status FROM job_queue WHERE id = :id"), {"id": job_id})
        status = res.scalar()
        assert status == "completed"


@pytest.mark.asyncio
async def test_sqlite_vector_store_in_memory_cosine(sqlite_test_engine):
    """Verifies that vector indexing and in-memory cosine similarity work seamlessly on SQLite."""
    engine, _ = sqlite_test_engine
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    store = PGVectorStore()

    test_source_id = str(uuid.uuid4())
    chunks = [
        {"text": "விண்ணப்பதாரர் கே. ராமலிங்கம் பெருந்துறை வட்டம் பட்டா மாறுதல் கோரிக்கை", "page_number": 1, "index": 0},
        {"text": "கிராம நத்தம் நில அளவை மற்றும் எல்லை கல் நடுதல் தொடர்பாக", "page_number": 1, "index": 1}
    ]

    async with session_maker() as db:
        # Insert parent source record to satisfy foreign key constraint
        await db.execute(text("""
            INSERT INTO sources (source_id, file_name, file_type, status, created_at, updated_at)
            VALUES (CAST(:source_id AS UUID), 'petition.pdf', 'pdf', 'uploaded', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """), {"source_id": test_source_id})
        await db.commit()

        await store.index_document(db, test_source_id, chunks)

        # Perform similarity search
        results = await store.similarity_search(db, query="பட்டா மாறுதல்", source_id=test_source_id, top_k=2)
        assert len(results) > 0
        assert "similarity" in results[0]
        assert results[0]["similarity"] > 0.0

        # Perform portable fulltext search
        ft_results = await store.fulltext_search(db, query="பட்டா", source_id=test_source_id, top_k=2)
        assert len(ft_results) > 0



def test_fastapi_spa_and_root_response():
    """Verifies that root endpoint serves SPA html to browsers and JSON to test/API clients."""
    with TestClient(app) as client:
        # 1. API client request (JSON expected)
        res_api = client.get("/", headers={"Accept": "application/json"})
        assert res_api.status_code == 200
        data = res_api.json()
        assert data["module"] == "DRO Grievance AI Module"
        assert "database" in data

        # 2. Browser request (HTML expected if frontend dist exists)
        res_browser = client.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
        assert res_browser.status_code == 200
        # If dist index.html exists, it returns HTML, otherwise graceful JSON
        content_type = res_browser.headers.get("content-type", "")
        assert "text/html" in content_type or "application/json" in content_type


def test_enterprise_health_sqlite_resilience():
    """Verifies that health check endpoint returns 200 with structured component metadata."""
    with TestClient(app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "components" in data
        assert "database" in data["components"]
        assert "storage" in data["components"]
        assert "ocr" in data["components"]
