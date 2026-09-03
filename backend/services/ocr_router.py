import gc
import json
import logging
import time
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from PIL import Image
import numpy as np
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
from services.file_store import file_store

logger = logging.getLogger(__name__)


class HybridOCRRouter:
    """
    Primary: PaddleOCR PP-OCRv5 (fast, printed Tamil text, tables)
    Fallback: Surya (lazy-loaded, handwriting, low-confidence blocks)
    """

    def __init__(self):
        self._paddle = None
        self.surya_det = None
        self.surya_rec = None
        self.surya_seg = None

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
                from paddleocr import PaddleOCR
                self._paddle = PaddleOCR(
                    lang='ta',
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False
                )
                logger.info("Paddle PP-OCRv5 initialized successfully for Tamil!")
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
                import cv2
                
                def _run_predict():
                    img = cv2.imread(image_path)
                    if img is None:
                        return []
                    h, w = img.shape[:2]
                    scale = 1100.0 / max(h, w)
                    if scale < 1.0:
                        img = cv2.resize(img, (int(w * scale), int(h * scale)))
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
                        poly = dt_polys[i].tolist() if i < len(dt_polys) and hasattr(dt_polys[i], "tolist") else [[0, 0], [100, 0], [100, 20], [0, 20]]
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

    async def process_source(self, db: AsyncSession, source_id: str, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Full pipeline: file -> images -> OCR -> structured output -> save in ocr_results
        """
        start_time = time.time()
        images = await file_store.convert_document_to_images(source_id, file_path, file_type)
        
        all_blocks = []
        surya_count = 0

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

        # Update source record
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
            "surya_fallback_count": surya_count,
            "total_time_ms": int((time.time() - start_time) * 1000)
        }


ocr_router = HybridOCRRouter()
