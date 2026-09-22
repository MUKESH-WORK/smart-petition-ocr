"""
Database Initialization Script
===============================
Creates the PostgreSQL user and database for DRO Grievance system.
All credentials sourced from environment variables (.env file).
"""
import asyncio
import os
import sys

# Ensure .env is loaded before anything else
backend_dir = os.path.dirname(os.path.abspath(__file__))
try:
    from dotenv import load_dotenv
    env_path = os.path.join(backend_dir, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass


async def setup():
    import asyncpg

    # Read credentials from environment — never hardcoded
    pg_admin_user = os.environ.get("PG_ADMIN_USER", "postgres")
    pg_admin_password = os.environ.get("PG_ADMIN_PASSWORD", os.environ.get("POSTGRES_ADMIN_PASSWORD", "postgres"))
    pg_host = os.environ.get("POSTGRES_HOST", "localhost")
    pg_port = int(os.environ.get("POSTGRES_PORT", "5432"))

    app_user = os.environ.get("POSTGRES_USER", "dro_user")
    app_password = os.environ.get("POSTGRES_PASSWORD", "")
    app_db = os.environ.get("POSTGRES_DB", "dro_grievance_db")

    if not app_password:
        print("ERROR: POSTGRES_PASSWORD is not set in .env. Aborting.")
        sys.exit(1)

    conn = await asyncpg.connect(
        user=pg_admin_user,
        password=pg_admin_password,
        host=pg_host,
        port=pg_port,
        database='postgres'
    )
    try:
        user_exists = await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname=$1", app_user)
        if not user_exists:
            await conn.execute(f"CREATE USER {app_user} WITH PASSWORD '{app_password}' SUPERUSER CREATEDB;")
            print(f"Created user: {app_user}")
        else:
            await conn.execute(f"ALTER USER {app_user} WITH PASSWORD '{app_password}' SUPERUSER CREATEDB;")
            print(f"Updated user: {app_user}")

        db_exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname=$1", app_db)
        if not db_exists:
            await conn.execute(f"CREATE DATABASE {app_db} OWNER {app_user};")
            print(f"Created database: {app_db}")
        else:
            print(f"Database {app_db} already exists")
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(setup())
