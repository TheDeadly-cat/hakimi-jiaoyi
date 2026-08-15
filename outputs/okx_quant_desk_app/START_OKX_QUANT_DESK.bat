@echo off
setlocal
cd /d "%~dp0"
echo Starting OKX Quant Desk...
set "NODE_EXE=C:\Program Files\nodejs\node.exe"
if not exist "%NODE_EXE%" set "NODE_EXE=node"
"%NODE_EXE%" server.mjs
pause
