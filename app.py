"""
Cryptogreek — browser-tab launcher.

Spins up a tiny local HTTP server on 127.0.0.1, opens your default browser
at it, and serves index.html. The page calls back into Python via /api/encipher
for translation + transliteration.

Why this instead of pywebview? Because pywebview requires `pythonnet` on
Windows, and `pythonnet` has no Python 3.14 wheel and won't build from source.
This version uses only stdlib + your existing files, works on any Python 3.x,
and doesn't pop up a console window if you launch via pyw.exe.

Run:   py app.py
"""

import json
import os
import sys
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from french_to_greek import transliterate


# ---------- Resource resolution (works in dev or frozen) ----------
def _resource_dir() -> str:
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

HERE = _resource_dir()


# If a bundled Argos model is shipped alongside, point Argos at it.
_argos_bundled = os.path.join(HERE, "argos-data")
if os.path.isdir(_argos_bundled):
    os.environ.setdefault("ARGOS_PACKAGES_DIR",
                          os.path.join(_argos_bundled, "packages"))
    os.environ.setdefault("ARGOS_DEVICE_TYPE", "cpu")


# ---------- Translation backend (lazy) ----------
class Translator:
    def __init__(self):
        self._tried = False
        self._available = False
        self._error = None

    def _try_load(self):
        if self._tried:
            return
        self._tried = True
        try:
            from argostranslate import translate as _t
            codes = {l.code for l in _t.get_installed_languages()}
            if "en" in codes and "fr" in codes:
                self._available = True
            else:
                self._error = ("Argos is installed but no English-French pack. "
                               "Run setup_translation.py once.")
        except ImportError:
            self._error = ("Argos Translate not installed - transliteration only. "
                           "Install with: pip install argostranslate")
        except Exception as e:
            self._error = f"Translation backend error: {e}"

    def translate(self, text):
        self._try_load()
        if not self._available:
            return text, self._error or "translation unavailable"
        try:
            import argostranslate.translate as at
            return at.translate(text, "en", "fr"), ""
        except Exception as e:
            return text, f"translation failed: {e}"


TRANSLATOR = Translator()


# ---------- Encipher logic ----------
def _encipher(text: str, mode: str) -> dict:
    """
    mode = 'en'  -> translate English to French, then transliterate
    mode = 'fr'  -> input is already French; transliterate directly
    mode = 'raw' -> don't translate at all; transliterate what was typed
    """
    try:
        if not text or not text.strip():
            return {"french": "", "greek": "", "note": ""}

        if mode == "fr":
            # User typed French — skip translation entirely.
            return {
                "french": "",   # nothing to show in the middle column
                "greek": transliterate(text),
                "note": "français → grec (no translation)",
            }

        if mode == "raw":
            return {
                "french": "",
                "greek": transliterate(text),
                "note": "transliterated as-is (no translation)",
            }

        # Default: English -> French -> Greek
        french, note = TRANSLATOR.translate(text)
        return {"french": french, "greek": transliterate(french), "note": note}
    except Exception as e:
        traceback.print_exc()
        return {"error": f"{type(e).__name__}: {e}"}


# ---------- HTTP handler ----------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass   # quiet

    def _serve_bytes(self, body, ctype="application/json; charset=utf-8",
                     status=200):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            try:
                with open(os.path.join(HERE, "index.html"), "rb") as f:
                    self._serve_bytes(f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._serve_bytes(b"index.html not found", "text/plain", 500)
            return
        if path == "/icon.png":
            p = os.path.join(HERE, "icon.png")
            if os.path.exists(p):
                with open(p, "rb") as f:
                    self._serve_bytes(f.read(), "image/png")
                return
        if path == "/favicon.ico":
            p = os.path.join(HERE, "icon.ico")
            if os.path.exists(p):
                with open(p, "rb") as f:
                    self._serve_bytes(f.read(), "image/vnd.microsoft.icon")
                return
            self._serve_bytes(b"", "image/x-icon")
            return
        self._serve_bytes(b"not found", "text/plain", 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/shutdown":
            # Browser window closed -> end the Python process too.
            self._serve_bytes(b'{"ok":true}')
            # Trigger shutdown after the response is flushed.
            threading.Thread(
                target=lambda: (time.sleep(0.1), os._exit(0)),
                daemon=True
            ).start()
            return
        if path != "/api/encipher":
            self._serve_bytes(b'{"error":"unknown endpoint"}', status=404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b""
            payload = json.loads(body or b"{}")
            text = payload.get("text", "")
            # Accept the new 'mode' field; fall back to the old 'skip_translate'
            # boolean if an older client is talking to us.
            mode = payload.get("mode")
            if mode is None:
                mode = "raw" if payload.get("skip_translate") else "en"
            if mode not in {"en", "fr", "raw"}:
                mode = "en"
            result = _encipher(text, mode)
            self._serve_bytes(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            traceback.print_exc()
            err = json.dumps({"error": f"{type(e).__name__}: {e}"}).encode("utf-8")
            self._serve_bytes(err, status=500)


def _pick_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _open_as_app(url: str):
    """
    Open `url` in a borderless app-style window using Chrome or Edge's
    --app= mode. Falls back to the default browser if neither is found.

    Chrome/Edge --app=<url> opens a clean window: no tabs, no address bar,
    no bookmarks. Looks and feels like a real desktop application, while
    still being our existing HTML/CSS/JS frontend talking to the Python
    server in the background.
    """
    import shutil
    import subprocess

    # Candidate app-mode browsers in priority order.
    candidates = []
    if sys.platform.startswith("win"):
        # Windows: check both Program Files and the per-user AppData install.
        pf  = os.environ.get("ProgramFiles",        r"C:\Program Files")
        pfx = os.environ.get("ProgramFiles(x86)",   r"C:\Program Files (x86)")
        local_app = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(pf,  r"Google\Chrome\Application\chrome.exe"),
            os.path.join(pfx, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(local_app, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(pf,  r"Microsoft\Edge\Application\msedge.exe"),
            os.path.join(pfx, r"Microsoft\Edge\Application\msedge.exe"),
            os.path.join(local_app, r"Microsoft\Edge\Application\msedge.exe"),
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
    else:  # Linux & co.
        candidates = [shutil.which(n) for n in
                      ("google-chrome", "chromium", "chromium-browser",
                       "microsoft-edge", "brave-browser")]
        candidates = [c for c in candidates if c]

    for path in candidates:
        if path and os.path.exists(path):
            try:
                # --app=<url>      → borderless app window
                # --window-size    → opens at a sensible default
                # --user-data-dir  → a dedicated profile so this doesn't
                #                    fight with your main browser session
                profile_dir = os.path.join(
                    os.path.expanduser("~"), ".cryptogreek-profile")
                subprocess.Popen([
                    path,
                    f"--app={url}",
                    "--window-size=1200,780",
                    f"--user-data-dir={profile_dir}",
                ])
                return True
            except Exception as e:
                print(f"app-mode launch via {path} failed: {e}")
                continue

    # Fallback: ordinary browser tab.
    webbrowser.open(url)
    return False


def main():
    if not os.path.exists(os.path.join(HERE, "index.html")):
        print(f"Cannot find index.html in {HERE}", file=sys.stderr)
        sys.exit(1)

    threading.Thread(target=TRANSLATOR._try_load, daemon=True).start()

    port = _pick_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)

    url = f"http://127.0.0.1:{port}/"
    print(f"Cryptogreek serving at {url}")
    print("Close the window (or press Ctrl+C in this console) to stop.")

    def _open():
        time.sleep(0.3)
        _open_as_app(url)
    threading.Thread(target=_open, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
