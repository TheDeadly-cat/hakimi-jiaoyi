@echo off
title Install Hakimi Trade v2 desktop dependencies
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_desktop_dependencies.ps1"
