@echo off
REM ============================
REM הפעלת השרת + הדשבורד
REM ============================
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    echo [!] אין venv. מתקין...
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate
)

if not exist .env (
    echo [!] חסר .env - מעתיק מ-.env.example
    copy .env.example .env
    echo [!] ערוך .env והוסף מפתחות לפני הפעלה אמיתית
)

echo.
echo ===============================================
echo   הדשבורד יעלה ב: http://127.0.0.1:8000
echo   API Docs:        http://127.0.0.1:8000/docs
echo   Ctrl+C לעצירה
echo ===============================================
echo.

python -m app.cli serve --reload
pause
