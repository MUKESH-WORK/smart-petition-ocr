@echo off
cd /d "%~dp0backend"
set TEMP=%~dp0temp_cache
set TMP=%~dp0temp_cache
set TMPDIR=%~dp0temp_cache
if not exist "%~dp0temp_cache" mkdir "%~dp0temp_cache"
echo Starting FastAPI Backend on http://127.0.0.1:8000 ...
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
