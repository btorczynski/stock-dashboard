@echo off
REM ============================================================
REM  Real-time Sector Heat Map dashboard - Windows launcher
REM  Double-click this file to install dependencies (first run)
REM  and start the dashboard.
REM ============================================================
cd /d "%~dp0"
title Sector Heat Map Dashboard

echo Installing / updating dependencies (first run can take a minute)...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Could not run "python". Make sure Python 3.9+ is installed and on your PATH.
  echo Download it from https://www.python.org/downloads/  ^(check "Add to PATH"^).
  pause
  exit /b 1
)

echo.
echo Starting dashboard... a browser tab will open at http://localhost:8765
start "" "http://localhost:8765"
python stock_dashboard.py

echo.
echo Dashboard stopped.
pause
