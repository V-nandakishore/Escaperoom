#!/bin/bash
echo "============================================"
echo " Escape Room GM - Mac/Linux Build Script"
echo "============================================"
echo

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install from https://python.org"
    exit 1
fi

echo "[1/3] Installing dependencies..."
pip3 install pyinstaller gtts pygame pyserial --quiet || {
    echo "ERROR: pip install failed."
    exit 1
}

echo "[2/3] Building app..."
pyinstaller \
    --onefile \
    --windowed \
    --name "EscapeRoomGM" \
    --hidden-import gtts \
    --hidden-import pygame \
    --hidden-import serial \
    --hidden-import serial.tools.list_ports \
    --hidden-import pygame.mixer \
    --collect-all gtts \
    --collect-all pygame \
    escape_room_gm.py

if [ $? -ne 0 ]; then
    echo "ERROR: PyInstaller build failed."
    exit 1
fi

echo "[3/3] Done!"
echo
echo "Your app is at:  dist/EscapeRoomGM"
echo "(On Mac it will be dist/EscapeRoomGM.app)"
echo
echo "Share the file — no Python needed on target machine!"
