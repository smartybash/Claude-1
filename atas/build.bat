@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo  L2 Recorder - build and install
echo  ================================
echo.

if not exist "L2Recorder.csproj" (
    echo  L2Recorder.csproj is not in this folder.
    echo  Unzip all four files together, then run build.bat from that folder.
    echo.
    pause
    exit /b 1
)

where dotnet >nul 2>&1
if errorlevel 1 (
    echo  The .NET SDK is not installed.
    echo.
    echo  Download it from https://dotnet.microsoft.com/download
    echo  Pick the SDK, not the Runtime, version 8.0 or newer.
    echo  Then close this window, reopen it, and run this file again.
    echo.
    pause
    exit /b 1
)

REM ----------------------------------------------------------------------
REM  Find ATAS.Indicators.dll. Likely folders first, then the whole drive.
REM ----------------------------------------------------------------------
echo  Looking for your ATAS installation...
set "ATASDIR="

call :find "%LOCALAPPDATA%"
call :find "%APPDATA%"
call :find "%ProgramFiles%"
call :find "%ProgramFiles(x86)%"
call :find "%ProgramW6432%"
call :find "%USERPROFILE%\Documents\ATAS"
call :find "%USERPROFILE%"

if not defined ATASDIR (
    echo  Not in the usual places. Searching all drives, this takes a minute...
    for %%D in (C D E F G) do (
        if not defined ATASDIR if exist "%%D:\" call :find "%%D:\"
    )
)

if not defined ATASDIR (
    echo.
    echo  ============================================================
    echo   ATAS.Indicators.dll was not found anywhere on this machine.
    echo.
    echo   Is ATAS actually installed on this PC? If it is installed
    echo   on a network drive or a drive letter beyond G, open a
    echo   command prompt and run:
    echo.
    echo     dir /s /b X:\ATAS.Indicators.dll
    echo.
    echo   then send me the folder it prints.
    echo  ============================================================
    echo.
    pause
    exit /b 1
)

REM strip the trailing backslash that %%~dpF leaves behind
if "!ATASDIR:~-1!"=="\" set "ATASDIR=!ATASDIR:~0,-1!"

echo  Found ATAS: !ATASDIR!
echo.

REM ----------------------------------------------------------------------
REM  Build. ATAS 7.x runs on .NET 8, newer builds on 9 or 10, so try each.
REM ----------------------------------------------------------------------
echo  Building against .NET 8...
echo.
dotnet build -c Release -v minimal -p:AtasDir="!ATASDIR!"
if not errorlevel 1 goto done

echo.
echo  Retrying on .NET 10...
echo.
dotnet build -c Release -v minimal -p:AtasDir="!ATASDIR!" -p:TargetFramework=net10.0-windows
if not errorlevel 1 goto done

echo.
echo  Retrying on .NET 9...
echo.
dotnet build -c Release -v minimal -p:AtasDir="!ATASDIR!" -p:TargetFramework=net9.0-windows
if not errorlevel 1 goto done

echo.
echo  ============================================================
echo   BUILD FAILED
echo.
echo   ATAS was found at:
echo     !ATASDIR!
echo.
echo   So this is now a compiler error in the C# itself.
echo   Copy everything above this line and send it back.
echo  ============================================================
echo.
pause
exit /b 1

:done
echo.
echo  ============================================================
echo   DONE. L2Recorder.dll is built and installed.
echo.
echo   Next:
echo     1. Restart ATAS
echo     2. Open your NQ chart
echo     3. Ctrl+I, find "L2 Recorder (CSV)", add it
echo.
echo   It draws nothing on the chart. That is correct.
echo   Files appear in:
echo     %USERPROFILE%\Documents\ATAS_Export\
echo  ============================================================
echo.
pause
exit /b 0

REM ----------------------------------------------------------------------
:find
if defined ATASDIR goto :eof
if "%~1"=="" goto :eof
if not exist "%~1" goto :eof
for /f "delims=" %%F in ('dir /s /b "%~1\ATAS.Indicators.dll" 2^>nul') do (
    set "ATASDIR=%%~dpF"
    goto :eof
)
goto :eof
