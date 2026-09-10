from typing import List, Optional
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from models.database import get_db
from models.schemas import QueueStatusResponse, MasterLocationCreate, QualityMetricsResponse

router = APIRouter(prefix="/admin", tags=["Admin & System"])


@router.get("/quality", response_model=QualityMetricsResponse)
async def get_quality_metrics(db: AsyncSession = Depends(get_db)):
    """
    Live data quality metrics derived from real database records:
    - Pass rate: ratio of approved drafts to total drafts
    - Review rate: ratio of drafts requiring officer correction
    - Average hallucination score across AI analysis runs
    - Failure count grouped by pipeline stage
    """
    # 1. Total and approved drafts
    d_res = await db.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE officer_approved = TRUE) as approved
        FROM grievance_drafts
    """))
    d_counts = d_res.mappings().one()
    total_drafts = d_counts["total"] or 0
    approved_drafts = d_counts["approved"] or 0
    pass_rate = round(float(approved_drafts) / float(total_drafts), 3) if total_drafts > 0 else 1.0

    # 2. Review rate (drafts where entities were corrected by officer)
    corr_res = await db.execute(text("""
        SELECT COUNT(DISTINCT source_id) as corrected
        FROM extracted_entities
        WHERE review_state = 'corrected' OR officer_corrected = TRUE
    """))
    corrected_count = corr_res.scalar() or 0
    review_rate = round(float(corrected_count) / float(total_drafts), 3) if total_drafts > 0 else 0.0

    # 3. Average hallucination score
    h_res = await db.execute(text("SELECT AVG(hallucination_score) as avg_hall FROM ai_analysis"))
    h_val = h_res.scalar()
    avg_hallucination = round(float(h_val), 3) if h_val is not None else 0.0

    # 4. Stage failures from job_queue
    f_res = await db.execute(text("""
        SELECT job_type, COUNT(*) as cnt
        FROM job_queue
        WHERE status = 'failed'
        GROUP BY job_type
    """))
    stage_failures = {r["job_type"]: r["cnt"] for r in f_res.mappings().all()}

    # 5. Total petitions
    s_cnt = await db.execute(text("SELECT COUNT(*) FROM sources"))
    total_petitions = s_cnt.scalar() or 0

    return QualityMetricsResponse(
        total_petitions=total_petitions,
        pass_rate=pass_rate,
        review_rate=review_rate,
        avg_hallucination_score=avg_hallucination,
        stage_failures=stage_failures
    )


@router.post("/benchmark/run")
async def trigger_benchmark_run(
    run_type: str = Query("latency", enum=["latency", "stock_vs_int8", "stock_vs_finetuned"]),
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers empirical benchmark measurement and stores results into benchmark_runs table.
    """
    import time
    start_t = time.time()

    # Query recent pages for latency measurement
    res = await db.execute(text("""
        SELECT page_number, processing_time_ms, avg_confidence
        FROM ocr_results
        ORDER BY id DESC
        LIMIT 8
    """))
    rows = res.mappings().all()
    latencies = [r["processing_time_ms"] for r in rows if r["processing_time_ms"]]
    confs = [r["avg_confidence"] for r in rows if r["avg_confidence"] is not None]

    avg_lat_s = round(float(np.mean(latencies)) / 1000.0, 2) if latencies else 0.0
    avg_conf = round(float(np.mean(confs)), 3) if confs else 0.0

    metrics = {
        "avg_latency_s": avg_lat_s,
        "avg_confidence": avg_conf,
        "sample_count": len(rows),
        "target_latency_s": 40.0,
        "meets_latency_gate": avg_lat_s <= 40.0,
        "execution_provider": "CPU"
    }
    config = {
        "engine": "PP-OCRv5",
        "det_tier": "mobile_det",
        "rec_model": "ta_PP-OCRv5_mobile_rec",
        "run_type": run_type
    }

    # Persist to benchmark_runs
    import json
    ins_res = await db.execute(text("""
        INSERT INTO benchmark_runs (run_type, config, metrics, run_at)
        VALUES (:rtype, :config, :metrics, NOW())
        RETURNING run_id, run_at
    """), {
        "rtype": run_type,
        "config": json.dumps(config),
        "metrics": json.dumps(metrics)
    })
    b_row = ins_res.mappings().one()
    await db.commit()

    from app.dependencies import log_audit_event
    await log_audit_event(
        db,
        action="BENCHMARK_RUN",
        details={"run_id": b_row["run_id"], "run_type": run_type, "metrics": metrics}
    )

    return {
        "run_id": b_row["run_id"],
        "run_type": run_type,
        "config": config,
        "metrics": metrics,
        "run_at": b_row["run_at"]
    }


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
