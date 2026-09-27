#!/usr/bin/env python3
"""
Verification Script for Option C Duplicate-Document Flow
Tests:
1. Upload a new petition -> new source_id, status=uploaded/processing
2. Simulate completion of the petition draft (status=draft_ready)
3. Upload the exact same file -> NEW source_id, status=duplicate_found, duplicate_detected=True, duplicate_source_id=OLD_SOURCE_ID
4. Test "Use Previous Result" (action="reuse") -> retains NEW source_id, copies all records with new draft_id, status=draft_ready
5. Upload same file again -> Select "Process Again" (action="reprocess") -> retains NEW source_id, status=processing, enqueued OCR
6. Upload a different file -> distinct hash, no duplicate prompt
7. Security: Attempt resolve-duplicate with invalid/mismatched duplicate_source_id -> rejected (400)
"""

import sys
import os
import uuid
import asyncio
import httpx
from sqlalchemy import text

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from models.database import get_db, user_engine, init_db_schema

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


async def run_tests():
    print("=" * 80)
    print("STARTING TEST SUITE: OPTION C DUPLICATE-DOCUMENT FLOW")
    print("=" * 80)

    # Initialize schema / migrations
    await init_db_schema()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # -------------------------------------------------------------
        # TEST 1: Upload a brand new petition
        # -------------------------------------------------------------
        print("\n--- TEST 1: Uploading a brand new petition ---")
        dummy_content_1 = b"%PDF-1.4 Mock Petition for Drinking Water Supply at Ward 4, Nambiyur " + str(uuid.uuid4()).encode()
        files = {"file": ("petition_drinking_water.pdf", dummy_content_1, "application/pdf")}
        headers = {"X-Officer-Id": "DRO_ERODE_01"}

        res1 = await client.post("/api/v1/grievance/upload", files=files, headers=headers)
        assert res1.status_code == 200, f"Upload failed: {res1.text}"
        data1 = res1.json()
        source_id_1 = data1["source_id"]
        assert data1["duplicate_detected"] is False, "New upload should not be detected as duplicate"
        assert data1["status"] in ("uploaded", "processing"), f"Unexpected status: {data1['status']}"
        print(f"  [PASSED] Upload 1 created source_id={source_id_1}, duplicate_detected=False")

        # Simulate pipeline completion on source 1 (insert OCR, chunks, entities, ai_analysis, and draft)
        print("  [SETUP] Simulating completed pipeline for source_id_1...")
        async with user_engine.begin() as conn:
            await conn.execute(text("""
                UPDATE sources SET status = 'draft_ready', page_count = 1, updated_at = NOW() WHERE source_id = :sid
            """), {"sid": source_id_1})
            
            await conn.execute(text("""
                INSERT INTO ocr_results (source_id, page_number, full_text, avg_confidence, ocr_engine, processing_time_ms)
                VALUES (:sid, 1, 'மனுதாரர்: க. முருகன். குடிநீர் வசதி கோருதல்.', 0.96, 'paddleocr', 350)
                ON CONFLICT (source_id, page_number) DO NOTHING
            """), {"sid": source_id_1})

            await conn.execute(text("""
                INSERT INTO grievance_drafts (
                    id, source_id, officer_id, petitioner_name, description, department, grievance_type,
                    district, taluk, status, dro_status, created_at, updated_at
                )
                VALUES (
                    :draft_id, :sid, 'DRO_ERODE_01', 'க. முருகன்', 'குடிநீர் குழாய் சீரமைக்க கோரிக்கை.',
                    'ஊரக வளர்ச்சி மற்றும் ஊராட்சித் துறை', 'குடிநீர் வசதி', 'ஈரோடு', 'நம்பியூர்',
                    'draft', 'draft', NOW(), NOW()
                )
                ON CONFLICT (id) DO NOTHING
            """), {"draft_id": str(uuid.uuid4()), "sid": source_id_1})

        # Verify draft can be fetched for source 1
        draft1_res = await client.get(f"/api/v1/grievance/{source_id_1}/draft")
        assert draft1_res.status_code == 200, f"Draft fetch failed: {draft1_res.text}"
        draft1 = draft1_res.json()
        print(f"  [PASSED] Source 1 draft initialized: Petitioner='{draft1.get('petitioner_name')}'")

        # -------------------------------------------------------------
        # TEST 2: Upload the EXACT same file again
        # -------------------------------------------------------------
        print("\n--- TEST 2: Upload exact same petition (Duplicate Detection) ---")
        files2 = {"file": ("petition_drinking_water.pdf", dummy_content_1, "application/pdf")}
        res2 = await client.post("/api/v1/grievance/upload", files=files2, headers=headers)
        assert res2.status_code == 200, f"Upload 2 failed: {res2.text}"
        data2 = res2.json()
        source_id_2 = data2["source_id"]

        assert source_id_2 != source_id_1, f"ERROR: New upload received old source_id ({source_id_2} == {source_id_1})!"
        assert data2["duplicate_detected"] is True, "Duplicate should have been detected!"
        assert data2["duplicate_source_id"] == source_id_1, f"Expected duplicate_source_id={source_id_1}, got {data2.get('duplicate_source_id')}"
        assert data2["status"] == "duplicate_found", f"Expected status duplicate_found, got {data2['status']}"
        print(f"  [PASSED] Duplicate detected! New source_id={source_id_2} retained (Old source_id={source_id_1})")

        # -------------------------------------------------------------
        # TEST 2B: Choose "Use Previous Result" (action="reuse")
        # -------------------------------------------------------------
        print("\n--- TEST 2B: Resolving with 'reuse' ---")
        resolve_res = await client.post(
            f"/api/v1/grievance/{source_id_2}/resolve-duplicate",
            json={"action": "reuse", "duplicate_source_id": source_id_1},
            headers=headers
        )
        assert resolve_res.status_code == 200, f"Reuse resolution failed: {resolve_res.text}"
        resolve_data = resolve_res.json()
        assert resolve_data["source_id"] == source_id_2, "Must retain new source_id on reuse"
        assert resolve_data["status"] == "draft_ready", f"Expected status draft_ready, got {resolve_data['status']}"

        # Fetch draft for NEW source_id_2
        draft2_res = await client.get(f"/api/v1/grievance/{source_id_2}/draft")
        assert draft2_res.status_code == 200, f"Draft fetch failed for new source: {draft2_res.text}"
        draft2 = draft2_res.json()
        assert draft2["source_id"] == source_id_2, f"Draft belongs to wrong source_id ({draft2['source_id']} != {source_id_2})"
        assert draft2["id"] != draft1["id"], f"Draft ID must be a fresh UUID! ({draft2['id']} == {draft1['id']})"
        assert draft2["petitioner_name"] == draft1["petitioner_name"], "Copied petitioner name must match"
        print(f"  [PASSED] 'reuse' successfully created new draft (id={draft2['id']}) for new source_id={source_id_2}")

        # -------------------------------------------------------------
        # TEST 3: Upload same file again and select "Process Again" (action="reprocess")
        # -------------------------------------------------------------
        print("\n--- TEST 3: Upload exact same file again & test 'reprocess' ---")
        files3 = {"file": ("petition_drinking_water.pdf", dummy_content_1, "application/pdf")}
        res3 = await client.post("/api/v1/grievance/upload", files=files3, headers=headers)
        data3 = res3.json()
        source_id_3 = data3["source_id"]
        assert source_id_3 not in (source_id_1, source_id_2), "Must create a 3rd distinct source_id"
        assert data3["duplicate_detected"] is True

        reprocess_res = await client.post(
            f"/api/v1/grievance/{source_id_3}/resolve-duplicate",
            json={"action": "reprocess", "duplicate_source_id": source_id_1},
            headers=headers
        )
        assert reprocess_res.status_code == 200, f"Reprocess failed: {reprocess_res.text}"
        reprocess_data = reprocess_res.json()
        assert reprocess_data["source_id"] == source_id_3
        assert reprocess_data["status"] == "processing"
        print(f"  [PASSED] 'reprocess' enqueued OCR pipeline for source_id={source_id_3} with status=processing")

        # -------------------------------------------------------------
        # TEST 4: Upload a different file
        # -------------------------------------------------------------
        print("\n--- TEST 4: Uploading a different document ---")
        dummy_content_2 = b"%PDF-1.4 Totally Different Petition for Land Patta " + str(uuid.uuid4()).encode()
        files4 = {"file": ("petition_patta.pdf", dummy_content_2, "application/pdf")}
        res4 = await client.post("/api/v1/grievance/upload", files=files4, headers=headers)
        data4 = res4.json()
        source_id_4 = data4["source_id"]
        assert data4["duplicate_detected"] is False, "Different file must NOT trigger duplicate detection"
        print(f"  [PASSED] Different file processed normally: source_id={source_id_4}, duplicate_detected=False")

        # -------------------------------------------------------------
        # TEST 5: Security Check - unauthorized / forged duplicate_source_id
        # -------------------------------------------------------------
        print("\n--- TEST 5: Security check on resolve-duplicate ---")
        # Attempt to reuse with an arbitrary non-matching source_id
        fake_uuid = str(uuid.uuid4())
        bad_resolve_res = await client.post(
            f"/api/v1/grievance/{source_id_4}/resolve-duplicate",
            json={"action": "reuse", "duplicate_source_id": fake_uuid},
            headers=headers
        )
        assert bad_resolve_res.status_code in (400, 404), f"Security check failed! Server returned {bad_resolve_res.status_code}"
        print(f"  [PASSED] Server rejected invalid duplicate reuse with HTTP {bad_resolve_res.status_code}")

    print("\n" + "=" * 80)
    print("ALL 5 TESTS COMPLETED AND VERIFIED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_tests())
