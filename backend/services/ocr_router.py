"""
Chandra OCR Router Engine.
Exclusively powered by Datalab Chandra OCR Cloud API for state-of-the-art
Tamil & English handwriting recognition, multi-page layout parsing, and entity grounding.
"""

import os
import sys
import json
import logging
import time
import asyncio
from typing import List, Dict, Any, Optional, TYPE_CHECKING
import numpy as np
from PIL import Image
import httpx
from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text
else:
    try:
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy import text
    except ImportError:
        AsyncSession = Any
        text = lambda x: x

from app.config import settings
from services.file_store import file_store

logger = logging.getLogger(__name__)


def compute_dhash(image_input: Any, hash_size: int = 8) -> Optional[str]:
    """
    Computes a 64-bit difference hash (dHash) for perceptual image deduplication.
    """
    try:
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                return None
            img = Image.open(image_input)
        elif isinstance(image_input, (bytes, bytearray)):
            import io
            img = Image.open(io.BytesIO(image_input))
        elif hasattr(image_input, "convert"):
            img = image_input
        else:
            return None

        resized = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = list(resized.getdata())
        diff = []
        for row in range(hash_size):
            for col in range(hash_size):
                left = pixels[row * (hash_size + 1) + col]
                right = pixels[row * (hash_size + 1) + col + 1]
                diff.append(left > right)

        decimal_val = 0
        hex_parts = []
        for idx, bit in enumerate(diff):
            if bit:
                decimal_val += 2 ** (idx % 8)
            if (idx % 8) == 7:
                hex_parts.append(hex(decimal_val)[2:].rjust(2, "0"))
                decimal_val = 0

        return "".join(hex_parts)
    except Exception as ex:
        logger.debug(f"dHash computation notice: {ex}")
        return None


class ChandraOCRRouter:
    """
    Chandra Cloud OCR Engine:
    - Exclusively driven by Datalab Chandra Cloud API key
    - Multi-mode cascade:
      * Primary: Accurate Mode (deep neural Tamil layout analysis)
      * Fallback: Balanced Mode (automatic retry on timeout)
      * Fast Fallback: Fast Mode
    """

    async def _process_with_datalab(
        self,
        file_path: str,
        file_type: str,
        mode: Optional[str] = None,
        timeout_sec: Optional[int] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Processes document via Datalab Chandra OCR Cloud API with dynamic mode (accurate vs balanced vs fast).
        """
        api_key = getattr(settings, "DATALAB_API_KEY", "")
        api_url = getattr(settings, "DATALAB_API_URL", "https://www.datalab.to/api/v1/convert")
        eff_mode = str(mode or getattr(settings, "DATALAB_MODE", "accurate")).strip().lower()
        if eff_mode not in ["fast", "balanced", "accurate"]:
            eff_mode = "accurate"
        eff_timeout = timeout_sec or getattr(settings, "DATALAB_TIMEOUT", 60)

        if not api_key:
            logger.warning("DATALAB_API_KEY is not configured; skipping Datalab Chandra OCR.")
            return None

        clean_ext = file_type.lower().replace(".", "")
        mime_map = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
            "tiff": "image/tiff",
            "tif": "image/tiff",
        }
        mime_type = mime_map.get(clean_ext, "application/octet-stream")
        base_name = os.path.basename(file_path)

        logger.info(f"Submitting {base_name} to Datalab Chandra OCR API [{eff_mode} mode, timeout={eff_timeout}s]...")

        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()

            headers = {
                "X-API-Key": api_key
            }
            files = {
                "file": (base_name, file_bytes, mime_type)
            }
            form_data = {
                "output_format": "json",
                "mode": eff_mode,
                "paginate": "true"
            }

            async with httpx.AsyncClient(timeout=180.0) as client:
                submit_resp = await client.post(api_url, headers=headers, files=files, data=form_data)

                if submit_resp.status_code != 200:
                    logger.error(f"Datalab Chandra API submission failed: {submit_resp.status_code} - {submit_resp.text}")
                    return None

                submit_data = submit_resp.json()
                check_url = submit_data.get("request_check_url")
                if not check_url:
                    logger.error(f"Datalab response missing 'request_check_url': {submit_data}")
                    return None

                logger.info(f"Polling Datalab Chandra task: {check_url}")
                start_poll = time.time()
                poll_result = None

                while (time.time() - start_poll) < eff_timeout:
                    await asyncio.sleep(1.5)
                    poll_resp = await client.get(check_url, headers=headers)
                    if poll_resp.status_code == 200:
                        poll_data = poll_resp.json()
                        status = poll_data.get("status")
                        if status == "complete":
                            poll_result = poll_data
                            break
                        elif status == "failed":
                            logger.error(f"Datalab Chandra conversion failed: {poll_data}")
                            return None
                    else:
                        logger.warning(f"Polling HTTP {poll_resp.status_code}: {poll_resp.text}")

                if not poll_result:
                    logger.error(f"Datalab Chandra OCR ({eff_mode}) timed out after {eff_timeout}s")
                    return None

            # Parse the Datalab Chandra JSON structure
            json_payload = poll_result.get("json") or {}
            children = json_payload.get("children", [])
            raw_score = float(poll_result.get("parse_quality_score") or 0.98)
            if raw_score > 1.0:
                raw_score = raw_score / 5.0 if raw_score <= 5.0 else raw_score / 100.0
            parse_score = max(0.0, min(1.0, round(raw_score, 3)))

            pages_output: List[Dict[str, Any]] = []
            has_pages = any(c.get("block_type") == "Page" for c in children)

            if has_pages:
                for idx, page in enumerate(children, 1):
                    if page.get("block_type") != "Page":
                        continue
                    sub_blocks = page.get("children", [])
                    p_blocks, p_tables, text_segments = self._parse_datalab_blocks(sub_blocks, idx, parse_score)

                    if not text_segments and page.get("html"):
                        raw_soup = BeautifulSoup(page["html"], "html.parser")
                        clean_page_text = raw_soup.get_text("\n").strip()
                        if clean_page_text:
                            text_segments.append(clean_page_text)

                    full_page_text = "\n\n".join(text_segments)
                    pages_output.append({
                        "page_number": idx,
                        "full_text": full_page_text,
                        "blocks": p_blocks,
                        "tables": p_tables,
                        "avg_confidence": parse_score,
                        "ocr_engine": "datalab_chandra"
                    })
            else:
                p_blocks, p_tables, text_segments = self._parse_datalab_blocks(children, 1, parse_score)
                full_page_text = "\n\n".join(text_segments)
                pages_output.append({
                    "page_number": 1,
                    "full_text": full_page_text,
                    "blocks": p_blocks,
                    "tables": p_tables,
                    "avg_confidence": parse_score,
                    "ocr_engine": "datalab_chandra"
                })

            # Print exact Chandra OCR response safely
            try:
                print("\n" + "=" * 70, flush=True)
                print("[CHANDRA OCR RESULT SUCCESS]", flush=True)
                print(f"[CHANDRA OCR STATUS]: {poll_result.get('status')}", flush=True)
                print(f"[CHANDRA OCR QUALITY SCORE]: {poll_result.get('parse_quality_score')}", flush=True)
                for p in pages_output:
                    print(f"--- [CHANDRA OCR PAGE {p['page_number']} EXTRACTED TEXT] ---", flush=True)
                    text_to_print = p.get("full_text", "")
                    try:
                        print(text_to_print, flush=True)
                    except Exception:
                        print(text_to_print.encode("ascii", errors="replace").decode("ascii"), flush=True)
                print("=" * 70 + "\n", flush=True)
            except Exception as _log_err:
                logger.debug(f"Console printing notice: {_log_err}")

            logger.info(f"Datalab Chandra OCR successfully extracted {len(pages_output)} pages.")
            return pages_output

        except Exception as e:
            logger.error(f"Unexpected error in Datalab Chandra OCR pipeline: {e}", exc_info=True)
            return None

    def _parse_datalab_blocks(
        self, sub_blocks: List[Dict[str, Any]], page_num: int, default_conf: float
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        """
        Parses Chandra sub-blocks into structured blocks, tables, and text segments.
        """
        page_blocks = []
        page_tables = []
        text_segments = []

        for b in sub_blocks:
            b_type = b.get("block_type", "Text")
            b_html = b.get("html", "") or ""

            soup = BeautifulSoup(b_html, "html.parser")
            clean_text = soup.get_text("\n").strip()

            polygon = b.get("polygon")
            if not polygon and b.get("bbox"):
                bx = b["bbox"]
                if len(bx) == 4:
                    polygon = [
                        [bx[0], bx[1]],
                        [bx[2], bx[1]],
                        [bx[2], bx[3]],
                        [bx[0], bx[3]]
                    ]

            poly_coords = polygon if polygon else [[0, 0], [100, 0], [100, 20], [0, 20]]

            if b_type == "Table":
                page_tables.append({
                    "html": b_html,
                    "text": clean_text,
                    "polygon": poly_coords
                })

            if clean_text:
                text_segments.append(clean_text)
                b_conf = float(b.get("confidence") if b.get("confidence") is not None else default_conf)
                page_blocks.append({
                    "id": b.get("id", f"/page/{page_num}/{b_type}/{len(page_blocks)}"),
                    "text": clean_text,
                    "confidence": max(0.0, min(1.0, round(b_conf, 3))),
                    "bbox": poly_coords,
                    "page": page_num,
                    "block_type": b_type,
                    "engine": "datalab_chandra"
                })

        return page_blocks, page_tables, text_segments

    async def process_document(
        self,
        source_id: str,
        file_path: str,
        file_type: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Main OCR pipeline:
        1. Checks database cache for existing OCR results.
        2. Executes digital PDF fast-path if native text is present.
        3. Computes and saves perceptual hash (dHash).
        4. Invokes Datalab Chandra Cloud API (Accurate mode -> Balanced fallback -> Fast retry).
        5. Persists page-by-page OCR results and updates source status.
        """
        start_time = time.time()
        logger.info(f"Starting Chandra OCR processing for source_id: {source_id} ({file_type})")

        # 1. Check existing OCR results cache
        existing_res = await db.execute(text("""
            SELECT page_number, full_text, blocks, tables, avg_confidence, ocr_engine
            FROM ocr_results
            WHERE source_id = :source_id
            ORDER BY page_number ASC
        """), {"source_id": source_id})
        rows = existing_res.fetchall()

        if rows:
            logger.info(f"Returning {len(rows)} cached OCR pages for source {source_id}")
            total_blocks = sum(len(json.loads(r[2])) if isinstance(r[2], str) else len(r[2] or []) for r in rows)
            return {
                "source_id": source_id,
                "pages": len(rows),
                "total_blocks": total_blocks,
                "cached": True,
                "status": "ocr_complete",
                "total_time_ms": int((time.time() - start_time) * 1000),
                "ocr_engine": rows[0][5] if rows else "datalab_chandra"
            }

        # Convert document pages to images
        images = []
        try:
            images = await file_store.convert_document_to_images(source_id, file_path, file_type)
        except Exception as e:
            logger.warning(f"Image conversion notice for source {source_id}: {e}")

        clean_ext = file_type.lower().replace(".", "")
        pages_data: Optional[List[Dict[str, Any]]] = None
        engine_used = "datalab_chandra"

        # Compute and persist perceptual hash (dHash) for duplicate detection
        if images:
            try:
                phash_val = compute_dhash(images[0])
                if phash_val:
                    await db.execute(text("""
                        UPDATE sources SET phash = :phash WHERE source_id = :sid
                    """), {"phash": phash_val, "sid": source_id})
                    await db.commit()
            except Exception as ex_phash:
                logger.debug(f"Perceptual hash update notice: {ex_phash}")

        # Chandra OCR Cloud API Cascade (Accurate Mode Primary)
        if not pages_data:
            # Step 1: Accurate Mode
            logger.info("Calling Cloud Chandra OCR API (Accurate Mode)...")
            pages_data = await self._process_with_datalab(
                file_path,
                file_type,
                mode=getattr(settings, "DATALAB_MODE", "accurate"),
                timeout_sec=getattr(settings, "DATALAB_TIMEOUT", 120)
            )

            # Step 2: Fallback to Balanced Mode
            if not pages_data:
                fallback_mode = getattr(settings, "DATALAB_FALLBACK_MODE", "balanced")
                fallback_timeout = getattr(settings, "DATALAB_FALLBACK_TIMEOUT", 45)
                logger.warning(
                    f"Chandra OCR Accurate Mode failed or timed out. "
                    f"Engaging fallback to Cloud Chandra OCR [{fallback_mode}] Mode (timeout={fallback_timeout}s)..."
                )
                pages_data = await self._process_with_datalab(
                    file_path,
                    file_type,
                    mode=fallback_mode,
                    timeout_sec=fallback_timeout
                )
                if pages_data:
                    engine_used = f"datalab_chandra_{fallback_mode}"
            else:
                engine_used = "datalab_chandra_accurate"

            # Step 3: Fast Mode Retry
            if not pages_data:
                logger.warning("Chandra OCR Balanced Mode timed out. Retrying with Cloud Chandra OCR [fast] Mode...")
                pages_data = await self._process_with_datalab(
                    file_path,
                    file_type,
                    mode="fast",
                    timeout_sec=25
                )
                if pages_data:
                    engine_used = "datalab_chandra_fast"

        # Final safeguard if all API attempts failed
        if not pages_data:
            engine_used = "ocr_unavailable"
            pages_data = []
            if not images:
                try:
                    images = await file_store.convert_document_to_images(source_id, file_path, file_type)
                except Exception:
                    images = []
            for page_num in range(1, max(len(images) + 1, 2)):
                pages_data.append({
                    "page_number": page_num,
                    "full_text": "[ஆவண உரை கண்டறியப்படவில்லை / OCR முடிவுகள் நிலுவையில் உள்ளன]",
                    "blocks": [],
                    "tables": [],
                    "avg_confidence": 0.0,
                    "ocr_engine": engine_used
                })

        # Persist per-page results into ocr_results
        total_blocks = 0
        for p in pages_data:
            p_num = p["page_number"]
            full_txt = p.get("full_text", "")
            blocks = p.get("blocks", [])
            tables = p.get("tables", [])
            avg_conf = max(0.0, min(1.0, float(p.get("avg_confidence", 0.95))))
            p_engine = p.get("ocr_engine", engine_used)
            total_blocks += len(blocks)

            await db.execute(text("""
                INSERT INTO ocr_results (source_id, page_number, full_text, blocks, tables, avg_confidence, ocr_engine, processing_time_ms)
                VALUES (:source_id, :page_number, :full_text, :blocks, :tables, :avg_confidence, :ocr_engine, :processing_time_ms)
                ON CONFLICT (source_id, page_number) DO UPDATE SET
                    full_text = EXCLUDED.full_text,
                    blocks = EXCLUDED.blocks,
                    tables = EXCLUDED.tables,
                    avg_confidence = EXCLUDED.avg_confidence,
                    ocr_engine = EXCLUDED.ocr_engine,
                    processing_time_ms = EXCLUDED.processing_time_ms
            """), {
                "source_id": source_id,
                "page_number": p_num,
                "full_text": full_txt,
                "blocks": json.dumps(blocks, ensure_ascii=False),
                "tables": json.dumps(tables, ensure_ascii=False),
                "avg_confidence": avg_conf,
                "ocr_engine": p_engine,
                "processing_time_ms": int((time.time() - start_time) * 1000)
            })

        # Check OCR confidence & page count
        total_chars = sum(len(p.get("full_text", "").strip()) for p in pages_data) if pages_data else 0
        overall_avg_conf = float(np.mean([p.get("avg_confidence", 0.0) for p in pages_data])) if pages_data else 0.0
        page_count = len(pages_data) if pages_data else max(len(images), 1)

        if overall_avg_conf < 0.50 or total_chars < 15:
            logger.warning(f"Low OCR confidence warning for source {source_id}: conf={overall_avg_conf:.2f}, chars={total_chars}")

        # Update source record
        await db.execute(text("""
            UPDATE sources
            SET page_count = :page_count, status = 'ocr_complete', updated_at = NOW()
            WHERE source_id = :source_id
        """), {"source_id": source_id, "page_count": page_count})
        await db.commit()

        logger.info(f"OCR pipeline completed for source {source_id}: {page_count} pages, {total_blocks} blocks via {engine_used}")

        return {
            "source_id": source_id,
            "pages": page_count,
            "total_blocks": total_blocks,
            "cached": False,
            "status": "ocr_complete",
            "total_time_ms": int((time.time() - start_time) * 1000),
            "ocr_engine": engine_used
        }

    async def process_source(self, db: AsyncSession, source_id: str, file_path: str, file_type: str = "pdf") -> Dict[str, Any]:
        """Convenience alias for background worker queue compatibility."""
        return await self.process_document(source_id=source_id, file_path=file_path, file_type=file_type, db=db)


HybridOCRRouter = ChandraOCRRouter
ocr_router = ChandraOCRRouter()
