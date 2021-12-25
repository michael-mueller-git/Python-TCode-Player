@echo off
rmdir /Q /S "build" 2>NUL
rmdir /Q /S "dist" 2>NUL
del tcode-player.spec 2>NUL
pyinstaller --noupx --onefile tcode-player.py

