import os
import sys
import time
import json
import asyncio
import logging
from pathlib import Path
import numpy as np
import cv2

try:
    import torch
except Exception:
    pass


# Set backend dir in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from models.database import AsyncSessionLocal
from services.ocr_router import ocr_router
from services.image_preprocessor import image_preprocessor
from services.region_analyzer import region_analyzer
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("benchmark_ocr")


async def run_benchmark():
    logger.info("=" * 60)
    logger.info("PP-OCRv5 Indications & Latency Benchmark (Windows 10, i5 CPU)")
    logger.info("=" * 60)

    # Gather test images from backend/ and backend/uploads/
    sample_images = []
    
    # 1. Local petition pages in backend root
    for p in ["user_petition_p1.png", "user_petition_p2.png", "user_petition_p3.png", "temp_ocr_test.png"]:
        full_p = os.path.join(BASE_DIR, p)
        if os.path.exists(full_p):
            sample_images.append(full_p)

    # 2. Check uploads
    uploads_dir = os.path.join(BASE_DIR, "uploads")
    if os.path.exists(uploads_dir):
        for f in os.listdir(uploads_dir):
            if f.endswith((".png", ".jpg", ".jpeg")) and os.path.getsize(os.path.join(uploads_dir, f)) > 20000:
                sample_images.append(os.path.join(uploads_dir, f))
                if len(sample_images) >= 8:
                    break

    logger.info(f"Discovered {len(sample_images)} benchmark sample images.")
    if not sample_images:
        logger.warning("No sample images found to benchmark.")
        return

    ta_ocr = ocr_router._get_paddle_ta()

    results = []
    total_start = time.time()

    for idx, img_path in enumerate(sample_images[:3], 1):
        fname = os.path.basename(img_path)
        logger.info(f"[{idx}/{min(8, len(sample_images))}] Benchmarking: {fname}")

        # Preprocessing Latency
        temp_dir = os.path.join(BASE_DIR, "temp_cache")
        os.makedirs(temp_dir, exist_ok=True)
        bench_out = os.path.join(temp_dir, f"bench_{fname}")
        t_prep_start = time.time()
        try:
            prep_img = image_preprocessor.process_image(img_path, output_path=bench_out)
        except Exception:
            prep_img = img_path
        t_prep_ms = int((time.time() - t_prep_start) * 1000)

        # Read image
        img = cv2.imread(prep_img)
        if img is None:
            continue
        h, w = img.shape[:2]

        # Region Analysis Latency
        t_reg_start = time.time()
        stamp_box = region_analyzer.detect_stamp_box(img, is_first_page=True)
        t_reg_ms = int((time.time() - t_reg_start) * 1000)

        # OCR Inference Latency
        t_ocr_start = time.time()
        ocr_res = await ocr_router._paddle_predict(ta_ocr, img)
        t_ocr_ms = int((time.time() - t_ocr_start) * 1000)

        line_count = 0
        conf_scores = []
        for res in ocr_res:
            rec_texts = res.get("rec_texts", [])
            rec_scores = res.get("rec_scores", [])
            line_count += len(rec_texts)
            for sc in rec_scores:
                conf_scores.append(float(sc))

        avg_conf = float(np.mean(conf_scores)) if conf_scores else 0.0
        total_page_s = round((t_prep_ms + t_reg_ms + t_ocr_ms) / 1000.0, 2)

        record = {
            "file": fname,
            "resolution": f"{w}x{h}",
            "lines": line_count,
            "prep_ms": t_prep_ms,
            "region_ms": t_reg_ms,
            "ocr_ms": t_ocr_ms,
            "total_latency_s": total_page_s,
            "avg_confidence": round(avg_conf, 3),
            "stamp_found": stamp_box is not None,
            "meets_40s_gate": total_page_s <= 40.0
        }
        results.append(record)
        logger.info(f" -> Lines: {line_count} | Latency: {total_page_s}s | Avg Conf: {record['avg_confidence']} | Stamp: {record['stamp_found']}")

    # Overall Summary
    latencies = [r["total_latency_s"] for r in results]
    confs = [r["avg_confidence"] for r in results]
    mean_lat = round(float(np.mean(latencies)), 2) if latencies else 0.0
    mean_conf = round(float(np.mean(confs)), 3) if confs else 0.0
    pass_gate = all(r["meets_40s_gate"] for r in results)

    logger.info("=" * 60)
    logger.info(f"BENCHMARK SUMMARY ({len(results)} pages processed):")
    logger.info(f"Average Total Latency: {mean_lat}s (Target: <= 40.0s)")
    logger.info(f"Average Confidence:    {mean_conf}")
    logger.info(f"Passes Latency Gate:   {pass_gate}")
    logger.info("=" * 60)

    # Persist to benchmark_runs table in Postgres
    async with AsyncSessionLocal() as db:
        config = {
            "engine": "PP-OCRv5",
            "det_model": "PP-OCRv5_mobile_det",
            "rec_model": "ta_PP-OCRv5_mobile_rec",
            "hardware": "Intel i5 CPU, 16GB RAM, Windows 10",
            "quantization": "FP32 (Stock)"
        }
        metrics = {
            "avg_latency_s": mean_lat,
            "avg_confidence": mean_conf,
            "pages_tested": len(results),
            "meets_latency_gate": pass_gate,
            "details": results
        }
        ins_q = text("""
            INSERT INTO benchmark_runs (run_type, config, metrics, run_at)
            VALUES ('latency', :cfg, :met, NOW())
            RETURNING run_id
        """)
        ins_res = await db.execute(ins_q, {
            "cfg": json.dumps(config),
            "met": json.dumps(metrics)
        })
        run_id = ins_res.scalar_one()
        await db.commit()
        logger.info(f"Benchmark record saved to DB with run_id={run_id}")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
