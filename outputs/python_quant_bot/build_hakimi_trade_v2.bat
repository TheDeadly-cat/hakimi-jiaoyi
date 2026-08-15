@echo off
title Build Hakimi Trade v2
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_hakimi_trade_v2.ps1"
