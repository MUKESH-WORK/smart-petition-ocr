import gc
import json
import logging
import time
from typing import List, Dict, Any, Optional, TYPE_CHECKING
import cv2
import numpy as np
from PIL import Image

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
    High-performance Tamil OCR engine powered by PaddleOCR PP-OCRv5.
    Features:
    - Preprocessing pipeline (adaptive binarization, deskew, denoise)
    - Hardware-aware auto-detection (CUDA GPU with graceful CPU fallback)
    - Document SHA256 result caching (sub-100ms on repeat documents)
    - Reading order sorting (top-to-bottom, left-to-right)
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
                import os
                torch_lib = r'E:\test_rat\GDP_Assistant\.venv\Lib\site-packages\torch\lib'
                if os.path.exists(torch_lib):
                    try:
                        os.add_dll_directory(torch_lib)
                    except Exception:
                        pass

                self._use_gpu = self._check_gpu()
                logger.info(f"PaddleOCR hardware acceleration: GPU={self._use_gpu}")

                from paddleocr import PaddleOCR
                try:
                    self._paddle = PaddleOCR(
                        lang='ta',
                        use_doc_orientation_classify=True,
                        use_doc_unwarping=False,
                        use_textline_orientation=True
                    )
                except Exception as ex_orient:
                    logger.warning(f"Orientation models unavailable, falling back to base mode: {ex_orient}")
                    self._paddle = PaddleOCR(
                        lang='ta',
                        use_doc_orientation_classify=False,
                        use_doc_unwarping=False,
                        use_textline_orientation=False
                    )

                logger.info("Paddle PP-OCRv5 initialized successfully for bilingual Tamil/English!")
            except Exception as e:
                logger.error(f"Failed to initialize Paddle PP-OCRv5: {e}", exc_info=True)
                self._paddle = None
        return self._paddle

    async def _paddle_process(self, image_path: str, page_num: int) -> List[Dict[str, Any]]:
        paddle_inst = self._get_paddle()
        blocks = []

        if paddle_inst is not None:
            try:
                import asyncio

                def _run_predict():
                    img = cv2.imread(image_path)
                    if img is None:
                        return []

                    # 1. OpenCV Preprocessing if enabled
                    if getattr(settings, "OCR_PREPROCESSING_ENABLED", True):
                        img = _preprocess_image(img)

                    # 2. Rescale long edge to target dimension (default 1500px)
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
        2. Convert document to 200 DPI normalized images
        3. Preprocess with OpenCV (deskew, binarize, denoise)
        4. Paddle PP-OCRv5 inference + reading-order sorting
        5. Persist page results into ocr_results
        """
        start_time = time.time()

        # 1. SHA256 Document Fingerprint Cache Hit Check
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
                "total_time_ms": int((time.time() - start_time) * 1000)
            }

        # 2. Document Conversion
        images = await file_store.convert_document_to_images(source_id, file_path, file_type)
        all_blocks = []

        # 3. Process Each Page
        for page_num, image_path in enumerate(images, 1):
            p_start = time.time()
            paddle_blocks = await self._paddle_process(image_path, page_num)

            # Sort reading order: top-to-bottom, left-to-right
            paddle_blocks.sort(key=lambda b: (b["bbox"][0][1], b["bbox"][0][0]))
            all_blocks.extend(paddle_blocks)

            page_full_text = "\n".join([b["text"] for b in paddle_blocks])
            avg_conf = float(np.mean([b["confidence"] for b in paddle_blocks])) if paddle_blocks else 0.0
            p_time_ms = int((time.time() - p_start) * 1000)

            # Persist per page in ocr_results
            await db.execute(text("""
                INSERT INTO ocr_results (source_id, page_number, full_text, blocks, tables, avg_confidence, ocr_engine, processing_time_ms)
                VALUES (CAST(:source_id AS UUID), :page_number, :full_text, :blocks, :tables, :avg_confidence, :ocr_engine, :processing_time_ms)
                ON CONFLICT (source_id, page_number) DO UPDATE SET
                    full_text = EXCLUDED.full_text,
                    blocks = EXCLUDED.blocks,
                    avg_confidence = EXCLUDED.avg_confidence,
                    processing_time_ms = EXCLUDED.processing_time_ms
            """), {
                "source_id": source_id,
                "page_number": page_num,
                "full_text": page_full_text,
                "blocks": json.dumps(paddle_blocks, ensure_ascii=False),
                "tables": json.dumps([], ensure_ascii=False),
                "avg_confidence": avg_conf,
                "ocr_engine": "paddleocr_v5",
                "processing_time_ms": p_time_ms
            })

        # 4. Update source record
        await db.execute(text("""
            UPDATE sources
            SET page_count = :page_count, status = 'ocr_complete', updated_at = NOW()
            WHERE source_id = CAST(:source_id AS UUID)
        """), {"source_id": source_id, "page_count": len(images)})
        await db.commit()

        return {
            "source_id": source_id,
            "pages": len(images),
            "total_blocks": len(all_blocks),
            "cached": False,
            "total_time_ms": int((time.time() - start_time) * 1000)
        }


ocr_router = HybridOCRRouter()
