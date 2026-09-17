#!/usr/bin/env python3
"""
District Revenue Officer (DRO) Grievance Digitization AI Module
Forward Deployment Turnkey Launcher (v0.01)

Supports zero-dependency turnkey operation:
- Auto-detects environment and databases
- Defaults to embedded SQLite mode (zero PostgreSQL / zero Docker required)
- Automatically creates required directories and database tables
- Serves both the FastAPI backend and pre-compiled React frontend on a single port
"""

import os
import sys
import argparse
import socket
import logging

# Ensure root & backend directories are in sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
DATA_DIR = os.path.join(BACKEND_DIR, "data")
UPLOADS_DIR = os.path.join(BACKEND_DIR, "uploads")
STATIC_MEDIA_DIR = os.path.join(BACKEND_DIR, "static", "media")
TEMP_CACHE_DIR = os.path.join(BACKEND_DIR, "temp_cache")

for d in [DATA_DIR, UPLOADS_DIR, STATIC_MEDIA_DIR, TEMP_CACHE_DIR]:
    os.makedirs(d, exist_ok=True)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

os.environ["TEMP"] = TEMP_CACHE_DIR
os.environ["TMP"] = TEMP_CACHE_DIR
os.environ["TMPDIR"] = TEMP_CACHE_DIR


def check_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a network port is reachable."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def setup_database_mode(db_mode: str) -> str:
    """Configures the database connection based on user flag and service availability."""
    sqlite_path = os.path.join(DATA_DIR, "dro_grievance.db")
    sqlite_url = f"sqlite+aiosqlite:///{sqlite_path.replace(os.sep, '/')}"

    if db_mode == "sqlite":
        os.environ["DATABASE_URL"] = sqlite_url
        return f"SQLite Embedded Database ({sqlite_path})"

    if db_mode == "postgres":
        # Keep existing DATABASE_URL from .env
        return "PostgreSQL (Configured via .env)"

    # Auto mode: check if PostgreSQL is reachable on localhost:5432
    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = int(os.getenv("POSTGRES_PORT", 5432))
    pg_online = check_port_open(pg_host, pg_port, timeout=0.8)

    if pg_online:
        return f"PostgreSQL Auto-Detected ({pg_host}:{pg_port})"
    else:
        # Fall back to zero-dependency SQLite
        os.environ["DATABASE_URL"] = sqlite_url
        return f"SQLite Zero-Dependency Embedded Mode ({sqlite_path})"


def print_banner(db_info: str, host: str, port: int):
    """Prints production banner with system access URLs."""
    banner = f"""
================================================================================
   TAMIL NADU DRO GRIEVANCE DIGITIZATION & AUTOMATION AI MODULE (v0.01)
            Forward Deployment Engineer - Turnkey Production System
================================================================================
 [Database]    : {db_info}
 [Status]      : Zero-Dependency Embedded Engine ACTIVE (No Docker/PG needed)
 [Application] : http://{host}:{port}/
 [API Docs]    : http://{host}:{port}/api/v1/docs
 [Health Check]: http://{host}:{port}/health
 [Storage]     : {UPLOADS_DIR}
================================================================================
"""
    print(banner)


def main():
    parser = argparse.ArgumentParser(
        description="DRO Grievance AI System - Turnkey Field Launcher"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Binding host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Binding port (default: 8000)")
    parser.add_argument("--db", choices=["auto", "sqlite", "postgres"], default="auto",
                        help="Database mode: 'auto' (detect PG or fallback to SQLite), 'sqlite', or 'postgres'")
    parser.add_argument("--reload", action="store_true", help="Enable code hot-reloading for development")
    args = parser.parse_args()

    db_info = setup_database_mode(args.db)
    print_banner(db_info, args.host, args.port)

    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
        app_dir=BACKEND_DIR
    )


if __name__ == "__main__":
    main()
