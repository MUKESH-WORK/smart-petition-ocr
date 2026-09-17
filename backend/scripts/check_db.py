import sys
import asyncio

sys.stdout.reconfigure(encoding="utf-8")
from models.database import AsyncSessionLocal
from sqlalchemy import text


async def check_results():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT source_id, file_name, status, page_count FROM sources ORDER BY created_at DESC LIMIT 5"))
        print("=== LATEST SOURCES ===")
        for r in res.mappings().all():
            print(dict(r))

        d_res = await db.execute(text("SELECT * FROM grievance_drafts ORDER BY created_at DESC LIMIT 1"))
        draft = d_res.mappings().one_or_none()
        if draft:
            print("\n=== LATEST DRAFT IN DB ===")
            for k, v in dict(draft).items():
                print(f"  {k}: {v}")

        o_res = await db.execute(text("SELECT source_id, page_number, avg_confidence, length(full_text) as txt_len, full_text FROM ocr_results ORDER BY id DESC LIMIT 5"))
        print("\n=== LATEST OCR RESULTS IN DB ===")
        for o in o_res.mappings().all():
            print(f"Page {o['page_number']} | Conf: {o['avg_confidence']:.2f} | Length: {o['txt_len']} chars:")
            txt = o['full_text'] or ''
            print(txt[:400])
            print("-" * 50)


if __name__ == "__main__":
    asyncio.run(check_results())
