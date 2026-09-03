from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from models.database import get_db
from models.schemas import QueueStatusResponse, MasterLocationCreate

router = APIRouter(prefix="/admin", tags=["Admin & System"])


@router.get("/queue-status", response_model=QueueStatusResponse)
async def get_queue_status(db: AsyncSession = Depends(get_db)):
    """
    Returns counts of pending, processing, completed, and failed tasks in PostgreSQL SKIP LOCKED queue
    """
    res = await db.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE status = 'pending') as pending,
            COUNT(*) FILTER (WHERE status = 'processing') as processing,
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) FILTER (WHERE status = 'failed') as failed
        FROM job_queue
    """))
    counts = res.mappings().one()
    return QueueStatusResponse(
        pending=counts["pending"] or 0,
        processing=counts["processing"] or 0,
        completed=counts["completed"] or 0,
        failed=counts["failed"] or 0
    )


@router.get("/stats")
async def get_system_stats(db: AsyncSession = Depends(get_db)):
    """
    System overview statistics
    """
    sources_cnt = await db.execute(text("SELECT COUNT(*) FROM sources"))
    chunks_cnt = await db.execute(text("SELECT COUNT(*) FROM document_chunks"))
    drafts_cnt = await db.execute(text("SELECT COUNT(*) FROM grievance_drafts"))
    approved_cnt = await db.execute(text("SELECT COUNT(*) FROM grievance_drafts WHERE officer_approved = TRUE"))
    audit_cnt = await db.execute(text("SELECT COUNT(*) FROM audit_log"))

    return {
        "total_sources": sources_cnt.scalar_one(),
        "total_chunks": chunks_cnt.scalar_one(),
        "total_drafts": drafts_cnt.scalar_one(),
        "approved_drafts": approved_cnt.scalar_one(),
        "total_audit_events": audit_cnt.scalar_one()
    }


@router.post("/master-location")
async def add_master_location(
    loc: MasterLocationCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Seed or add master location for Taluk/Village validation
    """
    await db.execute(text("""
        INSERT INTO master_locations (
            district_code, district_name_tamil, taluk_code, taluk_name_tamil,
            block_code, block_name_tamil, firka_code, firka_name_tamil,
            village_code, village_name_tamil
        ) VALUES (
            :d_code, :d_name, :t_code, :t_name,
            :b_code, :b_name, :f_code, :f_name,
            :v_code, :v_name
        ) ON CONFLICT DO NOTHING
    """), {
        "d_code": loc.district_code,
        "d_name": loc.district_name_tamil,
        "t_code": loc.taluk_code,
        "t_name": loc.taluk_name_tamil,
        "b_code": loc.block_code,
        "b_name": loc.block_name_tamil,
        "f_code": loc.firka_code,
        "f_name": loc.firka_name_tamil,
        "v_code": loc.village_code,
        "v_name": loc.village_name_tamil
    })
    await db.commit()
    return {"status": "success", "message": f"Master location {loc.village_name_tamil} registered"}


@router.get("/master-locations")
async def list_master_locations(
    query: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    sql = """
        SELECT * FROM master_locations
        WHERE (:query IS NULL OR village_name_tamil ILIKE :q_like OR taluk_name_tamil ILIKE :q_like)
        LIMIT :limit
    """
    res = await db.execute(text(sql), {"query": query, "q_like": f"%{query}%" if query else None, "limit": limit})
    return [dict(r) for r in res.mappings().all()]


@router.get("/audit-logs")
async def list_audit_logs(
    limit: int = 50,
    action: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    sql = """
        SELECT * FROM audit_log
        WHERE (:action IS NULL OR action = :action)
        ORDER BY timestamp DESC
        LIMIT :limit
    """
    res = await db.execute(text(sql), {"action": action, "limit": limit})
    return [dict(r) for r in res.mappings().all()]
