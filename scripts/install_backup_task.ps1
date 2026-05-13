# רישום משימה מתוזמנת לגיבוי יומי ב-02:00 בלילה
$ScriptPath = "$PSScriptRoot\backup_db.ps1"
$WorkDir    = (Resolve-Path "$PSScriptRoot\..").Path
$TaskName   = "TradingProBackup"

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File `"$ScriptPath`"" `
    -WorkingDirectory $WorkDir

# פעם ביום ב-02:00 בלילה
$trigger = New-ScheduledTaskTrigger -Daily -At "02:00"

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -WakeToRun

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Force | Out-Null

Write-Host "[OK] Backup task registered: daily at 02:00"
Write-Host "[i] Backups will be saved to: $env:USERPROFILE\Desktop\TradingPro-Backups"
Write-Host "[i] Run manually now? powershell -File $ScriptPath"

# הרצה ראשונה מיידית לבדיקה
Write-Host ""
Write-Host "Running first backup now..."
& $ScriptPath
