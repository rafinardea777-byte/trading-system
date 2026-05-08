# Re-register scheduled task with watchdog (repeats every 5 minutes)
# If wrapper dies for any reason, watchdog brings it back within 5 min
$ScriptPath = 'C:\Users\Refael Vardi\Desktop\trading-system\tunnel_persistent.ps1'
$WorkDir    = 'C:\Users\Refael Vardi\Desktop\trading-system'
$TaskName   = 'TradingSystemTunnel'

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File `"$ScriptPath`"" `
    -WorkingDirectory $WorkDir

# Triggers: at logon (no admin needed) + repeat every 5 minutes forever
$t1 = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$t2 = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(10) `
        -RepetitionInterval (New-TimeSpan -Minutes 5) `
        -RepetitionDuration (New-TimeSpan -Days 9999)

$settings = New-ScheduledTaskSettingsSet `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -StartWhenAvailable -DontStopOnIdleEnd `
    -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries `
    -MultipleInstances IgnoreNew -WakeToRun

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger @($t1, $t2) `
    -Settings $settings `
    -Force | Out-Null

Write-Host "[OK] Task registered with watchdog (5-min repeat)"
Start-ScheduledTask -TaskName $TaskName
Write-Host "[OK] Task started"
