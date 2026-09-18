@echo off
setlocal enabledelayedexpansion

echo =======================================================================
echo   🏛️ GDP Assistant — Automated 1-Click Environment Setup
echo =======================================================================
cd /d "%~dp0"

REM 1. Check Python
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.11+ from https://python.org and check "Add Python to PATH".
    pause
    exit /b 1
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Python version is below 3.11. Python 3.11 or higher is recommended.
)

REM 2. Setup Backend Virtual Environment
echo [2/5] Setting up Python virtual environment (backend\.venv)...
if not exist "backend\.venv\Scripts\python.exe" (
    echo Creating virtual environment in backend\.venv...
    python -m venv backend\.venv
)
set VENV_PYTHON="%~dp0backend\.venv\Scripts\python.exe"

REM 3. Install Python Dependencies
echo [3/5] Installing backend Python dependencies...
%VENV_PYTHON% -m pip install --upgrade pip --quiet
%VENV_PYTHON% -m pip install -r backend\requirements.txt

REM 4. Check Node.js and install Frontend dependencies
echo [4/5] Checking Node.js and frontend dependencies...
where npm >nul 2>&1
if %errorlevel% equ 0 (
    if not exist "frontend\node_modules" (
        echo Installing frontend npm packages...
        cd frontend && call npm install && cd ..
    ) else (
        echo Frontend node_modules already exists. Skipping npm install.
    )
) else (
    echo [WARNING] Node.js / npm not found in PATH.
    echo You will need Node.js to run the React frontend (https://nodejs.org).
)

REM 5. Setup / Seed Database
echo [5/5] Initializing database and authoritative administrative data...
if exist "gdp_database_bundle.tar.gz" (
    echo Found exported database bundle. Importing gdp_database_bundle.tar.gz...
    %VENV_PYTHON% scripts\manage_db.py import --input gdp_database_bundle.tar.gz
) else if exist "backend\gdp_database_bundle.tar.gz" (
    echo Found exported database bundle. Importing backend\gdp_database_bundle.tar.gz...
    %VENV_PYTHON% scripts\manage_db.py import --input backend\gdp_database_bundle.tar.gz
) else if not exist "backend\temp_cache\dro_admin.db" (
    echo Fresh installation detected. Seeding authoritative taxonomy and hierarchy...
    %VENV_PYTHON% scripts\manage_db.py seed-fresh
) else (
    echo Database already initialized.
)

echo.
%VENV_PYTHON% scripts\manage_db.py stats
echo.
echo =======================================================================
echo   🎉 Setup Completed Successfully!
echo =======================================================================
echo   👉 To launch the entire system (Backend + Frontend):
echo      run_all.bat
echo.
echo   👉 To activate your Python environment:
echo      activate.bat
echo =======================================================================
pause
