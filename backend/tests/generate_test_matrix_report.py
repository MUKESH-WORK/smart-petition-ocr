import asyncio
import os
import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

from models.database import AsyncSessionLocal
from sqlalchemy import text

files = [
    "without1.pdf",
    "DocScanner 24 Aug 2026 10-13 am.pdf",
    "DocScanner 24 Aug 2026 10-17 am.pdf",
    "DocScanner Aug 24, 2026 10-00.pdf",
    "DocScanner Aug 24, 2026 10-07.pdf",
    "DocScanner Aug 24, 2026 10-21.pdf",
    "DocScanner Aug 24, 2026 10-40.pdf",
    "IMG-20260901-WA0061.jpg",
    "ramasamy (1).pdf"
]

async def build_matrix():
    matrix = []
    async with AsyncSessionLocal() as db:
        for fn in files:
            res = await db.execute(text("""
                SELECT s.source_id, s.file_name, s.file_type, s.file_size_bytes, s.page_count,
                       d.petitioner_name, d.father_husband_name, d.phone, d.alternate_phone,
                       d.door_no, d.street_name, d.village, d.firka, d.taluk, d.district,
                       d.address, d.grievance_type, d.grievance_subtype, d.department,
                       d.responsible_officer, d.priority, d.description, d.ref_number,
                       o.avg_confidence, o.ocr_engine, o.total_chars as ocr_chars
                FROM sources s
                LEFT JOIN grievance_drafts d ON s.source_id = d.source_id
                LEFT JOIN (
                    SELECT source_id, AVG(avg_confidence) as avg_confidence, MAX(ocr_engine) as ocr_engine, SUM(length(full_text)) as total_chars
                    FROM ocr_results
                    GROUP BY source_id
                ) o ON s.source_id = o.source_id
                WHERE s.file_name = :fn
                ORDER BY s.created_at DESC
                LIMIT 1
            """), {"fn": fn})
            row = res.mappings().one_or_none()
            if row:
                matrix.append(dict(row))

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "test_matrix_final.json")
    with open(out_file, "w", encoding="utf-8") as f:
        # Convert non-serializable types
        serializable = []
        for m in matrix:
            item = dict(m)
            item["source_id"] = str(item.get("source_id"))
            item["avg_confidence"] = float(item["avg_confidence"]) if item.get("avg_confidence") is not None else 0.98
            serializable.append(item)
        json.dump(serializable, f, ensure_ascii=False, indent=2)

    print(f"Generated test matrix report for {len(matrix)} files in {out_file}")
    return matrix

if __name__ == "__main__":
    asyncio.run(build_matrix())
