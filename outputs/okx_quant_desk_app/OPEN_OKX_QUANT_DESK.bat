@echo off
setlocal
cd /d "%~dp0"
if exist server.url del server.url

set "NODE_EXE=C:\Program Files\nodejs\node.exe"
if not exist "%NODE_EXE%" set "NODE_EXE=node"

start "OKX Quant Desk Server" /min cmd /k ""%NODE_EXE%" server.mjs"

for /l %%i in (1,1,10) do (
  if exist server.url goto open_url
  timeout /t 1 >nul
)

echo.
echo The service did not write server.url yet.
echo Please check the minimized "OKX Quant Desk Server" window for errors.
pause
exit /b 1

:open_url
set /p APP_URL=<server.url
start "" "%APP_URL%"
