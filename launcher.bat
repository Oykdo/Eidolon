@echo off
chcp 65001 > nul
title Poly-Spinor Nexus 7D - Launcher
color 0A

:MENU
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║                                                                  ║
echo  ║       ◈ POLY-SPINOR NEXUS 7D - QUANTUM VAULT SYSTEM ◈           ║
echo  ║                                                                  ║
echo  ║              Post-Quantum Cryptography + Bell Verification       ║
echo  ║                                                                  ║
echo  ╠══════════════════════════════════════════════════════════════════╣
echo  ║                                                                  ║
echo  ║   [1] Generer une nouvelle cle vault                            ║
echo  ║   [2] Lancer l'interface graphique (GUI)                        ║
echo  ║   [3] Lancer le Vault Monitor                                   ║
echo  ║   [4] Lister les identites enregistrees                         ║
echo  ║   [5] Signer les blocs Genesis                                  ║
echo  ║   [6] Verifier les signatures Genesis                           ║
echo  ║   [7] Demo Genesis Evolutif                                     ║
echo  ║                                                                  ║
echo  ╠══════════════════════════════════════════════════════════════════╣
echo  ║                                                                  ║
echo  ║   [8] Installer les dependances                                 ║
echo  ║   [9] Ouvrir le dossier des cles                                ║
echo  ║   [0] Quitter                                                   ║
echo  ║                                                                  ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.
set /p choice="  Votre choix: "

if "%choice%"=="1" goto GENERATE_KEY
if "%choice%"=="2" goto LAUNCH_GUI
if "%choice%"=="3" goto VAULT_MONITOR
if "%choice%"=="4" goto LIST_IDENTITIES
if "%choice%"=="5" goto SIGN_GENESIS
if "%choice%"=="6" goto VERIFY_GENESIS
if "%choice%"=="7" goto DEMO_GENESIS
if "%choice%"=="8" goto INSTALL_DEPS
if "%choice%"=="9" goto OPEN_KEYS
if "%choice%"=="0" goto EXIT

echo.
echo  [!] Choix invalide. Appuyez sur une touche...
pause > nul
goto MENU

:GENERATE_KEY
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║              GENERATION DE CLE VAULT                             ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.
python scripts/generate_key.py
echo.
echo  ────────────────────────────────────────────────────────────────────
pause
goto MENU

:LAUNCH_GUI
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║              LANCEMENT INTERFACE GRAPHIQUE                       ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.
echo  [*] Demarrage de l'interface...
python ui/launch_gui.py
if errorlevel 1 (
    echo.
    echo  [!] Erreur lors du lancement. Tentative alternative...
    python ui/vault_monitor.py --auth
)
echo.
pause
goto MENU

:VAULT_MONITOR
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║              VAULT MONITOR - CYPHERPUNK UI                       ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.
echo  [*] Demarrage du Vault Monitor...
echo  [*] Selectionnez vos fichiers .psnx et .blend_data
echo.
python ui/vault_monitor.py --auth
echo.
pause
goto MENU

:LIST_IDENTITIES
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║              IDENTITES ENREGISTREES                              ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.
python scripts/generate_key.py --list
echo.
echo  ────────────────────────────────────────────────────────────────────
pause
goto MENU

:SIGN_GENESIS
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║              SIGNATURE DES BLOCS GENESIS                         ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.
echo  [1] Signer tous les blocs non signes
echo  [2] Signer un bloc specifique
echo  [3] Retour
echo.
set /p sign_choice="  Choix: "

if "%sign_choice%"=="1" (
    echo.
    python scripts/sign_genesis.py --all
)
if "%sign_choice%"=="2" (
    echo.
    set /p block_num="  Numero du bloc: "
    python scripts/sign_genesis.py --block %block_num%
)
echo.
pause
goto MENU

:VERIFY_GENESIS
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║              VERIFICATION DES SIGNATURES                         ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.
python scripts/sign_genesis.py --list
echo.
echo  ────────────────────────────────────────────────────────────────────
echo.
python scripts/sign_genesis.py --verify
echo.
pause
goto MENU

:DEMO_GENESIS
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║              DEMO GENESIS EVOLUTIF                               ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.
python tools/genesis_evolutif_demo.py
echo.
pause
goto MENU

:INSTALL_DEPS
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║              INSTALLATION DES DEPENDANCES                        ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.
echo  [*] Installation des dependances Python...
echo.
pip install -r requirements.txt
echo.
echo  [OK] Installation terminee!
echo.
pause
goto MENU

:OPEN_KEYS
cls
echo.
echo  [*] Ouverture du dossier des cles...
explorer vault_storage\keys
goto MENU

:EXIT
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║                                                                  ║
echo  ║          Merci d'utiliser Poly-Spinor Nexus 7D                  ║
echo  ║                                                                  ║
echo  ║              "Quantum Security for the Future"                   ║
echo  ║                                                                  ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.
timeout /t 2 > nul
exit
