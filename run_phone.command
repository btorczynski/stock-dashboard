#!/bin/bash
# ============================================================
#  Sector Heat Map - PHONE / LAN mode (macOS / Linux)
#  Serves the dashboard to other devices on your Wi-Fi so you
#  can open it on your iPhone. The console prints the exact
#  http://<your-ip>:8765 address to type on the phone.
#  Only use on a trusted network (anyone on the Wi-Fi can view it).
# ============================================================
cd "$(dirname "$0")" || exit 1
export DASH_HOST=0.0.0.0

echo "Installing / updating dependencies..."
python3 -m pip install -r requirements.txt || { echo "Install Python 3.9+ first."; read -r -p "Press Enter..."; exit 1; }

echo
echo "Starting in PHONE/LAN mode. On your iPhone (same Wi-Fi), open the"
echo "http://<ip>:8765 address shown just below this line:"
python3 stock_dashboard.py
read -r -p "Press Enter to close..."
