#!/usr/bin/env python
"""
Script d'initialisation et de test du stockage persistant des clés vault
"""

import os
import sys
import secrets
import getpass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vault_storage import get_vault_storage, storage_info, VAULT_STORAGE_DIR


def init_storage():
    """Initialise le stockage avec un nouveau mot de passe"""
    print("=" * 60)
    print("  INITIALISATION DU STOCKAGE VAULT PERSISTANT")
    print("=" * 60)
    print(f"\nDossier de stockage: {VAULT_STORAGE_DIR}")
    
    # Vérifier l'état actuel
    info = storage_info()
    if info['salt_initialized']:
        print(f"\n[!] Un stockage existe déjà ({info['encrypted_key_files']} clé(s))")
        confirm = input("Voulez-vous le réinitialiser? (oui/non): ")
        if confirm.lower() != 'oui':
            print("Annulé.")
            return False
    
    # Demander le mot de passe
    print("\nCréation d'un nouveau stockage sécurisé.")
    print("ATTENTION: Ce mot de passe ne peut pas être récupéré!")
    
    password = getpass.getpass("Nouveau mot de passe: ")
    password_confirm = getpass.getpass("Confirmer le mot de passe: ")
    
    if password != password_confirm:
        print("[ERREUR] Les mots de passe ne correspondent pas!")
        return False
    
    if len(password) < 8:
        print("[ERREUR] Le mot de passe doit faire au moins 8 caractères!")
        return False
    
    # Initialiser le stockage
    storage = get_vault_storage(password)
    
    # Créer une clé de test
    test_key = secrets.token_bytes(64)
    storage.store_vault_key(
        user_id="__init_test__",
        vault_key=test_key,
        access_level="system"
    )
    
    # Vérifier
    retrieved = storage.get_vault_key("__init_test__")
    if retrieved == test_key:
        print("\n[OK] Stockage initialisé avec succès!")
        print(f"[OK] Fichiers créés dans: {VAULT_STORAGE_DIR}")
        
        # Supprimer la clé de test
        storage.delete_vault_key("__init_test__")
        storage.secure_clear_all()
        return True
    else:
        print("[ERREUR] Échec de la vérification!")
        return False


def test_storage():
    """Teste le stockage existant"""
    print("=" * 60)
    print("  TEST DU STOCKAGE VAULT")
    print("=" * 60)
    
    info = storage_info()
    print(f"\nDossier: {info['storage_dir']}")
    print(f"Salt initialisé: {info['salt_initialized']}")
    print(f"Fichiers chiffrés: {info['encrypted_key_files']}")
    
    if not info['salt_initialized']:
        print("\n[!] Stockage non initialisé. Exécutez d'abord l'initialisation.")
        return False
    
    password = getpass.getpass("\nMot de passe du stockage: ")
    
    try:
        storage = get_vault_storage(password)
        
        # Créer une clé de test
        print("\nCréation d'une clé de test...")
        test_key = secrets.token_bytes(64)
        storage.store_vault_key(
            user_id="test_user",
            vault_key=test_key,
            access_level="test"
        )
        print("[OK] Clé stockée")
        
        # Récupérer
        retrieved = storage.get_vault_key("test_user")
        if retrieved == test_key:
            print("[OK] Clé récupérée correctement")
        else:
            print("[ERREUR] Clé corrompue!")
            return False
        
        # Lister
        keys = storage.list_keys()
        print(f"[OK] Clés dans le stockage: {len(keys)}")
        for key_id in keys:
            print(f"    - {key_id}")
        
        # Nettoyer
        storage.delete_vault_key("test_user")
        print("[OK] Clé de test supprimée")
        
        storage.secure_clear_all()
        print("\n[OK] Test réussi!")
        return True
        
    except Exception as e:
        print(f"\n[ERREUR] {e}")
        return False


def show_info():
    """Affiche les informations du stockage"""
    print("=" * 60)
    print("  INFORMATIONS STOCKAGE VAULT")
    print("=" * 60)
    
    info = storage_info()
    print(f"\nDossier: {info['storage_dir']}")
    print(f"Salt initialisé: {'Oui' if info['salt_initialized'] else 'Non'}")
    print(f"Fichiers chiffrés: {info['encrypted_key_files']}")
    
    if info['key_files']:
        print("\nFichiers de clés:")
        for f in info['key_files']:
            filepath = os.path.join(info['storage_dir'], f)
            size = os.path.getsize(filepath)
            print(f"  - {f} ({size} bytes)")


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'init':
            init_storage()
        elif cmd == 'test':
            test_storage()
        elif cmd == 'info':
            show_info()
        else:
            print(f"Commande inconnue: {cmd}")
            print("Usage: python init_storage.py [init|test|info]")
    else:
        print("Eidolon - Gestion du Stockage Vault")
        print("\nCommandes:")
        print("  python init_storage.py init  - Initialiser le stockage")
        print("  python init_storage.py test  - Tester le stockage")
        print("  python init_storage.py info  - Afficher les informations")


if __name__ == "__main__":
    main()
