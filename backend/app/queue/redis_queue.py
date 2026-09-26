import os
import json
import logging
import redis.asyncio as redis

logger = logging.getLogger("gdp_queue")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
QUEUE_NAME = os.getenv("REDIS_QUEUE_NAME", "ocr_jobs")

_client = None

def get_redis_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
    return _client

redis_client = get_redis_client()

async def enqueue_document(document_id: str, file_path: str):
    """
    Push document processing job to Redis queue for background worker consumption.
    """
    job = {
        "document_id": document_id,
        "file_path": file_path
    }
    client = get_redis_client()
    await client.rpush(
        QUEUE_NAME,
        json.dumps(job)
    )
    logger.info(f"Enqueued document {document_id} to queue '{QUEUE_NAME}'")
