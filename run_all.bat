@echo off
echo Starting GDP Assistant (Backend + Frontend)...
start "GDP Backend (FastAPI)" cmd /c "%~dp0run_backend.bat"
timeout /t 3 /nobreak >nul
start "GDP Frontend (Vite React)" cmd /c "%~dp0run_frontend.bat"
echo.
echo Both servers started!
echo Frontend: http://localhost:5174/
echo Backend:  http://127.0.0.1:8000/api/v1/docs
