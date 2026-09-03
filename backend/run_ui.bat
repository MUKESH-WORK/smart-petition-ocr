@echo off
set TEMP=E:\test_rat\GDP_Assistant\temp_cache
set TMP=E:\test_rat\GDP_Assistant\temp_cache
set TMPDIR=E:\test_rat\GDP_Assistant\temp_cache
if not exist "E:\test_rat\GDP_Assistant\temp_cache" mkdir "E:\test_rat\GDP_Assistant\temp_cache"
echo Starting Streamlit UI with 30GB+ E: drive temp storage...
.venv\Scripts\streamlit.exe run test_ui/app.py
