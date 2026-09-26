import os
import uuid
import shutil
import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from sqlalchemy import select, desc

from app.queue.redis_queue import enqueue_document
from app.database.connection import AsyncSessionLocal, init_db
from app.database.models import DocumentRecord
from app.schemas.document import DocumentUploadResponse, DocumentResponse

logger = logging.getLogger("gdp_documents_api")

router = APIRouter(
    prefix="/api/documents",
    tags=["Documents"]
)

DEFAULT_UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/storage/uploads")
if not os.path.isabs(DEFAULT_UPLOAD_DIR):
    DEFAULT_UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", DEFAULT_UPLOAD_DIR))

try:
    os.makedirs(DEFAULT_UPLOAD_DIR, exist_ok=True)
except Exception:
    DEFAULT_UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "storage", "uploads"))
    os.makedirs(DEFAULT_UPLOAD_DIR, exist_ok=True)

UPLOAD_DIR = DEFAULT_UPLOAD_DIR


@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentUploadResponse
)
async def upload_document(document: UploadFile = File(...)):
    """
    Accept PDF or scanned image upload, persist file, create PostgreSQL record (UPLOADED),
    and asynchronously enqueue to Redis queue for background worker processing.
    """
    if not document.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    document_id = str(uuid.uuid4())
    safe_filename = os.path.basename(document.filename).replace(" ", "_")
    file_path = os.path.join(UPLOAD_DIR, f"{document_id}_{safe_filename}")

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # 1. Save uploaded file to disk
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(document.file, buffer)
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store uploaded file: {str(e)}")

    # 2. Create PostgreSQL record
    try:
        async with AsyncSessionLocal() as session:
            record = DocumentRecord(
                id=document_id,
                filename=document.filename,
                file_path=file_path,
                status="UPLOADED",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(record)
            await session.commit()
    except Exception as db_err:
        logger.warning(f"PostgreSQL record creation notice: {db_err}. Retrying schema init.")
        try:
            await init_db()
            async with AsyncSessionLocal() as session:
                record = DocumentRecord(
                    id=document_id,
                    filename=document.filename,
                    file_path=file_path,
                    status="UPLOADED",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(record)
                await session.commit()
        except Exception as retry_err:
            logger.error(f"DB insert failed for {document_id}: {retry_err}")

    # 3. Add job to Redis queue
    try:
        await enqueue_document(
            document_id=document_id,
            file_path=file_path
        )
    except Exception as q_err:
        logger.error(f"Failed to enqueue document {document_id} to Redis: {q_err}")

    return {
        "success": True,
        "documentId": document_id,
        "status": "UPLOADED",
        "message": "Document accepted for processing."
    }


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document_status(document_id: str):
    """
    Query the processing status and results for a document.
    """
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(DocumentRecord).where(DocumentRecord.id == document_id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            if not record:
                raise HTTPException(status_code=404, detail="Document not found")
            return record.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Database query error")


@router.get("", response_model=List[DocumentResponse])
async def list_documents(limit: int = 50, offset: int = 0):
    """
    List recently uploaded documents.
    """
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(DocumentRecord).order_by(desc(DocumentRecord.created_at)).offset(offset).limit(limit)
            result = await session.execute(stmt)
            records = result.scalars().all()
            return [r.to_dict() for r in records]
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return []
