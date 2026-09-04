import asyncio
import json
import logging
import uuid
from typing import List, Dict, Any, Optional
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.config import settings
from models.database import AsyncSessionLocal
from services.ocr_router import ocr_router
from services.tamil_chunker import tamil_chunker
from services.vector_store import vector_store
from services.entity_extractor import entity_extractor
from services.ai_analyzer import ai_analyzer

logger = logging.getLogger(__name__)


class PostgresJobQueue:
    """
    Production-grade PostgreSQL FOR UPDATE SKIP LOCKED Queue.
    Features:
    - Zero external broker dependencies (zero Redis/RabbitMQ)
    - Concurrency-safe atomic dequeue via SKIP LOCKED
    - Exponential retry tracking for transient pipeline errors
    - Automatic stuck-job recovery (>5 minute processing timeout)
    - Sub-1.5s responsive polling
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

    async def recover_stuck_jobs(self, db: AsyncSession):
        """Recovers any jobs stuck in 'processing' state due to worker crashes or machine restarts."""
        timeout_min = getattr(settings, "JOB_STUCK_TIMEOUT_MINUTES", 5)
        try:
            result = await db.execute(text(f"""
                UPDATE job_queue
                SET status = 'pending', worker_id = NULL, started_at = NULL
                WHERE status = 'processing' AND started_at < NOW() - INTERVAL '{timeout_min} minutes'
            """))
            if result.rowcount > 0:
                logger.warning(f"Recovered {result.rowcount} stuck jobs back to 'pending'")
                await db.commit()
        except Exception as e:
            logger.debug(f"Stuck job check skipped: {e}")

    async def dequeue(self, db: AsyncSession, worker_id: str, job_types: List[str]) -> Optional[Dict[str, Any]]:
        """Dequeues one pending job atomically using FOR UPDATE SKIP LOCKED"""
        # Periodic recovery of orphaned jobs
        await self.recover_stuck_jobs(db)

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

    async def complete(self, db: AsyncSession, job_id: int, success: bool, error: Optional[str] = None, job: Optional[Dict[str, Any]] = None):
        """Marks job complete or handles retry with backoff"""
        if success:
            await db.execute(text("""
                UPDATE job_queue
                SET status = 'completed', completed_at = NOW(), error_message = NULL
                WHERE id = :id
            """), {"id": job_id})
            await db.commit()
            return

        # Failure path: check retry budget
        payload = {}
        if job and job.get("payload"):
            raw_payload = job["payload"]
            if isinstance(raw_payload, str):
                try:
                    payload = json.loads(raw_payload)
                except Exception:
                    payload = {}
            elif isinstance(raw_payload, dict):
                payload = raw_payload.copy()

        retry_count = payload.get("retry_count", 0)
        max_retries = getattr(settings, "JOB_MAX_RETRIES", 3)

        if retry_count < max_retries:
            payload["retry_count"] = retry_count + 1
            logger.warning(f"Job {job_id} failed ({error}). Scheduling retry {retry_count + 1}/{max_retries}.")
            await db.execute(text("""
                UPDATE job_queue
                SET status = 'pending', worker_id = NULL, started_at = NULL,
                    error_message = :error, payload = :payload
                WHERE id = :id
            """), {
                "id": job_id,
                "error": f"[Retry {retry_count + 1}] {error}",
                "payload": json.dumps(payload, ensure_ascii=False)
            })
        else:
            logger.error(f"Job {job_id} exceeded max retries ({max_retries}). Marking permanently failed: {error}")
            await db.execute(text("""
                UPDATE job_queue
                SET status = 'failed', completed_at = NOW(), error_message = :error
                WHERE id = :id
            """), {"id": job_id, "error": error})

            # Update source record to indicate failure
            if job and job.get("source_id"):
                await db.execute(text("""
                    UPDATE sources SET status = 'failed', updated_at = NOW()
                    WHERE source_id = CAST(:source_id AS UUID)
                """), {"source_id": str(job["source_id"])})

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
            # Parallel dispatch: vector indexing and entity extraction run independently
            await self.enqueue(db, "vector_indexing", source_id)
            await self.enqueue(db, "entity_extraction", source_id)

        elif job_type == "vector_indexing":
            res = await db.execute(
                text("SELECT page_number, full_text FROM ocr_results WHERE source_id = CAST(:source_id AS UUID) ORDER BY page_number"),
                {"source_id": source_id}
            )
            pages = res.mappings().all()
            all_chunks = []
            for p in pages:
                chunks = tamil_chunker.split(p["full_text"] or "", p["page_number"])
                all_chunks.extend(chunks)
            if all_chunks:
                await vector_store.index_document(db, source_id, all_chunks)

        elif job_type == "entity_extraction":
            await entity_extractor.extract_all(db, source_id)
            # Trigger AI analysis once entities are extracted
            await self.enqueue(db, "ai_analysis", source_id)

        elif job_type == "ai_analysis":
            await ai_analyzer.analyze(db, source_id)

        else:
            raise ValueError(f"Unknown job type: {job_type}")

    async def run_worker_loop(self, worker_id: str = None, poll_interval: Optional[float] = None):
        worker_id = worker_id or f"worker-{uuid.uuid4().hex[:6]}"
        interval = poll_interval or getattr(settings, "WORKER_POLL_INTERVAL", 1.5)
        logger.info(f"PostgresJobQueue worker {worker_id} started with {interval}s poll interval")
        job_types = ["ocr", "vector_indexing", "entity_extraction", "ai_analysis"]

        while True:
            try:
                async with AsyncSessionLocal() as db:
                    job = await self.dequeue(db, worker_id, job_types)
                    if job:
                        try:
                            await self.execute_job(db, job)
                            await self.complete(db, job["id"], success=True, job=job)
                        except Exception as e:
                            logger.error(f"Worker failed executing job {job['id']}: {e}", exc_info=True)
                            await self.complete(db, job["id"], success=False, error=str(e), job=job)
                    else:
                        await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker queue iteration error: {e}")
                await asyncio.sleep(interval)


job_queue = PostgresJobQueue()
