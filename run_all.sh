#!/usr/bin/env bash
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

PYTHON_EXE="python3"
if [ -f "$DIR/backend/.venv/bin/python" ]; then
    PYTHON_EXE="$DIR/backend/.venv/bin/python"
elif [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON_EXE="$DIR/.venv/bin/python"
fi

echo "Starting DRO Grievance AI System with $PYTHON_EXE..."
"$PYTHON_EXE" run.py "$@"
