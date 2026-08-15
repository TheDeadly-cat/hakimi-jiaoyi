@echo off
title Check BTC Daily Database
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ". '%~dp0find_python.ps1'; $p = Find-Python; if (-not $p) { Write-Host 'Python not found'; pause; exit 1 }; & $p.Exe @($p.Args) '%~dp0check_btc_daily_database.py'; pause"
