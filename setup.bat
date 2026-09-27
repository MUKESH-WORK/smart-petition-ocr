@echo off
echo ===================================================
echo  GDP Assistant - Initial Setup & Dependencies
echo ===================================================
python run.py --setup
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Setup encountered an issue. Please check the logs above.
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo [SUCCESS] Setup completed successfully!
pause
