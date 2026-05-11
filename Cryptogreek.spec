# Cryptogreek.spec — PyInstaller build recipe.
#
# Build with:
#     pyinstaller Cryptogreek.spec
#
# What gets bundled:
#   - app.py + french_to_greek.py (entry + transliterator)
#   - index.html (the UI)
#   - icon.ico (window + .exe icon)
#   - argostranslate Python package + its data files
#   - the installed en->fr language pack (copied from %LOCALAPPDATA%/argos-translate)

import os
import glob
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

here = os.path.abspath(os.path.dirname(SPECPATH) if "SPECPATH" in dir() else ".")

# ---- Gather Argos data ----
# The actual translation packages live in the user's data dir. We copy them
# in so the bundled .exe ships with the model.
def _argos_data_dir():
    # Argos uses platformdirs; on Windows it's %LOCALAPPDATA%\argos-translate
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA", "")
        return os.path.join(base, "argos-translate")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/argos-translate")
    return os.path.expanduser("~/.local/share/argos-translate")

argos_src = _argos_data_dir()
argos_datas = []
if os.path.isdir(argos_src):
    for root, dirs, files in os.walk(argos_src):
        for f in files:
            full = os.path.join(root, f)
            rel  = os.path.relpath(full, argos_src)
            # Bundle into "argos-data/<relative path>"
            argos_datas.append((full, os.path.join("argos-data",
                                                  os.path.dirname(rel))))
    print(f"[spec] Including Argos data from {argos_src} ({len(argos_datas)} files)")
else:
    print(f"[spec] WARNING: {argos_src} not found.")
    print(f"[spec]          Run 'py setup_translation.py' before building.")

# Also pull in argostranslate's own package data (configs etc.)
argos_pkg_datas = collect_data_files("argostranslate")

# ctranslate2 and sentencepiece ship native binaries we need to keep.
ct2_binaries = []
try:
    import ctranslate2, os as _os
    ct2_dir = _os.path.dirname(ctranslate2.__file__)
    for f in _os.listdir(ct2_dir):
        if f.endswith((".dll", ".pyd", ".so", ".dylib")):
            ct2_binaries.append((_os.path.join(ct2_dir, f), "ctranslate2"))
except Exception as e:
    print(f"[spec] ctranslate2 binary scan failed: {e}")

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=ct2_binaries,
    datas=[
        ('index.html', '.'),
        ('icon.ico',   '.'),
        ('french_to_greek.py', '.'),
        *argos_datas,
        *argos_pkg_datas,
    ],
    hiddenimports=[
        *collect_submodules('argostranslate'),
        'sentencepiece',
        'ctranslate2',
        'sacremoses',
        'stanza',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # Heavy stuff we don't actually use; cuts the bundle down a lot.
        'matplotlib', 'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'IPython', 'jupyter', 'notebook', 'pytest', 'scipy', 'pandas',
        'sklearn', 'tensorflow', 'torch.distributions', 'torchvision',
    ],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Cryptogreek',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,            # <- no terminal window
    icon='icon.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='Cryptogreek',
)
