import asyncio
# pyrefly: ignore [missing-import]
import asyncpg

async def update_schema():
    conn = await asyncpg.connect(user='dro_user', password='dro_password_2026', host='localhost', port=5432, database='dro_grievance_db')
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
