@echo off
REM סריקת חדשות חד-פעמית + הפקת דוח HTML
cd /d "%~dp0"
call .venv\Scripts\activate
python -m app.cli scan-news --hours 24 --report
pause
