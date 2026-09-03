@echo off
set TEMP=E:\test_rat\GDP_Assistant\temp_cache
set TMP=E:\test_rat\GDP_Assistant\temp_cache
set TMPDIR=E:\test_rat\GDP_Assistant\temp_cache
if not exist "E:\test_rat\GDP_Assistant\temp_cache" mkdir "E:\test_rat\GDP_Assistant\temp_cache"
echo Starting FastAPI Backend with 30GB+ E: drive temp storage...
.venv\Scripts\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8000
