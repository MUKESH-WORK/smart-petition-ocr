#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p "$SCRIPT_DIR/temp_cache"
export TEMP="$SCRIPT_DIR/temp_cache"
export TMP="$SCRIPT_DIR/temp_cache"
export TMPDIR="$SCRIPT_DIR/temp_cache"
export PYTHONPATH="$SCRIPT_DIR/backend:$SCRIPT_DIR:$PYTHONPATH"

echo "Starting FastAPI Backend on http://0.0.0.0:8000 ..."

if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    "$SCRIPT_DIR/.venv/bin/python" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
elif [ -f "$SCRIPT_DIR/backend/.venv/bin/python" ]; then
    cd "$SCRIPT_DIR/backend"
    "$SCRIPT_DIR/backend/.venv/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
elif command -v python3 &>/dev/null; then
    python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
else
    python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
fi
