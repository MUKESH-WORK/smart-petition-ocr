#!/usr/bin/env python3
"""Root forwarding wrapper for backend/scripts/manage_db.py"""
import sys
from pathlib import Path

backend_script = Path(__file__).resolve().parent.parent / "backend" / "scripts" / "manage_db.py"
if not backend_script.exists():
    backend_script = Path(__file__).resolve().parent / "backend" / "scripts" / "manage_db.py"

if __name__ == "__main__":
    import runpy
    sys.path.insert(0, str(backend_script.parent))
    runpy.run_path(str(backend_script), run_name="__main__")
