# 🔐 Escape Room Game Master Controller

## What's in this folder

| File | Purpose |
|---|---|
| `escape_room_gm.py` | Main application source |
| `talker.py` | Pico serial helper used by the app |
| `build_windows.bat` | One-click build for Windows → `.exe` |
| `build_mac_linux.sh` | One-click build for Mac/Linux → app |

---

## ► Build a shareable executable (do this ONCE on your machine)

### Windows
1. Make sure Python 3.10+ is installed from https://python.org
2. Double-click **`build_windows.bat`**
3. Wait ~2 minutes
4. Find your app at **`dist/EscapeRoomGM.exe`**
5. Share that single `.exe` file — no Python needed on the target machine!

### Mac / Linux
```bash
chmod +x build_mac_linux.sh
./build_mac_linux.sh
# App at: dist/EscapeRoomGM  (or .app on Mac)
```

---

## ► Using the App

When you open `EscapeRoomGM.exe` the GUI launches immediately.

| Button | What it does |
|---|---|
| 🔑 **Edit Passcode** | Change the unlock code. Automatically syncs to Pico 2 if connected |
| 🎙 **Edit Audio** | Type any text → converted to MP3 via Google TTS and saved |
| 🎮 **Test Game** | Enter the passcode to trigger audio playback |

**Settings are saved automatically** — passcode and audio text persist between sessions in `config.json` next to the `.exe`.

> ⚠️ **Edit Audio requires internet** (Google TTS). Once the MP3 is generated it works fully offline.

---

## ► Raspberry Pi Pico 2 Setup

### Step 1 — Flash CircuitPython
Download from https://circuitpython.org/board/raspberry_pi_pico2 and drag onto the Pico.

### Step 2 — Copy firmware/audio to Pico
On the Pico USB drive root:
- Save your Pico firmware as **`code.py`** (this is firmware on the Pico, not part of the GM EXE build)
- Copy generated **`audio.mp3`** (or adapt firmware if using WAV)

### Step 3 — Wiring
```
Pico GP0  ──→  Audio amplifier IN  ──→  Speaker
```
Adjust `AUDIO_PIN` in `code.py` if using a different pin.

For keypad, connect buttons to GP2–GP9 (or edit `KEYPAD_PINS` in `code.py`).

### Step 4 — Connect
Plug Pico into the GM PC via USB. The app auto-detects it and shows **◉ PICO: COMx** in the header. Passcode changes are synced instantly.

---

## Files created at runtime (next to the .exe)

| File | Contents |
|---|---|
| `config.json` | Current passcode + audio text |
| `audio.wav` | Generated TTS audio |
# Escaperoom
