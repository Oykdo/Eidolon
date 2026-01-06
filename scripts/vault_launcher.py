#!/usr/bin/env python
"""
Poly-Spinor Nexus 7D - Lanceur Principal du Vault
Point d'entrée unifié pour toutes les fonctionnalités du vault

Modes disponibles:
- gui: Interface graphique de monitoring
- cli: Interface en ligne de commande
- daemon: Service de monitoring en arrière-plan
- setup: Configuration initiale du vault
"""

import os
import sys
import argparse
import hashlib
import getpass
import json
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog


# ============================================================================
# IMPORTS LOCAUX
# ============================================================================

try:
    from ui.vault_monitor import VaultMonitorGUI, SecureVaultManager
    GUI_AVAILABLE = True
except ImportError as e:
    GUI_AVAILABLE = False
    print(f"[WARN] GUI non disponible: {e}")

try:
    from ui.vault_gui_complete import DualKeyAuthenticator, VaultGUI
    AUTH_AVAILABLE = True
except ImportError as e:
    AUTH_AVAILABLE = False
    print(f"[WARN] Authentification complète non disponible: {e}")

try:
    from core.persistent_vault import PersistentVaultManager, create_vault, open_vault
    PERSISTENT_AVAILABLE = True
except ImportError as e:
    PERSISTENT_AVAILABLE = False
    print(f"[WARN] Vault persistant non disponible: {e}")

try:
    from core.complete_key_generator import generate_complete_key, CompleteKeyFileGenerator
    KEYGEN_AVAILABLE = True
except ImportError as e:
    KEYGEN_AVAILABLE = False
    print(f"[INFO] Générateur de clés non disponible: {e}")


# ============================================================================
# CONFIGURATION
# ============================================================================

class VaultConfig:
    """Configuration du lanceur de vault"""
    
    DEFAULT_VAULT_DIR = Path(__file__).parent.parent / "vault_storage"
    CONFIG_FILE = DEFAULT_VAULT_DIR / "launcher_config.json"
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Charger la configuration"""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'last_vault': None,
            'auto_save': True,
            'backup_enabled': True,
            'theme': 'dark',
            'language': 'fr'
        }
    
    def save(self):
        """Sauvegarder la configuration"""
        self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def set(self, key, value):
        self.config[key] = value
        self.save()


# ============================================================================
# AUTHENTIFICATION
# ============================================================================

class VaultAuthenticator:
    """Gestionnaire d'authentification du vault"""
    
    def __init__(self):
        self.vault_key = None
        self.vault_name = None
        self.authenticated = False
    
    def authenticate_with_password(self, vault_name: str, password: str) -> bool:
        """Authentification par mot de passe"""
        # Dériver la clé à partir du mot de passe
        salt = hashlib.sha256(vault_name.encode()).digest()[:16]
        self.vault_key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt,
            100000,
            dklen=32
        )
        self.vault_name = vault_name
        self.authenticated = True
        return True
    
    def authenticate_with_files(self, psnx_path: str, blend_path: str) -> tuple:
        """Authentification par fichiers clés"""
        if not AUTH_AVAILABLE:
            return False, "Module d'authentification non disponible"
        
        auth = DualKeyAuthenticator()
        success, msg = auth.authenticate(psnx_path, blend_path)
        
        if success:
            self.vault_key = auth.vault_key
            self.vault_name = Path(psnx_path).stem
            self.authenticated = True
        
        return success, msg
    
    def authenticate_with_key(self, vault_name: str, key_hex: str) -> bool:
        """Authentification par clé hexadécimale"""
        try:
            self.vault_key = bytes.fromhex(key_hex)
            self.vault_name = vault_name
            self.authenticated = True
            return True
        except ValueError:
            return False


# ============================================================================
# MODE GUI
# ============================================================================

def launch_gui(auth: VaultAuthenticator):
    """Lancer l'interface graphique"""
    if not GUI_AVAILABLE:
        print("[ERREUR] Interface graphique non disponible")
        return False
    
    if not auth.authenticated:
        print("[ERREUR] Authentification requise")
        return False
    
    try:
        monitor = VaultMonitorGUI(auth.vault_key, auth.vault_name)
        monitor.run()
        return True
    except Exception as e:
        print(f"[ERREUR] Échec du lancement GUI: {e}")
        return False


def launch_gui_with_auth():
    """Lancer la GUI avec dialogue d'authentification"""
    root = tk.Tk()
    root.withdraw()
    
    # Dialogue de choix d'authentification
    auth_method = simpledialog.askstring(
        "Authentification",
        "Méthode d'authentification:\n1. Mot de passe\n2. Fichiers clés (.psnx + .blend_data)\n3. Clé hexadécimale\n\nEntrez 1, 2 ou 3:",
        initialvalue="1"
    )
    
    if not auth_method:
        root.destroy()
        return
    
    auth = VaultAuthenticator()
    
    if auth_method == "1":
        # Authentification par mot de passe
        vault_name = simpledialog.askstring("Vault", "Nom du vault:")
        if not vault_name:
            root.destroy()
            return
        
        password = simpledialog.askstring("Mot de passe", "Mot de passe:", show='*')
        if not password:
            root.destroy()
            return
        
        auth.authenticate_with_password(vault_name, password)
    
    elif auth_method == "2":
        # Authentification par fichiers
        psnx_path = filedialog.askopenfilename(
            title="Sélectionner le fichier .psnx",
            filetypes=[("PSNX files", "*.psnx"), ("All files", "*.*")]
        )
        if not psnx_path:
            root.destroy()
            return
        
        blend_path = filedialog.askopenfilename(
            title="Sélectionner le fichier .blend_data",
            filetypes=[("Blend Data", "*.blend_data"), ("All files", "*.*")]
        )
        if not blend_path:
            root.destroy()
            return
        
        success, msg = auth.authenticate_with_files(psnx_path, blend_path)
        if not success:
            messagebox.showerror("Erreur", f"Authentification échouée: {msg}")
            root.destroy()
            return
    
    elif auth_method == "3":
        # Authentification par clé hex
        vault_name = simpledialog.askstring("Vault", "Nom du vault:")
        if not vault_name:
            root.destroy()
            return
        
        key_hex = simpledialog.askstring("Clé", "Clé hexadécimale:")
        if not key_hex or not auth.authenticate_with_key(vault_name, key_hex):
            messagebox.showerror("Erreur", "Clé invalide")
            root.destroy()
            return
    
    else:
        messagebox.showerror("Erreur", "Choix invalide")
        root.destroy()
        return
    
    root.destroy()
    
    # Lancer la GUI
    launch_gui(auth)


# ============================================================================
# MODE CLI
# ============================================================================

def cli_interactive(auth: VaultAuthenticator):
    """Mode interactif en ligne de commande"""
    if not PERSISTENT_AVAILABLE:
        print("[ERREUR] Vault persistant non disponible")
        return
    
    if not auth.authenticated:
        print("[ERREUR] Authentification requise")
        return
    
    vault = PersistentVaultManager(auth.vault_key, auth.vault_name)
    
    print(f"\n=== Vault CLI: {auth.vault_name} ===")
    print("Commandes: stats, assets, docs, tokens, transfers, add-asset, add-doc, export, quit")
    
    while True:
        try:
            cmd = input("\nvault> ").strip().lower()
            
            if cmd == "quit" or cmd == "exit":
                print("Au revoir!")
                break
            
            elif cmd == "stats":
                stats = vault.get_stats()
                print(json.dumps(stats, indent=2, ensure_ascii=False))
            
            elif cmd == "assets":
                assets = vault.list_assets()
                if not assets:
                    print("Aucun actif")
                else:
                    for a in assets:
                        print(f"  [{a.get('id')}] {a.get('name', 'N/A')} - {a.get('status', 'unknown')}")
            
            elif cmd == "docs":
                docs = vault.list_documents()
                if not docs:
                    print("Aucun document")
                else:
                    for d in docs:
                        print(f"  [{d.get('id')}] {d.get('name', 'N/A')} ({d.get('size', 0)} bytes)")
            
            elif cmd == "tokens":
                tokens = vault.list_tokens()
                if not tokens:
                    print("Aucun token")
                else:
                    for t in tokens:
                        print(f"  [{t.get('symbol')}] {t.get('balance', '0')} - {t.get('contract', 'N/A')[:20]}...")
            
            elif cmd == "transfers":
                transfers = vault.get_pending_transfers()
                if not transfers:
                    print("Aucun transfer en attente")
                else:
                    for t in transfers:
                        print(f"  [{t.get('id')}] {t.get('transfer_type')} -> {t.get('destination', 'N/A')[:20]}... (expire: {t.get('expiry', 'N/A')[:10]})")
            
            elif cmd == "add-asset":
                name = input("Nom de l'actif: ")
                asset_type = input("Type (NFT/Token/Other): ")
                contract = input("Adresse du contrat: ")
                
                asset_id = vault.add_asset({
                    'name': name,
                    'asset_type': asset_type,
                    'contract': contract
                })
                print(f"Actif créé avec ID: {asset_id}")
            
            elif cmd == "add-doc":
                file_path = input("Chemin du fichier: ")
                if os.path.exists(file_path):
                    doc_id = vault.add_document(file_path)
                    print(f"Document ajouté avec ID: {doc_id}")
                else:
                    print("Fichier non trouvé")
            
            elif cmd == "export":
                output_dir = input("Répertoire de sortie (. par défaut): ") or "."
                zip_path = vault.export_vault(output_dir)
                print(f"Vault exporté vers: {zip_path}")
            
            elif cmd == "log":
                log = vault.get_activity_log(20)
                for entry in log:
                    print(f"  [{entry.get('timestamp', '')[:19]}] {entry.get('action')}: {entry.get('details', '')}")
            
            elif cmd == "help":
                print("""
Commandes disponibles:
  stats       - Afficher les statistiques du vault
  assets      - Lister les actifs
  docs        - Lister les documents
  tokens      - Lister les tokens
  transfers   - Lister les transfers en attente
  add-asset   - Ajouter un actif
  add-doc     - Ajouter un document
  export      - Exporter le vault
  log         - Afficher le journal d'activité
  help        - Afficher cette aide
  quit        - Quitter
                """)
            
            else:
                print("Commande inconnue. Tapez 'help' pour l'aide.")
        
        except KeyboardInterrupt:
            print("\nInterruption. Tapez 'quit' pour quitter.")
        except Exception as e:
            print(f"Erreur: {e}")


# ============================================================================
# MODE DAEMON
# ============================================================================

def run_daemon(auth: VaultAuthenticator, interval: int = 60):
    """Exécuter le daemon de monitoring"""
    import time
    
    if not PERSISTENT_AVAILABLE:
        print("[ERREUR] Vault persistant non disponible")
        return
    
    if not auth.authenticated:
        print("[ERREUR] Authentification requise")
        return
    
    vault = PersistentVaultManager(auth.vault_key, auth.vault_name)
    
    print(f"[DAEMON] Démarrage du monitoring pour vault '{auth.vault_name}'")
    print(f"[DAEMON] Intervalle: {interval} secondes")
    print("[DAEMON] Ctrl+C pour arrêter")
    
    try:
        while True:
            # Traiter les transfers arrivés à échéance
            executed = vault.process_due_transfers()
            if executed:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Transfers exécutés: {executed}")
            
            # Afficher les stats
            stats = vault.get_stats()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Assets: {stats['asset_count']}, Docs: {stats['document_count']}, Pending transfers: {stats['pending_transfers']}")
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n[DAEMON] Arrêt demandé")


# ============================================================================
# MODE SETUP
# ============================================================================

def run_setup():
    """Assistant de configuration initiale"""
    print("\n" + "="*60)
    print("  Poly-Spinor Nexus 7D - Configuration du Vault")
    print("="*60)
    
    # Nom du vault
    vault_name = input("\nNom du vault: ").strip()
    if not vault_name:
        print("Nom invalide")
        return
    
    # Méthode de sécurisation
    print("\nMéthode de sécurisation:")
    print("  1. Mot de passe simple")
    print("  2. Générer des fichiers clés (.psnx + .blend_data)")
    print("  3. Clé personnalisée (hex)")
    
    method = input("\nChoix (1/2/3): ").strip()
    
    auth = VaultAuthenticator()
    
    if method == "1":
        password = getpass.getpass("Mot de passe: ")
        confirm = getpass.getpass("Confirmer: ")
        
        if password != confirm:
            print("Les mots de passe ne correspondent pas")
            return
        
        auth.authenticate_with_password(vault_name, password)
        
        print(f"\n[INFO] Clé dérivée du mot de passe")
        print(f"[INFO] Gardez votre mot de passe en sécurité!")
    
    elif method == "2":
        if not KEYGEN_AVAILABLE:
            print("[ERREUR] Générateur de clés non disponible")
            return
        
        output_dir = input("Répertoire de sortie pour les clés: ") or "."
        
        try:
            key_data = generate_complete_key(
                vault_name=vault_name,
                output_dir=output_dir
            )
            
            print(f"\n[OK] Fichiers clés générés:")
            print(f"     - {key_data.psnx_path}")
            print(f"     - {key_data.blend_path}")
            print(f"\n[IMPORTANT] Conservez ces deux fichiers en lieu sûr!")
            print(f"[IMPORTANT] Les deux fichiers sont nécessaires pour accéder au vault.")
            
            auth.vault_key = key_data.vault_key
            auth.vault_name = vault_name
            auth.authenticated = True
        except Exception as e:
            print(f"[ERREUR] Génération échouée: {e}")
            return
    
    elif method == "3":
        key_hex = input("Clé hexadécimale (64 caractères): ").strip()
        if len(key_hex) != 64:
            print("Clé invalide (doit faire 64 caractères hex = 32 bytes)")
            return
        
        if not auth.authenticate_with_key(vault_name, key_hex):
            print("Clé invalide")
            return
    
    else:
        print("Choix invalide")
        return
    
    # Créer le vault
    if PERSISTENT_AVAILABLE:
        vault = PersistentVaultManager(auth.vault_key, auth.vault_name)
        stats = vault.get_stats()
        
        print(f"\n[OK] Vault '{vault_name}' créé avec succès!")
        print(f"     Chemin: {vault.vault_dir}")
        print(f"     Version: {stats['version']}")
    
    # Sauvegarder la config
    config = VaultConfig()
    config.set('last_vault', vault_name)
    
    print("\n[OK] Configuration terminée!")
    print(f"\nPour lancer le vault:")
    print(f"  python vault_launcher.py gui --vault {vault_name}")


# ============================================================================
# GÉNÉRATION DE CLÉS
# ============================================================================

def generate_keys():
    """Générer de nouvelles clés pour un vault"""
    if not KEYGEN_AVAILABLE:
        print("[ERREUR] Générateur de clés non disponible")
        print("Installez les dépendances: pip install blender-api numpy")
        return
    
    vault_name = input("Nom du vault: ").strip()
    if not vault_name:
        print("Nom invalide")
        return
    
    output_dir = input("Répertoire de sortie (. par défaut): ").strip() or "."
    
    try:
        key_data = generate_complete_key(
            vault_name=vault_name,
            output_dir=output_dir
        )
        
        print(f"\n[OK] Clés générées avec succès!")
        print(f"     Fichier PSNX: {key_data.psnx_path}")
        print(f"     Fichier Blend: {key_data.blend_path}")
        print(f"\n     Clé du vault (hex): {key_data.vault_key.hex()}")
        print(f"\n[IMPORTANT] Sauvegardez ces informations en lieu sûr!")
    
    except Exception as e:
        print(f"[ERREUR] {e}")


# ============================================================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Poly-Spinor Nexus 7D - Lanceur de Vault",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s gui                           # Lancer la GUI avec dialogue d'auth
  %(prog)s gui --vault mon_vault --password
  %(prog)s gui --vault mon_vault --key ABC123...
  %(prog)s cli --vault mon_vault --password
  %(prog)s daemon --vault mon_vault --interval 120
  %(prog)s setup                         # Assistant de configuration
  %(prog)s keygen                        # Générer des clés
        """
    )
    
    parser.add_argument(
        "mode",
        choices=["gui", "cli", "daemon", "setup", "keygen"],
        help="Mode de fonctionnement"
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
        help="Clé hexadécimale du vault"
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
        "--interval", "-i",
        type=int,
        default=60,
        help="Intervalle de monitoring en secondes (mode daemon)"
    )
    
    args = parser.parse_args()
    
    # Modes sans authentification
    if args.mode == "setup":
        run_setup()
        return
    
    if args.mode == "keygen":
        generate_keys()
        return
    
    # Modes avec authentification
    if args.mode == "gui" and not args.vault:
        # Lancer la GUI avec dialogue d'authentification
        launch_gui_with_auth()
        return
    
    # Authentification requise
    if not args.vault:
        print("[ERREUR] --vault requis")
        return
    
    auth = VaultAuthenticator()
    
    if args.psnx and args.blend:
        success, msg = auth.authenticate_with_files(args.psnx, args.blend)
        if not success:
            print(f"[ERREUR] Authentification échouée: {msg}")
            return
    
    elif args.key:
        if not auth.authenticate_with_key(args.vault, args.key):
            print("[ERREUR] Clé invalide")
            return
    
    elif args.password:
        password = getpass.getpass("Mot de passe: ")
        auth.authenticate_with_password(args.vault, password)
    
    else:
        # Par défaut, utiliser le nom du vault comme base de clé (démo)
        print("[INFO] Mode démo - clé dérivée du nom du vault")
        auth.authenticate_with_password(args.vault, args.vault)
    
    # Lancer le mode approprié
    if args.mode == "gui":
        launch_gui(auth)
    
    elif args.mode == "cli":
        cli_interactive(auth)
    
    elif args.mode == "daemon":
        run_daemon(auth, args.interval)


if __name__ == "__main__":
    main()
