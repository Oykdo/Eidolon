#!/usr/bin/env python3
"""
Script de lancement du monitoring du vault Eidolon

Modes de lancement:
- Interactif: Demande les fichiers clés en ligne de commande
- GUI: Ouvre des dialogues pour sélectionner les fichiers
- Direct: Utilise les chemins passés en arguments

Usage:
    python launch_vault_monitor.py                    # Mode interactif
    python launch_vault_monitor.py --gui              # Mode GUI (dialogues)
    python launch_vault_monitor.py --psnx KEY.psnx --blend KEY.blend_data
    python launch_vault_monitor.py --vault mon_vault --password
"""

import sys
import os
import argparse
import getpass
import hashlib

# Fix Windows console encoding for Unicode
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_banner():
    """Afficher la bannière"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║         Eidolon - Vault Monitor                     ║
║         Système de monitoring sécurisé avec persistance          ║
╚══════════════════════════════════════════════════════════════════╝
    """)


def authenticate_with_files(psnx_path: str, blend_path: str) -> tuple:
    """
    Authentification avec fichiers clés.
    
    Returns:
        (success, vault_key, message)
    """
    try:
        from ui.vault_gui_complete import DualKeyAuthenticator
        
        if not os.path.exists(psnx_path):
            return False, None, f"Fichier non trouvé: {psnx_path}"
        
        if not os.path.exists(blend_path):
            return False, None, f"Fichier non trouvé: {blend_path}"
        
        auth = DualKeyAuthenticator()
        success, msg = auth.authenticate(psnx_path, blend_path)
        
        if success:
            return True, auth.vault_key, "Authentification réussie"
        else:
            return False, None, msg
    
    except ImportError as e:
        return False, None, f"Module d'authentification non disponible: {e}"


def authenticate_with_password(vault_name: str, password: str) -> tuple:
    """
    Authentification par mot de passe.
    
    Returns:
        (success, vault_key, message)
    """
    salt = hashlib.sha256(vault_name.encode()).digest()[:16]
    vault_key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode(),
        salt,
        100000,
        dklen=32
    )
    return True, vault_key, "Clé dérivée du mot de passe"


def launch_monitor_gui(vault_key: bytes, vault_name: str):
    """Lancer l'interface graphique de monitoring"""
    try:
        from ui.vault_monitor import VaultMonitorGUI
        
        print(f"\n[OK] Lancement du monitoring pour le vault: {vault_name}")
        print("[INFO] Interface graphique en cours de chargement...")
        
        monitor = VaultMonitorGUI(vault_key, vault_name)
        monitor.run()
        
    except ImportError as e:
        print(f"[ERREUR] Interface de monitoring non disponible: {e}")
        sys.exit(1)


def interactive_mode():
    """Mode interactif en ligne de commande"""
    print_banner()
    print("Authentification requise avec double clé")
    print("-" * 50)
    
    # Demander les fichiers clés
    psnx_path = input("\nChemin du fichier .psnx: ").strip()
    blend_path = input("Chemin du fichier .blend_data: ").strip()
    
    if not psnx_path or not blend_path:
        print("[ERREUR] Les deux fichiers sont requis")
        sys.exit(1)
    
    # Authentification
    print("\n[INFO] Vérification des clés...")
    success, vault_key, msg = authenticate_with_files(psnx_path, blend_path)
    
    if success:
        print(f"[OK] {msg}")
        print(f"[OK] Clé vault générée: {vault_key.hex()[:16]}...")
        
        # Demander le nom du vault
        vault_name = input("\nNom du vault (default: 'main_vault'): ").strip()
        if not vault_name:
            vault_name = "main_vault"
        
        # Lancer le monitor
        launch_monitor_gui(vault_key, vault_name)
    else:
        print(f"[ERREUR] Échec d'authentification: {msg}")
        sys.exit(1)


def gui_mode():
    """Mode GUI avec dialogues de sélection de fichiers"""
    print_banner()
    
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, simpledialog
        
        root = tk.Tk()
        root.withdraw()
        
        # Sélection du fichier .psnx
        psnx_path = filedialog.askopenfilename(
            title="Sélectionner le fichier .psnx",
            filetypes=[("PSNX files", "*.psnx"), ("All files", "*.*")]
        )
        
        if not psnx_path:
            print("[INFO] Annulé par l'utilisateur")
            return
        
        # Sélection du fichier .blend_data
        blend_path = filedialog.askopenfilename(
            title="Sélectionner le fichier .blend_data",
            filetypes=[("Blend Data", "*.blend_data"), ("All files", "*.*")]
        )
        
        if not blend_path:
            print("[INFO] Annulé par l'utilisateur")
            return
        
        # Authentification
        success, vault_key, msg = authenticate_with_files(psnx_path, blend_path)
        
        if not success:
            messagebox.showerror("Erreur", f"Authentification échouée:\n{msg}")
            return
        
        # Demander le nom du vault
        vault_name = simpledialog.askstring(
            "Nom du vault",
            "Entrez le nom du vault:",
            initialvalue="main_vault"
        )
        
        if not vault_name:
            vault_name = "main_vault"
        
        root.destroy()
        
        # Lancer le monitor
        print(f"[OK] Authentification réussie")
        launch_monitor_gui(vault_key, vault_name)
        
    except ImportError:
        print("[ERREUR] tkinter non disponible")
        sys.exit(1)


def direct_mode(args):
    """Mode direct avec arguments"""
    print_banner()
    
    if args.psnx and args.blend:
        # Authentification par fichiers
        print("[INFO] Authentification par fichiers clés...")
        success, vault_key, msg = authenticate_with_files(args.psnx, args.blend)
        
        if not success:
            print(f"[ERREUR] {msg}")
            sys.exit(1)
        
        print(f"[OK] {msg}")
        vault_name = args.vault or os.path.splitext(os.path.basename(args.psnx))[0]
    
    elif args.vault and args.password:
        # Authentification par mot de passe
        print("[INFO] Authentification par mot de passe...")
        password = getpass.getpass("Mot de passe: ")
        success, vault_key, msg = authenticate_with_password(args.vault, password)
        print(f"[OK] {msg}")
        vault_name = args.vault
    
    elif args.vault and args.key:
        # Authentification par clé hex
        print("[INFO] Authentification par clé...")
        try:
            vault_key = bytes.fromhex(args.key)
            vault_name = args.vault
        except ValueError:
            print("[ERREUR] Clé hexadécimale invalide")
            sys.exit(1)
    
    else:
        print("[ERREUR] Arguments insuffisants")
        print("Utilisez --psnx et --blend, ou --vault avec --password ou --key")
        sys.exit(1)
    
    # Lancer le monitor
    launch_monitor_gui(vault_key, vault_name)


def main():
    parser = argparse.ArgumentParser(
        description="Eidolon - Vault Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s                                    # Mode interactif
  %(prog)s --gui                              # Mode GUI avec dialogues
  %(prog)s --psnx key.psnx --blend key.blend_data
  %(prog)s --vault mon_vault --password
  %(prog)s --vault mon_vault --key ABC123...
        """
    )
    
    parser.add_argument(
        "--gui", "-g",
        action="store_true",
        help="Utiliser les dialogues GUI pour sélectionner les fichiers"
    )
    
    parser.add_argument(
        "--psnx",
        help="Chemin du fichier .psnx"
    )
    
    parser.add_argument(
        "--blend",
        help="Chemin du fichier .blend_data"
    )
    
    parser.add_argument(
        "--vault", "-v",
        help="Nom du vault"
    )
    
    parser.add_argument(
        "--password", "-p",
        action="store_true",
        help="Authentification par mot de passe"
    )
    
    parser.add_argument(
        "--key", "-k",
        help="Clé du vault (hexadécimale)"
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Lancer en mode démo avec un vault de test"
    )
    
    args = parser.parse_args()
    
    # Mode démo
    if args.demo:
        print_banner()
        print("[INFO] Lancement en mode démo...")
        vault_key = hashlib.sha256(b"demo_vault_key").digest()
        launch_monitor_gui(vault_key, "demo_vault")
        return
    
    # Déterminer le mode
    if args.gui:
        gui_mode()
    elif args.psnx or args.vault:
        direct_mode(args)
    else:
        # Mode interactif par défaut
        interactive_mode()


if __name__ == "__main__":
    main()
