# Trading System - persistent tunnel launcher
# Auto-restarts on failure, writes current URL to Desktop\trading-system-url.txt

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

$UrlFile    = Join-Path $env:USERPROFILE "Desktop\trading-system-url.txt"
$LogFile    = Join-Path $PSScriptRoot "tunnel.log"
$ServerLog  = Join-Path $PSScriptRoot "server.log"
$ServerPort = 8000

function Test-PortListening {
    param([int]$Port)
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.ReceiveTimeout = 1000
        $tcp.SendTimeout = 1000
        $tcp.Connect("127.0.0.1", $Port)
        $tcp.Close()
        return $true
    } catch {
        return $false
    }
}

# Ensure venv exists
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[!] No venv found. Installing (one-time, 2-3 min)..." -ForegroundColor Yellow
    python -m venv .venv
    & .\.venv\Scripts\python.exe -m pip install --upgrade pip
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

# Ensure cloudflared
if (-not (Test-Path "bin\cloudflared.exe")) {
    Write-Host "[!] Downloading cloudflared..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force bin | Out-Null
    Invoke-WebRequest "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile "bin\cloudflared.exe"
}

# Start API server if not running
if (-not (Test-PortListening -Port $ServerPort)) {
    Write-Host "[+] Starting API server..." -ForegroundColor Cyan
    Start-Process -FilePath ".\.venv\Scripts\python.exe" `
        -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","$ServerPort" `
        -RedirectStandardOutput $ServerLog `
        -RedirectStandardError "$ServerLog.err" `
        -WindowStyle Hidden
    $waited = 0
    while (-not (Test-PortListening -Port $ServerPort) -and $waited -lt 30) {
        Start-Sleep 2
        $waited += 2
    }
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host " Trading System - persistent mode active"
Write-Host " Current URL stored in:"
Write-Host " $UrlFile" -ForegroundColor Yellow
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""

# Forever loop: restart cloudflared if it dies
while ($true) {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Starting tunnel..." -ForegroundColor Cyan

    # Reset logs
    if (Test-Path $LogFile) { Remove-Item $LogFile -Force -ErrorAction SilentlyContinue }
    if (Test-Path "$LogFile.err") { Remove-Item "$LogFile.err" -Force -ErrorAction SilentlyContinue }

    $proc = Start-Process -FilePath ".\bin\cloudflared.exe" `
        -ArgumentList "tunnel","--url","http://localhost:$ServerPort","--no-autoupdate" `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError "$LogFile.err" `
        -PassThru -WindowStyle Hidden

    # Wait up to 30s for URL to appear in log
    $url = $null
    $waited = 0
    while ($waited -lt 30 -and -not $url) {
        Start-Sleep 2
        $waited += 2
        $combined = ""
        foreach ($f in @($LogFile, "$LogFile.err")) {
            if (Test-Path $f) {
                try { $combined += (Get-Content $f -Raw -ErrorAction SilentlyContinue) } catch {}
            }
        }
        if ($combined -match "(https://[a-z0-9-]+\.trycloudflare\.com)") {
            $url = $matches[1]
        }
    }

    if ($url) {
        # Local desktop file (without BOM, ASCII)
        [System.IO.File]::WriteAllText($UrlFile, $url)
        $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content -Path "$UrlFile.history.txt" -Value "[$stamp] $url" -Encoding utf8
        Write-Host "[+] URL: $url" -ForegroundColor Green

        # Push to GitHub Pages so the stable redirect URL works
        $DocsFile = Join-Path $PSScriptRoot "docs\current_url.txt"
        $existing = ""
        if (Test-Path $DocsFile) {
            try { $existing = ([System.IO.File]::ReadAllText($DocsFile)).Trim() } catch {}
        }
        if ($url -ne $existing) {
            try {
                [System.IO.File]::WriteAllText($DocsFile, $url)
                & git -c "user.email=tunnel@local" -c "user.name=Tunnel Bot" add "docs/current_url.txt" 2>&1 | Out-Null
                & git -c "user.email=tunnel@local" -c "user.name=Tunnel Bot" commit -m "Update tunnel URL" 2>&1 | Out-Null
                & git push origin main 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "[+] Pushed URL to GitHub Pages" -ForegroundColor Green
                } else {
                    Write-Host "[!] git push failed (exit $LASTEXITCODE) - desktop file still works" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "[!] Pages sync error: $_" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "[!] Could not extract URL. Check $LogFile" -ForegroundColor Red
    }

    # Block until cloudflared exits
    try { $proc.WaitForExit() } catch {}

    Write-Host "[!] Tunnel exited. Restarting in 5s..." -ForegroundColor Yellow
    Start-Sleep 5

    # Restart server too if it died
    if (-not (Test-PortListening -Port $ServerPort)) {
        Write-Host "[!] Server also down. Restarting..." -ForegroundColor Yellow
        Start-Process -FilePath ".\.venv\Scripts\python.exe" `
            -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","$ServerPort" `
            -RedirectStandardOutput $ServerLog `
            -RedirectStandardError "$ServerLog.err" `
            -WindowStyle Hidden
        Start-Sleep 5
    }
}
