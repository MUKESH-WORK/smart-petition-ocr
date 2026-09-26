import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    pg_url = "postgresql+asyncpg://dro_user:dro_password_2026@localhost:5432/dro_grievance_db"
    engine = create_async_engine(pg_url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT table_name, column_name, data_type, udt_name FROM information_schema.columns WHERE column_name IN ('source_id', 'id') AND table_name IN ('sources', 'grievance_drafts', 'job_queue')"))
        for r in res.fetchall():
            print(r)

if __name__ == "__main__":
    asyncio.run(main())
