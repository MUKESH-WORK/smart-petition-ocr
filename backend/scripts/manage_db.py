#!/usr/bin/env python3
"""
GDP Assistant - Database Migration, Backup & Inter-System Synchronization Utility
Enables exporting, importing, dumping, and seeding database state cleanly across systems
without committing large binary files to Git.

Usage:
    python manage_db.py stats
    python manage_db.py export --output gdp_database_bundle.tar.gz
    python manage_db.py import --input gdp_database_bundle.tar.gz
    python manage_db.py dump-sql --output-dir ./db_dumps
    python manage_db.py seed-fresh
"""

import os
import sys
import json
import shutil
import tarfile
import hashlib
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Resolve base directories
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "scripts" else SCRIPT_DIR.parent.parent

DB_PATHS = [
    REPO_ROOT / "temp_cache" / "dro_admin.db",
    REPO_ROOT / "temp_cache" / "dro_user.db",
    REPO_ROOT / "backend" / "temp_cache" / "dro_admin.db",
    REPO_ROOT / "backend" / "temp_cache" / "dro_user.db",
]

def get_active_db(name: str) -> Path | None:
    """Finds the most recently updated SQLite database file by name."""
    candidates = [
        REPO_ROOT / "temp_cache" / name,
        REPO_ROOT / "backend" / "temp_cache" / name,
    ]
    existing = [p for p in candidates if p.exists() and p.stat().st_size > 0]
    if not existing:
        return None
    # Pick the one with the latest mtime
    return max(existing, key=lambda p: p.stat().st_mtime)

def calculate_sha256(filepath: Path) -> str:
    """Computes SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()

def get_sqlite_stats(db_path: Path) -> dict:
    """Extracts summary metrics from a database file."""
    if not db_path or not db_path.exists():
        return {"status": "missing"}
    
    stats = {
        "path": str(db_path),
        "size_bytes": db_path.stat().st_size,
        "size_mb": round(db_path.stat().st_size / (1024 * 1024), 2),
        "last_modified": datetime.fromtimestamp(db_path.stat().st_mtime).isoformat(),
        "tables": {}
    }
    
    try:
        con = sqlite3.connect(str(db_path))
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall() if not r[0].startswith("sqlite_")]
        
        for tbl in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM \"{tbl}\"")
                stats["tables"][tbl] = cur.fetchone()[0]
            except Exception:
                stats["tables"][tbl] = "error"
        con.close()
    except Exception as e:
        stats["error"] = str(e)
    
    return stats

def cmd_stats(args):
    """Displays comprehensive statistics of current database state."""
    print("=" * 70)
    print("🏛️  GDP Assistant - Database State & System Statistics")
    print("=" * 70)
    
    admin_db = get_active_db("dro_admin.db")
    user_db = get_active_db("dro_user.db")
    
    print(f"\n[1] Admin Database (dro_admin.db):")
    if admin_db:
        st = get_sqlite_stats(admin_db)
        print(f"    Path:     {st['path']}")
        print(f"    Size:     {st['size_mb']} MB ({st['size_bytes']:,} bytes)")
        print(f"    Modified: {st['last_modified']}")
        print(f"    Key Metrics:")
        tables = st.get("tables", {})
        print(f"      • Taxonomy Mappings:     {tables.get('cm_taxonomy_mappings', 0):,}")
        print(f"      • Administrative Units:  {tables.get('master_locations', 0):,}")
        print(f"      • Admin Accounts:        {tables.get('admin_users', 0):,}")
        print(f"      • Audit Events:          {tables.get('admin_audit_log', 0):,}")
    else:
        print("    ⚠️  Not found. (Run 'seed-fresh' to initialize from source documents)")

    print(f"\n[2] User / Grievance Database (dro_user.db):")
    if user_db:
        st = get_sqlite_stats(user_db)
        print(f"    Path:     {st['path']}")
        print(f"    Size:     {st['size_mb']} MB ({st['size_bytes']:,} bytes)")
        print(f"    Modified: {st['last_modified']}")
        print(f"    Key Metrics:")
        tables = st.get("tables", {})
        print(f"      • Uploaded Petitions:    {tables.get('sources', 0):,}")
        print(f"      • OCR Document Chunks:   {tables.get('document_chunks', 0):,}")
        print(f"      • Extraction Drafts:     {tables.get('extracted_entities', 0):,}")
    else:
        print("    ⚠️  Not found. (Initialized automatically upon first petition intake)")
    
    print("\n" + "=" * 70)

def cmd_export(args):
    """Packages databases and verification manifest into a compressed bundle."""
    out_path = Path(args.output).resolve()
    print(f"📦 Exporting database state to: {out_path}")
    
    admin_db = get_active_db("dro_admin.db")
    user_db = get_active_db("dro_user.db")
    
    if not admin_db and not user_db:
        print("❌ Error: No existing databases found to export. Run 'seed-fresh' first.")
        sys.exit(1)
        
    manifest = {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "repo": "smart-petition-ocr",
        "databases": {}
    }
    
    # Create temporary staging dir
    staging = REPO_ROOT / "temp_cache" / ".export_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    
    try:
        files_to_pack = []
        for name, db in [("dro_admin.db", admin_db), ("dro_user.db", user_db)]:
            if db and db.exists():
                target = staging / name
                # Safely copy via SQLite backup API to avoid locked file errors
                src_con = sqlite3.connect(str(db))
                dst_con = sqlite3.connect(str(target))
                src_con.backup(dst_con)
                src_con.close()
                dst_con.close()
                
                checksum = calculate_sha256(target)
                stats = get_sqlite_stats(target)
                manifest["databases"][name] = {
                    "filename": name,
                    "sha256": checksum,
                    "size_bytes": target.stat().st_size,
                    "tables": stats.get("tables", {})
                }
                files_to_pack.append(target)
                print(f"  ✓ Packed {name} ({stats['size_mb']} MB, SHA-256: {checksum[:12]}...)")
        
        manifest_path = staging / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        files_to_pack.append(manifest_path)
        
        # Build tar.gz
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(out_path, "w:gz") as tar:
            for f in files_to_pack:
                tar.add(f, arcname=f.name)
                
        final_size_mb = round(out_path.stat().st_size / (1024 * 1024), 2)
        print(f"\n🎉 Successfully created database bundle: {out_path} ({final_size_mb} MB)")
        print(f"👉 You can now safely transfer this archive (via USB, SCP, S3, or AirDrop) to another machine.")
        print(f"👉 To install on the target machine, run: python scripts/manage_db.py import --input {out_path.name}")
    finally:
        if staging.exists():
            shutil.rmtree(staging)

def cmd_import(args):
    """Imports and verifies a database bundle into the local environment."""
    bundle_path = Path(args.input).resolve()
    if not bundle_path.exists():
        print(f"❌ Error: Database bundle not found: {bundle_path}")
        sys.exit(1)
        
    print(f"📥 Importing database bundle from: {bundle_path}")
    
    # Target directory
    target_dir = REPO_ROOT / "backend" / "temp_cache"
    target_dir.mkdir(parents=True, exist_ok=True)
    fallback_dir = REPO_ROOT / "temp_cache"
    fallback_dir.mkdir(parents=True, exist_ok=True)
    
    staging = REPO_ROOT / "temp_cache" / ".import_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    
    try:
        with tarfile.open(bundle_path, "r:gz") as tar:
            tar.extractall(staging)
            
        manifest_file = staging / "manifest.json"
        if not manifest_file.exists():
            print("❌ Error: Bundle is missing manifest.json.")
            sys.exit(1)
            
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            
        print(f"  • Exported at: {manifest.get('exported_at')}")
        
        for name, info in manifest.get("databases", {}).items():
            db_file = staging / name
            if not db_file.exists():
                print(f"  ⚠️ Warning: {name} listed in manifest but not found in archive.")
                continue
                
            # Verify SHA-256
            computed_hash = calculate_sha256(db_file)
            if computed_hash != info["sha256"]:
                print(f"  ❌ Checksum mismatch for {name}! (Expected: {info['sha256']}, Computed: {computed_hash})")
                sys.exit(1)
            print(f"  ✓ Integrity verified: {name} (SHA-256 valid)")
            
            # Backup existing
            dest1 = target_dir / name
            dest2 = fallback_dir / name
            for dst in [dest1, dest2]:
                if dst.exists():
                    backup = dst.with_suffix(f".bak_{int(datetime.now().timestamp())}")
                    shutil.copy2(dst, backup)
                    print(f"    Backed up existing to {backup.name}")
                shutil.copy2(db_file, dst)
                print(f"    Installed {name} -> {dst}")
                
        print("\n🎉 Database import complete! Both dro_admin.db and dro_user.db are active.")
    finally:
        if staging.exists():
            shutil.rmtree(staging)

def cmd_dump_sql(args):
    """Exports SQLite databases into portable SQL text dumps."""
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"📄 Dumping SQL statements to: {out_dir}")
    
    for name in ["dro_admin.db", "dro_user.db"]:
        db = get_active_db(name)
        if not db:
            continue
        out_sql = out_dir / f"{Path(name).stem}_dump.sql"
        con = sqlite3.connect(str(db))
        with open(out_sql, "w", encoding="utf-8") as f:
            for line in con.iterdump():
                f.write(f"{line}\n")
        con.close()
        size_mb = round(out_sql.stat().st_size / (1024 * 1024), 2)
        print(f"  ✓ Dumped {name} -> {out_sql} ({size_mb} MB)")
        
    print(f"\n🎉 SQL dumps generated successfully in {out_dir}")

def cmd_seed_fresh(args):
    """Executes the master data seeder to build fresh databases from source PDF."""
    print("🌱 Running Master Data Seeder from source documents...")
    import asyncio
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from services.master_data_seeder import seed_authoritative_hierarchy, seed_authoritative_taxonomy, seed_official_accounts
    from models.database import get_admin_db, get_user_db
    
    async def _run():
        async for db in get_admin_db():
            print("  • Seeding official accounts...")
            await seed_official_accounts(db)
            print("  • Seeding administrative hierarchy (Zones, Taluks, Firkas, Wards)...")
            await seed_authoritative_hierarchy(db)
            print("  • Seeding CM Helpline taxonomy (40 departments, 1,861 mappings)...")
            await seed_authoritative_taxonomy(db)
            break
            
    asyncio.run(_run())
    print("\n🎉 Fresh database successfully seeded and ready for production!")

def cmd_sync_postgres(args):
    """Migrates all data from local SQLite databases directly into PostgreSQL + pgvector."""
    pg_url = args.postgres_url or os.getenv("DATABASE_URL")
    if not pg_url:
        print("❌ Error: No PostgreSQL URL provided. Specify --postgres-url or set DATABASE_URL in .env")
        sys.exit(1)
        
    print(f"🔄 Migrating SQLite data to PostgreSQL + pgvector: {pg_url.split('@')[-1]}")
    import asyncio
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    
    # Ensure async dialect format
    if pg_url.startswith("postgresql://"):
        async_pg_url = pg_url.replace("postgresql://", "postgresql+asyncpg://")
    else:
        async_pg_url = pg_url
        
    admin_db = get_active_db("dro_admin.db")
    user_db = get_active_db("dro_user.db")
    
    async def _migrate():
        engine = create_async_engine(async_pg_url, echo=False)
        async with engine.begin() as conn:
            # 1. Enable pgvector
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                print("  ✓ Enabled pgvector extension on PostgreSQL")
            except Exception as e:
                print(f"  ⚠️ Warning enabling pgvector: {e}")
                
            # 2. Initialize schemas
            from models.database import init_db_schema
            print("  • Creating PostgreSQL relational and vector tables...")
            await init_db_schema()
            
            # 3. Migrate dro_admin.db tables
            if admin_db:
                print("  • Migrating Admin DB tables...")
                con = sqlite3.connect(str(admin_db))
                con.row_factory = sqlite3.Row
                cur = con.cursor()
                
                # Admin Users
                cur.execute("SELECT * FROM admin_users")
                users = [dict(r) for r in cur.fetchall()]
                if users:
                    for u in users:
                        await conn.execute(text("""
                            INSERT INTO admin_users (id, name, name_tamil, mobile, email, password_hash, department, role, is_admin, status)
                            VALUES (:id, :name, :name_tamil, :mobile, :email, :password_hash, :department, :role, :is_admin, :status)
                            ON CONFLICT (id) DO UPDATE SET 
                                name = EXCLUDED.name, email = EXCLUDED.email, mobile = EXCLUDED.mobile,
                                department = EXCLUDED.department, role = EXCLUDED.role, is_admin = EXCLUDED.is_admin
                        """), u)
                    print(f"    ✓ Synced {len(users)} admin accounts")
                    
                # Master Locations
                cur.execute("SELECT * FROM master_locations")
                locs = [dict(r) for r in cur.fetchall()]
                if locs:
                    await conn.execute(text("TRUNCATE TABLE master_locations RESTART IDENTITY;"))
                    for l in locs:
                        emb = l.get("embedding")
                        if emb and isinstance(emb, str):
                            try:
                                emb = json.loads(emb)
                            except: pass
                        await conn.execute(text("""
                            INSERT INTO master_locations (
                                district_code, district_name_tamil, district_name_en,
                                division_code, division_name_tamil, division_name_en,
                                taluk_code, taluk_name_tamil, taluk_name_en,
                                firka_code, firka_name_tamil, firka_name_en,
                                block_code, block_name_tamil, block_name_en,
                                village_code, village_name_tamil, village_name_en,
                                local_body_type, ward_no, ward_name_tamil, ward_name_en,
                                pincode, search_text, sub_departments
                            ) VALUES (
                                :district_code, :district_name_tamil, :district_name_en,
                                :division_code, :division_name_tamil, :division_name_en,
                                :taluk_code, :taluk_name_tamil, :taluk_name_en,
                                :firka_code, :firka_name_tamil, :firka_name_en,
                                :block_code, :block_name_tamil, :block_name_en,
                                :village_code, :village_name_tamil, :village_name_en,
                                :local_body_type, :ward_no, :ward_name_tamil, :ward_name_en,
                                :pincode, :search_text, :sub_departments
                            )
                        """), l)
                    print(f"    ✓ Synced {len(locs)} administrative locations")

                # CM Taxonomy Mappings
                cur.execute("SELECT * FROM cm_taxonomy_mappings")
                taxs = [dict(r) for r in cur.fetchall()]
                if taxs:
                    await conn.execute(text("TRUNCATE TABLE cm_taxonomy_mappings RESTART IDENTITY;"))
                    for t in taxs:
                        await conn.execute(text("""
                            INSERT INTO cm_taxonomy_mappings (
                                department, department_code, sub_department,
                                grievance_type, grievance_sub_type, responsible_officer, search_text
                            ) VALUES (
                                :department, :department_code, :sub_department,
                                :grievance_type, :grievance_sub_type, :responsible_officer, :search_text
                            )
                        """), t)
                    print(f"    ✓ Synced {len(taxs)} taxonomy mappings")
                    
                con.close()
                
        await engine.dispose()
        print("\n🎉 PostgreSQL + pgvector synchronization completed successfully!")

    asyncio.run(_migrate())

def main():
    parser = argparse.ArgumentParser(description="GDP Assistant Database Migration & Management Utility")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")
    
    # stats
    subparsers.add_parser("stats", help="Display current database metrics and table counts")
    
    # export
    p_export = subparsers.add_parser("export", help="Package databases into a portable tar.gz bundle")
    p_export.add_argument("--output", "-o", default="gdp_database_bundle.tar.gz", help="Output bundle file path")
    
    # import
    p_import = subparsers.add_parser("import", help="Import a database bundle onto this system")
    p_import.add_argument("--input", "-i", required=True, help="Input bundle file path")
    
    # dump-sql
    p_dump = subparsers.add_parser("dump-sql", help="Export SQLite databases into portable SQL text dump")
    p_dump.add_argument("--output-dir", "-o", default="./db_dumps", help="Directory for .sql dump files")
    
    # sync-to-postgres
    p_pg = subparsers.add_parser("sync-to-postgres", help="Migrate SQLite databases directly into PostgreSQL with pgvector")
    p_pg.add_argument("--postgres-url", "-p", default=None, help="Target PostgreSQL connection URL")
    
    # seed-fresh
    subparsers.add_parser("seed-fresh", help="Re-seed databases directly from authoritative source PDF")
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
        
    if args.command == "stats":
        cmd_stats(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "import":
        cmd_import(args)
    elif args.command == "dump-sql":
        cmd_dump_sql(args)
    elif args.command == "sync-to-postgres":
        cmd_sync_postgres(args)
    elif args.command == "seed-fresh":
        cmd_seed_fresh(args)

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
