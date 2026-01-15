@echo off
echo ==========================================
echo NetMonitor Pro - Windows Executable Builder
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo.
echo Building executable...
python build_exe.py

echo.
echo ==========================================
echo Build process complete!
echo ==========================================
echo.
echo Your executable is in the 'dist' folder.
echo Copy both NetMonitorPro.exe and config.json to your desired location.
echo.
pause
