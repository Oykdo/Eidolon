@echo off
chcp 65001 > nul
title Eidolon - Quick Start
color 0A

echo.
echo  ◈ EIDOLON - QUICK START ◈
echo  ═══════════════════════════════════════
echo.

:: Verifier si Python est installe
python --version > nul 2>&1
if errorlevel 1 (
    echo  [X] Python n'est pas installe ou pas dans le PATH
    echo  [!] Installez Python 3.8+ depuis https://python.org
    pause
    exit /b 1
)

echo  [OK] Python detecte
echo.

:: Verifier les dependances
echo  [*] Verification des dependances...
python -c "import cryptography" > nul 2>&1
if errorlevel 1 (
    echo  [!] Installation des dependances...
    pip install -r requirements.txt
)
echo  [OK] Dependances OK
echo.

:: Lancer l'interface
echo  [*] Lancement de l'interface...
echo.
python ui/vault_monitor.py --auth

pause
