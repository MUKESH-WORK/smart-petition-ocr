import sys
import asyncio

sys.stdout.reconfigure(encoding="utf-8")

from models.database import AsyncSessionLocal
from services.entity_extractor import entity_extractor
from services.ai_analyzer import ai_analyzer
from sqlalchemy import text


async def run():
    source_id = "1d4dc1de-5f44-4138-8274-7f5ce345e6ec"
    async with AsyncSessionLocal() as db:
        print("=== STEP 3: Extracting Entities ===")
        ents = await entity_extractor.extract_all(db, source_id)
        for e in ents:
            print(f"  🏷️ {e['entity_type']}: {e['entity_value']} (Confidence: {e['confidence']})")

        print("\n=== STEP 4: AI Analysis & Drafting ===")
        analysis = await ai_analyzer.analyze(db, source_id)
        print("AI Analysis Complete!")
        print("  - Grievance Type:", analysis.get("grievance_type"))
        print("  - Department:", analysis.get("department"))
        print("  - Summary (Tamil):", analysis.get("description_summary_tamil"))
        print("  - Summary (English):", analysis.get("description_summary_english"))

        d_res = await db.execute(text("SELECT * FROM grievance_drafts WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": source_id})
        draft = d_res.mappings().one_or_none()
        if draft:
            print("\n============================================================")
            print("🏛️ FINAL AUTO-POPULATED GRIEVANCE DRAFT (TN DRO PORTAL)")
            print("============================================================")
            print(f"  📌 DRO Grievance ID : {draft.get('dro_grievance_id')}")
            print(f"  👤 Petitioner Name   : {draft.get('petitioner_name')}")
            print(f"  👨 Father/Husband    : {draft.get('father_husband_name')}")
            print(f"  📞 Phone Number       : {draft.get('phone')}")
            print(f"  🏠 Address            : {draft.get('address')}")
            print(f"  📍 Taluk              : {draft.get('taluk')}")
            print(f"  🗺️ District           : {draft.get('district')}")
            print(f"  🏢 Department         : {draft.get('department')}")
            print(f"  📋 Grievance Type     : {draft.get('grievance_type')}")
            print(f"  📑 Grievance Subtype  : {draft.get('grievance_subtype')}")
            print(f"  ⚠️ Priority Level     : {draft.get('priority')}")
            print(f"  📝 Grievance Summary  : {draft.get('description')}")
            print(f"  🎯 Action Requested   : {draft.get('relief_sought')}")
            print("============================================================")


if __name__ == "__main__":
    asyncio.run(run())
