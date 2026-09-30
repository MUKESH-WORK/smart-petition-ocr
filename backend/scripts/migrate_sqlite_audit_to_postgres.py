import os
import sys
import json
import sqlite3
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import settings
from models.database import init_db_schema, user_engine, audit_engine

def parse_dt_obj(val):
    if not val:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(val, datetime):
        return val.replace(tzinfo=None)
    if isinstance(val, str):
        try:
            clean = val.replace("Z", "").split("+")[0].strip()
            if "T" in clean:
                dt = datetime.fromisoformat(clean)
            else:
                dt = datetime.strptime(clean, "%Y-%m-%d %H:%M:%S")
            return dt.replace(tzinfo=None)
        except Exception:
            return datetime.now(timezone.utc).replace(tzinfo=None)
    return datetime.now(timezone.utc).replace(tzinfo=None)

async def migrate_sqlite_audit_to_postgres():
    print("=" * 70)
    print("🚀 MIGRATING AUDIT LOGS & EVENT HISTORY TO POSTGRESQL 16")
    print("=" * 70)

    # 1. Initialize schema in PostgreSQL first
    print("\n[STEP 1] Initializing PostgreSQL 16 schemas & audit tables...")
    await init_db_schema()

    async with audit_engine.begin() as alter_c:
        try:
            await alter_c.execute(text("ALTER TABLE audit_log ALTER COLUMN source_id TYPE VARCHAR(100);"))
            await alter_c.execute(text("ALTER TABLE audit_log ALTER COLUMN ip_address TYPE VARCHAR(50);"))
        except Exception:
            pass

    # 2. Check for SQLite audit databases
    candidates = [
        REPO_ROOT / "backend" / "temp_cache" / "dro_audit.db",
        REPO_ROOT / "temp_cache" / "dro_audit.db",
        REPO_ROOT / "backend" / "temp_cache" / "dro_admin.db",
        REPO_ROOT / "temp_cache" / "dro_admin.db",
    ]

    total_audit_migrated = 0
    total_admin_act_migrated = 0
    total_mov_migrated = 0

    seen_files = set()
    async with audit_engine.begin() as pg_conn:
        for cand in candidates:
            resolved = str(cand.resolve())
            if resolved in seen_files or not cand.exists() or cand.stat().st_size == 0:
                continue
            seen_files.add(resolved)

            print(f"\n[STEP 2] Processing SQLite file: {cand} ({cand.stat().st_size:,} bytes)...")
            try:
                con = sqlite3.connect(str(cand))
                con.row_factory = sqlite3.Row
                cur = con.cursor()

                tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

                # Migrate audit_log
                if "audit_log" in tables:
                    rows = cur.execute("SELECT timestamp, source_id, officer_id, action, details, ip_address FROM audit_log").fetchall()
                    for r in rows:
                        dtls = r["details"]
                        if isinstance(dtls, str):
                            try:
                                dtls_json = json.dumps(json.loads(dtls))
                            except Exception:
                                dtls_json = json.dumps({"raw": dtls})
                        elif dtls:
                            dtls_json = json.dumps(dtls)
                        else:
                            dtls_json = "{}"

                        await pg_conn.execute(text("""
                            INSERT INTO audit_log (timestamp, source_id, officer_id, action, details, ip_address)
                            VALUES (:ts, :source_id, :officer_id, :action, CAST(:details AS jsonb), :ip_address)
                        """), {
                            "ts": parse_dt_obj(r["timestamp"]),
                            "source_id": str(r["source_id"]) if r["source_id"] else None,
                            "officer_id": r["officer_id"],
                            "action": r["action"] or "EVENT",
                            "details": dtls_json,
                            "ip_address": r["ip_address"] or "127.0.0.1"
                        })
                        total_audit_migrated += 1

                # Migrate admin_activity_log
                if "admin_activity_log" in tables:
                    rows = cur.execute("SELECT id, type, detail, date, officer_id FROM admin_activity_log").fetchall()
                    for r in rows:
                        await pg_conn.execute(text("""
                            INSERT INTO admin_activity_log (id, type, detail, date, officer_id)
                            VALUES (:id, :type, :detail, :date, :officer_id)
                            ON CONFLICT (id) DO UPDATE SET detail = EXCLUDED.detail, date = EXCLUDED.date
                        """), {
                            "id": str(r["id"]),
                            "type": str(r["type"] or "UPDATE"),
                            "detail": str(r["detail"] or ""),
                            "date": parse_dt_obj(r["date"]),
                            "officer_id": str(r["officer_id"] or "SYSTEM")
                        })
                        total_admin_act_migrated += 1

                # Migrate petition_movements
                if "petition_movements" in tables:
                    rows = cur.execute("SELECT petition_id, movement_type, from_officer, to_officer, status, remark, timestamp FROM petition_movements").fetchall()
                    for r in rows:
                        await pg_conn.execute(text("""
                            INSERT INTO petition_movements (petition_id, movement_type, from_officer, to_officer, status, remark, timestamp)
                            VALUES (:petition_id, :movement_type, :from_officer, :to_officer, :status, :remark, :timestamp)
                        """), {
                            "petition_id": str(r["petition_id"]),
                            "movement_type": str(r["movement_type"] or "DISPATCH"),
                            "from_officer": r["from_officer"],
                            "to_officer": r["to_officer"],
                            "status": r["status"],
                            "remark": r["remark"],
                            "timestamp": parse_dt_obj(r["timestamp"])
                        })
                        total_mov_migrated += 1

                con.close()
            except Exception as e:
                print(f"  ⚠️ Note processing {cand}: {e}")

    # 3. Print verification stats from PostgreSQL
    print("\n[STEP 3] Verifying PostgreSQL Audit & Event Store Counts:")
    async with audit_engine.begin() as verify_conn:
        cnt_audit = (await verify_conn.execute(text("SELECT COUNT(*) FROM audit_log"))).scalar() or 0
        cnt_admin_act = (await verify_conn.execute(text("SELECT COUNT(*) FROM admin_activity_log"))).scalar() or 0
        cnt_mov = (await verify_conn.execute(text("SELECT COUNT(*) FROM petition_movements"))).scalar() or 0

        print(f"  • PostgreSQL audit_log count:          {cnt_audit:,}")
        print(f"  • PostgreSQL admin_activity_log count: {cnt_admin_act:,}")
        print(f"  • PostgreSQL petition_movements count: {cnt_mov:,}")

    print("\n" + "=" * 70)
    print(f"✅ MIGRATION COMPLETE: Successfully synchronized {total_audit_migrated} audit logs, {total_admin_act_migrated} admin activities, {total_mov_migrated} movements to PostgreSQL.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(migrate_sqlite_audit_to_postgres())
