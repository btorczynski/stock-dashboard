@echo off
REM ============================================================
REM  Runs the dashboard INDEFINITELY.
REM  If the server crashes or is killed, it restarts in 10s.
REM  Close this window (or Ctrl+C twice) to stop it for good.
REM ============================================================
cd /d "%~dp0"
title Market Pulse - running forever

echo Checking dependencies (one-time)...
python -m pip install -q -r requirements.txt

:loop
echo [%date% %time%] starting dashboard on http://localhost:8765
python stock_dashboard.py >> run_forever.log 2>&1
echo [%date% %time%] server exited - restarting in 10s... (Ctrl+C to stop)
timeout /t 10 /nobreak >nul
goto loop
