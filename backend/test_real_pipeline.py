import sys
import os
import shutil
import uuid
import asyncio

sys.stdout.reconfigure(encoding="utf-8")

from models.database import AsyncSessionLocal
from services.file_store import file_store
from services.ocr_router import ocr_router
from services.tamil_chunker import tamil_chunker
from services.vector_store import vector_store
from services.entity_extractor import entity_extractor
from services.ai_analyzer import ai_analyzer
# pyrefly: ignore [missing-import]
from sqlalchemy import text


async def run_real_user_petition():
    user_pdf = r"C:\Users\Naveen\.gemini\antigravity-ide\brain\081c8663-a3fa-47d8-b121-ca3bafd2e0f2\.user_uploaded\media_1788335022132.pdf"
    if not os.path.exists(user_pdf):
        print("User PDF not found!")
        return

    with open(user_pdf, "rb") as f:
        content = f.read()

    source_id = str(uuid.uuid4())
    filename = "DocScanner 24 Aug 2026 10-13 am.pdf"

    saved_path, file_hash, size = await file_store.save_uploaded_file(source_id, filename, content)
    print(f"Uploaded real petition to: {saved_path} (Size: {size} bytes, ID: {source_id})")

    async with AsyncSessionLocal() as db:
        # Check if source with hash already exists
        res = await db.execute(text("SELECT source_id FROM sources WHERE file_hash = :file_hash"), {"file_hash": file_hash})
        row = res.mappings().one_or_none()
        if row:
            source_id = str(row["source_id"])
            print(f"Using existing source record: {source_id}")
        else:
            # Insert Source record
            await db.execute(text("""
                INSERT INTO sources (source_id, file_name, file_type, file_size_bytes, file_hash, status, page_count)
                VALUES (CAST(:source_id AS UUID), :file_name, 'pdf', :file_size_bytes, :file_hash, 'uploaded', 3)
            """), {
                "source_id": source_id,
                "file_name": filename,
                "file_size_bytes": size,
                "file_hash": file_hash
            })
            await db.commit()

        # Step 1: Run Paddle PP-OCRv5
        print("\n=== STEP 1: Running Paddle PP-OCRv5 ===")
        ocr_result = await ocr_router.process_source(db, source_id, saved_path, "pdf")
        print("OCR Complete:", ocr_result)

        # Step 2: Extract and print OCR text per page
        txt_res = await db.execute(text("""
            SELECT page_number, full_text, avg_confidence 
            FROM ocr_results 
            WHERE source_id = CAST(:source_id AS UUID) 
            ORDER BY page_number
        """), {"source_id": source_id})
        pages = txt_res.mappings().all()

        all_chunks = []
        for p in pages:
            p_num = p["page_number"]
            txt = p["full_text"] or ""
            conf = p["avg_confidence"]
            print(f"\n📄 PAGE {p_num} OCR OUTPUT (Confidence: {conf:.2f}, {len(txt)} chars):")
            print("-" * 60)
            print(txt)
            print("-" * 60)
            chunks = tamil_chunker.split(txt, p_num)
            all_chunks.extend(chunks)

        # Step 3: Index in pgvector
        print(f"\n=== STEP 2: Indexing {len(all_chunks)} Tamil Chunks in PGVector ===")
        if all_chunks:
            await vector_store.index_document(db, source_id, all_chunks)
            print("Vector indexing complete!")

        # Step 4: Extract Tamil Entities
        print("\n=== STEP 3: Extracting Entities ===")
        ents = await entity_extractor.extract_all(db, source_id)
        for e in ents:
            print(f"  🏷️ {e['entity_type']}: {e['entity_value']} (Confidence: {e['confidence']})")

        # Step 5: AI Analysis & Grievance Drafting
        print("\n=== STEP 4: AI Analysis & Tamil Administrative Summarization ===")
        analysis = await ai_analyzer.analyze(db, source_id)
        print("AI Analysis Complete!")
        print("  - Grievance Type:", analysis.get("grievance_type"))
        print("  - Department:", analysis.get("department"))
        print("  - Summary (Tamil):", analysis.get("description_summary_tamil"))
        print("  - Summary (English):", analysis.get("description_summary_english"))

        # Step 6: Fetch Final Form Draft
        d_res = await db.execute(text("""
            SELECT * FROM grievance_drafts 
            WHERE source_id = CAST(:source_id AS UUID)
        """), {"source_id": source_id})
        draft = d_res.mappings().one_or_none()
        if draft:
            print("\n============================================================")
            print("🏛️ FINAL AUTO-POPULATED GRIEVANCE DRAFT (TN DRO PORTAL)")
            print("============================================================")
            print(f"  📌 DRO Grievance ID : {draft.get('dro_grievance_id')}")
            print(f"  👤 Petitioner Name   : {draft.get('petitioner_name')}")
            print(f"  📞 Phone Number       : {draft.get('phone')}")
            print(f"  🏠 Address            : {draft.get('address')}")
            print(f"  📍 Taluk              : {draft.get('taluk')}")
            print(f"  🗺️ District           : {draft.get('district')}")
            print(f"  🏢 Department         : {draft.get('department')}")
            print(f"  ⚠️ Priority Level     : {draft.get('priority')}")
            print(f"  📝 Grievance Summary  : {draft.get('description')}")
            print(f"  🎯 Action Requested   : {draft.get('relief_sought')}")
            print("============================================================")


if __name__ == "__main__":
    asyncio.run(run_real_user_petition())
