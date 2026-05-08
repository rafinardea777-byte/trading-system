@echo off
REM הפעלת ה-tunnel עם auto-restart
REM הקובץ הזה רץ ב-PowerShell (יותר יציב מ-batch לפעולה הזאת)
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0tunnel_persistent.ps1"
pause
