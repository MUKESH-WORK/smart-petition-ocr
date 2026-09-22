@echo off
REM GDP Assistant - Backend Server Launcher
REM Run this from the repo root: e:\Projects\Active\GDP_Assistant\

cd /d "%~dp0backend"

IF NOT EXIST ".venv\Scripts\python.exe" (
    echo [ERROR] Virtualenv not found. Run: python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo  Starting DRO Grievance AI Backend...
echo  URL: http://localhost:8000
echo  Docs: http://localhost:8000/api/v1/docs
echo  Press Ctrl+C to stop
echo.

.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
