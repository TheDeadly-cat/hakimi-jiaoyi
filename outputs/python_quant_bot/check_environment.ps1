$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
. "$root\find_python.ps1"

Write-Host "Python Quant Bot environment check"
Write-Host "Project: $root"
Write-Host ""

$python = Find-Python
if (-not $python) {
    Write-Host "Python: NOT FOUND"
    Write-Host "Fix: restart Codex/Windows, or reinstall Python 3.14 with 'Add python.exe to PATH'."
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "Python: FOUND"
Write-Host "Version: $($python.Version)"
Write-Host "Command: $($python.Display)"
Write-Host ""

Write-Host "Checking packages..."
foreach ($package in @("streamlit", "pandas", "numpy", "ccxt", "plotly")) {
    & $python.Exe @($python.Args) -m pip show $package >$null 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "${package}: OK"
    } else {
        Write-Host "${package}: MISSING"
    }
}

Write-Host ""
Write-Host "If anything is MISSING, run install_dependencies.bat."
Read-Host "Press Enter to close"
