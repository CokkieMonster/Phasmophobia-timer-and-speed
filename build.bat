@echo off
REM Builds the app locally into dist\PhasmoTimer\ (same settings as the GitHub release build).
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean --onedir --windowed --name PhasmoTimer --icon assets/icon.ico --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 run.py
echo.
echo Done: dist\PhasmoTimer\PhasmoTimer.exe
pause
