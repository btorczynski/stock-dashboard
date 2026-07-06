#!/bin/bash
# ============================================================
#  Sector Heat Map dashboard - macOS / Linux launcher
#  Double-click on a Mac (first time: right-click > Open to get
#  past Gatekeeper). Installs dependencies, then starts the app.
# ============================================================
cd "$(dirname "$0")" || exit 1

echo "Installing / updating dependencies (first run can take a minute)..."
python3 -m pip install -r requirements.txt || {
  echo
  echo "Could not run python3. Install Python 3.9+ from https://www.python.org/downloads/"
  read -r -p "Press Enter to close..."
  exit 1
}

echo
echo "Starting dashboard... opening http://localhost:8765"
( sleep 2; open "http://localhost:8765" 2>/dev/null || xdg-open "http://localhost:8765" 2>/dev/null ) &
python3 stock_dashboard.py

echo
echo "Dashboard stopped."
read -r -p "Press Enter to close..."
