@echo off
REM Root shortcut to activate the backend virtual environment
if exist "%~dp0backend\.venv\Scripts\activate.bat" (
    call "%~dp0backend\.venv\Scripts\activate.bat"
) else if exist "%~dp0.venv\Scripts\activate.bat" (
    call "%~dp0.venv\Scripts\activate.bat"
) else (
    echo [ERROR] Virtual environment not found in backend\.venv or .venv.
    echo Run 'python run.py --setup' or 'setup.bat' to create it automatically.
)
