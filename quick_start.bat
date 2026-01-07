@echo off
chcp 65001 > nul
title Eidolon - Quick Connect

:: Verifier si Python est installe
python --version > nul 2>&1
if errorlevel 1 (
    echo.
    echo  [X] Python n'est pas installe ou pas dans le PATH
    echo  [!] Installez Python 3.8+ depuis https://python.org
    pause
    exit /b 1
)

:: Verifier les dependances silencieusement
python -c "import cryptography" > nul 2>&1
if errorlevel 1 (
    echo  [*] Installation des dependances...
    pip install -r requirements.txt -q
)

:: Lancer l'interface de connexion
python ui/quick_connect.py

pause
