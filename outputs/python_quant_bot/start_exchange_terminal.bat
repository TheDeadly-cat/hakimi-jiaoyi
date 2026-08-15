@echo off
title Hakimi Trade v2
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_exchange_terminal.ps1"
