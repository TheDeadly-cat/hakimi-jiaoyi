@echo off
title Build BTC Daily Database
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_btc_daily_database.ps1"
