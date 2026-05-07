@echo off
REM סריקת שוק חד-פעמית
cd /d "%~dp0"
call .venv\Scripts\activate
python -m app.cli scan-market
pause
