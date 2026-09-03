import asyncio
import asyncpg

async def setup():
    conn = await asyncpg.connect(user='postgres', password='postgres', host='localhost', port=5432, database='postgres')
    try:
        user_exists = await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname='dro_user'")
        if not user_exists:
            await conn.execute("CREATE USER dro_user WITH PASSWORD 'dro_password_2026' SUPERUSER CREATEDB;")
            print("Created user: dro_user")
        else:
            await conn.execute("ALTER USER dro_user WITH PASSWORD 'dro_password_2026' SUPERUSER CREATEDB;")
            print("Updated user: dro_user")
            
        db_exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname='dro_grievance_db'")
        if not db_exists:
            await conn.execute("CREATE DATABASE dro_grievance_db OWNER dro_user;")
            print("Created database: dro_grievance_db")
        else:
            print("Database dro_grievance_db already exists")
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(setup())
