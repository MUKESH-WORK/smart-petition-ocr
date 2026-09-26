import os
import sys
import json
import tempfile
import asyncio
import logging
from contextlib import asynccontextmanager

# Ensure backend directory is in sys.path for robust imports across all processes
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Ensure all uploads & temp buffers use workspace temp cache
_workspace_temp = os.path.abspath(os.path.join(_backend_dir, "temp_cache"))
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
from app.routers import grievance, search, admin, translate, petitions
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

    # 2. Warm up background services & master data asynchronously so server binds instantly (<1s)
    from services.vector_store import vector_store
    from core.llm_client import llm_client

    async def _async_warmup():
        try:
            from services.master_data_seeder import seed_master_data_if_needed
            await seed_master_data_if_needed()
            await asyncio.to_thread(vector_store.warmup)
            await llm_client._verify_or_discover_model()
            await llm_client.keep_alive_ping()
            logger.info("AI models, embedder, and master data initialized and warmed in VRAM.")
        except Exception as e:
            logger.warning(f"Non-blocking model warmup notice: {e}")

    asyncio.create_task(_async_warmup())

    # 3. Always-Warm LLM Background Heartbeat Daemon
    async def _keep_alive_daemon():
        interval = getattr(settings, "LLM_KEEP_ALIVE_INTERVAL", 120)
        while True:
            try:
                await asyncio.sleep(interval)
                await llm_client.keep_alive_ping()
            except asyncio.CancelledError:
                break
            except Exception as ex:
                logger.debug(f"Keep-alive ping notice: {ex}")

    keep_alive_task = asyncio.create_task(_keep_alive_daemon())

    # 4. Start concurrent worker pool (Postgres SKIP LOCKED queue)
    worker_task = asyncio.create_task(job_queue.run_worker_pool())
    
    yield

    # Teardown
    job_queue.stop()
    worker_task.cancel()
    keep_alive_task.cancel()
    try:
        await asyncio.wait_for(asyncio.gather(worker_task, keep_alive_task, return_exceptions=True), timeout=2.0)
    except Exception:
        pass
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

# ------------------------------------------------------------------------------
# Security Hardening & Rate Limiting Middleware (OWASP & Industry Best Practices)
# ------------------------------------------------------------------------------
from collections import defaultdict
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory IP rate limiter protecting against automated brute-force DDoS.
    Exempts localhost/internal testing to avoid locking developers and workstations out.
    """
    def __init__(self, app):
        super().__init__(app)
        self.requests = defaultdict(list)
        self.cleanup_counter = 0

    async def dispatch(self, request: Request, call_next):
        # Extract true client IP from proxy headers if present
        forwarded = request.headers.get("CF-Connecting-IP") or request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"
        
        # Local development / loopback / container bridge addresses are exempt
        if client_ip in ["127.0.0.1", "localhost", "::1", "testclient"]:
            return await call_next(request)

        now = time.time()
        path = request.url.path

        # Exempt high-frequency real-time polling and status endpoints
        if any(p in path for p in ["/mobile-status", "/health", "/metrics", "/static", "/ws", "/stream", "/ping"]):
            return await call_next(request)

        # Cleanup old entries every 500 requests
        self.cleanup_counter += 1
        if self.cleanup_counter > 500:
            self.cleanup_counter = 0
            for ip in list(self.requests.keys()):
                self.requests[ip] = [ts for ts in self.requests[ip] if now - ts < 60]
                if not self.requests[ip]:
                    del self.requests[ip]

        # Rate limits supporting 10-20 concurrent officers & mobile citizens seamlessly
        is_login_post = request.method == "POST" and ("/login" in path)
        max_requests = 300 if is_login_post else 5000

        recent = [ts for ts in self.requests[client_ip] if now - ts < 60]
        if len(recent) >= max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please wait a moment before trying again."}
            )

        recent.append(now)
        self.requests[client_ip] = recent
        return await call_next(request)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# CORS configuration
raw_origins = getattr(settings, "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:5174")
allowed_origins = [orig.strip() for orig in raw_origins.split(",") if orig.strip()]
is_wildcard = "*" in allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Static media mount for rendered petition page images
app.mount("/static/media", StaticFiles(directory=settings.STATIC_MEDIA_DIR), name="static_media")

# Mount API Routers
app.include_router(grievance.router, prefix=settings.API_V1_STR)
app.include_router(search.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(translate.router, prefix=settings.API_V1_STR)
app.include_router(petitions.router, prefix=settings.API_V1_STR)

# Mount Architecture Pipeline Routers (Async OCR, Redis Queue, Documents API)
try:
    from app.api.routes.documents import router as documents_router
    from app.api.routes.auth import router as auth_router
    from app.api.routes.status import router as status_router
    app.include_router(documents_router)
    app.include_router(auth_router)
    app.include_router(status_router)
except Exception as _r_err:
    logger.warning(f"Architecture pipeline routes notice: {_r_err}")

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

    # 2. Check LLM Server (non-blocking probe; decoupled from liveness to prevent crash loops)
    try:
        active_model = getattr(llm_client, "model", settings.LLM_MODEL_NAME)
        try:
            active_model = await asyncio.wait_for(llm_client._verify_or_discover_model(), timeout=1.0)
        except Exception:
            pass
        checks["components"]["llm"] = {
            "status": "up" if getattr(llm_client, "_model_verified", False) else "standby",
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


# Static root files for the frontend (icons, logos, robots, sitemap)
for static_asset in ["favicon.svg", "icons.svg", "tn-emblem.png", "robots.txt", "sitemap.xml"]:
    asset_path = os.path.join(frontend_dist, static_asset)
    if not os.path.isfile(asset_path):
        # Also check public folder if not yet built
        fallback_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "public", static_asset))
        if os.path.isfile(fallback_path):
            asset_path = fallback_path

    if os.path.isfile(asset_path):
        def _make_static_route(p):
            async def _serve():
                return FileResponse(p)
            return _serve
        app.get(f"/{static_asset}")(_make_static_route(asset_path))

