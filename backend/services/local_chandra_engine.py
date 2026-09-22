import os
import io
import json
import time
import base64
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import httpx
from PIL import Image
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


def compute_dhash(image_input, hash_size: int = 8) -> str:
    """
    Computes a 64-bit difference hash (dHash) for fast perceptual duplicate detection.
    Robust to slight resizing, minor scanning noise, and format changes.
    """
    try:
        if isinstance(image_input, str):
            img = Image.open(image_input).convert("L")
        elif isinstance(image_input, Image.Image):
            img = image_input.convert("L")
        elif isinstance(image_input, np.ndarray):
            img = Image.fromarray(image_input).convert("L")
        else:
            return ""

        # Resize to (hash_size + 1, hash_size)
        resized = img.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = list(resized.get_flattened_data() if hasattr(resized, "get_flattened_data") else resized.getdata())

        difference = []
        for row in range(hash_size):
            for col in range(hash_size):
                pixel_left = pixels[row * (hash_size + 1) + col]
                pixel_right = pixels[row * (hash_size + 1) + col + 1]
                difference.append(pixel_left > pixel_right)

        # Convert boolean list to 64-bit hexadecimal string
        decimal_val = 0
        for idx, val in enumerate(difference):
            if val:
                decimal_val |= 1 << idx
        return f"{decimal_val:016x}"
    except Exception as e:
        logger.debug(f"Perceptual dHash calculation notice: {e}")
        return ""


def hamming_distance(hash1: str, hash2: str) -> int:
    """Computes the Hamming distance between two hex hash strings."""
    try:
        val1 = int(hash1, 16)
        val2 = int(hash2, 16)
        xor_val = val1 ^ val2
        return bin(xor_val).count("1")
    except Exception:
        return 999


class LocalChandraEngine:
    """
    High-Throughput Local Chandra OCR V2 (5.6B Parameter Model) Inference Client.
    Target: Up to 12 FPS / pages throughput.
    
    Production Features:
    - Asynchronous continuous batching support (submitting 4-8 pages per forward pass)
    - Connection pooling with persistent HTTP/2 / keep-alive sessions
    - Non-blocking dynamic health check
    - Normalizes local OCR polygons and layout tokens into identical Datalab Chandra schema
    """

    def __init__(self):
        self._base_url = getattr(settings, "LOCAL_CHANDRA_URL", "http://127.0.0.1:8088/v1").rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
        self._is_online: Optional[bool] = None
        self._last_health_check: float = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        timeout = float(getattr(settings, "LOCAL_CHANDRA_TIMEOUT", 30.0))
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=timeout,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )
        return self._client

    async def check_health(self) -> bool:
        """Lightweight probe to verify if local Chandra 5.6B server is running."""
        now = time.time()
        if self._is_online is not None and (now - self._last_health_check) < 10.0:
            return self._is_online

        if not getattr(settings, "LOCAL_CHANDRA_ENABLED", False):
            self._is_online = False
            return False

        try:
            client = await self._get_client()
            health_url = f"{self._base_url}/health"
            resp = await client.get(health_url, timeout=1.5)
            self._is_online = (resp.status_code == 200)
        except Exception:
            self._is_online = False

        self._last_health_check = now
        return self._is_online

    async def process_pages_batch(
        self,
        image_paths: List[str],
        start_page_num: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Submits a batch of preprocessed page images to local Chandra OCR V2 server.
        Processes in parallel batches to reach ~12 FPS throughput.
        """
        client = await self._get_client()
        batch_size = getattr(settings, "LOCAL_CHANDRA_BATCH_SIZE", 8)
        pages_result: List[Dict[str, Any]] = []

        for i in range(0, len(image_paths), batch_size):
            chunk_paths = image_paths[i:i + batch_size]
            encoded_images = []

            for p_path in chunk_paths:
                try:
                    with open(p_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                        encoded_images.append(b64)
                except Exception as ex:
                    logger.warning(f"Could not encode page image {p_path}: {ex}")

            if not encoded_images:
                continue

            payload = {
                "images": encoded_images,
                "model": "chandra-ocr-v2-5.6b",
                "options": {
                    "return_layout": True,
                    "return_tables": True,
                    "target_language": "ta"
                }
            }

            try:
                t0 = time.time()
                endpoint = f"{self._base_url}/ocr/batch"
                resp = await client.post(endpoint, json=payload)
                resp.raise_for_status()
                data = resp.json()

                batch_duration = time.time() - t0
                fps = len(encoded_images) / max(batch_duration, 0.001)
                logger.info(f"⚡ [LOCAL CHANDRA 5.6B] Processed {len(encoded_images)} pages in {batch_duration:.2f}s (~{fps:.1f} FPS)")

                batch_pages = data.get("pages", [])
                for idx, page_data in enumerate(batch_pages):
                    curr_page_num = start_page_num + i + idx
                    full_text = page_data.get("text", "").strip()
                    blocks = page_data.get("blocks", [])
                    tables = page_data.get("tables", [])
                    confidence = float(page_data.get("confidence", 0.96))

                    pages_result.append({
                        "page_number": curr_page_num,
                        "full_text": full_text,
                        "blocks": blocks,
                        "tables": tables,
                        "avg_confidence": confidence,
                        "ocr_engine": "local_chandra_v2"
                    })

            except Exception as e:
                logger.error(f"Local Chandra batch inference failed: {e}")
                break

        return pages_result


# Singleton
local_chandra = LocalChandraEngine()
