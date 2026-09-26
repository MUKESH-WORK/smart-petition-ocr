import os
from fastapi import APIRouter
from app.queue.redis_queue import get_redis_client
from app.database.connection import engine
from sqlalchemy import text

router = APIRouter(
    prefix="/api/status",
    tags=["Status"]
)

@router.get("")
async def get_system_status():
    """
    Check availability of core pipeline services (Database, Redis Queue, Storage).
    """
    db_ok = False
    redis_ok = False

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    try:
        client = get_redis_client()
        pong = await client.ping()
        redis_ok = (pong is True)
    except Exception:
        redis_ok = False

    storage_dir = os.getenv("UPLOAD_DIR", "/app/storage/uploads")
    storage_ok = os.path.exists(storage_dir)

    all_healthy = db_ok and redis_ok and storage_ok

    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": {
            "database": "up" if db_ok else "down",
            "redis": "up" if redis_ok else "down",
            "storage": "up" if storage_ok else "down"
        },
        "environment": os.getenv("ENVIRONMENT", "production")
    }
