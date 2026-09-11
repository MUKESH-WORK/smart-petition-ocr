@echo off
cd /d "%~dp0"
set TEMP=%~dp0temp_cache
set TMP=%~dp0temp_cache
set TMPDIR=%~dp0temp_cache
set PYTHONPATH=%~dp0backend;%~dp0
if not exist "%~dp0temp_cache" mkdir "%~dp0temp_cache"
echo Starting FastAPI Backend on http://0.0.0.0:8000 ...
"%~dp0.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
