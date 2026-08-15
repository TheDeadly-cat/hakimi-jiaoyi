$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
. "$root\find_python.ps1"

$logDir = Join-Path $root "runtime\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logPath = Join-Path $logDir "exchange_terminal.log"
Start-Transcript -Path $logPath -Append | Out-Null

try {
    $python = Find-Python
    if (-not $python) {
        Write-Host "Python was not found. Please run check_environment.bat first."
        Read-Host "Press Enter to close"
        exit 1
    }

    Write-Host "Using Python $($python.Version): $($python.Display)"
    Write-Host "Starting exchange terminal at http://127.0.0.1:8765"
    Write-Host "Log saved to $logPath"
    Write-Host ""

    & $python.Exe @($python.Args) exchange_terminal\server.py --host 127.0.0.1 --port 8765
} catch {
    Write-Host ""
    Write-Host "Exchange terminal failed:"
    Write-Host $_
    Write-Host "Log saved to $logPath"
    Read-Host "Press Enter to close"
    exit 1
} finally {
    Stop-Transcript | Out-Null
}
