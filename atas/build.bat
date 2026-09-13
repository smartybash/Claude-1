@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo  L2 Recorder - build and install
echo  ================================
echo.

if not exist "L2Recorder.csproj" (
    echo  L2Recorder.csproj is not in this folder.
    echo  Unzip all four files together and run build.bat from that folder.
    pause
    exit /b 1
)

where dotnet >nul 2>&1
if errorlevel 1 (
    echo  The .NET SDK is not installed.
    echo  Get it from https://dotnet.microsoft.com/download  ^(SDK, not Runtime^)
    pause
    exit /b 1
)

REM  ATAS Platform, not ATAS X. Override by passing the folder as argument 1.
set "ATASDIR=C:\Program Files (x86)\ATAS Platform"
if not "%~1"=="" set "ATASDIR=%~1"

if not exist "!ATASDIR!\ATAS.Indicators.dll" (
    echo  ATAS.Indicators.dll not found in !ATASDIR!
    echo  Run:  dir /s /b C:\ATAS.Indicators.dll
    echo  then: build.bat "the folder it prints"
    pause
    exit /b 1
)
if "!ATASDIR:~-1!"=="\" set "ATASDIR=!ATASDIR:~0,-1!"

echo  ATAS: !ATASDIR!
echo  Framework: net8.0-windows
echo.

rd /s /q obj 2>nul
rd /s /q bin 2>nul
dotnet build -c Release -v minimal -p:AtasDir="!ATASDIR!"

if errorlevel 1 (
    echo.
    echo  ============================================================
    echo   BUILD FAILED
    echo   Send back only the lines containing "error CS" - they name
    echo   the file, line and problem. Ignore every MSB3277 warning.
    echo  ============================================================
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo   DONE. Installed:
dir /b /t:w "%USERPROFILE%\Documents\ATAS\Indicators\L2Recorder.dll" 2>nul
for %%F in ("%USERPROFILE%\Documents\ATAS\Indicators\L2Recorder.dll") do echo   %%~tF   %%~fF
echo.
echo   The timestamp above must be RIGHT NOW. If it is older, ATAS
echo   is holding the old file open - close ATAS and run this again.
echo.
echo     1. Restart ATAS
echo     2. Open the NQ chart
echo     3. Ctrl+I, add "L2 Recorder (CSV)"
echo.
echo   It draws nothing on the chart. Instead a folder named
echo   ATAS_Export appears ON YOUR DESKTOP the moment you add it.
echo   Open _status.txt inside it.
echo  ============================================================
pause
exit /b 0
