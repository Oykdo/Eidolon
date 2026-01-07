@echo off
chcp 65001 >nul 2>&1
title Eidolon - Launcher
color 0A
cd /d "%~dp0"

:MENU
cls
echo.
echo  ============================================================
echo                EIDOLON
echo            Quantum Vault System - Launcher
echo  ============================================================
echo.
echo   [1] Generer une nouvelle cle vault
echo   [2] Lancer l'interface graphique (GUI)
echo   [3] Lancer le Vault Monitor
echo   [4] Lister les identites enregistrees
echo   [5] Signer les blocs Genesis
echo   [6] Verifier les signatures Genesis
echo   [7] Afficher le portfolio Runes
echo   [8] Demo Genesis Evolutif
echo.
echo   [9] Installer les dependances
echo   [K] Ouvrir le dossier des cles
echo   [0] Quitter
echo.
echo  ============================================================
echo.
set /p choice="  Votre choix: "

if "%choice%"=="1" goto GENERATE_KEY
if "%choice%"=="2" goto LAUNCH_GUI
if "%choice%"=="3" goto VAULT_MONITOR
if "%choice%"=="4" goto LIST_IDENTITIES
if "%choice%"=="5" goto SIGN_GENESIS
if "%choice%"=="6" goto VERIFY_GENESIS
if "%choice%"=="7" goto SHOW_RUNES
if "%choice%"=="8" goto DEMO_GENESIS
if "%choice%"=="9" goto INSTALL_DEPS
if /i "%choice%"=="K" goto OPEN_KEYS
if "%choice%"=="0" goto EXIT

echo.
echo  [!] Choix invalide.
timeout /t 2 >nul
goto MENU

:GENERATE_KEY
cls
echo.
echo  === GENERATION DE CLE VAULT ===
echo.
python scripts/generate_key.py
echo.
pause
goto MENU

:LAUNCH_GUI
cls
echo.
echo  === LANCEMENT INTERFACE GRAPHIQUE ===
echo.
python ui/launch_gui.py
if errorlevel 1 (
    echo.
    echo  [!] Erreur. Tentative alternative...
    python ui/vault_monitor.py --auth
)
echo.
pause
goto MENU

:VAULT_MONITOR
cls
echo.
echo  === VAULT MONITOR ===
echo.
python ui/vault_monitor.py --auth
echo.
pause
goto MENU

:LIST_IDENTITIES
cls
echo.
echo  === IDENTITES ENREGISTREES ===
echo.
python scripts/generate_key.py --list
echo.
pause
goto MENU

:SIGN_GENESIS
cls
echo.
echo  === SIGNATURE DES BLOCS GENESIS ===
echo.
echo  [1] Signer tous les blocs non signes
echo  [2] Signer un bloc specifique
echo  [3] Retour
echo.
set /p sign_choice="  Choix: "

if "%sign_choice%"=="1" (
    python scripts/sign_genesis.py --all
)
if "%sign_choice%"=="2" (
    set /p block_num="  Numero du bloc: "
    call python scripts/sign_genesis.py --block %block_num%
)
echo.
pause
goto MENU

:VERIFY_GENESIS
cls
echo.
echo  === VERIFICATION DES SIGNATURES ===
echo.
python scripts/sign_genesis.py --list
echo.
python scripts/sign_genesis.py --verify
echo.
pause
goto MENU

:SHOW_RUNES
cls
echo.
echo  === PORTFOLIO RUNES ===
echo.
python -c "import sys; sys.path.insert(0,'.'); from core.runes_monitor import RunesMonitor; m=RunesMonitor(); print(m.get_runes_display())"
echo.
pause
goto MENU

:DEMO_GENESIS
cls
echo.
echo  === DEMO GENESIS EVOLUTIF ===
echo.
python tools/genesis_evolutif_demo.py
echo.
pause
goto MENU

:INSTALL_DEPS
cls
echo.
echo  === INSTALLATION DES DEPENDANCES ===
echo.
pip install -r requirements.txt
echo.
echo  [OK] Installation terminee!
echo.
pause
goto MENU

:OPEN_KEYS
echo.
echo  [*] Ouverture du dossier des cles...
explorer vault_storage\keys
goto MENU

:EXIT
cls
echo.
echo  Merci d'utiliser Eidolon
echo  "Quantum Security for the Future"
echo.
timeout /t 2 >nul
exit
