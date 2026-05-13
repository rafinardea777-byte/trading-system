# DB Backup Script - יומי, עם rotation (שומר 14 גיבויים אחרונים)
# הפעלה ידנית: powershell -File scripts\backup_db.ps1
# הפעלה אוטומטית: Task Scheduler - ב-02:00 בלילה כל יום

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot\..

$BackupDir = "$env:USERPROFILE\Desktop\TradingPro-Backups"
$DbFile = "data\trading.db"
$Timestamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$BackupName = "trading_$Timestamp.db.gz"
$KeepDays = 14

# יצירת תיקיית גיבוי אם לא קיימת
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
}

if (-not (Test-Path $DbFile)) {
    Write-Host "[!] DB file not found at $DbFile"
    exit 1
}

# יצירת backup דחוס (gzip)
try {
    $sourcePath = (Resolve-Path $DbFile).Path
    $destPath = Join-Path $BackupDir $BackupName

    $source = [System.IO.File]::OpenRead($sourcePath)
    $dest = [System.IO.File]::Create($destPath)
    $gzip = New-Object System.IO.Compression.GzipStream($dest, [System.IO.Compression.CompressionLevel]::Optimal)
    $source.CopyTo($gzip)
    $gzip.Close()
    $dest.Close()
    $source.Close()

    $origSize = (Get-Item $sourcePath).Length / 1KB
    $newSize = (Get-Item $destPath).Length / 1KB
    Write-Host "[+] Backup OK: $BackupName ($([math]::Round($newSize,1)) KB from $([math]::Round($origSize,1)) KB)"
} catch {
    Write-Host "[!] Backup failed: $_"
    exit 1
}

# Rotation - מחיקת גיבויים ישנים מ-14 ימים
$cutoff = (Get-Date).AddDays(-$KeepDays)
$deleted = 0
Get-ChildItem -Path $BackupDir -Filter "trading_*.db.gz" | Where-Object {
    $_.LastWriteTime -lt $cutoff
} | ForEach-Object {
    Remove-Item $_.FullName -Force
    $deleted++
}

if ($deleted -gt 0) {
    Write-Host "[+] Rotated: deleted $deleted backups older than $KeepDays days"
}

# סיכום
$totalBackups = (Get-ChildItem -Path $BackupDir -Filter "trading_*.db.gz" | Measure-Object).Count
$totalSize = (Get-ChildItem -Path $BackupDir -Filter "trading_*.db.gz" | Measure-Object Length -Sum).Sum / 1MB
Write-Host "[i] Total backups: $totalBackups files, $([math]::Round($totalSize,2)) MB"
Write-Host "[i] Location: $BackupDir"
