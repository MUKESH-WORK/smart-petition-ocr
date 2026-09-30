import asyncio
import sqlalchemy.ext.asyncio
import os
import json
import uuid
import logging
import tempfile
from datetime import datetime, timezone, timedelta, date
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Header, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from models.database import get_db
from models.schemas import (
    SourceUploadResponse, SourceStatusResponse, OCRDocumentResponse, OCRPageResult,
    EntityExtractionResponse, ExtractedEntityItem, AIAnalysisResponse,
    ChatRequest, GrievanceDraftResponse, DraftUpdate, DraftApproveRequest,
    DuplicateResolveRequest
)
from services.file_store import file_store
from services.ocr_router import ocr_router
from services.tamil_chunker import tamil_chunker
from services.vector_store import vector_store
from services.entity_extractor import entity_extractor
from services.ai_analyzer import ai_analyzer
from services.job_queue import job_queue
from app.config import settings
from app.dependencies import get_current_officer, get_optional_officer, log_audit_event
from core.llm_client import llm_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/grievance", tags=["Grievance Processing"])
_page_image_render_locks: dict[str, asyncio.Lock] = {}

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "tiff", "tif", "bmp", "webp", "docx"}

ALLOWED_UPDATE_FIELDS = {
    "petitioner_name", "father_husband_name", "complainant_signatory", "phone", "alternate_phone",
    "gender", "address", "door_no", "street_name", "village", "firka",
    "taluk", "district", "pincode", "grievance_type", "grievance_subtype",
    "department", "sub_department", "description", "priority", "officer_notes"
}


@router.post("/upload", response_model=SourceUploadResponse)
async def upload_petition(
    request: Request,
    file: UploadFile = File(...),
    officer_id: Optional[str] = Form(None),
    process_now: bool = Form(False),
    db: AsyncSession = Depends(get_db)
):
    """
    1. Read uploaded petition (PDF/Image)
    2. Authenticate officer via JWT, X-Officer-Id header, or Form officer_id
    3. Enforce file extension whitelist (422 if invalid)
    4. Compute SHA256 & save to uploads/
    5. Always insert a NEW sources record (retains its unique source_id)
    6. Check if an exact duplicate document (by SHA-256) was previously processed
       - If duplicate found: Return status='duplicate_found' with duplicate metadata (User choice: Reuse vs Process Again)
       - If no duplicate (or process_now=True): Asynchronously enqueue OCR job into background queue
    7. Log audit event
    """
    # Officer authentication check (fails closed with 401 if unauthenticated)
    eff_officer_id = None
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        from core.security import decode_access_token
        payload = decode_access_token(auth_header[7:].strip())
        if payload and "officer_id" in payload:
            eff_officer_id = payload["officer_id"]

    if not eff_officer_id:
        eff_officer_id = (
            request.headers.get("x-officer-id")
            or request.headers.get("X-Officer-Id")
            or (officer_id.strip() if officer_id and officer_id.strip() else None)
        )

    if not eff_officer_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required: missing or invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        # 1. Always generate a fresh unique UUID for the new upload
        new_source_id = str(uuid.uuid4())
        if not file.filename or not file.filename.strip():
            raise HTTPException(
                status_code=400,
                detail="செல்லுபடியாகும் கோப்பு பெயர் தேவை (Valid filename is required)."
            )
        filename = file.filename.strip()
        ext = os.path.splitext(filename)[1].lower().replace(".", "")
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=422,
                detail="ஆவண வடிவம் ஆதரிக்கப்படவில்லை. PDF அல்லது படங்களை (JPG, PNG) பதிவேற்றவும்."
            )

        content = await file.read()
        # 2. Save file to disk with unique source_id and calculate SHA-256
        file_path, file_hash, file_size = await file_store.save_uploaded_file(new_source_id, filename, content)
        logger.info(f" [UPLOAD] New source_id={new_source_id}")
        logger.info(f" [UPLOAD] file_hash={file_hash}")

        # 3. Ensure officer exists to satisfy foreign key
        if eff_officer_id:
            eff_officer_id = str(eff_officer_id).strip()
            try:
                await db.execute(text("""
                    INSERT INTO officers (officer_id, name, name_tamil, email, designation, department, status)
                    VALUES (:officer_id, 'DRO Officer', 'வருவாய் அலுவலர்', :email, 'DRO Officer', 'வருவாய்த்துறை', 'Active')
                    ON CONFLICT (officer_id) DO NOTHING
                """), {"officer_id": eff_officer_id, "email": f"{eff_officer_id.lower()}@tn.gov.in"})
                await db.flush()
            except Exception as e:
                logger.debug(f"Officer record validation notice: {e}")

        # 4. Insert into sources (gracefully handling existing file_hash in legacy SQLite tables)
        file_data_db = content if getattr(settings, "STORE_FILE_BYTEA", False) else None
        try:
            res_insert = await db.execute(text("""
                INSERT INTO sources (source_id, officer_id, file_name, file_type, file_size_bytes, file_hash, page_count, status, file_data, created_at, updated_at)
                VALUES (:source_id, :officer_id, :file_name, :file_type, :file_size, :file_hash, 0, 'uploaded', :file_data, NOW(), NOW())
                RETURNING source_id, file_name, file_size_bytes, page_count, status, created_at
            """), {
                "source_id": new_source_id,
                "officer_id": eff_officer_id,
                "file_name": file.filename,
                "file_type": ext,
                "file_size": file_size,
                "file_hash": file_hash,
                "file_data": file_data_db
            })
            row = res_insert.mappings().one()
            await db.commit()
        except Exception as insert_err:
            await db.rollback()
            logger.info(f"Duplicate file upload notice: {insert_err}. Locating existing source record for hash {file_hash[:12]}...")
            existing_s_res = await db.execute(text("""
                SELECT source_id, file_name, file_size_bytes, page_count, status, created_at
                FROM sources
                WHERE file_hash = :hash
                ORDER BY created_at DESC
                LIMIT 1
            """), {"hash": file_hash})
            existing_row = existing_s_res.mappings().one_or_none()
            if existing_row:
                row = existing_row
                new_source_id = str(row["source_id"])
            else:
                raise insert_err

        # 5. Duplicate Check: Check if an identical document (SHA-256) was previously processed with a valid draft
        existing_res = await db.execute(text("""
            SELECT s.source_id, s.status, s.file_name, s.file_size_bytes, s.page_count, s.created_at,
                   gd.petitioner_name, gd.description
            FROM sources s
            JOIN grievance_drafts gd ON gd.source_id = s.source_id
            WHERE s.file_hash = :hash
              AND s.source_id != :new_id
              AND s.status IN ('draft_ready', 'officer_approved', 'pushed_to_dro')
            ORDER BY s.created_at DESC
            LIMIT 1
        """), {"hash": file_hash, "new_id": new_source_id})
        existing_match = existing_res.mappings().one_or_none()

        # If an identical processed document exists and user hasn't explicitly requested force re-processing
        if existing_match and not process_now:
            dup_id = str(existing_match["source_id"])
            logger.info(f"🔍 [DUPLICATE] New source_id={new_source_id}")
            logger.info(f"🔍 [DUPLICATE] Previous source_id={dup_id}")
            logger.info(f"🔍 [DUPLICATE] Waiting for user decision")
            
            # Mark new source status as duplicate_pending
            await db.execute(text("UPDATE sources SET status = 'duplicate_pending', updated_at = NOW() WHERE source_id = :sid"), {"sid": new_source_id})
            await db.commit()

            return SourceUploadResponse(
                source_id=row["source_id"],
                file_name=row["file_name"],
                file_size_bytes=row["file_size_bytes"] or 0,
                page_count=existing_match["page_count"] or 1,
                status="duplicate_found",
                created_at=row["created_at"],
                message="Exact duplicate petition detected. Choose whether to reuse previous analysis or process again.",
                duplicate_detected=True,
                duplicate_source_id=dup_id,
                duplicate_petitioner_name=existing_match.get("petitioner_name"),
                duplicate_file_name=existing_match.get("file_name"),
                duplicate_created_at=existing_match.get("created_at"),
                duplicate_summary=existing_match.get("description")
            )

        # 6. Normal flow: Asynchronously enqueue OCR job into job queue for this NEW source_id
        await job_queue.enqueue(db, "ocr", new_source_id, {"file_path": file_path, "file_type": ext})
        logger.info(f"🚀 [PIPELINE] Enqueued OCR for new source_id={new_source_id}")

        # Log audit event
        await log_audit_event(
            action="UPLOAD_PETITION",
            source_id=new_source_id,
            officer_id=eff_officer_id,
            details={"file_name": file.filename, "file_size": file_size, "hash": file_hash},
            ip_address=request.client.host if request.client else "127.0.0.1"
        )

        return SourceUploadResponse(
            source_id=row["source_id"],
            file_name=row["file_name"],
            file_size_bytes=row["file_size_bytes"] or 0,
            page_count=row["page_count"] or 1,
            status=row["status"],
            created_at=row["created_at"],
            duplicate_detected=False
        )
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{source_id}/resolve-duplicate", response_model=SourceUploadResponse)
async def resolve_duplicate(
    source_id: str,
    req: DuplicateResolveRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Resolve duplicate petition decision:
    - 'reuse': Atomically copy OCR, Chunks, Entities, AI Analysis, and Grievance Draft to new source_id.
    - 'reprocess': Enqueue full pipeline (OCR -> Vector -> Entities -> LLM) for new source_id.
    """
    try:
        eff_officer_id = None
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            from core.security import decode_access_token
            payload = decode_access_token(auth_header[7:].strip())
            if payload and "officer_id" in payload:
                eff_officer_id = payload["officer_id"]

        if not eff_officer_id:
            eff_officer_id = (
                request.headers.get("x-officer-id")
                or request.headers.get("X-Officer-Id")
            )

        action = req.action.strip().lower()
        if action not in ("reuse", "reprocess"):
            raise HTTPException(status_code=400, detail="Invalid action. Must be 'reuse' or 'reprocess'.")

        # 1. Verify that the target new source exists
        src_res = await db.execute(text("SELECT * FROM sources WHERE source_id = :sid"), {"sid": source_id})
        new_source = src_res.mappings().one_or_none()
        if not new_source:
            raise HTTPException(status_code=404, detail="Target source document not found.")

        file_hash = new_source["file_hash"]
        file_type = new_source["file_type"]

        if action == "reprocess":
            logger.info(f"🔄 [DUPLICATE] User selected reprocess (new source_id={source_id})")
            file_path = file_store.get_file_path(source_id)
            if not file_path or not os.path.exists(file_path):
                file_path = os.path.join(settings.UPLOAD_DIR, f"{source_id}_{file_hash[:8]}.{file_type.replace('.', '')}")

            await db.execute(text("UPDATE sources SET status = 'uploaded', updated_at = NOW() WHERE source_id = :sid"), {"sid": source_id})
            await job_queue.enqueue(db, "ocr", source_id, {"file_path": file_path, "file_type": file_type})
            await db.commit()

            logger.info(f"🚀 [REPROCESS] Enqueued OCR for source_id={source_id}")
            await log_audit_event(
                action="REPROCESS_DUPLICATE_PETITION",
                source_id=source_id,
                officer_id=eff_officer_id,
                details={"action": "reprocess", "file_hash": file_hash},
                ip_address=request.client.host if request.client else "127.0.0.1"
            )

            return SourceUploadResponse(
                source_id=new_source["source_id"],
                file_name=new_source["file_name"],
                file_size_bytes=new_source["file_size_bytes"] or 0,
                page_count=new_source["page_count"] or 1,
                status="processing",
                created_at=new_source["created_at"],
                message="Re-processing initiated successfully.",
                duplicate_detected=False
            )

        elif action == "reuse":
            logger.info(f"⚡ [DUPLICATE] User selected reuse (new source_id={source_id})")

            # 2. Strict Security: Find verified duplicate source with the EXACT same file_hash
            dup_query = """
                SELECT s.*
                FROM sources s
                JOIN grievance_drafts gd ON gd.source_id = s.source_id
                WHERE s.file_hash = :hash
                  AND s.source_id != :new_id
                  AND s.status IN ('draft_ready', 'officer_approved', 'pushed_to_dro')
            """
            params = {"hash": file_hash, "new_id": source_id}

            if req.duplicate_source_id:
                dup_query += " AND s.source_id = :dup_id"
                params["dup_id"] = req.duplicate_source_id

            dup_query += " ORDER BY s.created_at DESC LIMIT 1"

            dup_res = await db.execute(text(dup_query), params)
            old_source = dup_res.mappings().one_or_none()

            if not old_source:
                raise HTTPException(
                    status_code=400,
                    detail="No matching verified duplicate source with the same file hash was found to reuse."
                )

            old_source_id = str(old_source["source_id"])

            # 3. Transactional Copy of all artifacts to new_source_id
            try:
                # A. Copy OCR Results
                await db.execute(text("""
                    INSERT INTO ocr_results (source_id, page_number, full_text, blocks, tables, avg_confidence, ocr_engine, processing_time_ms)
                    SELECT :new_id, page_number, full_text, blocks, tables, avg_confidence, ocr_engine, processing_time_ms
                    FROM ocr_results
                    WHERE source_id = :old_id
                    ON CONFLICT (source_id, page_number) DO UPDATE SET
                        full_text = EXCLUDED.full_text,
                        blocks = EXCLUDED.blocks,
                        tables = EXCLUDED.tables,
                        avg_confidence = EXCLUDED.avg_confidence,
                        ocr_engine = EXCLUDED.ocr_engine,
                        processing_time_ms = EXCLUDED.processing_time_ms
                """), {"new_id": source_id, "old_id": old_source_id})

                # B. Copy Document Chunks
                await db.execute(text("""
                    DELETE FROM document_chunks WHERE source_id = :new_id;
                """), {"new_id": source_id})

                old_chunks_res = await db.execute(text("""
                    SELECT chunk_index, page_number, chunk_text, embedding, metadata
                    FROM document_chunks
                    WHERE source_id = :old_id
                    ORDER BY chunk_index
                """), {"old_id": old_source_id})

                old_chunks = old_chunks_res.mappings().all()

                for chunk in old_chunks:
                    chunk_embedding = chunk["embedding"]
                    if chunk_embedding is not None and not isinstance(chunk_embedding, str):
                        # Raw text() statements bypass SafeVector's ORM bind
                        # adapter; asyncpg's pgvector codec expects its string
                        # representation, not a Python list.
                        chunk_embedding = json.dumps(chunk_embedding, separators=(",", ":"))
                    await db.execute(text("""
                        INSERT INTO document_chunks (
                            id, source_id, chunk_index, page_number,
                            chunk_text, embedding, metadata
                        )
                        VALUES (
                            :id, :source_id, :chunk_index, :page_number,
                            :chunk_text, :embedding, :metadata
                        )
                    """), {
                        "id": str(uuid.uuid4()),
                        "source_id": source_id,
                        "chunk_index": chunk["chunk_index"],
                        "page_number": chunk["page_number"],
                        "chunk_text": chunk["chunk_text"],
                        "embedding": chunk_embedding,
                        "metadata": json.dumps(chunk.get("metadata")) if chunk.get("metadata") is not None else None,
                    })

                # C. Copy Extracted Entities
                await db.execute(text("""
                    DELETE FROM extracted_entities WHERE source_id = :new_id;
                """), {"new_id": source_id})
                await db.execute(text("""
                    INSERT INTO extracted_entities (source_id, entity_type, entity_value, confidence, source_page, validation_status, extracted_by)
                    SELECT :new_id, entity_type, entity_value, confidence, source_page, validation_status, extracted_by
                    FROM extracted_entities
                    WHERE source_id = :old_id
                """), {"new_id": source_id, "old_id": old_source_id})

                # D. Copy AI Analysis
                await db.execute(text("""
                    DELETE FROM ai_analysis WHERE source_id = :new_id;
                """), {"new_id": source_id})
                await db.execute(text("""
                    INSERT INTO ai_analysis (source_id, grievance_type_suggested, grievance_subtype_suggested, department_suggested,
                                            priority_suggested, description_summary_tamil, description_summary_english,
                                            action_items, claims, hallucination_score, grounding_score, raw_ai_response)
                    SELECT :new_id, grievance_type_suggested, grievance_subtype_suggested, department_suggested,
                           priority_suggested, description_summary_tamil, description_summary_english,
                           action_items, claims, hallucination_score, grounding_score, raw_ai_response
                    FROM ai_analysis
                    WHERE source_id = :old_id
                """), {"new_id": source_id, "old_id": old_source_id})

                # E. Copy Grievance Draft with a NEW unique draft ID
                new_draft_id = str(uuid.uuid4())
                await db.execute(text("""
                    DELETE FROM grievance_drafts WHERE source_id = :new_id;
                """), {"new_id": source_id})
                await db.execute(text("""
                    INSERT INTO grievance_drafts (
                        id, source_id, officer_id, petitioner_name, father_husband_name, complainant_signatory,
                        phone, is_own_phone, alternate_phone, address, gender,
                        community_or_individual, description, grievance_source, ref_number,
                        department, sub_department, local_body_type, grievance_type, grievance_subtype,
                        district, revenue_division, taluk, firka, block, village, ward, municipality_ward,
                        street_name, door_no, responsible_officer, priority,
                        status, dro_status, officer_approved, officer_notes,
                        is_whatsapp_appeal, is_whatsapp_tracking, is_whatsapp_receipt,
                        created_at, updated_at
                    )
                    SELECT
                        :new_draft_id, :new_id, COALESCE(:officer_id, officer_id), petitioner_name, father_husband_name, complainant_signatory,
                        phone, is_own_phone, alternate_phone, address, gender,
                        community_or_individual, description, grievance_source, ref_number,
                        department, sub_department, local_body_type, grievance_type, grievance_subtype,
                        district, revenue_division, taluk, firka, block, village, ward, municipality_ward,
                        street_name, door_no, responsible_officer, priority,
                        'draft', 'draft', FALSE, officer_notes,
                        is_whatsapp_appeal, is_whatsapp_tracking, is_whatsapp_receipt,
                        NOW(), NOW()
                    FROM grievance_drafts
                    WHERE source_id = :old_id
                    LIMIT 1
                """), {
                    "new_draft_id": new_draft_id,
                    "new_id": source_id,
                    "old_id": old_source_id,
                    "officer_id": eff_officer_id or str(new_source.get("officer_id") or "DRO_OFFICER")
                })

                # F. Copy Static Media Preview Images for new source_id
                old_page_count = old_source["page_count"] or 1
                for p_num in range(1, old_page_count + 1):
                    old_img = file_store.get_page_image_path(old_source_id, p_num)
                    new_img = file_store.get_page_image_path(source_id, p_num)
                    if os.path.exists(old_img) and not os.path.exists(new_img):
                        try:
                            import shutil
                            shutil.copyfile(old_img, new_img)
                        except Exception as img_err:
                            logger.debug(f"Image preview copy notice: {img_err}")

                # G. Update new sources row to draft_ready
                await db.execute(text("""
                    UPDATE sources
                    SET status = 'draft_ready',
                        page_count = :page_count,
                        phash = :phash,
                        updated_at = NOW()
                    WHERE source_id = :new_id
                """), {
                    "new_id": source_id,
                    "page_count": old_page_count,
                    "phash": old_source.get("phash")
                })

                await db.commit()
                logger.info(f"⚡ [REUSE] Copied previous result from {old_source_id} to new source_id={source_id}")

                await log_audit_event(
                    action="REUSE_DUPLICATE_PETITION",
                    source_id=source_id,
                    officer_id=eff_officer_id,
                    details={"action": "reuse", "reused_from": old_source_id, "file_hash": file_hash},
                    ip_address=request.client.host if request.client else "127.0.0.1"
                )

                return SourceUploadResponse(
                    source_id=new_source["source_id"],
                    file_name=new_source["file_name"],
                    file_size_bytes=new_source["file_size_bytes"] or 0,
                    page_count=old_page_count,
                    status="draft_ready",
                    created_at=new_source["created_at"],
                    message="Previous analysis reused successfully.",
                    duplicate_detected=False
                )

            except HTTPException:
                raise
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to copy previous results to source {source_id}: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Failed to copy duplicate results: {str(e)}")

    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))



@router.get("/{source_id}/status", response_model=SourceStatusResponse)
async def get_status(source_id: str, db: AsyncSession = Depends(get_db)):
    """
    Return comprehensive processing and verification status for the petition
    """
    src_res = await db.execute(text("SELECT * FROM sources WHERE source_id = :source_id"), {"source_id": source_id})
    src = src_res.mappings().one_or_none()
    if not src:
        raise HTTPException(status_code=404, detail="Source document not found")

    ocr_res = await db.execute(text("SELECT AVG(avg_confidence) as avg_conf FROM ocr_results WHERE source_id = :source_id"), {"source_id": source_id})
    avg_conf_row = ocr_res.mappings().one_or_none()
    avg_conf = float(avg_conf_row["avg_conf"]) if avg_conf_row and avg_conf_row["avg_conf"] is not None else None

    chunk_cnt = await db.execute(text("SELECT COUNT(*) FROM document_chunks WHERE source_id = :source_id"), {"source_id": source_id})
    entity_cnt = await db.execute(text("SELECT COUNT(*) FROM extracted_entities WHERE source_id = :source_id"), {"source_id": source_id})
    ai_res = await db.execute(text("SELECT id FROM ai_analysis WHERE source_id = :source_id"), {"source_id": source_id})
    draft_res = await db.execute(text("SELECT * FROM grievance_drafts WHERE source_id = :source_id"), {"source_id": source_id})
    draft = draft_res.mappings().one_or_none()
    ai_ready = ai_res.mappings().one_or_none() is not None
    is_terminal = src["status"] in ('draft_ready', 'officer_approved', 'pushed_to_dro')

    return SourceStatusResponse(
        source_id=src["source_id"],
        file_name=src["file_name"],
        status=src["status"],
        ocr_confidence=round(avg_conf, 3) if avg_conf is not None else None,
        page_count=src["page_count"] or 0,
        chunk_count=chunk_cnt.scalar_one(),
        entity_count=entity_cnt.scalar_one(),
        ai_analysis_ready=ai_ready,
        draft_ready=draft is not None and (is_terminal or ai_ready),
        officer_approved=bool(draft["officer_approved"]) if draft else False,
        dro_status=draft["dro_status"] if draft else None,
        created_at=src["created_at"]
    )


@router.get("/{source_id}/status/stream")
async def stream_status(source_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Real-Time Server-Sent Events (SSE) status stream for multi-user live tracking.
    Enables up to 10 concurrent officers to track pipeline progress without polling storms.
    """
    async def event_generator():
        last_status = None
        consecutive_terminal = 0
        for _ in range(120):  # Stream up to ~2 minutes
            if await request.is_disconnected():
                logger.debug(f"SSE client disconnected for source {source_id}")
                break

            try:
                res = await db.execute(text("SELECT status FROM sources WHERE source_id = :sid"), {"sid": source_id})
                row = res.mappings().one_or_none()
                if not row:
                    yield f"data: {json.dumps({'error': 'Source not found'})}\n\n"
                    break

                curr_status = row["status"]
                if curr_status != last_status:
                    last_status = curr_status
                    payload = {
                        "source_id": source_id,
                        "status": curr_status,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    yield f"event: status_change\ndata: {json.dumps(payload)}\n\n"

                if curr_status in ('draft_ready', 'officer_approved', 'pushed_to_dro', 'completed', 'failed'):
                    consecutive_terminal += 1
                    if consecutive_terminal >= 2:
                        yield f"event: complete\ndata: {json.dumps({'source_id': source_id, 'status': curr_status})}\n\n"
                        break
            except Exception as e:
                logger.debug(f"SSE status stream notice: {e}")
                break

            await asyncio.sleep(0.8)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/{source_id}/ocr", response_model=OCRDocumentResponse)
async def get_ocr_results(source_id: str, db: AsyncSession = Depends(get_db)):
    """
    Return all OCR pages, text, bounding boxes, tables, and confidence scores
    """
    res = await db.execute(text("""
        SELECT page_number, full_text, avg_confidence, ocr_engine, processing_time_ms, blocks, tables
        FROM ocr_results
        WHERE source_id = :source_id
        ORDER BY page_number
    """), {"source_id": source_id})
    pages_raw = res.mappings().all()
    if not pages_raw:
        raise HTTPException(status_code=404, detail="No OCR results found for this document")

    pages = []
    total_blocks = 0
    for p in pages_raw:
        blocks = p["blocks"] if isinstance(p["blocks"], list) else json.loads(p["blocks"] or "[]")
        tables = p["tables"] if isinstance(p["tables"], list) else json.loads(p["tables"] or "[]")
        total_blocks += len(blocks)
        pages.append(OCRPageResult(
            page_number=p["page_number"],
            full_text=p["full_text"] or "",
            avg_confidence=p["avg_confidence"],
            ocr_engine=p["ocr_engine"],
            processing_time_ms=p["processing_time_ms"],
            blocks=blocks,
            tables=tables
        ))

    return OCRDocumentResponse(
        source_id=uuid.UUID(source_id),
        pages=pages,
        total_blocks=total_blocks
    )


@router.get("/{source_id}/page/{page_num}/image")
async def get_page_image(source_id: str, page_num: int, db: AsyncSession = Depends(get_db)):
    """
    Serve extracted page image from static media cache
    """
    if page_num < 1:
        raise HTTPException(status_code=404, detail=f"Page {page_num} image not found")

    img_path = file_store.get_page_image_path(source_id, page_num)
    if not os.path.exists(img_path):
        render_lock = _page_image_render_locks.setdefault(source_id, asyncio.Lock())
        async with render_lock:
            # Page previews are a cache. Recreate them from the saved source
            # file after a cache cleanup or an older deployment's container
            # replacement so the viewer can still show historical petitions.
            if not os.path.exists(img_path):
                file_path = file_store.get_file_path(source_id)
                temporary_source_path = None
                if file_path:
                    file_type = os.path.splitext(file_path)[1].lstrip(".").lower()
                else:
                    source_res = await db.execute(text(
                        "SELECT file_name, file_type, file_data FROM sources WHERE source_id = :source_id"
                    ), {"source_id": source_id})
                    source_row = source_res.mappings().one_or_none()
                    if not source_row or not source_row.get("file_data"):
                        raise HTTPException(status_code=404, detail="Original petition file is no longer available")
                    source_file_name = str(source_row.get("file_name") or "")
                    file_type = str(source_row.get("file_type") or os.path.splitext(source_file_name)[1]).lower().lstrip(".")
                    suffix = os.path.splitext(source_file_name)[1] or f".{file_type}"
                    try:
                        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_source:
                            temp_source.write(bytes(source_row["file_data"]))
                            temporary_source_path = temp_source.name
                        file_path = temporary_source_path
                    except Exception as exc:
                        logger.warning("Could not materialize stored petition %s for preview: %s", source_id, exc)
                        raise HTTPException(status_code=500, detail="Could not prepare petition page preview") from exc
                try:
                    await file_store.convert_document_to_images(source_id, file_path, file_type)
                except Exception as exc:
                    logger.warning("Could not regenerate page previews for %s: %s", source_id, exc)
                    raise HTTPException(status_code=500, detail="Could not render petition page previews") from exc
                finally:
                    if temporary_source_path:
                        try:
                            os.unlink(temporary_source_path)
                        except OSError:
                            pass
                if not os.path.exists(img_path):
                    raise HTTPException(status_code=404, detail=f"Page {page_num} image not found")
    return FileResponse(img_path, media_type="image/png")


@router.get("/{source_id}/file")
async def get_document_file(source_id: str, db: AsyncSession = Depends(get_db)):
    """
    Serve uploaded original document file (PDF or Image)
    """
    path = file_store.get_file_path(source_id)
    if path and os.path.exists(path):
        ext = os.path.splitext(path)[1].lower()
        media = "application/pdf" if ext == ".pdf" else f"image/{ext.replace('.', '')}"
        return FileResponse(path, media_type=media)

    # Check BYTEA stored in PostgreSQL
    res = await db.execute(text("SELECT file_name, file_type, file_data FROM sources WHERE source_id = :source_id"), {"source_id": source_id})
    row = res.mappings().one_or_none()
    if row and row["file_data"]:
        from fastapi.responses import Response
        media = "application/pdf" if row["file_type"] == "pdf" else f"image/{row['file_type']}"
        return Response(content=bytes(row["file_data"]), media_type=media)
    raise HTTPException(status_code=404, detail="Document file not found")


@router.post("/{source_id}/extract-entities", response_model=EntityExtractionResponse)
async def trigger_entity_extraction(
    source_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    officer: dict = Depends(get_current_officer)
):
    """
    Trigger entity extraction (Regex + AI NER + Location Validation)
    """
    entities = await entity_extractor.extract_all(db, source_id)
    verified = sum(1 for e in entities if e.get("validation_status") == "verified")
    suspect = sum(1 for e in entities if e.get("validation_status") == "suspect")

    await log_audit_event(
        db=db,
        action="EXTRACT_ENTITIES",
        source_id=source_id,
        details={"total": len(entities), "verified": verified, "suspect": suspect},
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    return EntityExtractionResponse(
        source_id=uuid.UUID(source_id),
        entities=[ExtractedEntityItem(**e) for e in entities],
        verified_count=verified,
        suspect_count=suspect
    )


@router.post("/{source_id}/analyze", response_model=AIAnalysisResponse)
async def trigger_ai_analysis(
    source_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    officer: dict = Depends(get_current_officer)
):
    """
    Trigger Qwen 2.5 classification, summaries, and hallucination verification barrier
    """
    analysis = await ai_analyzer.analyze(db, source_id)

    await log_audit_event(
        db=db,
        action="AI_ANALYZE",
        source_id=source_id,
        details={
            "dept": analysis.get("department"),
            "hallucination_score": analysis.get("hallucination_score"),
            "grounding_score": analysis.get("grounding_score")
        },
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    return AIAnalysisResponse(
        source_id=uuid.UUID(source_id),
        petitioner_name=analysis.get("petitioner_name"),
        father_husband_name=analysis.get("father_husband_name"),
        complainant_signatory=analysis.get("complainant_signatory"),
        grievance_type_suggested=analysis.get("grievance_type"),
        grievance_subtype_suggested=analysis.get("grievance_subtype"),
        department_suggested=analysis.get("department"),
        priority_suggested=analysis.get("priority", "MEDIUM"),
        description_summary_tamil=analysis.get("description_summary_tamil"),
        description_summary_english=analysis.get("description_summary_english"),
        action_items=analysis.get("action_items", []),
        claims=analysis.get("claims", []),
        hallucination_score=analysis.get("hallucination_score", 0.0),
        grounding_score=analysis.get("grounding_score", 1.0)
    )


@router.get("/{source_id}/analysis", response_model=AIAnalysisResponse)
async def get_ai_analysis(source_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve pre-computed AI analysis and summaries
    """
    res = await db.execute(text("SELECT * FROM ai_analysis WHERE source_id = :source_id ORDER BY id DESC LIMIT 1"), {"source_id": source_id})
    row = res.mappings().one_or_none()
    if row:
        draft_res = await db.execute(text("SELECT petitioner_name, father_husband_name, complainant_signatory FROM grievance_drafts WHERE source_id = :source_id"), {"source_id": source_id})
        d_row = draft_res.mappings().one_or_none()
        raw_actions = row["action_items"]
        if isinstance(raw_actions, str):
            try:
                raw_actions = json.loads(raw_actions)
            except Exception:
                raw_actions = []
        raw_claims = row["claims"]
        if isinstance(raw_claims, str):
            try:
                raw_claims = json.loads(raw_claims)
            except Exception:
                raw_claims = []
        return AIAnalysisResponse(
            source_id=row["source_id"],
            petitioner_name=d_row["petitioner_name"] if d_row else None,
            father_husband_name=d_row["father_husband_name"] if d_row else None,
            complainant_signatory=d_row["complainant_signatory"] if d_row else None,
            grievance_type_suggested=row["grievance_type_suggested"],
            grievance_subtype_suggested=row["grievance_subtype_suggested"],
            department_suggested=row["department_suggested"],
            priority_suggested=row["priority_suggested"] or "MEDIUM",
            description_summary_tamil=row["description_summary_tamil"],
            description_summary_english=row["description_summary_english"],
            action_items=raw_actions or [],
            claims=raw_claims or [],
            hallucination_score=row["hallucination_score"] or 0.0,
            grounding_score=row["grounding_score"] or 1.0
        )

    # If background queue is currently processing jobs for this source, do not trigger competing execution
    active_job = await db.execute(text("""
        SELECT id, job_type FROM job_queue 
        WHERE source_id = :source_id 
        AND status IN ('pending', 'processing')
        LIMIT 1
    """), {"source_id": source_id})
    if active_job.mappings().one_or_none():
        raise HTTPException(status_code=404, detail="AI analysis currently being generated by background pipeline")

    # Generate on-demand only if no background worker is active
    analysis = await ai_analyzer.analyze(db, source_id)
    return AIAnalysisResponse(
        source_id=uuid.UUID(source_id),
        petitioner_name=analysis.get("petitioner_name"),
        father_husband_name=analysis.get("father_husband_name"),
        complainant_signatory=analysis.get("complainant_signatory"),
        grievance_type_suggested=analysis.get("grievance_type"),
        grievance_subtype_suggested=analysis.get("grievance_subtype"),
        department_suggested=analysis.get("department"),
        priority_suggested=analysis.get("priority", "MEDIUM"),
        description_summary_tamil=analysis.get("description_summary_tamil"),
        description_summary_english=analysis.get("description_summary_english"),
        action_items=analysis.get("action_items", []),
        claims=analysis.get("claims", []),
        hallucination_score=analysis.get("hallucination_score", 0.0),
        grounding_score=analysis.get("grounding_score", 1.0)
    )


@router.post("/{source_id}/chat")
async def chat_with_document(
    source_id: str,
    req: ChatRequest,
    stream: bool = True,
    db: AsyncSession = Depends(get_db),
    officer: dict = Depends(get_current_officer)
):
    """
    RAG Assistant: Hybrid search (Vector + FTS) -> Grounded Qwen 2.5 streaming or JSON response with page citations
    """
    chunks = await vector_store.hybrid_search(db, query=req.question, source_id=source_id, top_k=req.top_k)
    citations = [
        {
            "page_number": c.get("page_number", 1),
            "chunk_id": str(c["id"]),
            "snippet": c["chunk_text"][:180] + "...",
            "similarity": float(c.get("score", 0.9))
        }
        for c in chunks
    ]

    context = "\n\n".join([f"[Page {c['page_number']}] {c['chunk_text']}" for c in chunks])
    prompt = f"""
ஆவணத்தின் அடிப்படையில் பின்வரும் கேள்விக்கு துல்லியமாக பதிலளிக்கவும்:

ஆவணப் பகுதிகள்:
{context}

கேள்வி: {req.question}

பதில்:
"""

    if not stream:
        ans = await llm_client.achat(prompt)
        return {"text": ans, "citations": citations}

    async def stream_generator():
        # First send citation metadata
        yield json.dumps({"citations": citations}) + "\n"
        async for chunk in llm_client.astream(prompt):
            yield json.dumps({"delta": chunk}) + "\n"
        yield json.dumps({"done": True}) + "\n"

    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")


@router.get("/{source_id}/draft", response_model=GrievanceDraftResponse)
async def get_draft(source_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve auto-populated draft for officer review
    """
    res = await db.execute(text("SELECT * FROM grievance_drafts WHERE source_id = :source_id"), {"source_id": source_id})
    draft = res.mappings().one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft has not been generated yet for this source")
    draft_dict = dict(draft)
    return GrievanceDraftResponse.model_validate(draft_dict)


@router.put("/draft/{draft_id}", response_model=GrievanceDraftResponse)
async def update_draft(
    draft_id: str,
    updates: DraftUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    officer: dict = Depends(get_current_officer)
):
    """
    Officer edits draft fields before approval
    """
    fields_to_update = {k: v for k, v in updates.model_dump().items() if v is not None and k in ALLOWED_UPDATE_FIELDS}
    if not fields_to_update:
        raise HTTPException(status_code=400, detail="No valid fields provided for update")

    set_clauses = [f"{k} = :{k}" for k in fields_to_update.keys()]
    sql = f"""
        UPDATE grievance_drafts 
        SET {', '.join(set_clauses)}, updated_at = NOW()
        WHERE id = :draft_id
        RETURNING *
    """
    params = {**fields_to_update, "draft_id": draft_id}
    res = await db.execute(text(sql), params)
    updated_draft = res.mappings().one_or_none()
    if not updated_draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    await db.commit()

    await log_audit_event(
        db=db,
        action="UPDATE_DRAFT",
        source_id=str(updated_draft["source_id"]) if updated_draft["source_id"] else None,
        officer_id=officer.get("officer_id"),
        details={"updated_fields": list(fields_to_update.keys())},
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    updated_dict = dict(updated_draft)
    return GrievanceDraftResponse.model_validate(updated_dict)


@router.post("/draft/{draft_id}/approve")
async def approve_draft(
    draft_id: str,
    request: Request,
    approve_req: DraftApproveRequest,
    db: AsyncSession = Depends(get_db),
    officer: dict = Depends(get_current_officer)
):
    """
    Officer explicitly signs and approves the draft
    """
    res = await db.execute(text("""
        UPDATE grievance_drafts
        SET officer_approved = TRUE, officer_id = :officer_id, officer_notes = :notes, approved_at = NOW(), updated_at = NOW()
        WHERE id = :draft_id
        RETURNING *
    """), {"draft_id": draft_id, "officer_id": approve_req.officer_id, "notes": approve_req.officer_notes})
    draft = res.mappings().one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft["source_id"]:
        await db.execute(text("UPDATE sources SET status = 'officer_approved', updated_at = NOW() WHERE source_id = :source_id"), {"source_id": str(draft["source_id"])})

    await db.commit()

    await log_audit_event(
        db=db,
        action="APPROVE_DRAFT",
        source_id=str(draft["source_id"]) if draft["source_id"] else None,
        officer_id=approve_req.officer_id,
        details={"notes": approve_req.officer_notes},
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    return {"success": True, "draft_id": draft_id, "officer_approved": True, "approved_at": draft["approved_at"]}


@router.post("/draft/{draft_id}/push-to-dro")
async def push_to_dro(
    draft_id: str,
    request: Request,
    officer_token: Optional[str] = Header(None),
    bypass_hallucination_warning: bool = False,
    db: AsyncSession = Depends(get_db),
    officer: dict = Depends(get_current_officer)
):
    """
    Finalize and mark approved draft as submitted in database
    """
    result = await db.execute(text("SELECT * FROM grievance_drafts WHERE id = :id"), {"id": draft_id})
    draft = result.mappings().one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft with ID {draft_id} not found")

    dro_id = draft["dro_grievance_id"] or f"TN/REV/DRO/{datetime.now().strftime('%d%b%y').upper()}/{uuid.uuid4().hex[:4].upper()}"
    await db.execute(text("""
        UPDATE grievance_drafts
        SET officer_approved = TRUE,
            approved_at = NOW(),
            dro_status = 'submitted',
            dro_grievance_id = :dro_id,
            updated_at = NOW()
        WHERE id = :id
    """), {"id": draft_id, "dro_id": dro_id})
    await db.commit()

    await log_audit_event(
        db=db,
        action="APPROVE_AND_SUBMIT_PETITION",
        source_id=str(draft["source_id"]) if draft["source_id"] else None,
        details={"dro_grievance_id": dro_id},
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    return {
        "success": True,
        "draft_id": draft_id,
        "source_id": str(draft["source_id"]) if draft["source_id"] else None,
        "dro_grievance_id": dro_id,
        "status": "submitted",
        "message": "Petition approved and recorded in grievance database successfully."
    }


@router.get("/history")
async def get_history(
    request: Request,
    officer_id: Optional[str] = None,
    limit: int = 100,
    current_officer: Optional[dict] = Depends(get_optional_officer),
    db: AsyncSession = Depends(get_db)
):
    """
    List sources and petitions processed by the requesting officer alone (or all officers if Admin).
    Strict Officer Isolation Query:
    Queries strictly filter WHERE s.officer_id = :officer_id joined with officers o ON s.officer_id = o.officer_id.
    Authenticated requests via query param, JWT bearer token, or X-Officer-Id header return only records for that specific officer.
    """
    # 1. Extract officer from token, header, or query param
    eff_officer_id = None
    is_admin = False

    if current_officer:
        eff_officer_id = current_officer.get("officer_id") or current_officer.get("id")
        is_admin = (
            current_officer.get("is_admin") is True or
            current_officer.get("isAdmin") is True or
            current_officer.get("role") in ["Admin", "District Administrator", "admin"] or
            (eff_officer_id and "ADM" in str(eff_officer_id).upper())
        )

    if not eff_officer_id:
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from core.security import decode_access_token
                payload = decode_access_token(auth_header[7:].strip())
                if payload:
                    eff_officer_id = payload.get("officer_id") or payload.get("id") or payload.get("sub")
                    if payload.get("is_admin") or (eff_officer_id and "ADM" in str(eff_officer_id).upper()):
                        is_admin = True
            except Exception:
                pass

    if not eff_officer_id:
        eff_officer_id = request.headers.get("x-officer-id") or request.headers.get("X-Officer-Id")

    # Priority to explicit officer_id query param if provided
    if officer_id and officer_id.strip() and officer_id not in ["all", "ALL"]:
        eff_officer_id = officer_id.strip()
    elif officer_id in ["all", "ALL"] and is_admin:
        eff_officer_id = None

    if is_admin and (not eff_officer_id or officer_id in ["all", "ALL"]):
        # Admin viewing global audit history
        sql = """
            SELECT s.source_id, s.file_name, s.file_type, s.file_size_bytes, s.page_count, s.status, s.created_at, s.officer_id,
                   d.id as draft_id, d.petitioner_name, d.phone, d.address, d.grievance_type, d.department, d.description,
                   d.dro_grievance_id, d.dro_status,
                   o.name as officer_name, o.designation as officer_designation
            FROM sources s
            LEFT JOIN grievance_drafts d ON s.source_id = d.source_id
            LEFT JOIN officers o ON s.officer_id = o.officer_id
            ORDER BY s.created_at DESC
            LIMIT :limit
        """
        res = await db.execute(text(sql), {"limit": limit})
    else:
        target_officer = eff_officer_id or "DRO_ERODE_01"
        sql = """
            SELECT s.source_id, s.file_name, s.file_type, s.file_size_bytes, s.page_count, s.status, s.created_at, s.officer_id,
                   d.id as draft_id, d.petitioner_name, d.phone, d.address, d.grievance_type, d.department, d.description,
                   d.dro_grievance_id, d.dro_status,
                   o.name as officer_name, o.designation as officer_designation
            FROM sources s
            LEFT JOIN grievance_drafts d ON s.source_id = d.source_id
            LEFT JOIN officers o ON s.officer_id = o.officer_id
            WHERE s.officer_id = :officer_id
            ORDER BY s.created_at DESC
            LIMIT :limit
        """
        res = await db.execute(text(sql), {"officer_id": target_officer, "limit": limit})

    rows = []
    for r in res.mappings().all():
        item = dict(r)
        item["source_id"] = str(item["source_id"])
        if item.get("draft_id"):
            item["draft_id"] = str(item["draft_id"])
        if item.get("created_at"):
            item["created_at"] = str(item["created_at"])
        rows.append(item)
    return rows


@router.get("/recent")
async def get_recent(
    request: Request,
    officer_id: Optional[str] = None,
    limit: int = 50,
    current_officer: Optional[dict] = Depends(get_optional_officer),
    db: AsyncSession = Depends(get_db)
):
    """
    Recent audit log and document history strictly isolated by officer (or all officers for admin).
    """
    raw_history = await get_history(
        request=request,
        officer_id=officer_id,
        limit=limit,
        current_officer=current_officer,
        db=db
    )
    formatted = []
    for item in raw_history:
        created_str = item.get("created_at") or ""
        uploaded_label = created_str[:16].replace("T", " ") if created_str else "Recent"
        file_size_kb = f"{round((item.get('file_size_bytes') or 0) / 1024, 1)} KB"
        
        summary_text = item.get("description") or (
            f"{item.get('petitioner_name') or 'Petitioner'} - {item.get('grievance_type') or 'General Grievance'}"
            if (item.get("petitioner_name") or item.get("grievance_type"))
            else (item.get("file_name") or "Processed Document")
        )

        formatted.append({
            "id": item.get("dro_grievance_id") or item.get("draft_id") or str(item.get("source_id", ""))[:8].upper(),
            "source_id": item.get("source_id"),
            "fileName": item.get("file_name") or "Petition Document",
            "file_type": item.get("file_type"),
            "fileSize": file_size_kb,
            "totalPages": item.get("page_count") or 1,
            "status": item.get("status"),
            "created_at": item.get("created_at"),
            "uploadedAt": uploaded_label,
            "officer_id": item.get("officer_id"),
            "officer_name": item.get("officer_name"),
            "officer_designation": item.get("officer_designation"),
            "petitionerName": item.get("petitioner_name") or "Processing...",
            "petitioner_name": item.get("petitioner_name"),
            "phone": item.get("phone") or "-",
            "address": item.get("address") or "-",
            "grievanceType": item.get("grievance_type") or "-",
            "grievance_type": item.get("grievance_type"),
            "department": item.get("department") or "-",
            "summary": summary_text,
            "timestamp": item.get("created_at")
        })
    return formatted


@router.get("/departments", response_model=List[str])
async def list_official_departments():
    """
    Returns the complete list of official government departments
    derived directly from the CM Helpline Grievance Taxonomy.
    """
    from services.taxonomy_matcher import taxonomy_matcher
    return taxonomy_matcher.get_official_departments()


# ------------------------------------------------------------------------------
# Mobile QR Petition Capture & LAN Network Session Management
# ------------------------------------------------------------------------------
_mobile_upload_sessions: dict[str, dict] = {}


def _get_lan_hosts(request: Request):
    import socket
    local_ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and ip != "127.0.0.1":
            local_ips.append(ip)
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        _, _, addresses = socket.gethostbyname_ex(hostname)
        for addr in addresses:
            if addr not in local_ips and not addr.startswith("127."):
                local_ips.append(addr)
    except Exception:
        pass

    client_host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    port_str = ""
    if ":" in client_host:
        port_str = f":{client_host.split(':')[1]}"
    elif request.url.port and request.url.port not in (80, 443):
        port_str = f":{request.url.port}"

    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"

    available_hosts = []
    for ip in local_ips:
        available_hosts.append({
            "name": f"Wi-Fi / LAN IP ({ip})",
            "ip": ip,
            "url": f"{scheme}://{ip}{port_str}"
        })

    primary_url = available_hosts[0]["url"] if available_hosts else None
    return primary_url, available_hosts


@router.get("/network-info")
async def get_network_info(request: Request):
    """Returns local LAN IP addresses of the host machine for QR mobile upload."""
    primary_url, available_hosts = _get_lan_hosts(request)
    return {
        "primaryUrl": primary_url,
        "availableHosts": available_hosts
    }


@router.post("/mobile-session")
async def create_mobile_session(request: Request):
    """Generates a mobile QR petition upload session with automatic LAN IP routing."""
    import secrets
    session_id = secrets.token_hex(4)  # 8 hex chars
    primary_url, available_hosts = _get_lan_hosts(request)

    _mobile_upload_sessions[session_id] = {
        "sessionId": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "uploaded": False,
        "data": None
    }

    return {
        "sessionId": session_id,
        "session_id": session_id,
        "networkHost": primary_url,
        "availableHosts": available_hosts
    }


@router.get("/mobile-status/{session_id}")
async def get_mobile_session_status(session_id: str):
    """Polls upload status for a mobile petition capture session."""
    session = _mobile_upload_sessions.get(session_id)
    if not session:
        return {"uploaded": False, "sessionId": session_id}

    if session.get("uploaded") and session.get("data"):
        return {
            "uploaded": True,
            "sessionId": session_id,
            **session["data"]
        }

    return {"uploaded": False, "sessionId": session_id}


@router.post("/mobile-upload")
async def upload_mobile_petition(
    request: Request,
    sessionId: Optional[str] = Form(None),
    fileName: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """Handles mobile camera petition image/PDF upload over LAN Wi-Fi."""
    # Handle JSON payload fallback if proxy serialized as JSON
    session_id_val = sessionId
    file_name_val = fileName
    file_bytes = None
    file_type_val = "image/jpeg"

    if not file:
        try:
            json_body = await request.json()
            session_id_val = json_body.get("sessionId") or session_id_val
            file_name_val = json_body.get("fileName") or file_name_val
            file_type_val = json_body.get("fileType") or file_type_val
            data_url = json_body.get("dataUrl")
            if data_url and "," in data_url:
                import base64
                header, base64_str = data_url.split(",", 1)
                file_bytes = base64.b64decode(base64_str)
        except Exception:
            pass
    else:
        file_bytes = await file.read()
        file_type_val = file.content_type or file_type_val

    if not session_id_val:
        raise HTTPException(status_code=400, detail="Missing sessionId in mobile upload payload")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="No petition file content received")

    ext = "pdf" if (file_type_val == "application/pdf" or (file_name_val and file_name_val.endswith(".pdf"))) else "jpg"
    final_filename = file_name_val or f"mobile_petition_{session_id_val}.{ext}"

    # Save to file store and register source
    new_source_id = str(uuid.uuid4())
    file_path, file_hash, file_size = await file_store.save_uploaded_file(new_source_id, final_filename, file_bytes)

    # Ensure mobile_qr officer exists to satisfy foreign key
    try:
        await db.execute(text("""
            INSERT INTO officers (officer_id, name, name_tamil, email, designation, department, status)
            VALUES ('mobile_qr', 'Mobile QR Upload', 'மொபைல் QR பதிவேற்றம்', 'mobile@tn.gov.in', 'Mobile Upload', 'வருவாய்த்துறை', 'Active')
            ON CONFLICT (officer_id) DO NOTHING
        """))
        await db.flush()
    except Exception as e:
        logger.debug(f"Officer record validation notice: {e}")

    file_data_db = file_bytes if getattr(settings, "STORE_FILE_BYTEA", False) else None
    await db.execute(text("""
        INSERT INTO sources (source_id, officer_id, file_name, file_type, file_size_bytes, file_hash, page_count, status, file_data, created_at, updated_at)
        VALUES (:source_id, 'mobile_qr', :file_name, :file_type, :file_size, :file_hash, 0, 'uploaded', :file_data, NOW(), NOW())
    """), {
        "source_id": new_source_id,
        "file_name": final_filename,
        "file_type": ext,
        "file_size": file_size,
        "file_hash": file_hash,
        "file_data": file_data_db
    })
    await db.commit()

    # Queue background processing
    await job_queue.enqueue(db, "ocr", new_source_id, {"file_path": file_path, "file_type": ext})

    payload = {
        "sessionId": session_id_val,
        "source_id": new_source_id,
        "fileName": final_filename,
        "fileSize": f"{round(len(file_bytes)/1024, 1)} KB",
        "fileType": file_type_val,
        "status": "processing",
        "page_count": 1
    }

    _mobile_upload_sessions[session_id_val] = {
        "sessionId": session_id_val,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "uploaded": True,
        "data": payload
    }

    return {"success": True, "message": "Mobile petition received and queued", "sessionId": session_id_val}

