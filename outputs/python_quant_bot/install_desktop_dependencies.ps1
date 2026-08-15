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
& $python.Exe @($python.Args) -m pip install --upgrade pip
& $python.Exe @($python.Args) -m pip install -r requirements-desktop.txt

Write-Host ""
Write-Host "Desktop dependencies installed."
Write-Host "You can now run build_hakimi_trade_v2.bat."
Read-Host "Press Enter to close"
