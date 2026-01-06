"""
Vault Storage - Stockage persistant sécurisé des clés
Dossier protégé pour le stockage chiffré AES-256-GCM

Fonctionnalités:
- Stockage chiffré AES-256-GCM avec dérivation Scrypt
- Rotation automatique des masques mémoire (toutes les 5 min)
- Expiration configurable des clés
- Backup chiffré automatisé avec vérification d'intégrité
"""

import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.secure_key_storage import (
    SecureKeyStorage,
    VaultKeyStorage,
    create_secure_vault_storage
)

from .vault_backup import (
    VaultBackupManager,
    VaultKeyExpiration,
    BackupMetadata,
    create_vault_backup,
    restore_vault_backup
)

# Chemin par défaut du stockage
VAULT_STORAGE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STORAGE_PATH = os.path.join(VAULT_STORAGE_DIR, 'keys')


def get_vault_storage(password: str, auto_rotate_interval: int = 300) -> VaultKeyStorage:
    """
    Crée ou ouvre le stockage de clés vault persistant.
    
    Args:
        password: Mot de passe pour chiffrer/déchiffrer les clés
        auto_rotate_interval: Intervalle de rotation des masques (défaut: 300s = 5 min)
    
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


def store_key_with_expiration(password: str, user_id: str, vault_key: bytes,
                               expiration_preset: str = "monthly") -> dict:
    """
    Stocke une clé avec expiration configurée.
    
    Args:
        password: Mot de passe du stockage
        user_id: Identifiant utilisateur
        vault_key: Clé à stocker
        expiration_preset: 'session', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'never'
    
    Returns:
        Métadonnées de la clé stockée
    
    Usage:
        from vault_storage import store_key_with_expiration
        
        meta = store_key_with_expiration(
            password="secret",
            user_id="alice",
            vault_key=key_bytes,
            expiration_preset="monthly"  # Expire dans 30 jours
        )
    """
    storage = get_vault_storage(password)
    
    expires_in = VaultKeyExpiration.get_expiration_seconds(expiration_preset)
    
    key_id = f"vault_{user_id}"
    metadata = storage.store_key(
        key_id=key_id,
        key_data=vault_key,
        purpose=f"vault_access",
        expires_in_seconds=expires_in,
        algorithm="AES-256-GCM"
    )
    
    return {
        'key_id': metadata.key_id,
        'created_at': metadata.created_at,
        'expires_at': metadata.expires_at,
        'expiration_preset': expiration_preset,
        'key_size_bits': metadata.key_size_bits
    }


def list_stored_keys(password: str) -> list:
    """Liste toutes les clés stockées avec leur statut d'expiration"""
    storage = get_vault_storage(password)
    keys = storage.list_keys()
    
    result = []
    for key_meta in keys:
        remaining = VaultKeyExpiration.time_remaining(key_meta.expires_at)
        result.append({
            'key_id': key_meta.key_id,
            'created_at': key_meta.created_at,
            'expires_at': key_meta.expires_at,
            'is_expired': VaultKeyExpiration.is_expired(key_meta.expires_at),
            'time_remaining': str(remaining) if remaining else 'never',
            'access_count': key_meta.access_count
        })
    
    return result


def backup_vault(backup_password: str, backup_dir: Optional[str] = None) -> BackupMetadata:
    """
    Crée un backup chiffré du vault.
    
    Args:
        backup_password: Mot de passe pour chiffrer le backup
        backup_dir: Répertoire de destination (défaut: vault_storage/backups)
    
    Returns:
        Métadonnées du backup
    
    Usage:
        from vault_storage import backup_vault
        
        backup = backup_vault("backup_secret")
        print(f"Backup créé: {backup.backup_id}")
        print(f"Fichiers: {backup.files_count}")
    """
    return create_vault_backup(
        vault_dir=VAULT_STORAGE_DIR,
        backup_password=backup_password,
        backup_dir=backup_dir
    )


def restore_vault(backup_password: str, backup_id: str,
                  target_dir: Optional[str] = None) -> tuple:
    """
    Restaure un backup du vault.
    
    Args:
        backup_password: Mot de passe du backup
        backup_id: ID ou nom du backup
        target_dir: Répertoire cible (défaut: vault_storage)
    
    Returns:
        Tuple (succès: bool, détails: dict)
    """
    backup_dir = os.path.join(VAULT_STORAGE_DIR, 'backups')
    manager = VaultBackupManager(VAULT_STORAGE_DIR, backup_dir, backup_password)
    return manager.restore_backup(backup_id, target_dir)


def list_backups(backup_password: str) -> list:
    """Liste tous les backups disponibles"""
    backup_dir = os.path.join(VAULT_STORAGE_DIR, 'backups')
    manager = VaultBackupManager(VAULT_STORAGE_DIR, backup_dir, backup_password)
    return manager.list_backups()


def verify_backup(backup_password: str, backup_id: str) -> tuple:
    """Vérifie l'intégrité d'un backup sans le restaurer"""
    backup_dir = os.path.join(VAULT_STORAGE_DIR, 'backups')
    manager = VaultBackupManager(VAULT_STORAGE_DIR, backup_dir, backup_password)
    return manager.restore_backup(backup_id, verify_only=True)


def storage_info() -> dict:
    """Informations sur le stockage"""
    key_files = [f for f in os.listdir(VAULT_STORAGE_DIR) if f.endswith('.enc')]
    salt_exists = os.path.exists(os.path.join(VAULT_STORAGE_DIR, 'vault_keys.salt'))
    
    backup_dir = os.path.join(VAULT_STORAGE_DIR, 'backups')
    backup_count = 0
    if os.path.exists(backup_dir):
        backup_count = len([f for f in os.listdir(backup_dir) if f.endswith('.vaultbackup')])
    
    return {
        'storage_dir': VAULT_STORAGE_DIR,
        'salt_initialized': salt_exists,
        'encrypted_key_files': len(key_files),
        'key_files': key_files,
        'backup_count': backup_count,
        'backup_dir': backup_dir
    }


# Exports
__all__ = [
    'get_vault_storage',
    'store_key_with_expiration',
    'list_stored_keys',
    'backup_vault',
    'restore_vault',
    'list_backups',
    'verify_backup',
    'storage_info',
    'VaultKeyExpiration',
    'VaultBackupManager',
    'VAULT_STORAGE_DIR'
]
