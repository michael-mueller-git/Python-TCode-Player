@echo off
rmdir /Q /S "build" 2>NUL
rmdir /Q /S "dist" 2>NUL
del tcode-player.spec 2>NUL
pyinstaller --hidden-import "pynput.keyboard._win32" --hidden-import "pynput.mouse._win32" --noupx --onefile tcode-player.py

