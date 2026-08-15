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
& $python.Exe @($python.Args) -m streamlit --version
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Streamlit is not installed for this Python."
    Write-Host "Please run install_dependencies.bat first."
    Read-Host "Press Enter to close"
    exit 1
}

& $python.Exe @($python.Args) -m streamlit run dashboard_app.py --server.address 127.0.0.1 --server.port 8501
Read-Host "Press Enter to close"
