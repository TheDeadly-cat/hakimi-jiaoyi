@echo off
title Hakimi Trade v2
cd /d "%~dp0python_quant_bot"
powershell -NoProfile -ExecutionPolicy Bypass -Command ". .\find_python.ps1; $py = Find-Python; if (-not $py) { Write-Host 'Python not found. Run check_environment.bat first.'; pause; exit 1 }; & $py.Exe @($py.Args) hakimi_trade_desktop.py"
