@echo off
REM Build a single-file Windows executable: dist\WireGuardClient.exe
REM Run this on Windows with Python 3.10+ installed.

setlocal
cd /d "%~dp0"

echo [1/3] Creating virtual environment...
if not exist .venv (
    python -m venv .venv || goto :error
)
call .venv\Scripts\activate.bat || goto :error

echo [2/3] Installing dependencies...
python -m pip install --upgrade pip || goto :error
python -m pip install -r requirements.txt pyinstaller || goto :error

echo [3/3] Building single-file exe...
pyinstaller --clean --noconfirm wireguard-client.spec || goto :error

echo.
echo Done. Output: dist\WireGuardClient.exe
goto :eof

:error
echo.
echo Build failed with error %errorlevel%.
exit /b %errorlevel%
