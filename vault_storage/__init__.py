"""
Vault Storage - Stockage persistant sécurisé des clés
Dossier protégé pour le stockage chiffré AES-256-GCM
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.secure_key_storage import (
    SecureKeyStorage,
    VaultKeyStorage,
    create_secure_vault_storage
)

# Chemin par défaut du stockage
VAULT_STORAGE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STORAGE_PATH = os.path.join(VAULT_STORAGE_DIR, 'keys')


def get_vault_storage(password: str) -> VaultKeyStorage:
    """
    Crée ou ouvre le stockage de clés vault persistant.
    
    Args:
        password: Mot de passe pour chiffrer/déchiffrer les clés
    
    Returns:
        VaultKeyStorage configuré avec stockage persistant
    
    Usage:
        from poly_spinor_nexus_7d.vault_storage import get_vault_storage
        
        storage = get_vault_storage("mon_mot_de_passe")
        storage.store_vault_key("user_123", vault_key_bytes)
        key = storage.get_vault_key("user_123")
    """
    return create_secure_vault_storage(
        password=password,
        storage_dir=VAULT_STORAGE_DIR
    )


def list_stored_keys(password: str) -> list:
    """Liste toutes les clés stockées"""
    storage = get_vault_storage(password)
    return storage.list_keys()


def storage_info() -> dict:
    """Informations sur le stockage"""
    key_files = [f for f in os.listdir(VAULT_STORAGE_DIR) if f.endswith('.enc')]
    salt_exists = os.path.exists(os.path.join(VAULT_STORAGE_DIR, 'vault_keys.salt'))
    
    return {
        'storage_dir': VAULT_STORAGE_DIR,
        'salt_initialized': salt_exists,
        'encrypted_key_files': len(key_files),
        'key_files': key_files
    }
