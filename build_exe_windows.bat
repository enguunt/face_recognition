@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv\Scripts\python.exe oldsongui.
    echo Ehleed README_FIX.md dahi suulgah zaavriig dagana uu.
    pause
    exit /b 1
)
set "PY=.venv\Scripts\python.exe"
"%PY%" -m pip install --upgrade pyinstaller
if errorlevel 1 goto failed
set "MODEL_DIR=%USERPROFILE%\.deepface\weights"
if exist "%MODEL_DIR%" (
    echo Modeliin weights directory oldloo; offline ajilluulah gej bagtsalna.
    "%PY%" -m PyInstaller --noconfirm --clean --onedir --windowed --name FACEVISION --collect-all deepface --collect-all mediapipe --collect-all tf_keras --collect-all onnxruntime --hidden-import openpyxl --hidden-import PIL.ImageTk --add-data "%MODEL_DIR%;bundled_facevision_weights" facevision.py
) else (
    echo Anhaarah: DeepFace weights oldsongui. Shine komputer internet shaardaj magadgui.
    "%PY%" -m PyInstaller --noconfirm --clean --onedir --windowed --name FACEVISION --collect-all deepface --collect-all mediapipe --collect-all tf_keras --collect-all onnxruntime --hidden-import openpyxl --hidden-import PIL.ImageTk facevision.py
)
if errorlevel 1 goto failed
 echo.
 echo [OK] EXE: dist\FACEVISION\FACEVISION.exe
 echo Busad hund yavuulahdaa dist\FACEVISION havtasiig BUGDIIG ni ZIP bolgono.
 pause
 exit /b 0
:failed
 echo.
 echo [ERROR] EXE build amjiltgui. Terminaliin aldaag harna uu.
 pause
 exit /b 1
