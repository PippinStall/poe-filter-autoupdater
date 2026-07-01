@echo off
echo Installing dependencies...
pip install pyinstaller customtkinter

echo.
echo Building executable...
pyinstaller --onefile --windowed --name "PoE2FilterUpdater" --collect-data customtkinter app\main.py

echo.
echo Done! Find PoE2FilterUpdater.exe in the dist\ folder.
pause
