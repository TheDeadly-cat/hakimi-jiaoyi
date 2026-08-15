$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
. "$root\find_python.ps1"

$python = Find-Python
if (-not $python) {
    Write-Host "Python was not found. Run check_environment.bat first."
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "Using Python $($python.Version): $($python.Display)"

try {
    & $python.Exe @($python.Args) -m PyInstaller --version | Out-Null
} catch {
    Write-Host "PyInstaller is not available. Run install_desktop_dependencies.bat first."
    Read-Host "Press Enter to close"
    exit 1
}

$addStatic = "exchange_terminal\static;exchange_terminal\static"
$addServices = "exchange_terminal\services;exchange_terminal\services"

& $python.Exe @($python.Args) -m PyInstaller `
    --noconfirm `
    --clean `
    --name "HakimiTradeV2" `
    --add-data $addStatic `
    --add-data $addServices `
    hakimi_trade_desktop.py

Write-Host ""
Write-Host "Build finished. Check:"
Write-Host "$root\dist\HakimiTradeV2"
Read-Host "Press Enter to close"
