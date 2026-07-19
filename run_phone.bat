@echo off
REM ============================================================
REM  Sector Heat Map - PHONE / LAN mode (Windows)
REM  Serves the dashboard to other devices on your Wi-Fi so you
REM  can open it on your iPhone. The console prints the exact
REM  http://<your-ip>:8765 address to type on the phone.
REM  Only use on a trusted network (anyone on the Wi-Fi can view it).
REM ============================================================
cd /d "%~dp0"
set DASH_HOST=0.0.0.0
title Sector Heat Map (Phone/LAN mode)

echo Installing / updating dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Install Python 3.9+ from https://www.python.org/downloads/ ^(check "Add to PATH"^).
  pause
  exit /b 1
)

echo.
echo Starting in PHONE/LAN mode. On your iPhone (same Wi-Fi), open the
echo http://<ip>:8765 address shown just below:
python stock_dashboard.py
pause
