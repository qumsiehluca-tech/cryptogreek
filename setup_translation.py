"""
One-time setup: downloads the English -> French Argos Translate package.
You only need internet for this script. After it runs, the app works offline.

Run:  py setup_translation.py
"""
import sys

try:
    import argostranslate.package
    import argostranslate.translate
except ImportError:
    print("Argos Translate not installed. Skipping language pack download.")
    print("The app will still work in transliteration-only mode.")
    print("(To enable translation: pip install argostranslate, then re-run this.)")
    sys.exit(0)

# Quick check: is the package already installed? Don't re-download.
installed = [l.code for l in argostranslate.translate.get_installed_languages()]
if "en" in installed and "fr" in installed:
    print("English-French pack already installed. Nothing to do.")
    sys.exit(0)

print("Updating package index from the internet...")
argostranslate.package.update_package_index()

available = argostranslate.package.get_available_packages()
match = next(
    (p for p in available if p.from_code == "en" and p.to_code == "fr"),
    None,
)
if not match:
    raise SystemExit("No en->fr package found in the index.")

print(f"Downloading {match} ...")
path = match.download()
print(f"Installing from {path} ...")
argostranslate.package.install_from_path(path)

installed_langs = [l.code for l in argostranslate.translate.get_installed_languages()]
print(f"Done. Installed languages: {installed_langs}")
print("You can now run:  py app.py")
