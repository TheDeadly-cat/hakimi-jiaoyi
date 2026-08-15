$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
. "$root\find_python.ps1"

$python = Find-Python
if (-not $python) {
    Write-Host "Python was not found."
    Write-Host "Please reinstall Python 3.14 and tick 'Add python.exe to PATH', or restart Codex/Windows after installation."
    $manualPath = Read-Host "If you know python.exe path, paste it here; otherwise press Enter"
    if (-not [string]::IsNullOrWhiteSpace($manualPath) -and (Test-Path $manualPath)) {
        $python = Test-PythonCommand -Exe $manualPath
    }
}

if (-not $python) {
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "Using Python $($python.Version): $($python.Display)"
& $python.Exe @($python.Args) -m pip install --upgrade pip
& $python.Exe @($python.Args) -m pip install -r requirements-core.txt

Write-Host ""
Write-Host "Core dependencies installed."
Write-Host "Optional research dependencies are listed in requirements.txt."

Write-Host ""
Write-Host "Dependencies installed. You can now run start_dashboard.bat."
Read-Host "Press Enter to close"
