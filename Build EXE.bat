@echo off
REM Builds the shareable Cryptogreek bundle.
REM
REM Prerequisites (one-time):
REM   pip install --no-deps pywebview
REM   pip install bottle proxy_tools typing_extensions argostranslate pyinstaller pillow cairosvg
REM   py setup_translation.py
REM   py make_icon.py
REM
REM Then double-click this file. Output goes to dist\Cryptogreek\.
REM Zip that folder and send it to anyone — they run Cryptogreek.exe inside.

cd /d "%~dp0"

echo.
echo === Cleaning previous builds ===
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo === Running PyInstaller ===
py -m PyInstaller Cryptogreek.spec --noconfirm
if errorlevel 1 (
    echo.
    echo BUILD FAILED. See the messages above.
    pause
    exit /b 1
)

echo.
echo === Done! ===
echo Your bundle is in:  dist\Cryptogreek\
echo The launcher is:    dist\Cryptogreek\Cryptogreek.exe
echo.
echo To share: right-click the Cryptogreek folder, "Send to → Compressed (zipped) folder".
echo Recipients unzip and double-click Cryptogreek.exe. No install needed.
pause
