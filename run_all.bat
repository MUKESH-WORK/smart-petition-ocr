@echo off
echo =======================================================================
echo        Launching GDP Assistant System
echo =======================================================================
cd /d "%~dp0"

REM Detect Python executable
set PYTHON_EXE=python
if exist "%~dp0backend\.venv\Scripts\python.exe" (
    set PYTHON_EXE="%~dp0backend\.venv\Scripts\python.exe"
) else if exist "%~dp0.venv\Scripts\python.exe" (
    set PYTHON_EXE="%~dp0.venv\Scripts\python.exe"
)

REM Auto-seed database if fresh clone
if not exist "%~dp0backend\temp_cache\dro_admin.db" (
    if exist "%~dp0gdp_database_bundle.tar.gz" (
        echo Importing pre-packaged database bundle...
        %PYTHON_EXE% scripts\manage_db.py import --input gdp_database_bundle.tar.gz
    ) else if exist "%~dp0backend\gdp_database_bundle.tar.gz" (
        echo Importing pre-packaged database bundle...
        %PYTHON_EXE% scripts\manage_db.py import --input backend\gdp_database_bundle.tar.gz
    ) else (
        echo Fresh clone detected. Seeding authoritative taxonomy and hierarchy...
        %PYTHON_EXE% scripts\manage_db.py seed-fresh
    )
)

echo.
echo [1/2] Launching FastAPI Backend (Port 8000)...
start "GDP Assistant - Backend" cmd /k "cd /d ""%~dp0backend"" && call .venv\Scripts\activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/2] Launching React Vite Frontend (Port 5174)...
start "GDP Assistant - Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

echo.
echo Waiting for servers to initialize...
timeout /t 3 /nobreak >nul

echo Opening browser at http://localhost:5174 ...
start http://localhost:5174

echo =======================================================================
echo    GDP Assistant is running!
echo      • Frontend Portal:  http://localhost:5174
echo      • Backend API:      http://127.0.0.1:8000
echo      • API Swagger Docs: http://127.0.0.1:8000/api/v1/docs
echo =======================================================================
