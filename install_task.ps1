# Register scheduled task that keeps the tunnel running
$ScriptPath = 'C:\Users\Refael Vardi\Desktop\trading-system\tunnel_persistent.ps1'
$WorkDir    = 'C:\Users\Refael Vardi\Desktop\trading-system'
$TaskName   = 'TradingSystemTunnel'

# הסר אם קיים
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File `"$ScriptPath`"" `
    -WorkingDirectory $WorkDir

$triggers = @(
    (New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME),
    (New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(5))
)

$settings = New-ScheduledTaskSettingsSet `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $triggers `
    -Settings $settings `
    -Force | Out-Null

Write-Host "[OK] Task registered: $TaskName"

Start-ScheduledTask -TaskName $TaskName
Write-Host "[OK] Task started"
