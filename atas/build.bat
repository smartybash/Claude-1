@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo  L2 Recorder - build and install
echo  ================================
echo.

where dotnet >nul 2>&1
if errorlevel 1 (
    echo  The .NET SDK is not installed.
    echo.
    echo  Download it from https://dotnet.microsoft.com/download
    echo  Pick the SDK - not the Runtime - and take version 8.0 or newer.
    echo  Then close this window, reopen it, and run this file again.
    echo.
    pause
    exit /b 1
)

echo  Building against .NET 8...
dotnet build -c Release -v minimal
if not errorlevel 1 goto done

echo.
echo  .NET 8 build failed. Some ATAS builds run on .NET 10 - retrying...
echo.
dotnet build -c Release -v minimal -p:TargetFramework=net10.0-windows
if not errorlevel 1 goto done

echo.
echo  ============================================================
echo   BUILD FAILED
echo.
echo   Copy everything above this line and send it back.
echo   The error text says exactly what needs changing.
echo.
echo   If it says ATAS.Indicators.dll could not be found, locate
echo   your ATAS install folder and run instead:
echo.
echo     dotnet build -c Release -p:AtasDir="C:\Your\Path\ATAS Platform"
echo  ============================================================
echo.
pause
exit /b 1

:done
echo.
echo  ============================================================
echo   DONE. L2Recorder.dll is installed.
echo.
echo   Next:
echo     1. Restart ATAS
echo     2. Open your NQ chart
echo     3. Indicators (Ctrl+I) - find "L2 Recorder (CSV)" - add it
echo.
echo   It draws nothing. Files appear in:
echo     %USERPROFILE%\Documents\ATAS_Export\
echo  ============================================================
echo.
pause
