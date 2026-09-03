import asyncio
import json
import logging
import uuid
from typing import List, Dict, Any, Optional
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from models.database import AsyncSessionLocal
from services.ocr_router import ocr_router
from services.tamil_chunker import tamil_chunker
from services.vector_store import vector_store
from services.entity_extractor import entity_extractor
from services.ai_analyzer import ai_analyzer

logger = logging.getLogger(__name__)


class PostgresJobQueue:
    """
    PostgreSQL FOR UPDATE SKIP LOCKED Queue.
    Zero Redis. Zero RabbitMQ. Zero Kafka.
    """

    def __init__(self, pool: Optional[asyncpg.Pool] = None):
        self.pool = pool

    async def enqueue(self, db: AsyncSession, job_type: str, source_id: str, payload: Optional[Dict[str, Any]] = None) -> int:
        result = await db.execute(text("""
            INSERT INTO job_queue (job_type, source_id, payload, status, created_at)
            VALUES (:job_type, CAST(:source_id AS UUID), :payload, 'pending', NOW())
            RETURNING id
        """), {
            "job_type": job_type,
            "source_id": source_id,
            "payload": json.dumps(payload or {}, ensure_ascii=False)
        })
        await db.commit()
        return result.scalar_one()

    async def dequeue(self, db: AsyncSession, worker_id: str, job_types: List[str]) -> Optional[Dict[str, Any]]:
        """
        Dequeues one pending job atomically using FOR UPDATE SKIP LOCKED
        """
        sql = """
            SELECT id, job_type, source_id, payload
            FROM job_queue
            WHERE status = 'pending' AND job_type = ANY(:job_types)
            ORDER BY created_at ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        """
        result = await db.execute(text(sql), {"job_types": job_types})
        row = result.mappings().one_or_none()
        if not row:
            return None

        job_id = row["id"]
        await db.execute(text("""
            UPDATE job_queue
            SET status = 'processing', worker_id = :worker_id, started_at = NOW()
            WHERE id = :id
        """), {"id": job_id, "worker_id": worker_id})
        await db.commit()

        return dict(row)

    async def complete(self, db: AsyncSession, job_id: int, success: bool, error: Optional[str] = None):
        status = "completed" if success else "failed"
        await db.execute(text("""
            UPDATE job_queue
            SET status = :status, completed_at = NOW(), error_message = :error
            WHERE id = :id
        """), {"id": job_id, "status": status, "error": error})
        await db.commit()

    async def execute_job(self, db: AsyncSession, job: Dict[str, Any]):
        job_type = job["job_type"]
        source_id = str(job["source_id"])
        payload = job.get("payload") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}

        logger.info(f"Executing queue job {job['id']} of type {job_type} for source {source_id}")

        if job_type == "ocr":
            file_path = payload.get("file_path")
            file_type = payload.get("file_type", "pdf")
            await ocr_router.process_source(db, source_id, file_path, file_type)
            # Chain next jobs: vector indexing -> entity extraction -> ai analysis
            await self.enqueue(db, "vector_indexing", source_id)
            await self.enqueue(db, "entity_extraction", source_id)

        elif job_type == "vector_indexing":
            # Fetch OCR text and chunk
            res = await db.execute(text("SELECT page_number, full_text FROM ocr_results WHERE source_id = CAST(:source_id AS UUID) ORDER BY page_number"), {"source_id": source_id})
            pages = res.mappings().all()
            all_chunks = []
            for p in pages:
                chunks = tamil_chunker.split(p["full_text"] or "", p["page_number"])
                all_chunks.extend(chunks)
            if all_chunks:
                await vector_store.index_document(db, source_id, all_chunks)

        elif job_type == "entity_extraction":
            await entity_extractor.extract_all(db, source_id)
            # Trigger AI analysis
            await self.enqueue(db, "ai_analysis", source_id)

        elif job_type == "ai_analysis":
            await ai_analyzer.analyze(db, source_id)

        else:
            raise ValueError(f"Unknown job type: {job_type}")

    async def run_worker_loop(self, worker_id: str = None, poll_interval: float = 2.0):
        worker_id = worker_id or f"worker-{uuid.uuid4().hex[:6]}"
        logger.info(f"PostgresJobQueue worker {worker_id} started")
        job_types = ["ocr", "vector_indexing", "entity_extraction", "ai_analysis"]

        while True:
            try:
                async with AsyncSessionLocal() as db:
                    job = await self.dequeue(db, worker_id, job_types)
                    if job:
                        try:
                            await self.execute_job(db, job)
                            await self.complete(db, job["id"], success=True)
                        except Exception as e:
                            logger.error(f"Worker failed executing job {job['id']}: {e}", exc_info=True)
                            await self.complete(db, job["id"], success=False, error=str(e))
                    else:
                        await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker queue iteration error: {e}")
                await asyncio.sleep(poll_interval)


job_queue = PostgresJobQueue()
