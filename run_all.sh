#!/usr/bin/env bash
set -e

echo "======================================================================="
echo "  🏛️ Launching GDP Assistant System"
echo "======================================================================="
cd "$(dirname "$0")"

# Detect Python
PYTHON_EXE="python3"
if [ -f "backend/.venv/bin/python" ]; then
    PYTHON_EXE="$(pwd)/backend/.venv/bin/python"
elif [ -f ".venv/bin/python" ]; then
    PYTHON_EXE="$(pwd)/.venv/bin/python"
fi

# Auto-seed database if fresh clone
if [ ! -f "backend/temp_cache/dro_admin.db" ]; then
    if [ -f "gdp_database_bundle.tar.gz" ]; then
        echo "Importing database bundle..."
        $PYTHON_EXE scripts/manage_db.py import --input gdp_database_bundle.tar.gz
    elif [ -f "backend/gdp_database_bundle.tar.gz" ]; then
        echo "Importing database bundle..."
        $PYTHON_EXE scripts/manage_db.py import --input backend/gdp_database_bundle.tar.gz
    else
        echo "Fresh clone detected. Seeding authoritative taxonomy and hierarchy..."
        $PYTHON_EXE scripts/manage_db.py seed-fresh
    fi
fi

echo "[1/2] Launching FastAPI Backend (Port 8000)..."
(cd backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload) &
BACKEND_PID=$!

echo "[2/2] Launching React Vite Frontend (Port 5174)..."
(cd frontend && npm run dev) &
FRONTEND_PID=$!

cleanup() {
    echo "Stopping GDP Assistant servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "======================================================================="
echo "  ✅ GDP Assistant is running!"
echo "     • Frontend Portal:  http://localhost:5174"
echo "     • Backend API:      http://127.0.0.1:8000"
echo "     • API Swagger Docs: http://127.0.0.1:8000/api/v1/docs"
echo "  Press Ctrl+C to stop both servers."
echo "======================================================================="

wait
