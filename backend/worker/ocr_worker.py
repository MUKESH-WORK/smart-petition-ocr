import asyncio
import json
import os
import sys
import logging
from datetime import datetime, timezone
import redis.asyncio as redis
from sqlalchemy import select

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.services.ocr_service import process_document
from app.services.extraction_service import extract_document
from app.services.validation_service import validate_document
from app.services.verification_service import verify_document
from app.database.connection import AsyncSessionLocal, init_db
from app.database.models import DocumentRecord

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [OCR_WORKER]: %(message)s"
)
logger = logging.getLogger("ocr_worker")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
QUEUE_NAME = os.getenv("REDIS_QUEUE_NAME", "ocr_jobs")


async def update_status(
    document_id: str,
    status: str,
    error: str = None,
    ocr_result=None,
    extracted_data: dict = None,
    validation_result: dict = None
):
    """
    Persist document status transition and intermediate artifacts to PostgreSQL.
    """
    logger.info(f"{document_id} -> {status}")
    if error:
        logger.error(f"{document_id} Error: {error}")

    try:
        async with AsyncSessionLocal() as session:
            stmt = select(DocumentRecord).where(DocumentRecord.id == document_id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if record:
                record.status = status
                record.updated_at = datetime.now(timezone.utc)
                if error:
                    record.error_message = str(error)
                if ocr_result:
                    record.page_count = ocr_result.page_count
                    record.full_text = ocr_result.full_text
                    record.ocr_result = ocr_result.model_dump() if hasattr(ocr_result, "model_dump") else ocr_result.dict()
                if extracted_data:
                    record.extracted_data = extracted_data
                if validation_result:
                    record.validation_result = validation_result
                await session.commit()
    except Exception as db_err:
        logger.warning(f"Failed to persist status update for {document_id}: {db_err}")


async def main():
    logger.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}, queue: {QUEUE_NAME}...")

    await init_db()

    client = None
    while client is None:
        try:
            client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=True
            )
            await client.ping()
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            logger.warning(f"Redis not ready ({e}). Retrying in 3 seconds...")
            await asyncio.sleep(3)

    logger.info("OCR Worker started and listening for jobs...")

    while True:
        try:
            result = await client.blpop(QUEUE_NAME, timeout=5)
            if not result:
                continue

            _, raw_job = result
            job = json.loads(raw_job)

            document_id = job["document_id"]
            file_path = job["file_path"]

            try:
                logger.info(f"Processing document {document_id} (Path: {file_path})")

                # 1. OCR_PROCESSING
                await update_status(document_id, "OCR_PROCESSING")
                ocr_result = await process_document(file_path, document_id)

                # 2. EXTRACTING
                await update_status(
                    document_id,
                    "EXTRACTING",
                    ocr_result=ocr_result
                )
                extracted_data = await extract_document(ocr_result)

                # 3. VALIDATING
                await update_status(
                    document_id,
                    "VALIDATING",
                    extracted_data=extracted_data
                )
                validation_result = await validate_document(extracted_data)

                # 4. Final verification & status determination
                if validation_result.get("is_valid", False):
                    await update_status(
                        document_id,
                        "VERIFIED",
                        validation_result=validation_result
                    )
                else:
                    await update_status(
                        document_id,
                        "FLAGGED_FOR_REVIEW",
                        validation_result=validation_result
                    )

                logger.info(f"Completed processing for {document_id}")

            except Exception as error:
                logger.error(f"Failed processing {document_id}: {error}", exc_info=True)
                await update_status(
                    document_id,
                    "FAILED",
                    error=str(error)
                )

        except asyncio.CancelledError:
            logger.info("OCR Worker shutting down...")
            break
        except Exception as loop_error:
            logger.error(f"Worker queue polling error: {loop_error}")
            await asyncio.sleep(2)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("OCR Worker stopped by user.")
