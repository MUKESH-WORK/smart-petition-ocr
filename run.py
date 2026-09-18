#!/usr/bin/env python3
"""
District Revenue Officer (DRO) Grievance Digitization AI Module
Turnkey System Launcher & Developer Environment Manager

Features:
- 1-command startup: Launches both FastAPI backend and React frontend
- System Doctor (`--doctor`): Diagnostics for Python, Node, DBs, and hardware
- Environment Setup (`--setup`): Automates virtualenv, pip, npm, and DB seeding
- Test Runner (`--test`): Runs automated test suite
- Auto-seeding: Automatically initializes 40 departments and 477 administrative units
"""

import os
import sys
import shutil
import socket
import logging
import argparse
import subprocess
from pathlib import Path

# Ensure UTF-8 output across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
TEMP_CACHE_DIR = ROOT_DIR / "backend" / "temp_cache"
TEMP_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Path configuration
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ["TEMP"] = str(TEMP_CACHE_DIR)
os.environ["TMP"] = str(TEMP_CACHE_DIR)
os.environ["TMPDIR"] = str(TEMP_CACHE_DIR)


def check_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Check if a network port is reachable."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def run_doctor():
    """Runs a comprehensive system diagnostic check."""
    print("=" * 70)
    print("🩺  GDP Assistant — System Environment Doctor")
    print("=" * 70)
    
    # Python Check
    py_ver = sys.version.split()[0]
    py_ok = sys.version_info >= (3, 11)
    print(f"  • Python Version:      {py_ver} {'✓' if py_ok else '⚠️ (3.11+ recommended)'}")
    
    # Node.js Check
    node_path = shutil.which("node")
    npm_path = shutil.which("npm")
    print(f"  • Node.js Installed:   {'✓ ' + node_path if node_path else '❌ Not found (needed for frontend)'}")
    print(f"  • npm Installed:       {'✓ ' + npm_path if npm_path else '❌ Not found'}")
    
    # Virtual Environment
    venv_py = BACKEND_DIR / ".venv" / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
    print(f"  • Backend Virtualenv:  {'✓ ' + str(venv_py) if venv_py.exists() else '⚠️ Missing (run --setup)'}")
    
    # Frontend Node Modules
    node_modules = FRONTEND_DIR / "node_modules"
    print(f"  • Frontend Modules:    {'✓ Installed' if node_modules.exists() else '⚠️ Missing (run cd frontend && npm install)'}")
    
    # Database Files
    admin_db = TEMP_CACHE_DIR / "dro_admin.db"
    user_db = TEMP_CACHE_DIR / "dro_user.db"
    print(f"  • Admin Database:      {'✓ Ready (' + str(round(admin_db.stat().st_size / (1024*1024), 1)) + ' MB)' if admin_db.exists() else '⚠️ Missing (auto-seeds on start)'}")
    print(f"  • User Database:       {'✓ Ready' if user_db.exists() else '✓ Auto-initializes on start'}")
    
    # Ports
    b_port_busy = check_port_open("127.0.0.1", 8000)
    f_port_busy = check_port_open("127.0.0.1", 5174) or check_port_open("127.0.0.1", 5173)
    print(f"  • Backend Port (8000): {'⚠️ Already in use' if b_port_busy else '✓ Available'}")
    print(f"  • Frontend Port(5174): {'⚠️ Already in use' if f_port_busy else '✓ Available'}")
    
    # Source PDF for Seeding
    pdf_source = BACKEND_DIR / "data" / "government_taxonomy.pdf"
    print(f"  • Government Taxonomy: {'✓ Found (' + str(round(pdf_source.stat().st_size / 1024, 1)) + ' KB)' if pdf_source.exists() else '❌ Missing in backend/data/'}")
    
    print("=" * 70)


def run_setup():
    """Automates initial environment setup and dependency installation."""
    print("🚀 Initializing complete GDP Assistant environment...")
    
    # 1. Check/create venv
    venv_dir = BACKEND_DIR / ".venv"
    if not venv_dir.exists():
        print("  • Creating backend Python virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_dir)])
        
    py_exec = venv_dir / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
    
    # 2. Pip requirements
    print("  • Installing backend Python dependencies...")
    subprocess.check_call([str(py_exec), "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
    subprocess.check_call([str(py_exec), "-m", "pip", "install", "-r", str(BACKEND_DIR / "requirements.txt")])
    
    # 3. Frontend npm install
    if shutil.which("npm"):
        print("  • Installing frontend Node packages...")
        subprocess.check_call(["npm", "install"], cwd=str(FRONTEND_DIR), shell=True)
    else:
        print("  ⚠️ npm not found. Please install Node.js (https://nodejs.org).")
        
    # 4. Database Seeding
    admin_db = TEMP_CACHE_DIR / "dro_admin.db"
    bundle = ROOT_DIR / "gdp_database_bundle.tar.gz"
    backend_bundle = BACKEND_DIR / "gdp_database_bundle.tar.gz"
    
    if bundle.exists():
        print("  • Importing database bundle...")
        subprocess.check_call([str(py_exec), str(ROOT_DIR / "scripts" / "manage_db.py"), "import", "--input", str(bundle)])
    elif backend_bundle.exists():
        print("  • Importing database bundle...")
        subprocess.check_call([str(py_exec), str(ROOT_DIR / "scripts" / "manage_db.py"), "import", "--input", str(backend_bundle)])
    elif not admin_db.exists():
        print("  • Seeding authoritative taxonomy and administrative hierarchy...")
        subprocess.check_call([str(py_exec), str(ROOT_DIR / "scripts" / "manage_db.py"), "seed-fresh"])
        
    print("\n🎉 Environment setup complete! Run 'python run.py' or 'run_all.bat' to start.")


def run_tests():
    """Runs the backend test suite."""
    print("🧪 Running GDP Assistant test suite...")
    subprocess.check_call([sys.executable, "-m", "pytest", "tests/", "-v"], cwd=str(BACKEND_DIR))


def start_system(host: str, port: int, reload: bool, backend_only: bool):
    """Starts backend and optional frontend concurrent servers."""
    admin_db = TEMP_CACHE_DIR / "dro_admin.db"
    if not admin_db.exists():
        print("🌱 First run detected: Seeding authoritative government taxonomy and hierarchy...")
        manage_script = ROOT_DIR / "scripts" / "manage_db.py"
        try:
            subprocess.check_call([sys.executable, str(manage_script), "seed-fresh"])
        except Exception as e:
            print(f"⚠️ Automatic seeding notice: {e}")
            
    banner = f"""
================================================================================
   🏛️  TAMIL NADU DRO GRIEVANCE DIGITIZATION & CIVIC AUTOMATION AI PLATFORM
================================================================================
  [Backend API]   : http://{host}:{port}/
  [API Docs]      : http://{host}:{port}/api/v1/docs
  [Health Check]  : http://{host}:{port}/api/v1/health
  [Frontend UI]   : http://localhost:5174/
  [Mode]          : {'Development (Hot Reload)' if reload else 'Production Turnkey'}
================================================================================
"""
    print(banner)

    # Start Vite frontend as subprocess if requested
    frontend_proc = None
    if not backend_only and shutil.which("npm"):
        print("🌐 Starting Vite frontend on port 5174...")
        frontend_proc = subprocess.Popen(["npm", "run", "dev"], cwd=str(FRONTEND_DIR), shell=True)

    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
            app_dir=str(BACKEND_DIR)
        )
    finally:
        if frontend_proc:
            print("\nShutting down frontend server...")
            frontend_proc.terminate()


def main():
    parser = argparse.ArgumentParser(description="GDP Assistant Platform Launcher")
    parser.add_argument("--host", default="127.0.0.1", help="Binding host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Backend port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable hot reload for backend code")
    parser.add_argument("--backend-only", action="store_true", help="Launch backend only without frontend")
    parser.add_argument("--doctor", action="store_true", help="Run system environment diagnostics")
    parser.add_argument("--setup", action="store_true", help="Automatically install dependencies and seed database")
    parser.add_argument("--test", action="store_true", help="Run automated test suite")
    
    args = parser.parse_args()
    
    if args.doctor:
        run_doctor()
    elif args.setup:
        run_setup()
    elif args.test:
        run_tests()
    else:
        start_system(args.host, args.port, args.reload, args.backend_only)


if __name__ == "__main__":
    main()
