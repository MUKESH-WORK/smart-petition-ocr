@echo off
cd /d "%~dp0"
set TEMP=%~dp0..\temp_cache
set TMP=%~dp0..\temp_cache
set TMPDIR=%~dp0..\temp_cache
if not exist "%~dp0..\temp_cache" mkdir "%~dp0..\temp_cache"
echo Starting Streamlit UI...
streamlit run test_ui/app.py
