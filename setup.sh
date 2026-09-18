#!/usr/bin/env bash
set -e

echo "======================================================================="
echo "  🏛️ GDP Assistant — Automated 1-Click Environment Setup (Linux/macOS)"
echo "======================================================================="
cd "$(dirname "$0")"

# 1. Check Python
echo "[1/5] Checking Python installation..."
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 is not installed or not in PATH."
    exit 1
fi

# 2. Setup Virtual Environment
echo "[2/5] Setting up Python virtual environment (backend/.venv)..."
if [ ! -f "backend/.venv/bin/python" ]; then
    python3 -m venv backend/.venv
fi
VENV_PYTHON="$(pwd)/backend/.venv/bin/python"

# 3. Install Python Dependencies
echo "[3/5] Installing backend dependencies..."
$VENV_PYTHON -m pip install --upgrade pip --quiet
$VENV_PYTHON -m pip install -r backend/requirements.txt

# 4. Check Node.js and install Frontend dependencies
echo "[4/5] Checking Node.js and frontend dependencies..."
if command -v npm &>/dev/null; then
    if [ ! -d "frontend/node_modules" ]; then
        echo "Installing frontend npm packages..."
        (cd frontend && npm install)
    else
        echo "Frontend node_modules already exists."
    fi
else
    echo "[WARNING] Node.js / npm not found. Install Node.js from https://nodejs.org"
fi

# 5. Initialize Database
echo "[5/5] Initializing database and authoritative data..."
if [ -f "gdp_database_bundle.tar.gz" ]; then
    echo "Found gdp_database_bundle.tar.gz. Importing..."
    $VENV_PYTHON scripts/manage_db.py import --input gdp_database_bundle.tar.gz
elif [ -f "backend/gdp_database_bundle.tar.gz" ]; then
    echo "Found backend/gdp_database_bundle.tar.gz. Importing..."
    $VENV_PYTHON scripts/manage_db.py import --input backend/gdp_database_bundle.tar.gz
elif [ ! -f "backend/temp_cache/dro_admin.db" ]; then
    echo "Seeding authoritative taxonomy and administrative hierarchy..."
    $VENV_PYTHON scripts/manage_db.py seed-fresh
else
    echo "Database already initialized."
fi

echo ""
$VENV_PYTHON scripts/manage_db.py stats
echo ""
echo "======================================================================="
echo "  🎉 Setup Completed Successfully!"
echo "======================================================================="
echo "  👉 To launch the entire system: ./run_all.sh"
echo "  👉 To activate virtualenv:     source backend/.venv/bin/activate"
echo "======================================================================="
