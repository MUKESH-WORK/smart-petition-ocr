#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting GDP Assistant (Backend + Frontend)..."

"$SCRIPT_DIR/run_backend.sh" &
BACKEND_PID=$!

sleep 3

"$SCRIPT_DIR/run_frontend.sh" &
FRONTEND_PID=$!

echo ""
echo "Both servers started!"
echo "Frontend: http://localhost:5174/"
echo "Backend:  http://127.0.0.1:8000/api/v1/docs"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true" EXIT
wait
