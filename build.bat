@echo off
setlocal

where py >nul 2>nul
if errorlevel 1 (
    set "PYTHON_CMD=python"
) else (
    set "PYTHON_CMD=py -3"
)

if not exist .venv\Scripts\python.exe (
    %PYTHON_CMD% -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "PrivacyScreen" main.py

echo.
echo Build complete: dist\PrivacyScreen.exe
pause
