@echo off
title Hakimi Trade v2 Electron
cd /d "%~dp0hakimi_trade_electron"
set "npm_config_cache=%cd%\.npm-cache"
set "electron_config_cache=%cd%\.electron-cache"
set "ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/"
set "ELECTRON_GET_NO_PROGRESS=1"
if not exist node_modules\electron\dist\electron.exe (
  echo Electron dependencies are not installed.
  echo Running npm install now...
  call npm.cmd install --no-audit --no-fund
  if errorlevel 1 (
    echo Failed to install Electron dependencies.
    pause
    exit /b 1
  )
)
if exist node_modules\electron\path.txt (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.IO.File]::WriteAllText((Join-Path (Get-Location) 'node_modules\electron\path.txt'), 'electron.exe', [System.Text.Encoding]::ASCII)"
)
call npm.cmd start
