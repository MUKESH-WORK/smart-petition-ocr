import asyncio
import os
import sys
import logging
sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

from models.database import AsyncSessionLocal
from services.ai_analyzer import ai_analyzer
from sqlalchemy import text

async def test():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT source_id FROM sources WHERE file_name LIKE '%10-07%' LIMIT 1"))
        row = res.mappings().one()
        source_id = str(row["source_id"])
        print(f"Re-analyzing source {source_id}...")
        analysis = await ai_analyzer.analyze(db, source_id)
        print("=== RESULT ===")
        import json
        print(json.dumps(analysis, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(test())
