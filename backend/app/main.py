import os
import json
import tempfile
import asyncio
import logging
from contextlib import asynccontextmanager

# Ensure all uploads & temp buffers use workspace temp cache
_workspace_temp = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "temp_cache"))
os.makedirs(_workspace_temp, exist_ok=True)
os.environ["TEMP"] = _workspace_temp
os.environ["TMP"] = _workspace_temp
os.environ["TMPDIR"] = _workspace_temp
tempfile.tempdir = _workspace_temp

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text

from app.config import settings
from app.routers import grievance, search, admin
from models.database import engine, AsyncSessionLocal, init_db_schema, is_sqlite
from services.job_queue import job_queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("dro_backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing DRO Grievance AI Backend...")

    # 1. Ensure all database tables exist (SQLite & PostgreSQL)
    try:
        await init_db_schema()
    except Exception as e:
        logger.error(f"Schema initialization warning: {e}")

    # 2. Seed default officer and master locations portably if empty
    try:
        async with AsyncSessionLocal() as db:
            # Seed default officer
            off_check = await db.execute(text("SELECT officer_id FROM officers WHERE officer_id = 'DRO_ERODE_01'"))
            if not off_check.scalar():
                if is_sqlite:
                    await db.execute(text("""
                        INSERT INTO officers (officer_id, name_tamil, designation, department, taluk_access)
                        VALUES ('DRO_ERODE_01', 'சுந்தரம் கே.', 'மாவட்ட வருவாய் அலுவலர்', 'வருவாய்த்துறை', :taluk)
                    """), {"taluk": json.dumps(['பெருந்துறை', 'ஈரோடு', 'பவானி'])})
                else:
                    await db.execute(text("""
                        INSERT INTO officers (officer_id, name_tamil, designation, department, taluk_access)
                        VALUES ('DRO_ERODE_01', 'சுந்தரம் கே.', 'மாவட்ட வருவாய் அலுவலர்', 'வருவாய்த்துறை', ARRAY['பெருந்துறை', 'ஈரோடு', 'பவானி'])
                        ON CONFLICT (officer_id) DO NOTHING;
                    """))

            # Seed sample master locations if empty
            loc_cnt = await db.execute(text("SELECT COUNT(*) FROM master_locations"))
            if (loc_cnt.scalar() or 0) == 0:
                await db.execute(text("""
                    INSERT INTO master_locations (district_code, district_name_tamil, taluk_code, taluk_name_tamil, block_code, block_name_tamil, firka_code, firka_name_tamil, village_code, village_name_tamil)
                    VALUES 
                    ('10', 'ஈரோடு', '01', 'பெருந்துறை', '01', 'பெருந்துறை', '01', 'பெருந்துறை', '001', 'காந்தி நகர்'),
                    ('10', 'ஈரோடு', '01', 'பெருந்துறை', '01', 'பெருந்துறை', '01', 'பெருந்துறை', '002', 'விஜயமங்கலம்'),
                    ('10', 'ஈரோடு', '02', 'பவானி', '02', 'பவானி', '02', 'பவானி', '003', 'அந்தியூர்'),
                    ('10', 'ஈரோடு', '03', 'ஈரோடு', '03', 'ஈரோடு', '03', 'சூரியம்பாளையம்', '004', 'சூரியம்பாளையம்'),
                    ('12', 'கோயம்புத்தூர்', '01', 'பொள்ளாச்சி', '01', 'பொள்ளாச்சி', '01', 'ஆனைமலை', '005', 'ஆனைமலை')
                """))
            await db.commit()
            logger.info("Master locations and default officers verified.")
    except Exception as e:
        logger.warning(f"Could not auto-seed master locations: {e}")

    # 3. Warm up background services asynchronously so server binds instantly (<1s)
    from services.vector_store import vector_store
    from core.llm_client import llm_client

    async def _async_warmup():
        try:
            await asyncio.to_thread(vector_store.warmup)
            await llm_client._verify_or_discover_model()
            logger.info("AI models and embedder initialized and ready.")
        except Exception as e:
            logger.warning(f"Non-blocking model warmup notice: {e}")

    asyncio.create_task(_async_warmup())

    # 4. Start background job queue worker
    worker_task = asyncio.create_task(job_queue.run_worker_loop(worker_id="worker-primary-01"))
    
    yield

    # Teardown
    worker_task.cancel()
    await engine.dispose()
    logger.info("DRO Grievance Backend shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="District Revenue Officer (DRO) Grievance Digitization & Automation Module - Production Backend",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static media mount for rendered petition page images
app.mount("/static/media", StaticFiles(directory=settings.STATIC_MEDIA_DIR), name="static_media")

# Mount API Routers
app.include_router(grievance.router, prefix=settings.API_V1_STR)
app.include_router(search.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)

# Locate pre-built frontend distribution
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
frontend_assets = os.path.join(frontend_dist, "assets")
if os.path.isdir(frontend_assets):
    app.mount("/assets", StaticFiles(directory=frontend_assets), name="frontend_assets")


@app.get("/health")
@app.get(f"{settings.API_V1_STR}/health")
async def health_check():
    """
    Enterprise health check endpoint (Microsoft/Azure/Google Cloud monitoring pattern).
    Inspects database, Ollama/LLM, disk storage, and queue status.
    """
    import shutil
    from core.llm_client import llm_client

    checks = {
        "status": "healthy",
        "timestamp": os.getenv("CURRENT_TIME", ""),
        "components": {}
    }

    # 1. Check Database
    try:
        async with AsyncSessionLocal() as db:
            db_res = await db.execute(text("SELECT 1"))
            db_res.scalar_one()

            # Check queue counts using portable aggregation
            q_res = await db.execute(text("""
                SELECT 
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending_count,
                    SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) AS processing_count,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_count
                FROM job_queue
            """))
            q_stats = {k: v or 0 for k, v in dict(q_res.mappings().one()).items()}

        checks["components"]["database"] = {
            "status": "up",
            "type": "SQLite (Zero-Dependency Embedded Mode)" if is_sqlite else "PostgreSQL 16 + pgvector",
            "queue": q_stats
        }
    except Exception as e:
        checks["status"] = "degraded"
        checks["components"]["database"] = {"status": "down", "error": str(e)}

    # 2. Check LLM Server
    try:
        active_model = await llm_client._verify_or_discover_model()
        checks["components"]["llm"] = {
            "status": "up",
            "provider": settings.LLM_PROVIDER,
            "active_model": active_model,
            "base_url": settings.LLM_API_BASE_URL
        }
    except Exception as e:
        checks["components"]["llm"] = {
            "status": "offline_with_heuristic_fallback",
            "warning": str(e)
        }

    # 3. Check Storage & Disk
    try:
        total, used, free = shutil.disk_usage(settings.UPLOAD_DIR)
        checks["components"]["storage"] = {
            "status": "up",
            "upload_dir": settings.UPLOAD_DIR,
            "free_gb": round(free / (1024 ** 3), 2),
            "used_gb": round(used / (1024 ** 3), 2)
        }
    except Exception as e:
        checks["components"]["storage"] = {"status": "error", "error": str(e)}

    # 4. OCR Engine
    provider = getattr(settings, "OCR_PROVIDER", "datalab")
    engine_label = "Datalab Chandra OCR (Cloud API)" if provider == "datalab" else "PaddleOCR PP-OCRv5 (Tamil/English)"
    checks["components"]["ocr"] = {
        "engine": engine_label,
        "provider": provider,
        "preprocessing": getattr(settings, "OCR_PREPROCESSING_ENABLED", True),
        "target_dimension": getattr(settings, "OCR_MAX_IMAGE_DIMENSION", 1500),
        "dpi": getattr(settings, "OCR_DPI", 200)
    }

    return checks


@app.get("/")
async def root(request: Request):
    """
    Root endpoint:
    - Serves the Single Page Application (SPA) HTML to web browsers
    - Returns structured JSON to API clients and automated tests
    """
    accept = request.headers.get("accept", "")
    index_file = os.path.join(frontend_dist, "index.html")

    # If browser is requesting HTML and dist build exists, serve the rich UI
    if accept.startswith("text/html") and os.path.isfile(index_file):
        return FileResponse(index_file)

    # Otherwise return API info JSON (compatible with TestClient and API explorers)
    return {
        "module": "DRO Grievance AI Module",
        "state": "Tamil Nadu Revenue Department",
        "database": "SQLite (Zero-Dependency Embedded Mode)" if is_sqlite else "PostgreSQL 16 with pgvector",
        "health": "/health",
        "docs": f"{settings.API_V1_STR}/docs",
        "ui": "/app" if os.path.isfile(index_file) else None
    }


@app.get("/app")
@app.get("/ui")
async def serve_ui():
    """Explicit endpoint to serve the frontend application."""
    index_file = os.path.join(frontend_dist, "index.html")
    if os.path.isfile(index_file):
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Frontend distribution build not found. Run 'npm run build' in frontend/.")


# Static root files for the frontend (icons, logos)
for static_asset in ["favicon.svg", "icons.svg", "tn-emblem.png"]:
    asset_path = os.path.join(frontend_dist, static_asset)
    if os.path.isfile(asset_path):
        def _make_static_route(p):
            async def _serve():
                return FileResponse(p)
            return _serve
        app.get(f"/{static_asset}")(_make_static_route(asset_path))

