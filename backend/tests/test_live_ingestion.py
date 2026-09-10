import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from models.database import AsyncSessionLocal
from sqlalchemy import text


@pytest.mark.asyncio
async def test_live_upload_and_pipeline():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Health check
        h_res = await client.get("/health")
        assert h_res.status_code == 200
        assert h_res.json()["status"] == "healthy"

        # 2. Quality Metrics
        q_res = await client.get("/api/v1/admin/quality")
        assert q_res.status_code == 200
        q_data = q_res.json()
        assert "total_petitions" in q_data
        assert "stage_failures" in q_data

        # 3. Test Ingestion with user_petition_p1.png
        img_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_petition_p1.png")
        if not os.path.exists(img_path):
            pytest.skip("user_petition_p1.png not found")

        with open(img_path, "rb") as f:
            files = {"file": ("test_petition.png", f, "image/png")}
            up_res = await client.post("/api/v1/grievance/upload?process_now=true", files=files)
            assert up_res.status_code == 200
            data = up_res.json()
            source_id = data["source_id"]
            assert source_id is not None

        # 4. Fetch Stage 0 & Stage 1 OCR results
        ocr_res = await client.get(f"/api/v1/grievance/{source_id}/ocr")
        assert ocr_res.status_code == 200
        ocr_data = ocr_res.json()
        assert "pages" in ocr_data
        assert len(ocr_data["pages"]) > 0
        p1 = ocr_data["pages"][0]
        assert "lines" in p1
        assert len(p1["lines"]) > 0
        assert p1["avg_confidence"] > 0.0

        # 5. Check Stamp API
        stamp_res = await client.get(f"/api/v1/grievance/{source_id}/stamp")
        assert stamp_res.status_code == 200
        stamp_data = stamp_res.json()
        assert "stamp_found" in stamp_data
        assert stamp_data["stamp_found"] is True

        # 6. Check Fields Provenance API
        fields_res = await client.get(f"/api/v1/grievance/{source_id}/fields")
        assert fields_res.status_code == 200
        f_data = fields_res.json()
        assert "fields" in f_data
        assert "can_approve" in f_data

        # 7. Test Field Correction (PUT /fields/{field})
        put_res = await client.put(f"/api/v1/grievance/{source_id}/fields/petitioner_name?value=திரு. கே. ராமலிங்கம்&note=Verified with Aadhaar")
        assert put_res.status_code == 200
        assert put_res.json()["review_state"] == "corrected"

        # Verify field reflects correction
        fields_res2 = await client.get(f"/api/v1/grievance/{source_id}/fields")
        f_map = fields_res2.json()["fields"]
        assert f_map["petitioner_name"]["value"] == "திரு. கே. ராமலிங்கம்"
        assert f_map["petitioner_name"]["review_state"] == "corrected"

        # 8. Test Diagnostic Debug OCR Text Endpoint
        debug_res = await client.get(f"/api/v1/grievance/{source_id}/debug-ocr-text")
        assert debug_res.status_code == 200
        d_data = debug_res.json()
        assert d_data["page_count"] >= 1
        assert d_data["length"] > 0
        assert "raw_text" in d_data

        # 9. Test Draft Approval with Missing vs Present Fields
        async with AsyncSessionLocal() as db:
            await db.execute(text("""
                INSERT INTO officers (officer_id, name_tamil, designation, department)
                VALUES ('OFFICER_001', 'அலுவலர் 1', 'DRO Assistant', 'வருவாய்த்துறை')
                ON CONFLICT (officer_id) DO NOTHING
            """))
            await db.commit()
            d_res = await db.execute(text("SELECT id FROM grievance_drafts WHERE source_id = CAST(:sid AS UUID)"), {"sid": source_id})
            draft_id = str(d_res.scalar_one())

        # Ensure all legal fields are set so approve succeeds
        await client.put(f"/api/v1/grievance/{source_id}/fields/phone?value=9788180010")
        await client.put(f"/api/v1/grievance/{source_id}/fields/taluk?value=பெருந்துறை")
        await client.put(f"/api/v1/grievance/{source_id}/fields/department?value=வருவாய்த்துறை")

        app_res = await client.post(
            f"/api/v1/grievance/draft/{draft_id}/approve",
            json={
                "officer_id": "OFFICER_001",
                "officer_notes": "All legal fields grounded and verified.",
                "bypass_hallucination_warning": True
            }
        )
        assert app_res.status_code == 200
        assert app_res.json()["officer_approved"] is True

        # 10. Check Complete Audit Log Event Taxonomy
        async with AsyncSessionLocal() as db:
            audit_res = await db.execute(text("""
                SELECT action FROM audit_log
                WHERE source_id = CAST(:sid AS UUID)
                ORDER BY timestamp ASC
            """), {"sid": source_id})
            actions = [r[0] for r in audit_res.fetchall()]
            assert "UPLOADED" in actions
            assert "OFFICER_REVIEWED" in actions
            assert "OFFICER_APPROVED" in actions


@pytest.mark.asyncio
async def test_upload_enqueue_background_preprocess_job():
    """Verify standard UI upload enqueues 'preprocess' job without constraint violation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        import uuid
        unique_bytes = b"%PDF-1.4 Fresh queue test petition content: " + uuid.uuid4().bytes
        files = {"file": ("fresh_queue_petition.pdf", unique_bytes, "application/pdf")}
        up_res = await client.post("/api/v1/grievance/upload", files=files, data={"process_now": "false"})
        assert up_res.status_code == 200
        data = up_res.json()
        source_id = data["source_id"]
        assert source_id is not None

        # Verify job was placed in job_queue with job_type='preprocess'
        async with AsyncSessionLocal() as db:
            q_res = await db.execute(text("""
                SELECT job_type, status FROM job_queue
                WHERE source_id = CAST(:sid AS UUID)
            """), {"sid": source_id})
            row = q_res.fetchone()
            assert row is not None
            assert row[0] == "preprocess"
            assert row[1] == "pending"

        # 2. Test via Query Param (?process_now=false)
        unique_bytes2 = b"%PDF-1.4 Fresh query test petition content: " + uuid.uuid4().bytes
        files2 = {"file": ("fresh_query_petition.pdf", unique_bytes2, "application/pdf")}
        up_res2 = await client.post("/api/v1/grievance/upload?process_now=false", files=files2)
        assert up_res2.status_code == 200
        source_id2 = up_res2.json()["source_id"]

        async with AsyncSessionLocal() as db:
            q_res2 = await db.execute(text("""
                SELECT job_type, status FROM job_queue
                WHERE source_id = CAST(:sid AS UUID)
            """), {"sid": source_id2})
            row2 = q_res2.fetchone()
            assert row2 is not None
            assert row2[0] == "preprocess"
            assert row2[1] == "pending"


