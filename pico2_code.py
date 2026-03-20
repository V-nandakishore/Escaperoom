# ── Raspberry Pi Pico 2 - CircuitPython ─────────────────────────────────────
# Save this file as:  code.py  on your Pico 2
# Also copy audio.mp3 to the Pico 2 root folder
#
# Wiring:
#   Audio out → GP0 (PWM) → amplifier/speaker
#   Keypad    → GP2-GP9   (adjust KEYPAD_PINS below)
# ─────────────────────────────────────────────────────────────────────────────

import board
import busio
import os
import time
import usb_cdc
import storage
import audiomp3
import audiopwmio
import digitalio

# ── Config ───────────────────────────────────────────────────────────────────
PASSCODE_FILE = "/passcode.txt"
AUDIO_FILE    = "/audio.mp3"
AUDIO_PIN     = board.GP0      # PWM audio out pin — change to match your wiring

# ── Optional: Simple 4-button keypad on GP2..GP5 ─────────────────────────────
# Change or expand pins to match your keypad wiring
KEYPAD_PINS = [board.GP2, board.GP3, board.GP4, board.GP5,
               board.GP6, board.GP7, board.GP8, board.GP9]
KEYPAD_KEYS = ["1", "2", "3", "4", "5", "6", "7", "8"]

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_passcode():
    try:
        with open(PASSCODE_FILE, "r") as f:
            return f.read().strip()
    except Exception:
        return "1234"

def save_passcode(code):
    try:
        storage.remount("/", readonly=False)
        with open(PASSCODE_FILE, "w") as f:
            f.write(code)
        storage.remount("/", readonly=True)
        print(f"Passcode saved: {code}")
    except Exception as e:
        print(f"Save failed: {e}")

def play_audio():
    try:
        dac = audiopwmio.PWMAudioOut(AUDIO_PIN)
        with open(AUDIO_FILE, "rb") as f:
            mp3 = audiomp3.MP3Decoder(f)
            dac.play(mp3)
            while dac.playing:
                time.sleep(0.1)
        dac.deinit()
        print("Audio played.")
    except Exception as e:
        print(f"Audio error: {e}")

# ── Keypad setup ──────────────────────────────────────────────────────────────
keys = []
for pin in KEYPAD_PINS:
    try:
        k = digitalio.DigitalInOut(pin)
        k.direction = digitalio.Direction.INPUT
        k.pull = digitalio.Pull.UP
        keys.append(k)
    except Exception:
        keys.append(None)

def read_keypad():
    """Returns key character if pressed, else None."""
    for i, k in enumerate(keys):
        if k and not k.value:   # active LOW (pull-up)
            time.sleep(0.05)    # debounce
            if not k.value:
                return KEYPAD_KEYS[i]
    return None

# ── Serial (USB) ──────────────────────────────────────────────────────────────
serial = usb_cdc.data  # usb_cdc.data is the second USB serial port

# ── Main ─────────────────────────────────────────────────────────────────────
passcode = load_passcode()
entered  = ""
print(f"Escape Room Pico ready. Passcode loaded ({len(passcode)} chars).")

while True:
    # ── Listen for passcode updates from Game Master GUI ──────────────────
    if serial and serial.in_waiting:
        try:
            line = serial.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("PASSCODE:"):
                new_code = line.split(":", 1)[1].strip()
                if new_code:
                    save_passcode(new_code)
                    passcode = new_code
                    serial.write(b"OK\n")
                    print(f"Passcode updated via GM: {new_code}")
        except Exception as e:
            print(f"Serial error: {e}")

    # ── Read keypad ───────────────────────────────────────────────────────
    key = read_keypad()
    if key:
        entered += key
        print(f"Key: {key}  |  Entered: {'*' * len(entered)}")
        time.sleep(0.3)   # simple debounce delay

        # Check after every keypress once length matches
        if len(entered) >= len(passcode):
            if entered[-len(passcode):] == passcode:
                print("CORRECT! Playing audio.")
                entered = ""
                play_audio()
            elif len(entered) > len(passcode) + 4:
                # Reset buffer if too many wrong keys
                entered = ""
                print("Buffer reset.")

    time.sleep(0.05)
