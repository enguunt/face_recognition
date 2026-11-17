@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Python virtual environment oldsongui: .venv\Scripts\python.exe
    echo README_FIX.md-iig unshina uu.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" facevision.py
if errorlevel 1 pause
