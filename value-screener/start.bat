@echo off
title US Value Screener
cd /d "%~dp0"

echo.
echo  US Value Screener
echo  =================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not on PATH.
    echo Install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

if not exist "data\screen_results.json" (
    echo Seeding US data...
    python seed_data.py
)

if not exist "data\screen_results_hk.json" (
    echo Seeding HK data ^(first run takes a few minutes^)...
    python seed_hk_data.py
)

echo.
echo Stopping any old servers on port 5000/5001...
powershell -Command "Get-NetTCPConnection -LocalPort 5000,5001 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
timeout /t 2 /nobreak >nul

echo.
echo Starting server — browser will open automatically.
echo   US page:  http://127.0.0.1:PORT/
echo   HK page:  http://127.0.0.1:PORT/hk
echo Keep this window open while using the site.
echo Press Ctrl+C to stop.
echo.

python run.py
pause