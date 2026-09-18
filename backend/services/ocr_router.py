import os
import sys
import gc
import json
import logging
import time
import asyncio
from typing import List, Dict, Any, Optional, TYPE_CHECKING
import cv2
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


def _preprocess_image(img: np.ndarray) -> np.ndarray:
    """
    Google Document AI & Azure AI-inspired preprocessing pipeline for Tamil OCR:
    1. Grayscale conversion (reduces channel noise & data volume)
    2. Adaptive Gaussian binarization (handles uneven lighting & scanner shadows)
    3. Deskew detection & correction (straightens tilted scans)
    4. Median blur denoising (eliminates salt-and-pepper noise)
    5. Re-convert to BGR for PaddleOCR inference
    """
    if img is None or img.size == 0:
        return img

    try:
        # 1. Grayscale
        if len(img.shape) == 3 and img.shape[2] == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        elif len(img.shape) == 3 and img.shape[2] == 4:
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        else:
            gray = img.copy()

        # 2. Adaptive Binarization
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 15, 8
        )

        # 3. Selective Deskew (only for clear tilt between 1.5° and 45°)
        coords = np.column_stack(np.where(binary < 128))
        if len(coords) > 100:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle

            if 1.5 < abs(angle) < 45.0:
                h, w = binary.shape[:2]
                center = (w // 2, h // 2)
                m = cv2.getRotationMatrix2D(center, angle, 1.0)
                binary = cv2.warpAffine(
                    binary, m, (w, h),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_REPLICATE
                )

        # 4. Light Denoise
        denoised = cv2.medianBlur(binary, 3)

        # 5. Convert back to 3-channel BGR for PaddleOCR
        return cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)
    except Exception as e:
        logger.warning(f"Preprocessing fallback triggered due to: {e}")
        return img


class HybridOCRRouter:
    """
    High-performance Tamil OCR Engine:
    - Primary: Datalab Chandra OCR Cloud API (State-of-the-Art Layout-Aware Tamil/English OCR)
    - Fallback: Local PaddleOCR PP-OCRv5 engine
    - Features:
      * Full layout preservation (text blocks, tables, headers, forms)
      * Document SHA256 caching for instantaneous re-runs
      * Automatic page parsing and bounding box / polygon extraction
    """

    def __init__(self):
        self._paddle = None
        self._use_gpu = False

    def _check_gpu(self) -> bool:
        try:
            import paddle
            if paddle.device.is_compiled_with_cuda():
                gpu_count = paddle.device.cuda.device_count()
                return gpu_count > 0
        except Exception:
            pass
        return False

    def _get_paddle(self):
        if self._paddle is None:
            try:
                import site
                search_dirs = []
                # Dynamically locate torch/lib if present for Windows DLL resolution
                try:
                    import torch
                    torch_lib = os.path.join(os.path.dirname(torch.__file__), "lib")
                    if os.path.exists(torch_lib):
                        search_dirs.append(torch_lib)
                except Exception:
                    pass

                try:
                    for s in site.getsitepackages():
                        t_lib = os.path.join(s, "torch", "lib")
                        if os.path.exists(t_lib):
                            search_dirs.append(t_lib)
                except Exception:
                    pass

                if hasattr(os, "add_dll_directory"):
                    for t_dir in search_dirs:
                        if os.path.exists(t_dir):
                            try:
                                os.add_dll_directory(t_dir)
                            except Exception:
                                pass

                self._use_gpu = self._check_gpu()
                logger.info(f"PaddleOCR hardware acceleration: GPU={self._use_gpu}")

                try:
                    import paddle
                    paddle.set_flags({'FLAGS_enable_pir_in_executor': False, 'FLAGS_use_mkldnn': False})
                except Exception:
                    pass

                from paddleocr import PaddleOCR
                try:
                    self._paddle = PaddleOCR(
                        lang='ta',
                        use_doc_orientation_classify=False,
                        use_doc_unwarping=False,
                        use_textline_orientation=False
                    )
                except Exception as ex_orient:
                    logger.warning(f"Orientation models unavailable, falling back to base mode: {ex_orient}")
                    self._paddle = PaddleOCR(
                        lang='ta',
                        use_doc_orientation_classify=False,
                        use_doc_unwarping=False,
                        use_textline_orientation=False
                    )

                logger.info("Paddle PP-OCRv5 initialized successfully for bilingual Tamil/English fallback!")
            except Exception as e:
                logger.error(f"Failed to initialize Paddle PP-OCRv5 fallback: {e}", exc_info=True)
                self._paddle = None
        return self._paddle

    async def _paddle_process(self, image_path: str, page_num: int) -> List[Dict[str, Any]]:
        paddle_inst = self._get_paddle()
        blocks = []

        if paddle_inst is not None:
            try:
                def _run_predict():
                    img = cv2.imread(image_path)
                    if img is None:
                        return []

                    if getattr(settings, "OCR_PREPROCESSING_ENABLED", True):
                        img = _preprocess_image(img)

                    h, w = img.shape[:2]
                    target_dim = getattr(settings, "OCR_MAX_IMAGE_DIMENSION", 1500)
                    scale = target_dim / max(h, w)
                    if scale < 1.0:
                        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

                    return list(paddle_inst.predict(img))

                results = await asyncio.to_thread(_run_predict)
                for res in results:
                    rec_texts = res.get("rec_texts", [])
                    rec_scores = res.get("rec_scores", [])
                    dt_polys = res.get("dt_polys", []) or res.get("rec_polys", [])

                    for i, txt in enumerate(rec_texts):
                        clean_txt = str(txt).strip()
                        if not clean_txt:
                            continue
                        conf = float(rec_scores[i]) if i < len(rec_scores) else 0.95
                        poly = (
                            dt_polys[i].tolist()
                            if i < len(dt_polys) and hasattr(dt_polys[i], "tolist")
                            else [[0, 0], [100, 0], [100, 20], [0, 20]]
                        )
                        blocks.append({
                            "text": clean_txt,
                            "confidence": round(conf, 3),
                            "bbox": poly,
                            "page": page_num,
                            "engine": "paddleocr_v5"
                        })
                if blocks:
                    return blocks
            except Exception as e:
                logger.error(f"Paddle PP-OCRv5 inference error on {image_path}: {e}", exc_info=True)

        return blocks

    async def _process_with_datalab(self, file_path: str, file_type: str) -> Optional[List[Dict[str, Any]]]:
        """
        Processes document via Datalab Chandra OCR Cloud API.
        Returns a list of structured page dictionaries:
        [
            {
                "page_number": int,
                "full_text": str,
                "blocks": List[Dict],
                "tables": List[Dict],
                "avg_confidence": float,
                "ocr_engine": "datalab_chandra"
            }, ...
        ]
        """
        api_key = getattr(settings, "DATALAB_API_KEY", "")
        api_url = getattr(settings, "DATALAB_API_URL", "https://www.datalab.to/api/v1/convert")
        mode = str(getattr(settings, "DATALAB_MODE", "accurate")).strip().lower()
        if mode not in ["fast", "balanced", "accurate"]:
            mode = "accurate"
        timeout_sec = getattr(settings, "DATALAB_TIMEOUT", 120)

        if not api_key:
            logger.warning("DATALAB_API_KEY is not configured; skipping Datalab OCR.")
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

        logger.info(f"🌐 Submitting {base_name} ({clean_ext}) to Datalab Chandra OCR API...")

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
                "mode": mode,
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

                logger.info(f"⏳ Polling Datalab Chandra task: {check_url}")
                start_poll = time.time()
                poll_result = None

                while (time.time() - start_poll) < timeout_sec:
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
                    logger.error(f"Datalab Chandra OCR timed out after {timeout_sec}s")
                    return None

            # Parse the Datalab Chandra JSON structure
            json_payload = poll_result.get("json") or {}
            children = json_payload.get("children", [])
            raw_score = float(poll_result.get("parse_quality_score") or 0.98)
            # Normalize 1-5 or 0-100 scales to 0.0-1.0
            if raw_score > 1.0:
                raw_score = raw_score / 5.0 if raw_score <= 5.0 else raw_score / 100.0
            parse_score = max(0.0, min(1.0, round(raw_score, 3)))

            pages_output: List[Dict[str, Any]] = []

            # Check if children represent Pages
            has_pages = any(c.get("block_type") == "Page" for c in children)

            if has_pages:
                for idx, page in enumerate(children, 1):
                    if page.get("block_type") != "Page":
                        continue
                    sub_blocks = page.get("children", [])
                    p_blocks, p_tables, text_segments = self._parse_datalab_blocks(sub_blocks, idx, parse_score)

                    # If no sub_blocks text was extracted, fallback to page-level HTML
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
                # Single-page or flat block layout
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

            # Print exact Chandra OCR response to console for testing/inspection
            print("\n" + "=" * 70, flush=True)
            print("🌟 [CHANDRA OCR EXACT RESULT RESPONSE IN CONSOLE]", flush=True)
            print("=" * 70, flush=True)
            try:
                print(f"[CHANDRA OCR STATUS]: {poll_result.get('status')}", flush=True)
                print(f"[CHANDRA OCR QUALITY SCORE]: {poll_result.get('parse_quality_score')}", flush=True)
                if "markdown" in poll_result and poll_result["markdown"]:
                    print("\n--- [CHANDRA RAW MARKDOWN / TEXT] ---", flush=True)
                    print(poll_result["markdown"], flush=True)
                elif "text" in poll_result and poll_result["text"]:
                    print("\n--- [CHANDRA RAW TEXT] ---", flush=True)
                    print(poll_result["text"], flush=True)
            except Exception as ex:
                print(f"[Raw dump notice: {ex}]", flush=True)

            for p in pages_output:
                print(f"\n--- [CHANDRA OCR PAGE {p['page_number']} EXTRACTED TEXT] (Confidence: {p.get('avg_confidence', 0.98)}) ---", flush=True)
                text_to_print = p.get("full_text", "")
                try:
                    print(text_to_print, flush=True)
                except Exception:
                    print(text_to_print.encode("utf-8", errors="replace").decode("utf-8"), flush=True)
            print("=" * 70 + "\n", flush=True)

            logger.info(f"✅ Datalab Chandra OCR successfully extracted {len(pages_output)} pages.")
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

            # Extract clean text from HTML
            soup = BeautifulSoup(b_html, "html.parser")
            clean_text = soup.get_text("\n").strip()

            # Extract spatial coordinates (polygon preferred, bbox fallback)
            polygon = b.get("polygon")
            if not polygon and b.get("bbox"):
                bx = b["bbox"]
                if len(bx) == 4:
                    # [ymin, xmin, ymax, xmax] or [x1, y1, x2, y2]
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

    async def _check_ocr_cache(self, db: AsyncSession, source_id: str) -> Optional[str]:
        """
        Microsoft Azure pattern: Check if an identical document (SHA256 fingerprint)
        has already been processed. If so, return the cached source_id.
        """
        try:
            result = await db.execute(text("""
                SELECT s2.source_id 
                FROM sources s1
                JOIN sources s2 ON s1.file_hash = s2.file_hash AND s2.status IN ('ocr_complete', 'draft_ready')
                JOIN ocr_results o2 ON s2.source_id = o2.source_id AND o2.ocr_engine = 'datalab_chandra'
                WHERE s1.source_id = CAST(:sid AS UUID) AND s2.source_id != CAST(:sid AS UUID)
                LIMIT 1
            """), {"sid": source_id})
            cached = result.scalar_one_or_none()
            return str(cached) if cached else None
        except Exception as e:
            logger.warning(f"Error checking OCR cache: {e}")
            return None

    async def process_source(self, db: AsyncSession, source_id: str, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Full production pipeline:
        1. Check SHA256 document cache -> return instantly if match found
        2. Convert document to PNG page images in static/media/ for visual inspection in UI
        3. Datalab Chandra OCR Cloud API inference (with Paddle PP-OCRv5 graceful fallback)
        4. Persist structured page results into ocr_results
        5. Update source record
        """
        start_time = time.time()

        # 0. Instant reuse if this source_id already has completed OCR results
        existing_ocr = await db.execute(
            text("SELECT COUNT(*) FROM ocr_results WHERE source_id = CAST(:sid AS UUID)"),
            {"sid": source_id}
        )
        if existing_ocr.scalar_one() > 0:
            count_res = await db.execute(
                text("SELECT page_count FROM sources WHERE source_id = CAST(:sid AS UUID)"),
                {"sid": source_id}
            )
            page_count = count_res.scalar() or 1
            logger.info(f"⚡ OCR results already exist for source {source_id} ({page_count} pages), reusing existing OCR instantly.")
            await db.execute(text("""
                UPDATE sources
                SET page_count = :page_count, status = 'ocr_complete', updated_at = NOW()
                WHERE source_id = CAST(:source_id AS UUID)
            """), {"source_id": source_id, "page_count": page_count})
            await db.commit()
            return {
                "source_id": source_id,
                "pages": page_count,
                "total_blocks": 0,
                "cached": True,
                "total_time_ms": int((time.time() - start_time) * 1000),
                "ocr_engine": "cached_existing"
            }

        # 1. SHA256 Document Fingerprint Cache Hit Check (Identical file previously uploaded)
        cached_source_id = await self._check_ocr_cache(db, source_id)
        if cached_source_id:
            logger.info(f"⚡ Cache HIT for source {source_id}: copying OCR results from {cached_source_id}")
            await db.execute(text("""
                INSERT INTO ocr_results (source_id, page_number, full_text, blocks, tables, avg_confidence, ocr_engine, processing_time_ms)
                SELECT CAST(:new_id AS UUID), page_number, full_text, blocks, tables, avg_confidence, ocr_engine, 0
                FROM ocr_results
                WHERE source_id = CAST(:cached_id AS UUID)
                ON CONFLICT (source_id, page_number) DO UPDATE SET
                    full_text = EXCLUDED.full_text,
                    blocks = EXCLUDED.blocks,
                    avg_confidence = EXCLUDED.avg_confidence,
                    processing_time_ms = 0
            """), {"new_id": source_id, "cached_id": cached_source_id})

            count_res = await db.execute(
                text("SELECT page_count FROM sources WHERE source_id = CAST(:cid AS UUID)"),
                {"cid": cached_source_id}
            )
            page_count = count_res.scalar() or 1

            await db.execute(text("""
                UPDATE sources
                SET page_count = :page_count, status = 'ocr_complete', updated_at = NOW()
                WHERE source_id = CAST(:source_id AS UUID)
            """), {"source_id": source_id, "page_count": page_count})
            await db.commit()

            return {
                "source_id": source_id,
                "pages": page_count,
                "total_blocks": 0,
                "cached": True,
                "total_time_ms": int((time.time() - start_time) * 1000),
                "ocr_engine": "cached"
            }

        # 2. Document Conversion to Images for UI visual viewer
        images = []
        try:
            images = await file_store.convert_document_to_images(source_id, file_path, file_type)
        except Exception as e:
            logger.warning(f"Notice: Page image conversion encountered error (continuing OCR): {e}")

        # Fast Digital PDF extraction: If PDF contains selectable/digital text, extract directly in milliseconds
        clean_ext = file_type.lower().replace(".", "")
        pages_data: Optional[List[Dict[str, Any]]] = None
        engine_used = "datalab_chandra"

        if clean_ext == "pdf":
            try:
                import fitz
                with fitz.open(file_path) as pdf_doc:
                    direct_pages = []
                    total_pdf_chars = 0
                    for p_idx, page in enumerate(pdf_doc, 1):
                        p_txt = page.get_text("text").strip()
                        total_pdf_chars += len(p_txt)
                        blocks = []
                        for b in page.get_text("blocks"):
                            b_text = str(b[4]).strip() if len(b) > 4 else ""
                            if b_text:
                                poly = [[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]]
                                blocks.append({
                                    "text": b_text,
                                    "confidence": 0.99,
                                    "bbox": poly,
                                    "page": p_idx,
                                    "engine": "digital_pdf"
                                })
                        direct_pages.append({
                            "page_number": p_idx,
                            "full_text": p_txt,
                            "blocks": blocks,
                            "tables": [],
                            "avg_confidence": 0.99,
                            "ocr_engine": "digital_pdf"
                        })

                    # If PDF has embedded text across pages
                    if total_pdf_chars >= 20:
                        logger.info(f"⚡ Digital PDF fast-path: extracted {total_pdf_chars} characters across {len(direct_pages)} pages in <0.05s")
                        pages_data = direct_pages
                        engine_used = "digital_pdf"
            except Exception as pdf_ex:
                logger.debug(f"Direct PDF text extraction notice: {pdf_ex}")

        # 3. OCR Processing (Primary: Datalab Chandra API, Fallback: Local PaddleOCR)
        if not pages_data:
            ocr_provider = getattr(settings, "OCR_PROVIDER", "datalab").lower()

            if ocr_provider == "datalab":
                pages_data = await self._process_with_datalab(file_path, file_type)
                if not pages_data:
                    logger.warning("⚠️ Datalab Chandra OCR unavailable or failed; falling back to local PaddleOCR...")
                    engine_used = "paddleocr_v5"
                else:
                    engine_used = "datalab_chandra"

        # Fallback to local PaddleOCR if Datalab was skipped or failed
        if not pages_data:
            engine_used = "paddleocr_v5"
            pages_data = []
            # Ensure we have page images to run paddle on
            if not images:
                images = await file_store.convert_document_to_images(source_id, file_path, file_type)

            for page_num, image_path in enumerate(images, 1):
                p_start = time.time()
                paddle_blocks = await self._paddle_process(image_path, page_num)
                paddle_blocks.sort(key=lambda b: (b["bbox"][0][1], b["bbox"][0][0]))

                page_full_text = "\n".join([b["text"] for b in paddle_blocks])
                avg_conf = float(np.mean([b["confidence"] for b in paddle_blocks])) if paddle_blocks else 0.0
                pages_data.append({
                    "page_number": page_num,
                    "full_text": page_full_text,
                    "blocks": paddle_blocks,
                    "tables": [],
                    "avg_confidence": avg_conf,
                    "ocr_engine": "paddleocr_v5"
                })

        # 4. Persist per-page results into ocr_results
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
                VALUES (CAST(:source_id AS UUID), :page_number, :full_text, :blocks, :tables, :avg_confidence, :ocr_engine, :processing_time_ms)
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

        # 5. Check OCR confidence & page count
        total_chars = sum(len(p.get("full_text", "").strip()) for p in pages_data) if pages_data else 0
        overall_avg_conf = float(np.mean([p.get("avg_confidence", 0.0) for p in pages_data])) if pages_data else 0.0
        page_count = len(pages_data) if pages_data else max(len(images), 1)

        if overall_avg_conf < 0.50 or total_chars < 15:
            logger.warning(f"Low OCR confidence warning for source {source_id}: conf={overall_avg_conf:.2f}, chars={total_chars} (continuing to analysis)")

        # 6. Update source record
        await db.execute(text("""
            UPDATE sources
            SET page_count = :page_count, status = 'ocr_complete', updated_at = NOW()
            WHERE source_id = CAST(:source_id AS UUID)
        """), {"source_id": source_id, "page_count": page_count})
        await db.commit()

        logger.info(f"✨ OCR pipeline completed for source {source_id}: {page_count} pages, {total_blocks} blocks via {engine_used}")

        return {
            "source_id": source_id,
            "pages": page_count,
            "total_blocks": total_blocks,
            "cached": False,
            "status": "ocr_complete",
            "total_time_ms": int((time.time() - start_time) * 1000),
            "ocr_engine": engine_used
        }

ocr_router = HybridOCRRouter()
