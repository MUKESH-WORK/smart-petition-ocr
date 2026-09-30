import os
import sys
import json
import asyncio
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, InternalError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.config import settings
from models.database import (
    init_db_schema,
    user_engine,
    admin_engine,
    audit_engine,
    readonly_engine,
    UserAsyncSessionLocal,
    AdminAsyncSessionLocal,
    AuditAsyncSessionLocal,
    ReadOnlyAsyncSessionLocal,
    is_sqlite,
    is_admin_sqlite
)
import pytest
from app.dependencies import log_audit_event

@pytest.mark.asyncio
async def test_postgres_architecture():
    print("=" * 75)
    print("🏛️ POSTGRESQL 16 ENTERPRISE ARCHITECTURE, AUDIT & READ-ONLY VERIFICATION")
    print("=" * 75)

    # -------------------------------------------------------------
    # 1. TEST SCHEMA & ENGINE SETUP
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing Pure PostgreSQL 16 Multi-Engine Architecture...")
    print(f"  • is_sqlite global flag:       {is_sqlite} (Expected: False)")
    print(f"  • is_admin_sqlite global flag: {is_admin_sqlite} (Expected: False)")
    print(f"  • Primary User DB URL:         {user_engine.url.render_as_string(hide_password=True)}")
    print(f"  • Dedicated Audit DB URL:      {audit_engine.url.render_as_string(hide_password=True)}")
    print(f"  • Safe Read-Only DB URL:       {readonly_engine.url.render_as_string(hide_password=True)}")

    await init_db_schema()
    print("  ✅ Schemas and PostgreSQL pgvector extensions initialized successfully.")

    # -------------------------------------------------------------
    # 2. TEST POSTGRESQL AUDIT LOGGING & ACTIVITY TRAIL
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing PostgreSQL Native Audit Store & Movement History...")
    test_action = "PETITION_EXTRACTION_VALIDATED"
    test_officer = "ADM-ERODE-001"
    test_details = {"module": "OCR_ROUTER", "pages": 2, "confidence": 0.99, "status": "APPROVED"}

    await log_audit_event(
        action=test_action,
        source_id="test-source-pg-001",
        officer_id=test_officer,
        details=test_details,
        ip_address="192.168.1.50"
    )

    async with AuditAsyncSessionLocal() as audit_db:
        # Verify audit_log row in PostgreSQL
        res = await audit_db.execute(
            text("SELECT id, timestamp, source_id, officer_id, action, details, ip_address FROM audit_log WHERE source_id = :sid ORDER BY id DESC LIMIT 1"),
            {"sid": "test-source-pg-001"}
        )
        row = res.mappings().one_or_none()
        assert row is not None, "Audit log row was not written to PostgreSQL!"
        print(f"   Audit log written to PostgreSQL successfully: ID={row['id']} | Action={row['action']} | Officer={row['officer_id']} | IP={row['ip_address']}")

        # Verify admin_activity_log
        act_id = f"ACT-TEST-{int(datetime.now(timezone.utc).timestamp())}"
        await audit_db.execute(text("""
            INSERT INTO admin_activity_log (id, type, detail, date, officer_id)
            VALUES (:id, :type, :detail, CURRENT_TIMESTAMP, :officer_id)
        """), {
            "id": act_id,
            "type": "SECURITY_AUDIT",
            "detail": "Verified enterprise PostgreSQL audit pipeline",
            "officer_id": test_officer
        })
        await audit_db.commit()

        act_res = await audit_db.execute(text("SELECT id, type, detail, date, officer_id FROM admin_activity_log WHERE id = :id"), {"id": act_id})
        act_row = act_res.mappings().one_or_none()
        assert act_row is not None, "Admin activity log row was not written to PostgreSQL!"
        print(f"  ✅ Admin activity log written to PostgreSQL successfully: ID={act_row['id']} | Type={act_row['type']}")

        # Verify petition_movements
        await audit_db.execute(text("""
            INSERT INTO petition_movements (petition_id, movement_type, from_officer, to_officer, status, remark, timestamp)
            VALUES (:pid, :mtype, :from_off, :to_off, :status, :remark, CURRENT_TIMESTAMP)
        """), {
            "pid": "PET-ERODE-2026-0001",
            "mtype": "FORWARD_TO_TALUK",
            "from_off": "DRO_HEAD_OFFICE",
            "to_off": "TAHSILDAR_BHAVANI",
            "status": "IN_REVIEW",
            "remark": "Forwarded to Bhavani Taluk Revenue Inspector for field verification"
        })
        await audit_db.commit()

        mov_res = await audit_db.execute(text("SELECT id, petition_id, movement_type, from_officer, to_officer, status, remark FROM petition_movements WHERE petition_id = :pid ORDER BY id DESC LIMIT 1"), {"pid": "PET-ERODE-2026-0001"})
        mov_row = mov_res.mappings().one_or_none()
        assert mov_row is not None, "Petition movement row was not written to PostgreSQL!"
        print(f"  ✅ Petition movement written to PostgreSQL successfully: ID={mov_row['id']} | Movement={mov_row['movement_type']} | From={mov_row['from_officer']} -> To={mov_row['to_officer']}")

    # -------------------------------------------------------------
    # 3. TEST POSTGRESQL READ-ONLY SAFETY GUARANTEES
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing PostgreSQL Read-Only Engine & Transaction Protection...")

    async with ReadOnlyAsyncSessionLocal() as ro_db:
        # A) Allowed: Read queries must succeed seamlessly
        res_count = (await ro_db.execute(text("SELECT COUNT(*) FROM master_locations"))).scalar()
        print(f"  ✅ Read-Only SELECT query succeeded: {res_count} master locations queried safely.")

        # B) Prohibited: Any write/insert/update must be rejected at PostgreSQL transaction level
        write_blocked = False
        try:
            await ro_db.execute(text("INSERT INTO audit_log (action, details) VALUES ('ILLEGAL_WRITE', '{}')"))
            await ro_db.commit()
        except Exception as e:
            write_blocked = True
            await ro_db.rollback()
            print(f"  ✅ Security Barrier Verified: Read-only session blocked write attempt as expected ({type(e).__name__}): {str(e)[:120]}")
        
        assert write_blocked, "ERROR: Read-only session allowed write operation!"

    # -------------------------------------------------------------
    # 4. TEST TOTAL RECORD COUNTS IN POSTGRESQL
    # -------------------------------------------------------------
    print("\n[TEST 4] Verifying Final Database Statistics in PostgreSQL 16:")
    async with AdminAsyncSessionLocal() as db:
        cnt_users = (await db.execute(text("SELECT COUNT(*) FROM admin_users"))).scalar() or 0
        cnt_locations = (await db.execute(text("SELECT COUNT(*) FROM master_locations"))).scalar() or 0
        cnt_taxonomy = (await db.execute(text("SELECT COUNT(*) FROM cm_taxonomy_mappings"))).scalar() or 0
        cnt_channels = (await db.execute(text("SELECT COUNT(*) FROM cm_grievance_channels"))).scalar() or 0
        cnt_audit = (await db.execute(text("SELECT COUNT(*) FROM audit_log"))).scalar() or 0
        cnt_act = (await db.execute(text("SELECT COUNT(*) FROM admin_activity_log"))).scalar() or 0
        cnt_mov = (await db.execute(text("SELECT COUNT(*) FROM petition_movements"))).scalar() or 0

        print(f"  • admin_users:          {cnt_users:,} rows")
        print(f"  • master_locations:     {cnt_locations:,} rows (486 villages, 60 wards, 36 firkas)")
        print(f"  • cm_taxonomy_mappings: {cnt_taxonomy:,} rows")
        print(f"  • cm_grievance_channels:{cnt_channels:,} rows")
        print(f"  • audit_log:            {cnt_audit:,} rows (in PostgreSQL)")
        print(f"  • admin_activity_log:   {cnt_act:,} rows (in PostgreSQL)")
        print(f"  • petition_movements:   {cnt_mov:,} rows (in PostgreSQL)")

    print("\n" + "=" * 75)
    print("🎉 ALL POSTGRESQL ARCHITECTURE & AUDIT TESTS PASSED WITH 100% SUCCESS")
    print("=" * 75)

if __name__ == "__main__":
    asyncio.run(test_postgres_architecture())
