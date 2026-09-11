@echo off
echo =======================================================================
echo   DRO Grievance AI Module v0.01 - Turnkey Production Launcher
echo =======================================================================
cd /d "%~dp0"

REM Detect Python executable (prefer backend venv if present)
set PYTHON_EXE=python
if exist "%~dp0backend\.venv\Scripts\python.exe" (
    set PYTHON_EXE=%~dp0backend\.venv\Scripts\python.exe
) else if exist "%~dp0.venv\Scripts\python.exe" (
    set PYTHON_EXE=%~dp0.venv\Scripts\python.exe
)

echo Starting system via: %PYTHON_EXE%
"%PYTHON_EXE%" run.py %*
