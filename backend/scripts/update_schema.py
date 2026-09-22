"""
Schema Update Script
=====================
Adds new columns to the grievance_drafts table for TN portal fields.
All credentials sourced from environment variables (.env file).
"""
import asyncio
import os
import sys

# Ensure .env is loaded before anything else
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    from dotenv import load_dotenv
    env_path = os.path.join(backend_dir, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass


async def update_schema():
    # pyrefly: ignore [missing-import]
    import asyncpg

    # Read credentials from environment — never hardcoded
    app_user = os.environ.get("POSTGRES_USER", "dro_user")
    app_password = os.environ.get("POSTGRES_PASSWORD", "")
    pg_host = os.environ.get("POSTGRES_HOST", "localhost")
    pg_port = int(os.environ.get("POSTGRES_PORT", "5432"))
    app_db = os.environ.get("POSTGRES_DB", "dro_grievance_db")

    if not app_password:
        print("ERROR: POSTGRES_PASSWORD is not set in .env. Aborting.")
        sys.exit(1)

    conn = await asyncpg.connect(
        user=app_user,
        password=app_password,
        host=pg_host,
        port=pg_port,
        database=app_db
    )
    queries = [
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS is_own_phone BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS alternate_phone VARCHAR(20);",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS gender VARCHAR(20) DEFAULT '-None-';",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS is_differently_abled VARCHAR(10) DEFAULT 'No';",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS community_or_individual VARCHAR(50) DEFAULT 'Public';",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS grievance_source VARCHAR(100) DEFAULT 'DRO Camp';",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS ref_number VARCHAR(100);",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS sub_department VARCHAR(100);",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS local_body_type VARCHAR(100) DEFAULT 'Village Panchayat';",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS revenue_division VARCHAR(100);",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS ward VARCHAR(50);",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS municipality_ward VARCHAR(50);",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS street_name VARCHAR(150);",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS door_no VARCHAR(50);",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS responsible_officer VARCHAR(100);",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS reason_for_redirection TEXT;",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS communication_address_different BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS communication_address TEXT;",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS due_date TIMESTAMP;",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Open';",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS source_code VARCHAR(50);",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS call_disposition VARCHAR(50);",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS is_whatsapp_appeal BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS is_whatsapp_tracking BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS is_whatsapp_receipt BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE grievance_drafts ADD COLUMN IF NOT EXISTS ex_servicemen_relationship VARCHAR(50) DEFAULT '-None-';"
    ]
    for q in queries:
        await conn.execute(q)
    print("Schema updated successfully with all TN portal fields!")
    await conn.close()

if __name__ == '__main__':
    asyncio.run(update_schema())
