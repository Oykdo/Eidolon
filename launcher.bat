@echo off
chcp 65001 >nul 2>&1
title Eidolon - Launcher
cd /d "%~dp0"

:: Launch the Python launcher
python ui/launcher.py
if errorlevel 1 (
    echo.
    echo [!] Python launcher failed. Check Python installation.
    pause
)
exit
