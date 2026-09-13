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
    echo  Get it from https://dotnet.microsoft.com/download  ^(SDK, not Runtime^)
    echo.
    pause
    exit /b 1
)

REM ----------------------------------------------------------------------
REM  Find every ATAS installation on the machine
REM ----------------------------------------------------------------------
echo  Looking for ATAS installations...
set "LIST=%TEMP%\atas_found.txt"
set "ULIST=%TEMP%\atas_uniq.txt"
del /q "%LIST%" "%ULIST%" 2>nul

call :scan "%ProgramFiles(x86)%"
call :scan "%ProgramFiles%"
call :scan "%ProgramW6432%"
call :scan "%LOCALAPPDATA%"
call :scan "%APPDATA%"

if not exist "%LIST%" (
    echo  Nothing in the usual places. Searching all drives, this takes a minute...
    for %%D in (C D E F G) do if exist "%%D:\" call :scan "%%D:\"
)

if not exist "%LIST%" (
    echo.
    echo  ATAS.Indicators.dll was not found anywhere.
    echo  If ATAS is on another drive, run:  dir /s /b X:\ATAS.Indicators.dll
    echo  and send me the folder it prints.
    echo.
    pause
    exit /b 1
)

sort /unique "%LIST%" /o "%ULIST%" 2>nul || copy /y "%LIST%" "%ULIST%" >nul

set N=0
echo.
echo  Found:
for /f "usebackq delims=" %%L in ("%ULIST%") do (
    set /a N+=1
    set "P!N!=%%L"
    echo     !N!.  %%L
)

if %N%==1 (
    set "ATASDIR=!P1!"
) else (
    echo.
    echo  Pick the ATAS you actually trade on.
    set /p "PICK=  Number [1]: "
    if "!PICK!"=="" set "PICK=1"
    set "ATASDIR=!P%PICK%!"
)

if not defined ATASDIR (
    echo  Invalid choice.
    pause
    exit /b 1
)
if "!ATASDIR:~-1!"=="\" set "ATASDIR=!ATASDIR:~0,-1!"

echo.
echo  Building against: !ATASDIR!

REM  ATAS X ships on .NET 10; the classic ATAS Platform build is on .NET 8.
REM  Try the likely one first, then the others. Each attempt wipes obj so the
REM  restore runs again for that framework -- without this the second attempt
REM  fails with NETSDK1005 on a stale assets file.
echo !ATASDIR! | find /i "ATAS X" >nul
if errorlevel 1 (
    set "TRY1=net8.0-windows"
    set "TRY2=net10.0-windows"
    set "TRY3=net9.0-windows"
) else (
    set "TRY1=net10.0-windows"
    set "TRY2=net9.0-windows"
    set "TRY3=net8.0-windows"
)

call :try "!TRY1!" && goto done
call :try "!TRY2!" && goto done
call :try "!TRY3!" && goto done

echo.
echo  ============================================================
echo   BUILD FAILED on all three .NET versions.
echo   ATAS: !ATASDIR!
echo   Send back the LAST error line only - the one starting CSC
echo   or ending in .cs(line,col). Ignore the MSB3277 warnings.
echo  ============================================================
echo.
pause
exit /b 1

:done
echo.
echo  ============================================================
echo   DONE. L2Recorder.dll is built and installed.
echo.
echo     1. Restart ATAS
echo     2. Open your NQ chart
echo     3. Ctrl+I, find "L2 Recorder (CSV)", add it
echo.
echo   It draws nothing on the chart. That is correct.
echo   Files appear in:  %USERPROFILE%\Documents\ATAS_Export\
echo  ============================================================
echo.
pause
exit /b 0

REM ----------------------------------------------------------------------
:scan
if "%~1"=="" goto :eof
if not exist "%~1" goto :eof
for /f "delims=" %%F in ('dir /s /b "%~1\ATAS.Indicators.dll" 2^>nul') do (
    >>"%LIST%" echo %%~dpF
)
goto :eof

:try
echo.
echo  --- %~1 ---
rd /s /q obj 2>nul
rd /s /q bin 2>nul
dotnet build -c Release -v minimal -p:AtasDir="!ATASDIR!" -p:TargetFramework=%~1
if errorlevel 1 exit /b 1
exit /b 0
