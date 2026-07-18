@echo off
REM CAD-CAE Backend startup script for Windows
REM Forces UTF-8 encoding to prevent UnicodeEncodeError in logs

SET PYTHONUTF8=1
SET PYTHONIOENCODING=utf-8

echo Starting CAD-CAE Analyzer API...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
