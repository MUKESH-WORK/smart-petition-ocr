import os
import tempfile
import asyncio
import logging

# Ensure all uploads & temp buffers use E: drive with 30GB+ free space instead of full C: drive
_workspace_temp = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "temp_cache"))
os.makedirs(_workspace_temp, exist_ok=True)
os.environ["TEMP"] = _workspace_temp
os.environ["TMP"] = _workspace_temp
os.environ["TMPDIR"] = _workspace_temp
tempfile.tempdir = _workspace_temp

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.routers import grievance, search, admin
from models.database import engine, AsyncSessionLocal
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

    # Seed default officer and master locations if empty
    try:
        async with AsyncSessionLocal() as db:
            # Seed default officer
            await db.execute(text("""
                INSERT INTO officers (officer_id, name_tamil, designation, department, taluk_access)
                VALUES ('DRO_ERODE_01', 'சுந்தரம் கே.', 'மாவட்ட வருவாய் அலுவலர்', 'வருவாய்த்துறை', ARRAY['பெருந்துறை', 'ஈரோடு', 'பவானி'])
                ON CONFLICT (officer_id) DO NOTHING;
            """))

            # Seed sample master locations
            await db.execute(text("""
                INSERT INTO master_locations (district_code, district_name_tamil, taluk_code, taluk_name_tamil, block_code, block_name_tamil, firka_code, firka_name_tamil, village_code, village_name_tamil)
                VALUES 
                ('10', 'ஈரோடு', '01', 'பெருந்துறை', '01', 'பெருந்துறை', '01', 'பெருந்துறை', '001', 'காந்தி நகர்'),
                ('10', 'ஈரோடு', '01', 'பெருந்துறை', '01', 'பெருந்துறை', '01', 'பெருந்துறை', '002', 'விஜயமங்கலம்'),
                ('10', 'ஈரோடு', '02', 'பவானி', '02', 'பவானி', '02', 'பவானி', '003', 'அந்தியூர்'),
                ('10', 'ஈரோடு', '03', 'ஈரோடு', '03', 'ஈரோடு', '03', 'சூரியம்பாளையம்', '004', 'சூரியம்பாளையம்'),
                ('12', 'கோயம்புத்தூர்', '01', 'பொள்ளாச்சி', '01', 'பொள்ளாச்சி', '01', 'ஆனைமலை', '005', 'ஆனைமலை')
                ON CONFLICT (district_code, taluk_code, block_code, firka_code, village_code) DO NOTHING;
            """))
            await db.commit()
            logger.info("Master locations and default officers verified.")
    except Exception as e:
        logger.warning(f"Could not auto-seed master locations: {e}")

    # Warm up background services
    from services.vector_store import vector_store
    from services.ocr_router import ocr_router
    from core.llm_client import llm_client

    try:
        vector_store.warmup()
        await llm_client._verify_or_discover_model()
        logger.info("AI models and embedder initialized and ready.")
    except Exception as e:
        logger.warning(f"Non-blocking model warmup notice: {e}")

    # Start background job queue worker
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


@app.get("/")
async def root():
    return {
        "module": "DRO Grievance AI Module",
        "state": "Tamil Nadu Revenue Department",
        "database": "PostgreSQL 16 with pgvector, tsvector & JSONB",
        "docs": "/api/v1/docs"
    }
