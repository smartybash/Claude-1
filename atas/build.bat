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

REM ----------------------------------------------------------------------
REM  The ATAS that is actually traded on. Passed as argument 1 to override;
REM  otherwise the classic ATAS Platform, never ATAS X, which is a separate
REM  product on a different .NET runtime.
REM ----------------------------------------------------------------------
set "ATASDIR=C:\Program Files (x86)\ATAS Platform"
if not "%~1"=="" set "ATASDIR=%~1"

if not exist "!ATASDIR!\ATAS.Indicators.dll" (
    echo  ATAS.Indicators.dll not in !ATASDIR!
    echo  Searching for it...
    set "FOUND="
    for %%R in ("%ProgramFiles(x86)%" "%ProgramFiles%" "%LOCALAPPDATA%" "%APPDATA%") do (
        if not defined FOUND if exist "%%~R" (
            for /f "delims=" %%F in ('dir /s /b "%%~R\ATAS.Indicators.dll" 2^>nul') do (
                if not defined FOUND (
                    echo %%~dpF | find /i "ATAS X" >nul || set "FOUND=%%~dpF"
                )
            )
        )
    )
    if not defined FOUND (
        echo  Could not find it. Run:  dir /s /b C:\ATAS.Indicators.dll
        echo  then:  build.bat "the folder it prints"
        pause
        exit /b 1
    )
    set "ATASDIR=!FOUND!"
)
if "!ATASDIR:~-1!"=="\" set "ATASDIR=!ATASDIR:~0,-1!"

echo  ATAS: !ATASDIR!

REM  Framework must match the runtime that ATAS itself is built on, so try
REM  each in turn. obj and bin are wiped between attempts because changing
REM  TargetFramework alone leaves a stale assets file and the next build
REM  dies on NETSDK1005 rather than on anything real.
call :try net8.0-windows  && goto done
call :try net10.0-windows && goto done
call :try net9.0-windows  && goto done
call :try net7.0-windows  && goto done
call :try net6.0-windows  && goto done

echo.
echo  ============================================================
echo   BUILD FAILED on every framework.
echo   ATAS: !ATASDIR!
echo   Send back only the last line starting with CSC, or the one
echo   ending in .cs(line,col). Ignore every MSB3277 warning.
echo  ============================================================
pause
exit /b 1

:done
echo.
echo  ============================================================
echo   DONE. L2Recorder.dll installed to
echo   %USERPROFILE%\Documents\ATAS\Indicators
echo.
echo     1. Restart ATAS
echo     2. Open the NQ chart
echo     3. Ctrl+I, add "L2 Recorder (CSV)"
echo.
echo   It draws nothing. Files land in:
echo   %USERPROFILE%\Documents\ATAS_Export\
echo  ============================================================
pause
exit /b 0

:try
echo.
echo  --- trying %~1 ---
rd /s /q obj 2>nul
rd /s /q bin 2>nul
dotnet build -c Release -v minimal -p:AtasDir="!ATASDIR!" -p:TargetFramework=%~1
if errorlevel 1 exit /b 1
exit /b 0
