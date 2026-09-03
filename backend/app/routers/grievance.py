import os
import json
import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Header, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from models.database import get_db
from models.schemas import (
    SourceUploadResponse, SourceStatusResponse, OCRDocumentResponse, OCRPageResult,
    EntityExtractionResponse, ExtractedEntityItem, AIAnalysisResponse,
    ChatRequest, GrievanceDraftResponse, DraftUpdate, DraftApproveRequest
)
from services.file_store import file_store
from services.ocr_router import ocr_router
from services.tamil_chunker import tamil_chunker
from services.vector_store import vector_store
from services.entity_extractor import entity_extractor
from services.ai_analyzer import ai_analyzer
from services.dro_bridge import dro_bridge
from services.job_queue import job_queue
from app.dependencies import get_current_officer, log_audit_event
from core.llm_client import llm_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/grievance", tags=["Grievance Processing"])


@router.post("/upload", response_model=SourceUploadResponse)
async def upload_petition(
    request: Request,
    file: UploadFile = File(...),
    officer_id: str = Form("DRO_DEFAULT_OFFICER"),
    process_now: bool = Form(True),
    db: AsyncSession = Depends(get_db)
):
    """
    1. Read uploaded petition (PDF/Image)
    2. Compute SHA256 & save to uploads/
    3. Insert sources record (status='uploaded')
    4. Save BYTEA into PostgreSQL for single-store archival
    5. Enqueue OCR job into PostgreSQL SKIP LOCKED queue
    6. If process_now is True, synchronously or via worker trigger OCR
    7. Log audit event
    """
    try:
        source_id = str(uuid.uuid4())
        content = await file.read()
        ext = os.path.splitext(file.filename)[1].lower().replace(".", "")
        if ext not in ["pdf", "png", "jpg", "jpeg", "tiff", "docx"]:
            ext = "png"

        # Save to disk and calculate SHA256
        file_path, file_hash, file_size = await file_store.save_uploaded_file(source_id, file.filename, content)

        # Ensure officer exists to satisfy foreign key
        if officer_id:
            await db.execute(text("""
                INSERT INTO officers (officer_id, name_tamil, designation, department)
                VALUES (:officer_id, 'வருவாய் அலுவலர்', 'DRO Officer', 'வருவாய்த்துறை')
                ON CONFLICT (officer_id) DO NOTHING
            """), {"officer_id": officer_id})

        # Insert into sources
        res_insert = await db.execute(text("""
            INSERT INTO sources (source_id, officer_id, file_name, file_type, file_size_bytes, file_hash, page_count, status, file_data, created_at, updated_at)
            VALUES (CAST(:source_id AS UUID), :officer_id, :file_name, :file_type, :file_size, :file_hash, 0, 'uploaded', :file_data, NOW(), NOW())
            ON CONFLICT (file_hash) DO UPDATE SET
                file_name = EXCLUDED.file_name,
                updated_at = NOW()
            RETURNING source_id, file_name, file_size_bytes, page_count, status, created_at
        """), {
            "source_id": source_id,
            "officer_id": officer_id,
            "file_name": file.filename,
            "file_type": ext,
            "file_size": file_size,
            "file_hash": file_hash,
            "file_data": content
        })
        row = res_insert.mappings().one()
        source_id = str(row["source_id"])
        await db.commit()

        # If draft already exists for this source_id (e.g. re-upload / cached file), return immediately
        draft_check = await db.execute(text("SELECT id FROM grievance_drafts WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": source_id})
        if draft_check.mappings().one_or_none():
            logger.info(f"Existing draft found for source {source_id}, returning immediately.")
            return SourceUploadResponse(
                source_id=row["source_id"],
                file_name=row["file_name"],
                file_size_bytes=row["file_size_bytes"],
                page_count=row["page_count"] or 1,
                status="draft_ready",
                created_at=row["created_at"],
                message="Petition recognized and draft loaded from database."
            )

        # Enqueue OCR job to background worker only if not processing immediately
        if not process_now:
            await job_queue.enqueue(db, "ocr", source_id, {"file_path": file_path, "file_type": ext})
        else:
            # Synchronous fast-track processing
            try:
                await ocr_router.process_source(db, source_id, file_path, ext)
                # Chunk & index vector
                res = await db.execute(text("SELECT page_number, full_text FROM ocr_results WHERE source_id = CAST(:source_id AS UUID) ORDER BY page_number"), {"source_id": source_id})
                pages = res.mappings().all()
                all_chunks = []
                for p in pages:
                    chunks = tamil_chunker.split(p["full_text"] or "", p["page_number"])
                    all_chunks.extend(chunks)
                if all_chunks:
                    await vector_store.index_document(db, source_id, all_chunks)
                
                # Extract entities
                await entity_extractor.extract_all(db, source_id)

                # AI Analysis
                await ai_analyzer.analyze(db, source_id)
            except Exception as e:
                logger.error(f"Error during immediate pipeline processing: {e}", exc_info=True)

        # Log audit event
        await log_audit_event(
            db=db,
            action="UPLOAD_PETITION",
            source_id=source_id,
            officer_id=officer_id,
            details={"file_name": file.filename, "file_size": file_size, "hash": file_hash},
            ip_address="127.0.0.1"
        )

        # Refresh row status
        res_final = await db.execute(text("SELECT source_id, file_name, file_size_bytes, page_count, status, created_at FROM sources WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": source_id})
        row_final = res_final.mappings().one()

        return SourceUploadResponse(
            source_id=row_final["source_id"],
            file_name=row_final["file_name"],
            file_size_bytes=row_final["file_size_bytes"] or 0,
            page_count=row_final["page_count"] or 1,
            status=row_final["status"],
            created_at=row_final["created_at"]
        )
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{source_id}/status", response_model=SourceStatusResponse)
async def get_status(source_id: str, db: AsyncSession = Depends(get_db)):
    """
    Return comprehensive processing and verification status for the petition
    """
    src_res = await db.execute(text("SELECT * FROM sources WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": source_id})
    src = src_res.mappings().one_or_none()
    if not src:
        raise HTTPException(status_code=404, detail="Source document not found")

    ocr_res = await db.execute(text("SELECT AVG(avg_confidence) as avg_conf FROM ocr_results WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": source_id})
    avg_conf_row = ocr_res.mappings().one_or_none()
    avg_conf = float(avg_conf_row["avg_conf"]) if avg_conf_row and avg_conf_row["avg_conf"] is not None else None

    chunk_cnt = await db.execute(text("SELECT COUNT(*) FROM document_chunks WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": source_id})
    entity_cnt = await db.execute(text("SELECT COUNT(*) FROM extracted_entities WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": source_id})
    ai_res = await db.execute(text("SELECT id FROM ai_analysis WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": source_id})
    draft_res = await db.execute(text("SELECT * FROM grievance_drafts WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": source_id})
    draft = draft_res.mappings().one_or_none()

    return SourceStatusResponse(
        source_id=src["source_id"],
        file_name=src["file_name"],
        status=src["status"],
        ocr_confidence=round(avg_conf, 3) if avg_conf is not None else None,
        page_count=src["page_count"] or 0,
        chunk_count=chunk_cnt.scalar_one(),
        entity_count=entity_cnt.scalar_one(),
        ai_analysis_ready=ai_res.mappings().one_or_none() is not None,
        draft_ready=draft is not None,
        officer_approved=bool(draft["officer_approved"]) if draft else False,
        dro_status=draft["dro_status"] if draft else None,
        created_at=src["created_at"]
    )


@router.get("/{source_id}/ocr", response_model=OCRDocumentResponse)
async def get_ocr_results(source_id: str, db: AsyncSession = Depends(get_db)):
    """
    Return all OCR pages, text, bounding boxes, tables, and confidence scores
    """
    res = await db.execute(text("""
        SELECT page_number, full_text, avg_confidence, ocr_engine, processing_time_ms, blocks, tables
        FROM ocr_results
        WHERE source_id = CAST(:source_id AS UUID)
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
async def get_page_image(source_id: str, page_num: int):
    """
    Serve extracted page image from static media cache
    """
    img_path = file_store.get_page_image_path(source_id, page_num)
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
    res = await db.execute(text("SELECT file_name, file_type, file_data FROM sources WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": source_id})
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
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db)
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
    res = await db.execute(text("SELECT * FROM ai_analysis WHERE source_id = CAST(:source_id AS UUID) ORDER BY id DESC LIMIT 1"), {"source_id": source_id})
    row = res.mappings().one_or_none()
    if row:
        return AIAnalysisResponse(
            source_id=row["source_id"],
            grievance_type_suggested=row["grievance_type_suggested"],
            grievance_subtype_suggested=row["grievance_subtype_suggested"],
            department_suggested=row["department_suggested"],
            priority_suggested=row["priority_suggested"] or "MEDIUM",
            description_summary_tamil=row["description_summary_tamil"],
            description_summary_english=row["description_summary_english"],
            action_items=row["action_items"] or [],
            claims=row["claims"] or [],
            hallucination_score=row["hallucination_score"] or 0.0,
            grounding_score=row["grounding_score"] or 1.0
        )
    # Generate if not cached
    analysis = await ai_analyzer.analyze(db, source_id)
    return AIAnalysisResponse(
        source_id=uuid.UUID(source_id),
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
    db: AsyncSession = Depends(get_db)
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
    res = await db.execute(text("SELECT * FROM grievance_drafts WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": source_id})
    draft = res.mappings().one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft has not been generated yet for this source")
    return GrievanceDraftResponse(**dict(draft))


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
    fields_to_update = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not fields_to_update:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    set_clauses = [f"{k} = :{k}" for k in fields_to_update.keys()]
    sql = f"""
        UPDATE grievance_drafts 
        SET {', '.join(set_clauses)}, updated_at = NOW()
        WHERE id = CAST(:draft_id AS UUID)
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
        ip_address="127.0.0.1"
    )

    return GrievanceDraftResponse(**dict(updated_draft))


@router.post("/draft/{draft_id}/approve")
async def approve_draft(
    draft_id: str,
    request: Request,
    approve_req: DraftApproveRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Officer explicitly signs and approves the draft
    """
    res = await db.execute(text("""
        UPDATE grievance_drafts
        SET officer_approved = TRUE, officer_id = :officer_id, officer_notes = :notes, approved_at = NOW(), updated_at = NOW()
        WHERE id = CAST(:draft_id AS UUID)
        RETURNING *
    """), {"draft_id": draft_id, "officer_id": approve_req.officer_id, "notes": approve_req.officer_notes})
    draft = res.mappings().one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft["source_id"]:
        await db.execute(text("UPDATE sources SET status = 'officer_approved', updated_at = NOW() WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": str(draft["source_id"])})

    await db.commit()

    await log_audit_event(
        db=db,
        action="APPROVE_DRAFT",
        source_id=str(draft["source_id"]) if draft["source_id"] else None,
        officer_id=approve_req.officer_id,
        details={"notes": approve_req.officer_notes},
        ip_address="127.0.0.1"
    )

    return {"success": True, "draft_id": draft_id, "officer_approved": True, "approved_at": draft["approved_at"]}


@router.post("/draft/{draft_id}/push-to-dro")
async def push_to_dro(
    draft_id: str,
    request: Request,
    officer_token: Optional[str] = Header(None),
    bypass_hallucination_warning: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Call DRO portal API bridge to submit approved draft
    """
    token = officer_token or "DRO_OFFICER_SESSION_TOKEN_2026"
    try:
        result = await dro_bridge.push_draft(
            draft_id=draft_id,
            officer_token=token,
            db=db,
            bypass_hallucination_warning=bypass_hallucination_warning
        )

        await log_audit_event(
            db=db,
            action="PUSH_TO_DRO",
            source_id=result.get("source_id"),
            details={"dro_grievance_id": result.get("dro_grievance_id")},
            ip_address=request.client.host if request.client else "127.0.0.1"
        )

        return result
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))


@router.get("/history")
async def get_history(
    officer_id: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    List sources and petitions processed by officer
    """
    if officer_id:
        sql = """
            SELECT s.source_id, s.file_name, s.file_type, s.page_count, s.status, s.created_at,
                   d.id as draft_id, d.petitioner_name, d.grievance_type, d.dro_grievance_id, d.dro_status
            FROM sources s
            LEFT JOIN grievance_drafts d ON s.source_id = d.source_id
            WHERE s.officer_id = :officer_id
            ORDER BY s.created_at DESC
            LIMIT :limit
        """
        res = await db.execute(text(sql), {"officer_id": officer_id, "limit": limit})
    else:
        sql = """
            SELECT s.source_id, s.file_name, s.file_type, s.page_count, s.status, s.created_at,
                   d.id as draft_id, d.petitioner_name, d.grievance_type, d.dro_grievance_id, d.dro_status
            FROM sources s
            LEFT JOIN grievance_drafts d ON s.source_id = d.source_id
            ORDER BY s.created_at DESC
            LIMIT :limit
        """
        res = await db.execute(text(sql), {"limit": limit})

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
