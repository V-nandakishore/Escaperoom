#!/usr/bin/env python3
"""
Escape Room Game Master Controller
Packaged with PyInstaller → single .exe / app bundle
No external installs needed by end user.
"""

import tkinter as tk
from tkinter import messagebox
import json, os, sys, threading, datetime, time
import subprocess

# ── Resolve base path (works both in dev and PyInstaller bundle) ─────────────
def resource_path(rel):
    """Get absolute path — works for dev and PyInstaller --onefile."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)

def data_path(filename):
    """Writable path next to the exe (or script) for user data."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)

# ── Bundled deps live inside the package ────────────────────────────────────
CONFIG_FILE = data_path("config.json")
AUDIO_FILE  = data_path("audio.wav")

DEFAULT_CONFIG = {
    "passcode": "1234",
    "audio_text": "Congratulations! You have escaped. Well done!",
}

# ── Config helpers ────────────────────────────────────────────────────────────
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

# ── TTS ───────────────────────────────────────────────────────────────────────
def _ps_quote(s):
    return s.replace("'", "''")

def generate_audio(text, callback=None):
    try:
        # Synthesize directly to WAV (Windows PowerShell TTS)
        script = f"""
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SetOutputToWaveFile('{_ps_quote(AUDIO_FILE)}')
$synth.Speak('{_ps_quote(text)}')
$synth.Dispose()
"""
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            check=True,
            capture_output=True,
            text=True,
        )
        if callback:
            callback(True, None)
    except Exception as e:
        if callback:
            callback(False, str(e))

# ── Audio playback ────────────────────────────────────────────────────────────
_mixer_ready = False

def init_mixer():
    global _mixer_ready
    if not _mixer_ready:
        try:
            import pygame
            pygame.mixer.init()
            _mixer_ready = True
        except Exception:
            pass

def play_audio():
    try:
        import pygame
        init_mixer()
        if os.path.exists(AUDIO_FILE):
            pygame.mixer.music.load(AUDIO_FILE)
            pygame.mixer.music.play()
            return True
    except Exception:
        pass
    return False

# ── Pico serial ───────────────────────────────────────────────────────────────
def find_pico_ports():
    try:
        import serial.tools.list_ports
        matches = []
        for p in serial.tools.list_ports.comports():
            hwid = (p.hwid or "").lower()
            desc = (p.description or "").lower()
            if "2e8a" in hwid or "pico" in desc or "circuitpython" in desc:
                matches.append(p.device)
        return matches
    except Exception:
        return []

def find_pico_port():
    ports = find_pico_ports()
    return ports[0] if ports else None

def _talker_sync(passcode, port):
    try:
        from talker import Talker
        t = Talker(port=port, baudrate=115200, timeout=2)
        t.change_code(passcode)
        t.close()
        return True, f"{port} (talker)"
    except Exception as e:
        return False, str(e)

def _line_sync(passcode, port):
    try:
        import serial
        with serial.Serial(port, 9600, timeout=2) as s:
            s.write(f"PASSCODE:{passcode}\n".encode("utf-8"))
            s.flush()
        return True, f"{port} (PASSCODE)"
    except Exception as e:
        return False, str(e)

def send_to_pico(passcode, port=None):
    ports = [port] if port else find_pico_ports()
    if not ports:
        return False, "Pico not found"

    errors = []
    for port_try in ports:
        ok, msg = _talker_sync(passcode, port_try)
        if ok:
            return True, msg

        ok2, msg2 = _line_sync(passcode, port_try)
        if ok2:
            return True, msg2
        errors.append(f"{port_try}: talker={msg}; passcode={msg2}")

    return False, " | ".join(errors)

# ═════════════════════════════════════════════════════════════════════════════
# GUI
# ═════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    # Palette
    BG      = "#0b0c10"
    CARD    = "#13141a"
    BORDER  = "#252530"
    RED     = "#e63946"
    AMBER   = "#ffb703"
    TEAL    = "#2ec4b6"
    FG      = "#f0f0f0"
    MUTED   = "#5a5a6e"

    FT      = ("Georgia", 24, "bold")
    FS      = ("Georgia", 10, "italic")
    FB      = ("Courier New", 12, "bold")
    FM      = ("Courier New", 11)
    FX      = ("Courier New", 9)

    def __init__(self):
        super().__init__()
        self.cfg       = load_config()
        self.pico_port = None
        self._running  = True

        self.title("Escape Room — Game Master")
        self.geometry("620x560")
        self.resizable(False, False)
        self.configure(bg=self.BG)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self._build()
        threading.Thread(target=self._monitor_pico, daemon=True).start()

        # Pre-generate audio if wav missing
        if not os.path.exists(AUDIO_FILE):
            self._log("Generating default audio…")
            threading.Thread(
                target=generate_audio,
                args=(self.cfg["audio_text"], lambda ok, err: self.after(0, self._audio_done, ok, err)),
                daemon=True
            ).start()
        else:
            self._log("System ready.")

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        # ── Header
        hdr = tk.Frame(self, bg=self.BG)
        hdr.pack(fill="x", padx=36, pady=(28, 0))
        tk.Label(hdr, text="🔐  GAME MASTER", font=self.FT,
                 bg=self.BG, fg=self.RED).pack(side="left")
        self.pico_dot = tk.Label(hdr, text="◉ PICO …", font=self.FX,
                                 bg=self.BG, fg=self.MUTED)
        self.pico_dot.pack(side="right", pady=4)

        tk.Label(self, text="Escape Room Controller  v1.0",
                 font=self.FS, bg=self.BG, fg=self.MUTED).pack(anchor="w", padx=36)

        self._hr()

        # ── Status card
        card = self._card(self)
        card.pack(fill="x", padx=36, pady=(0, 16))
        inner = tk.Frame(card, bg=self.CARD)
        inner.pack(fill="x", padx=14, pady=10)

        tk.Label(inner, text="PASSCODE", font=self.FX,
                 bg=self.CARD, fg=self.MUTED).grid(row=0, column=0, sticky="w")
        self.pc_lbl = tk.Label(inner, text=self._mask(self.cfg["passcode"]),
                               font=self.FM, bg=self.CARD, fg=self.AMBER)
        self.pc_lbl.grid(row=1, column=0, sticky="w", padx=(0, 36))

        tk.Label(inner, text="AUDIO TEXT", font=self.FX,
                 bg=self.CARD, fg=self.MUTED).grid(row=0, column=1, sticky="w")
        self.at_lbl = tk.Label(inner, text=self._trunc(self.cfg["audio_text"]),
                               font=self.FM, bg=self.CARD, fg=self.TEAL,
                               wraplength=310, justify="left")
        self.at_lbl.grid(row=1, column=1, sticky="w")

        # ── Buttons
        bf = tk.Frame(self, bg=self.BG)
        bf.pack(pady=4)
        self._btn(bf, "🔑   EDIT PASSCODE",  self.RED,   self.do_passcode, 0)
        self._btn(bf, "🎙   EDIT AUDIO",     self.AMBER, self.do_audio,    1)
        self._btn(bf, "🎮   TEST GAME",      self.TEAL,  self.do_test,     2)

        self._hr()

        # ── Log
        tk.Label(self, text="EVENT LOG", font=self.FX,
                 bg=self.BG, fg=self.MUTED).pack(anchor="w", padx=36)
        lf = self._card(self)
        lf.pack(fill="both", expand=True, padx=36, pady=(4, 24))
        self.log = tk.Text(lf, height=6, bg=self.CARD, fg=self.MUTED,
                           font=self.FX, bd=0, state="disabled",
                           wrap="word", insertbackground=self.FG)
        self.log.pack(fill="both", expand=True, padx=10, pady=8)

    # ── Widget helpers ────────────────────────────────────────────────────────
    def _hr(self):
        tk.Frame(self, height=1, bg=self.BORDER).pack(fill="x", padx=36, pady=14)

    def _card(self, parent):
        f = tk.Frame(parent, bg=self.CARD,
                     highlightbackground=self.BORDER, highlightthickness=1)
        return f

    def _btn(self, parent, label, color, cmd, row):
        b = tk.Button(parent, text=label, font=self.FB,
                      bg=self.CARD, fg=color, activebackground=color,
                      activeforeground=self.BG, bd=0, cursor="hand2",
                      padx=28, pady=13, command=cmd,
                      highlightbackground=color, highlightthickness=1,
                      relief="flat")
        b.grid(row=row, column=0, pady=6, sticky="ew", ipadx=50)
        b.bind("<Enter>", lambda e: b.configure(bg=color, fg=self.BG))
        b.bind("<Leave>", lambda e: b.configure(bg=self.CARD, fg=color))

    def _modal(self, title, w, h):
        m = tk.Toplevel(self)
        m.title(title)
        m.geometry(f"{w}x{h}")
        m.resizable(False, False)
        m.configure(bg=self.CARD)
        m.grab_set()
        m.transient(self)
        x = self.winfo_x() + (self.winfo_width()  - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        m.geometry(f"+{x}+{y}")
        return m

    # ── Actions ───────────────────────────────────────────────────────────────
    def do_passcode(self):
        win = self._modal("Edit Passcode", 380, 230)
        tk.Label(win, text="New passcode:", font=self.FM,
                 bg=self.CARD, fg=self.FG).pack(pady=(22, 6))
        e = tk.Entry(win, font=("Courier New", 20, "bold"), bg=self.BG,
                     fg=self.AMBER, insertbackground=self.AMBER,
                     bd=0, justify="center", width=14)
        e.pack(ipady=9, padx=44, fill="x")
        e.insert(0, self.cfg["passcode"])
        e.focus()
        info = tk.Label(win, text="", font=self.FX, bg=self.CARD, fg=self.MUTED)
        info.pack(pady=6)

        def save():
            v = e.get().strip()
            if not v:
                messagebox.showerror("Error", "Passcode cannot be empty.", parent=win)
                return
            self.cfg["passcode"] = v
            save_config(self.cfg)
            self.pc_lbl.config(text=self._mask(v))
            self._log(f"Passcode changed → {self._mask(v)}")
            info.config(text="Syncing to Pico…", fg=self.AMBER)
            win.update()

            def sync():
                ok, msg = send_to_pico(v, self.pico_port)
                txt   = f"Pico synced on {msg}" if ok else f"Pico sync skipped: {msg}"
                color = self.TEAL if ok else self.MUTED
                def finish():
                    info.config(text=txt, fg=color)
                    self._log(txt)
                    win.after(2200, win.destroy)
                self.after(0, finish)

            threading.Thread(target=sync, daemon=True).start()

        tk.Button(win, text="SAVE & SYNC TO PICO", font=self.FB,
                  bg=self.RED, fg=self.BG, bd=0, cursor="hand2",
                  padx=18, pady=9, command=save).pack(pady=6)

    def do_audio(self):
        win = self._modal("Edit Audio Text", 460, 300)
        tk.Label(win, text="Text to speak:", font=self.FM,
                 bg=self.CARD, fg=self.FG).pack(pady=(18, 6), padx=20, anchor="w")
        txt = tk.Text(win, height=5, font=self.FM, bg=self.BG,
                      fg=self.AMBER, insertbackground=self.AMBER,
                      bd=0, padx=8, pady=6, wrap="word")
        txt.pack(padx=20, fill="both", expand=True)
        txt.insert("1.0", self.cfg["audio_text"])
        txt.focus()
        prog = tk.Label(win, text="", font=self.FX, bg=self.CARD, fg=self.MUTED)
        prog.pack(pady=4)

        def save():
            v = txt.get("1.0", "end").strip()
            if not v:
                messagebox.showerror("Error", "Audio text cannot be empty.", parent=win)
                return
            prog.config(text="Generating WAV audio…", fg=self.AMBER)
            win.update()

            def done(ok, err):
                def apply_result():
                    if ok:
                        self.cfg["audio_text"] = v
                        save_config(self.cfg)
                        self.at_lbl.config(text=self._trunc(v))
                        prog.config(text="✓ WAV saved!", fg=self.TEAL)
                        self._log(f"Audio updated: \"{self._trunc(v)}\"")
                    else:
                        prog.config(text=f"Error: {err}", fg=self.RED)
                        self._log(f"TTS error: {err}")
                    win.after(2000, win.destroy)
                self.after(0, apply_result)

            threading.Thread(target=generate_audio, args=(v, done), daemon=True).start()

        tk.Button(win, text="GENERATE & SAVE WAV", font=self.FB,
                  bg=self.AMBER, fg=self.BG, bd=0, cursor="hand2",
                  padx=18, pady=9, command=save).pack(pady=6)

    def do_test(self):
        win = self._modal("Test Game", 380, 240)
        tk.Label(win, text="ENTER PASSCODE", font=("Courier New", 14, "bold"),
                 bg=self.CARD, fg=self.RED).pack(pady=(30, 10))
        e = tk.Entry(win, font=("Courier New", 24, "bold"), bg=self.BG,
                     fg=self.FG, insertbackground=self.FG,
                     bd=0, justify="center", show="●", width=12)
        e.pack(ipady=10, padx=50, fill="x")
        e.focus()
        res = tk.Label(win, text="", font=self.FM, bg=self.CARD)
        res.pack(pady=8)
        attempts = [0]

        def check(event=None):
            v = e.get().strip()
            if v == self.cfg["passcode"]:
                res.config(text="✓ CORRECT — Playing audio!", fg=self.TEAL)
                self._log("Test: correct passcode → audio playing")
                win.after(500, lambda: [play_audio(), win.after(2500, win.destroy)])
            else:
                attempts[0] += 1
                res.config(text=f"✗ Incorrect  (attempt {attempts[0]})", fg=self.RED)
                e.delete(0, "end")
                self._log(f"Test: wrong passcode attempt #{attempts[0]}")

        e.bind("<Return>", check)
        tk.Button(win, text="SUBMIT", font=self.FB,
                  bg=self.TEAL, fg=self.BG, bd=0, cursor="hand2",
                  padx=24, pady=9, command=check).pack()

    # ── Pico ──────────────────────────────────────────────────────────────────
    def _monitor_pico(self):
        last_port = None
        while self._running:
            port = find_pico_port()
            if port != last_port:
                self.after(0, lambda p=port: self._update_pico_status(p))
                last_port = port
            time.sleep(2.0)

    def _update_pico_status(self, port):
        if port:
            self.pico_port = port
            self.pico_dot.config(text=f"◉ PICO: {port}", fg=self.TEAL)
            self._log(f"Pico detected on {port}")
        else:
            self.pico_port = None
            self.pico_dot.config(text="◉ PICO: not found", fg=self.MUTED)
            self._log("Pico not detected — connect via USB to enable sync.")

    # ── Misc ──────────────────────────────────────────────────────────────────
    def _audio_done(self, ok, err):
        if ok:
            self._log("Default audio generated.")
        else:
            self._log(f"Audio generation failed: {err}")

    def _log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log.config(state="normal")
        self.log.insert("end", f"[{ts}]  {msg}\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def on_close(self):
        self._running = False
        try:
            import pygame
            pygame.mixer.quit()
        except Exception:
            pass
        self.destroy()

    @staticmethod
    def _mask(c):  return "●" * len(c) + f"  ({len(c)} chars)"
    @staticmethod
    def _trunc(t, n=46): return t if len(t) <= n else t[:n] + "…"


if __name__ == "__main__":
    App().mainloop()
