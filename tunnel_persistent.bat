@echo off
REM =====================================================
REM Cloudflare Tunnel עם auto-restart
REM שומר את ה-URL הנוכחי ב-current_url.txt על שולחן העבודה
REM =====================================================
chcp 65001 >nul
cd /d "%~dp0"

set URL_FILE=%USERPROFILE%\Desktop\trading-system-url.txt
set LOG_FILE=tunnel.log

if not exist bin\cloudflared.exe (
    echo מוריד cloudflared...
    mkdir bin 2>nul
    curl -L -o bin\cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
)

echo ========================================
echo  Tunnel עם auto-restart פעיל
echo  אם נופל - מפעיל מחדש אוטומטית
echo  ה-URL הנוכחי יישמר ב:
echo  %URL_FILE%
echo ========================================
echo.

:LOOP
echo [%date% %time%] מפעיל tunnel חדש...
echo --- run started %date% %time% --- >> %LOG_FILE%

REM הפעלת cloudflared ושמירת output ל-log
bin\cloudflared.exe tunnel --url http://localhost:8000 --no-autoupdate --logfile %LOG_FILE% --loglevel info > tmp_output.txt 2>&1 &

REM מחכה 8 שניות שה-URL יודפס ל-log
timeout /t 8 /nobreak >nul

REM מחלץ את ה-URL ושומר לקובץ קבוע
for /f "tokens=*" %%a in ('findstr /R "https://[a-z0-9-]*\.trycloudflare\.com" %LOG_FILE% 2^>nul ^| findstr /v "^---"') do (
    for /f "tokens=*" %%b in ('echo %%a ^| findstr /R "https://[a-z0-9-]*\.trycloudflare\.com"') do (
        powershell -NoProfile -Command "$line='%%b'; if($line -match 'https://[a-z0-9-]+\.trycloudflare\.com') { $matches[0] | Out-File -FilePath '%URL_FILE%' -Encoding utf8 -NoNewline; Write-Host \"URL: $($matches[0])\" }"
    )
)

REM מחכה לסיום של cloudflared. אם נסגר - לולאה תפעיל מחדש.
:WAIT
tasklist /FI "IMAGENAME eq cloudflared.exe" 2>nul | findstr "cloudflared.exe" >nul
if errorlevel 1 (
    echo [%date% %time%] tunnel נפל - מפעיל מחדש בעוד 5 שניות...
    timeout /t 5 /nobreak >nul
    goto LOOP
)
timeout /t 30 /nobreak >nul
goto WAIT
