$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
. "$root\find_python.ps1"

$logDir = Join-Path $root "runtime\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logPath = Join-Path $logDir "build_btc_daily_database.log"
Start-Transcript -Path $logPath -Append | Out-Null

try {
$python = Find-Python
if (-not $python) {
    Write-Host "Python was not found."
    Write-Host "Please run check_environment.bat first."
    Read-Host "Press Enter to close"
    exit 1
}

$outputDir = "Z:\jiaoyiguowangshuju"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

Write-Host "Using Python $($python.Version): $($python.Display)"
Write-Host "Building BTC daily price database in $outputDir"
Write-Host ""

& $python.Exe @($python.Args) build_btc_daily_database.py --output-dir $outputDir

Write-Host ""
Write-Host "Done. Files should be in $outputDir"
Write-Host "Log saved to $logPath"
Read-Host "Press Enter to close"
} catch {
    Write-Host ""
    Write-Host "Build failed:"
    Write-Host $_
    Write-Host "Log saved to $logPath"
    Read-Host "Press Enter to close"
    exit 1
} finally {
    Stop-Transcript | Out-Null
}
