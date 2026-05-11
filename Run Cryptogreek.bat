@echo off
REM ===================================================================
REM  Cryptogreek launcher
REM  Double-click me. First run will install dependencies (one-time).
REM  Subsequent runs are instant.
REM ===================================================================

cd /d "%~dp0"

REM --- Check for Python ---
where py >nul 2>&1
if %errorlevel% neq 0 (
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo Python is not installed.
        echo Please install Python 3.12 from https://www.python.org/downloads/
        echo Make sure to tick "Add Python to PATH" during install.
        echo.
        pause
        exit /b 1
    )
    set PYCMD=python
) else (
    set PYCMD=py
)

REM --- Use a stamp file to skip pip on subsequent runs ---
if not exist ".deps_installed" (
    echo.
    echo === First-time setup: installing dependencies ===
    echo This will take a few minutes. Future runs will be instant.
    echo.
    %PYCMD% -m pip install --quiet argostranslate
    if %errorlevel% neq 0 (
        echo.
        echo Failed to install argostranslate.
        echo Trying without it - transliteration will still work.
        echo.
    )

    REM Download the English-French language pack if Argos is present
    %PYCMD% setup_translation.py
    if %errorlevel% neq 0 (
        echo.
        echo Language pack download skipped or failed.
        echo The app will still work in "Skip Fr." mode (transliteration only).
        echo.
    )

    REM Mark setup as done
    echo done > .deps_installed
    echo.
    echo === Setup complete ===
    echo.
)

REM --- Launch the app ---
echo Launching Cryptogreek...
%PYCMD% app.py
