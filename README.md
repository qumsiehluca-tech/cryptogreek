# ΚΡΥΠΤΟΣ · Cryptogreek

Desktop app that translates English -> French, then renders the French in
Greek letters. Opens in a browser tab; Python runs the cipher in the background.

---

## Why a browser tab and not a real window?

The original plan was pywebview (a real desktop window with HTML inside).
But pywebview requires `pythonnet` on Windows, and `pythonnet` has **no wheel
for Python 3.14** — pip tries to build it from source and fails. So this
version uses Python's built-in HTTP server and your default browser. Looks
the same, works on any Python, no native-extension nightmare.

---

## Files

| File | Purpose |
|---|---|
| `app.py` | Starts the local server + opens your browser |
| `index.html` | The UI |
| `french_to_greek.py` | Transliteration engine |
| `setup_translation.py` | One-time language-pack download |
| `make_icon.py` | Generates `icon.ico` + `icon.png` (Pillow-only) |
| `make_shortcut.ps1` | Creates the desktop shortcut |
| `Make Shortcut.bat` | Double-click version of the above |
| `Run Cryptogreek.bat` | Auto-installs deps and runs the app — share this with friends |

---

## Setup

### Step 1 — Install Pillow and argostranslate

```powershell
pip install pillow argostranslate
```

(Pillow is for generating the icon. argostranslate is for the English->French
translation. The app works without argostranslate — it just won't translate.)

### Step 2 — Download the translation model (one-time, online)

```powershell
py setup_translation.py
```

After this, the translation works offline forever.

### Step 3 — Generate the icon

```powershell
py make_icon.py
```

Creates `icon.ico` and `icon.png` in this folder.

### Step 4 — Run it

```powershell
py app.py
```

A browser tab opens at `http://127.0.0.1:<port>/`. Type English, watch the
French and Greek-letter forms appear. The console window has to stay open
while the app runs — close it to shut everything down.

---

## Desktop shortcut with the gold-Phi icon

Double-click **`Make Shortcut.bat`**.

You'll get `Cryptogreek.lnk` on your desktop with the seal icon. Double-click
that to launch — uses `pyw.exe` so no console window appears.

---

## Sharing with other people

Send them this whole folder as a zip. They:

1. Install Python from python.org (any version 3.9+).
2. Unzip the folder somewhere.
3. Double-click **`Run Cryptogreek.bat`**.

First run installs argostranslate, downloads the language model, and launches
the app. Future runs are instant. That's it — they don't need to know `pip`
or anything else.

> If you want zero-install (recipient doesn't need Python at all), the
> traditional answer is PyInstaller. But on Python 3.14 the PyInstaller +
> argostranslate combo is rough right now. If you really need a single .exe,
> install Python 3.12 first, then we can build that.

---

## In-app controls

The mode selector (segmented control) picks how your input is handled:

- **EN → fr → gr** — type English; it gets translated to French, then to Greek letters
- **FR → gr** — type French directly (no translation); transliterated straight to Greek letters
- **EN → gr** — no translation at all; transliterate whatever you type as-is

Plus:
- **Encipher** — force a run
- **Copy** — copy the Greek-script output
- **Clear** — reset
- **Live** — auto-encipher as you type (350ms debounce)
- **Ctrl+Enter** — keyboard shortcut to force a run

The middle column (showing the French intermediate translation) dims out
when you're in FR or plain mode, since there's nothing to translate.

---

## Troubleshooting

**`pythonnet cannot be loaded` / `No module named 'clr'`**
You're on the old pywebview-based app.py. The new `app.py` in this folder
doesn't use pywebview at all. Make sure you replaced it.

**Browser doesn't open automatically.**
Check the console — it prints `Cryptogreek serving at http://127.0.0.1:<port>/`.
Open that URL manually.

**Port already in use.**
The app picks a free port each launch, so this shouldn't happen — but if it
does, just relaunch.

**`make_icon.py` errors about fonts.**
Pillow couldn't find Georgia/Times. The script falls back to defaults, but
the Phi might not render perfectly. On Windows this shouldn't happen — those
fonts ship with the OS.

**The "Skip Fr." mode works but normal mode doesn't translate.**
Run `py setup_translation.py`. If that fails too, run `pip install argostranslate`
first.
