@echo off
cd /d "%~dp0"

echo.
echo  Shrink ATAS recordings for transfer
echo  ===================================
echo.
echo  Trims to the cash session and gzips. Nothing is re-recorded and
echo  nothing in the cash session is discarded.
echo.

if not exist "shrink.ps1" (
    echo  shrink.ps1 is not in this folder. Unzip all files together.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0shrink.ps1" %*
pause
