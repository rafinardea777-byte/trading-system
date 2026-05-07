@echo off
REM =====================================================
REM הפעלת השרת + Cloudflare Tunnel (כתובת ציבורית)
REM =====================================================
cd /d "%~dp0"
chcp 65001 >nul

if not exist .venv\Scripts\python.exe (
    echo [!] אין venv. מתקין...
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements.txt
)

if not exist bin\cloudflared.exe (
    echo [!] מוריד cloudflared...
    mkdir bin 2>nul
    curl -L -o bin\cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
)

echo.
echo ===============================================
echo   מעלה את השרת ואת ה-tunnel
echo   חכה כ-15 שניות עד שיופיע ה-URL הציבורי
echo   Ctrl+C עוצר הכל
echo ===============================================
echo.

start "trading-system server" /MIN .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

timeout /t 4 /nobreak >nul

bin\cloudflared.exe tunnel --url http://localhost:8000 --no-autoupdate
