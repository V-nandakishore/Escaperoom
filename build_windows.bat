@echo off
echo ============================================
echo  Escape Room GM - Windows Build Script
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install from https://python.org
    pause & exit /b 1
)

echo [1/3] Installing dependencies...
pip install pyinstaller gtts pygame pyserial --quiet
if errorlevel 1 (
    echo ERROR: pip install failed.
    pause & exit /b 1
)

echo [2/3] Building executable...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "EscapeRoomGM" ^
    --hidden-import gtts ^
    --hidden-import pygame ^
    --hidden-import serial ^
    --hidden-import serial.tools.list_ports ^
    --hidden-import pygame.mixer ^
    --hidden-import talker ^
    --collect-all gtts ^
    --collect-all pygame ^
    escape_room_gm.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause & exit /b 1
)

echo [3/3] Done!
echo.
echo Your executable is at:  dist\EscapeRoomGM.exe
echo.
echo Share the EscapeRoomGM.exe file — no Python needed on target machine!
echo The config.json and audio.wav will be created next to the .exe on first run.
echo.
pause

