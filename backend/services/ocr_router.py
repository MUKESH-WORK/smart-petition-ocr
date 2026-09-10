import gc
import json
import logging
import os
import re
import time
import unicodedata
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
import cv2
import numpy as np
from PIL import Image

try:
    import torch
except Exception:
    pass

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
from services.image_preprocessor import image_preprocessor
from services.region_analyzer import region_analyzer

logger = logging.getLogger(__name__)


def classify_script(text_str: str) -> str:
    """Classifies script as 'ta', 'en', or 'mixed' based on Unicode codepoints."""
    if not text_str:
        return "ta"
    tamil_chars = sum(1 for c in text_str if '\u0B80' <= c <= '\u0BFF')
    latin_chars = sum(1 for c in text_str if c.isascii() and c.isalpha())
    if tamil_chars > 0 and latin_chars > 0:
        return "mixed"
    elif latin_chars > 0 and tamil_chars == 0:
        return "en"
    return "ta"


def classify_style(crop: np.ndarray) -> str:
    """Classifies style as 'printed' or 'handwritten' using stroke variance heuristic."""
    if crop is None or crop.size == 0:
        return "printed"
    try:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop.copy()
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return "printed"
        areas = [cv2.contourArea(c) for c in contours if cv2.contourArea(c) > 5]
        if len(areas) < 3:
            return "printed"
        cv_var = np.std(areas) / (np.mean(areas) + 1e-5)
        return "handwritten" if cv_var > 0.85 else "printed"
    except Exception:
        return "printed"


class HybridOCRRouter:
    """
    Production-grade Bilingual Indic OCR Router (PP-OCRv5):
    - Stage 0 Image Preprocessing (deskew, CLAHE, perspective correction, 300 DPI)
    - Stage 1 Region Analysis (GDP stamp box extraction, photo/thumbprint rejection, strikethrough detection)
    - Stage 2 & 3 Line Detection & Recognition (PP-OCRv5 mobile/server det, ta_rec, en_rec)
    - Per-line persistence to ocr_lines (fixes D1)
    - Stage 4 Stamp parsing & insertion to stamp_parse (fixes D6)
    - Real computed page confidence (fixes D3)
    """

    def __init__(self):
        self._paddle_ta = None
        self._paddle_en = None
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

    def _get_paddle_ta(self):
        if self._paddle_ta is None:
            try:
                import os, site
                search_dirs = [
                    r'e:\test_rat\GDP_Assistant\backend\.venv\Lib\site-packages\torch\lib',
                    r'E:\test_rat\GDP_Assistant\.venv\Lib\site-packages\torch\lib'
                ]
                try:
                    for s in site.getsitepackages():
                        search_dirs.append(os.path.join(s, "torch", "lib"))
                except Exception:
                    pass
                for t_dir in search_dirs:
                    if os.path.exists(t_dir):
                        try:
                            os.add_dll_directory(t_dir)
                        except Exception:
                            pass

                self._use_gpu = self._check_gpu()
                logger.info(f"Paddle PP-OCRv5 hardware acceleration: GPU={self._use_gpu}")

                from paddleocr import PaddleOCR
                self._paddle_ta = PaddleOCR(
                    text_detection_model_name='PP-OCRv5_mobile_det',
                    text_recognition_model_name='ta_PP-OCRv5_mobile_rec',
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False
                )
                logger.info("Paddle PP-OCRv5 Tamil/Bilingual engine initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Paddle PP-OCRv5 (Tamil): {e}", exc_info=True)
                self._paddle_ta = None
        return self._paddle_ta

    def _get_paddle_en(self):
        if self._paddle_en is None:
            try:
                from paddleocr import PaddleOCR
                self._paddle_en = PaddleOCR(
                    text_detection_model_name='PP-OCRv5_mobile_det',
                    text_recognition_model_name='en_PP-OCRv5_mobile_rec',
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False
                )
                logger.info("Paddle PP-OCR English engine initialized successfully.")
            except Exception as e:
                logger.warning(f"Paddle English engine fallback to Tamil engine: {e}")
                self._paddle_en = self._get_paddle_ta()
        return self._paddle_en

    async def _paddle_predict(self, ocr_inst, img: np.ndarray) -> List[Dict[str, Any]]:
        if ocr_inst is None or img is None or img.size == 0:
            return []
        import asyncio

        def _predict_sync():
            try:
                return list(ocr_inst.predict(img))
            except Exception as e:
                logger.error(f"Paddle predict exception: {e}")
                return []

        return await asyncio.to_thread(_predict_sync)

    def parse_stamp_fields(self, stamp_lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parses stamp cells into structured GDP schema."""
        raw_cells = {}
        date_norm = None
        department = None
        subject = None
        sub_subject = None
        forwarding_officer = None

        full_stamp_text = " ".join([l.get("text", "") for l in stamp_lines])

        # 1. Date normalization
        date_match = re.search(r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})\b', full_stamp_text)
        if date_match:
            d, m, y = date_match.groups()
            if len(y) == 2:
                y = f"20{y}"
            date_norm = f"{y}-{int(m):02d}-{int(d):02d}"
            raw_cells["date"] = date_match.group(0)

        # 2. Extract specific department & subject lines
        for l in stamp_lines:
            t = l.get("text", "").strip()
            if any(k in t for k in ["Home Prohib", "Home", "Prohib", "Police", "Revenue", "வருவாய்", "காவல்துறை", "வட்டாட்சியர்"]):
                department = t
                raw_cells["department"] = t
            elif any(k in t for k in ["Land Grabbing", "நில ஆக்கிரமிப்பு", "பட்டா", "Patta", "ஆக்கிரமிப்பு", "புகார்"]):
                subject = t
                raw_cells["subject"] = t
            elif any(k in t for k in ["அலுவலர்", "ஆட்சியர்", "வட்டாட்சியர்", "DRO", "Collector", "Tahsildar"]):
                forwarding_officer = t
                raw_cells["forwarding_officer"] = t

        validation = {
            "date_valid": date_norm is not None,
            "department_valid": department is not None,
            "subject_valid": subject is not None,
            "forwarding_officer_valid": forwarding_officer is not None
        }

        return {
            "stamp_found": len(stamp_lines) > 0,
            "raw_cells": raw_cells,
            "date_norm": date_norm,
            "department": department or "[தகவல் இல்லை]",
            "subject": subject or "[தகவல் இல்லை]",
            "sub_subject": sub_subject or "[தகவல் இல்லை]",
            "forwarding_officer": forwarding_officer or "[தகவல் இல்லை]",
            "validation": validation
        }

    async def _check_ocr_cache(self, db: AsyncSession, source_id: str) -> Optional[str]:
        try:
            result = await db.execute(text("""
                SELECT s2.source_id 
                FROM sources s1
                JOIN sources s2 ON s1.file_hash = s2.file_hash AND s2.status IN ('ocr_complete', 'draft_ready')
                WHERE s1.source_id = CAST(:sid AS UUID) AND s2.source_id != CAST(:sid AS UUID)
                  AND EXISTS (SELECT 1 FROM ocr_lines ol WHERE ol.source_id = s2.source_id)
                LIMIT 1
            """), {"sid": source_id})
            cached = result.scalar_one_or_none()
            return str(cached) if cached else None
        except Exception as e:
            logger.warning(f"Error checking OCR cache: {e}")
            return None

    async def process_source(self, db: AsyncSession, source_id: str, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Executes full hardened OCR pipeline:
        Stage 0: Image Preprocessing (deskew, perspective correction, CLAHE, 300 DPI)
        Stage 1: Region Analysis (stamp box detection, masking, non-text rejection)
        Stage 2 & 3: PP-OCRv5 Line Detection & Recognition (script & style routing, strikethrough detection)
        Stage 4: Stamp Parsing & persistence into stamp_parse
        Per-line persistence into ocr_lines (fixes D1)
        Real confidence scores (fixes D3)
        """
        start_time = time.time()

        # Check Cache Hit
        cached_source_id = await self._check_ocr_cache(db, source_id)
        if cached_source_id:
            logger.info(f"⚡ Cache HIT for source {source_id}: copying OCR results from {cached_source_id}")
            # Copy ocr_lines
            await db.execute(text("""
                INSERT INTO ocr_lines (source_id, page_number, line_index, polygon, text, score, script, style, struck, region_type)
                SELECT CAST(:new_id AS UUID), page_number, line_index, polygon, text, score, script, style, struck, region_type
                FROM ocr_lines
                WHERE source_id = CAST(:cached_id AS UUID)
            """), {"new_id": source_id, "cached_id": cached_source_id})

            # Copy stamp_parse
            await db.execute(text("""
                INSERT INTO stamp_parse (source_id, stamp_found, raw_cells, date_norm, department, subject, sub_subject, forwarding_officer, validation)
                SELECT CAST(:new_id AS UUID), stamp_found, raw_cells, date_norm, department, subject, sub_subject, forwarding_officer, validation
                FROM stamp_parse
                WHERE source_id = CAST(:cached_id AS UUID)
                ON CONFLICT (source_id) DO NOTHING
            """), {"new_id": source_id, "cached_id": cached_source_id})

            # Copy ocr_results
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
                "cached": True,
                "total_time_ms": int((time.time() - start_time) * 1000)
            }

        # Convert Document to Images
        raw_images = await file_store.convert_document_to_images(source_id, file_path, file_type)
        ta_ocr = self._get_paddle_ta()
        en_ocr = self._get_paddle_en()

        all_page_lines = []
        stamp_parsed_record = None

        for page_num, image_path in enumerate(raw_images, 1):
            p_start = time.time()

            # Stage 0: Preprocessing (Deskew, CLAHE, 300 DPI)
            try:
                processed_image_path = image_preprocessor.process_image(image_path)
            except Exception as ex_prep:
                logger.warning(f"Preprocessing fallback on {image_path}: {ex_prep}")
                processed_image_path = image_path

            img = cv2.imread(processed_image_path)
            if img is None:
                continue

            h, w = img.shape[:2]
            page_lines = []
            line_idx = 0

            # Stage 1: Region Analysis & Stamp Detection (Page 1)
            stamp_box = None
            if page_num == 1:
                stamp_box = region_analyzer.detect_stamp_box(img, is_first_page=True)
                if stamp_box:
                    sx, sy, sw, sh = stamp_box
                    stamp_crop = img[sy:sy+sh, sx:sx+sw]
                    # Run English & Tamil recognition on stamp crop
                    stamp_results = await self._paddle_predict(en_ocr, stamp_crop)
                    stamp_page_lines = []

                    for s_res in stamp_results:
                        rec_texts = s_res.get("rec_texts", [])
                        rec_scores = s_res.get("rec_scores", [])
                        dt_polys = s_res.get("dt_polys", []) or s_res.get("rec_polys", [])

                        for i, txt in enumerate(rec_texts):
                            clean_t = str(txt).strip()
                            if not clean_t:
                                continue
                            sc = float(rec_scores[i]) if i < len(rec_scores) else None
                            p = dt_polys[i].tolist() if i < len(dt_polys) and hasattr(dt_polys[i], "tolist") else [[0,0],[10,0],[10,10],[0,10]]
                            # Offset polygon by stamp_box origin
                            poly_global = [[pt[0] + sx, pt[1] + sy] for pt in p]
                            line_dict = {
                                "page_number": page_num,
                                "line_index": line_idx,
                                "polygon": poly_global,
                                "text": clean_t,
                                "score": round(sc, 3) if sc is not None else None,
                                "script": classify_script(clean_t),
                                "style": "printed",
                                "struck": False,
                                "region_type": "stamp"
                            }
                            stamp_page_lines.append(line_dict)
                            page_lines.append(line_dict)
                            line_idx += 1

                    stamp_parsed_record = self.parse_stamp_fields(stamp_page_lines)
                    # Mask stamp box on body image so body OCR doesn't duplicate stamp text
                    img = region_analyzer.mask_stamp_region(img, stamp_box)

            # Stage 2 & 3: Body Line Detection + Recognition
            body_results = await self._paddle_predict(ta_ocr, img)
            for b_res in body_results:
                rec_texts = b_res.get("rec_texts", [])
                rec_scores = b_res.get("rec_scores", [])
                dt_polys = b_res.get("dt_polys", []) or b_res.get("rec_polys", [])

                for i, txt in enumerate(rec_texts):
                    clean_t = str(txt).strip()
                    if not clean_t:
                        continue
                    sc = float(rec_scores[i]) if i < len(rec_scores) else None
                    poly = dt_polys[i].tolist() if i < len(dt_polys) and hasattr(dt_polys[i], "tolist") else [[0,0],[100,0],[100,20],[0,20]]

                    # Crop line image for strikethrough and style classification
                    try:
                        xs = [int(p[0]) for p in poly]
                        ys = [int(p[1]) for p in poly]
                        lx1, lx2 = max(0, min(xs)), min(w, max(xs))
                        ly1, ly2 = max(0, min(ys)), min(h, max(ys))
                        line_crop = img[ly1:ly2, lx1:lx2] if (lx2 > lx1 and ly2 > ly1) else None
                    except Exception:
                        line_crop = None

                    # Strikethrough detection (D7)
                    is_struck = region_analyzer.is_strikethrough(line_crop) if line_crop is not None else False
                    script = classify_script(clean_t)
                    style = classify_style(line_crop) if line_crop is not None else "printed"

                    line_dict = {
                        "page_number": page_num,
                        "line_index": line_idx,
                        "polygon": poly,
                        "text": clean_t,
                        "score": round(sc, 3) if sc is not None else None,
                        "script": script,
                        "style": style,
                        "struck": is_struck,
                        "region_type": "body"
                    }
                    page_lines.append(line_dict)
                    line_idx += 1

            # Sort reading order (top-to-bottom, left-to-right)
            page_lines.sort(key=lambda l: (l["polygon"][0][1], l["polygon"][0][0]))
            # Re-index lines sequentially
            for idx, l in enumerate(page_lines):
                l["line_index"] = idx

            all_page_lines.extend(page_lines)

            # Persist per-line data into ocr_lines (fixes D1)
            for l in page_lines:
                await db.execute(text("""
                    INSERT INTO ocr_lines (source_id, page_number, line_index, polygon, text, score, script, style, struck, region_type)
                    VALUES (CAST(:source_id AS UUID), :page_number, :line_index, :polygon, :text, :score, :script, :style, :struck, :region_type)
                """), {
                    "source_id": source_id,
                    "page_number": page_num,
                    "line_index": l["line_index"],
                    "polygon": json.dumps(l["polygon"]),
                    "text": l["text"],
                    "score": l["score"],
                    "script": l["script"],
                    "style": l["style"],
                    "struck": l["struck"],
                    "region_type": l["region_type"]
                })

            # Calculate genuine page average confidence (fixes D3)
            valid_scores = [l["score"] for l in page_lines if l.get("score") is not None]
            avg_conf = float(np.mean(valid_scores)) if valid_scores else None
            page_full_text = "\n".join([l["text"] for l in page_lines])
            p_time_ms = int((time.time() - p_start) * 1000)

            # Persist legacy page summary into ocr_results
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
                "blocks": json.dumps(page_lines, ensure_ascii=False),
                "tables": json.dumps([], ensure_ascii=False),
                "avg_confidence": avg_conf,
                "ocr_engine": "paddleocr_v5",
                "processing_time_ms": p_time_ms
            })

        # Persist Stage 4 Stamp Parse if found or write clean default
        if stamp_parsed_record is None:
            stamp_parsed_record = {
                "stamp_found": False,
                "raw_cells": {},
                "date_norm": None,
                "department": "[தகவல் இல்லை]",
                "subject": "[தகவல் இல்லை]",
                "sub_subject": "[தகவல் இல்லை]",
                "forwarding_officer": "[தகவல் இல்லை]",
                "validation": {"stamp_found": False}
            }

        await db.execute(text("""
            INSERT INTO stamp_parse (source_id, stamp_found, raw_cells, date_norm, department, subject, sub_subject, forwarding_officer, validation)
            VALUES (CAST(:source_id AS UUID), :stamp_found, :raw_cells, :date_norm, :department, :subject, :sub_subject, :forwarding_officer, :validation)
            ON CONFLICT (source_id) DO UPDATE SET
                stamp_found = EXCLUDED.stamp_found,
                raw_cells = EXCLUDED.raw_cells,
                date_norm = EXCLUDED.date_norm,
                department = EXCLUDED.department,
                subject = EXCLUDED.subject,
                sub_subject = EXCLUDED.sub_subject,
                forwarding_officer = EXCLUDED.forwarding_officer,
                validation = EXCLUDED.validation
        """), {
            "source_id": source_id,
            "stamp_found": stamp_parsed_record["stamp_found"],
            "raw_cells": json.dumps(stamp_parsed_record["raw_cells"], ensure_ascii=False),
            "date_norm": stamp_parsed_record["date_norm"],
            "department": stamp_parsed_record["department"],
            "subject": stamp_parsed_record["subject"],
            "sub_subject": stamp_parsed_record["sub_subject"],
            "forwarding_officer": stamp_parsed_record["forwarding_officer"],
            "validation": json.dumps(stamp_parsed_record["validation"], ensure_ascii=False)
        })

        # Update source status
        await db.execute(text("""
            UPDATE sources
            SET page_count = :page_count, status = 'ocr_complete', updated_at = NOW()
            WHERE source_id = CAST(:source_id AS UUID)
        """), {"source_id": source_id, "page_count": len(raw_images)})
        await db.commit()

        # Audit Event: OCR_COMPLETED
        from app.dependencies import log_audit_event
        low_conf_count = sum(1 for l in all_page_lines if l.get("score") is not None and l["score"] < 0.60)
        overall_avg = float(np.mean([l["score"] for l in all_page_lines if l.get("score") is not None])) if all_page_lines else None
        await log_audit_event(
            db,
            action="OCR_COMPLETED",
            source_id=source_id,
            details={
                "page_count": len(raw_images),
                "total_lines": len(all_page_lines),
                "avg_confidence": overall_avg,
                "low_confidence_count": low_conf_count,
                "stamp_found": stamp_parsed_record["stamp_found"]
            }
        )

        return {
            "source_id": source_id,
            "pages": len(raw_images),
            "total_lines": len(all_page_lines),
            "cached": False,
            "total_time_ms": int((time.time() - start_time) * 1000)
        }


ocr_router = HybridOCRRouter()
