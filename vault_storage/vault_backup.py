"""
Système de Backup Automatisé pour le Vault
Sauvegarde chiffrée des fichiers .enc avec vérification d'intégrité
"""

import os
import shutil
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


@dataclass
class BackupMetadata:
    """Métadonnées d'un backup"""
    backup_id: str
    created_at: str
    source_dir: str
    files_count: int
    total_size: int
    integrity_hash: str
    encrypted: bool


class VaultBackupManager:
    """
    Gestionnaire de backup pour les fichiers vault.
    
    Fonctionnalités:
    - Backup chiffré de tous les fichiers .enc et .salt
    - Vérification d'intégrité SHA-256
    - Rotation automatique des anciens backups
    - Restauration sécurisée
    """
    
    BACKUP_EXTENSION = ".vaultbackup"
    MAX_BACKUPS = 5  # Nombre max de backups à conserver
    
    def __init__(self, vault_dir: str, backup_dir: Optional[str] = None,
                 backup_password: Optional[str] = None):
        """
        Args:
            vault_dir: Répertoire du vault source
            backup_dir: Répertoire de destination des backups (défaut: vault_dir/backups)
            backup_password: Mot de passe pour chiffrer les backups (optionnel)
        """
        self.vault_dir = Path(vault_dir)
        self.backup_dir = Path(backup_dir) if backup_dir else self.vault_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self._backup_key: Optional[bytes] = None
        if backup_password:
            self._init_backup_encryption(backup_password)
    
    def _init_backup_encryption(self, password: str):
        """Initialise le chiffrement des backups"""
        salt_file = self.backup_dir / "backup.salt"
        
        if salt_file.exists():
            salt = salt_file.read_bytes()
        else:
            salt = secrets.token_bytes(32)
            salt_file.write_bytes(salt)
        
        kdf = Scrypt(salt=salt, length=32, n=2**17, r=8, p=1)
        self._backup_key = kdf.derive(password.encode('utf-8'))
    
    def _compute_file_hash(self, filepath: Path) -> str:
        """Calcule le hash SHA-256 d'un fichier"""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _compute_backup_hash(self, files_data: Dict[str, bytes]) -> str:
        """Calcule le hash d'intégrité du backup complet"""
        combined = b''
        for name in sorted(files_data.keys()):
            combined += name.encode() + files_data[name]
        return hashlib.sha256(combined).hexdigest()
    
    def _encrypt_backup_data(self, data: bytes) -> bytes:
        """Chiffre les données du backup"""
        if not self._backup_key:
            return data
        
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(self._backup_key)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext
    
    def _decrypt_backup_data(self, encrypted_data: bytes) -> bytes:
        """Déchiffre les données du backup"""
        if not self._backup_key:
            return encrypted_data
        
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        aesgcm = AESGCM(self._backup_key)
        return aesgcm.decrypt(nonce, ciphertext, None)
    
    def create_backup(self, include_salt: bool = True) -> BackupMetadata:
        """
        Crée un backup complet du vault.
        
        Args:
            include_salt: Inclure le fichier .salt (recommandé)
        
        Returns:
            Métadonnées du backup créé
        """
        backup_id = f"vault_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Collecter les fichiers à sauvegarder
        files_to_backup: Dict[str, bytes] = {}
        total_size = 0
        
        for filepath in self.vault_dir.iterdir():
            if filepath.suffix == '.enc' or (include_salt and filepath.suffix == '.salt'):
                file_data = filepath.read_bytes()
                files_to_backup[filepath.name] = file_data
                total_size += len(file_data)
        
        if not files_to_backup:
            raise ValueError("Aucun fichier à sauvegarder")
        
        # Calculer le hash d'intégrité
        integrity_hash = self._compute_backup_hash(files_to_backup)
        
        # Créer le package de backup (JSON + données binaires)
        backup_package = {
            'metadata': {
                'backup_id': backup_id,
                'created_at': datetime.now().isoformat(),
                'source_dir': str(self.vault_dir),
                'files_count': len(files_to_backup),
                'total_size': total_size,
                'integrity_hash': integrity_hash,
                'encrypted': self._backup_key is not None
            },
            'files': {name: data.hex() for name, data in files_to_backup.items()}
        }
        
        # Sérialiser et optionnellement chiffrer
        backup_bytes = json.dumps(backup_package).encode('utf-8')
        final_data = self._encrypt_backup_data(backup_bytes)
        
        # Sauvegarder
        backup_path = self.backup_dir / f"{backup_id}{self.BACKUP_EXTENSION}"
        backup_path.write_bytes(final_data)
        
        # Rotation des anciens backups
        self._rotate_old_backups()
        
        return BackupMetadata(**backup_package['metadata'])
    
    def _rotate_old_backups(self):
        """Supprime les backups excédentaires (garde les plus récents)"""
        backups = sorted(
            self.backup_dir.glob(f"*{self.BACKUP_EXTENSION}"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for old_backup in backups[self.MAX_BACKUPS:]:
            # Écraser avant suppression
            old_backup.write_bytes(secrets.token_bytes(old_backup.stat().st_size))
            old_backup.unlink()
    
    def list_backups(self) -> List[Dict]:
        """Liste tous les backups disponibles"""
        backups = []
        
        for backup_file in self.backup_dir.glob(f"*{self.BACKUP_EXTENSION}"):
            try:
                data = backup_file.read_bytes()
                decrypted = self._decrypt_backup_data(data)
                package = json.loads(decrypted.decode('utf-8'))
                
                backups.append({
                    'file': backup_file.name,
                    'size': backup_file.stat().st_size,
                    **package['metadata']
                })
            except Exception as e:
                backups.append({
                    'file': backup_file.name,
                    'size': backup_file.stat().st_size,
                    'error': str(e)
                })
        
        return sorted(backups, key=lambda x: x.get('created_at', ''), reverse=True)
    
    def restore_backup(self, backup_id: str, 
                       target_dir: Optional[str] = None,
                       verify_only: bool = False) -> Tuple[bool, Dict]:
        """
        Restaure un backup.
        
        Args:
            backup_id: ID du backup ou nom de fichier
            target_dir: Répertoire cible (défaut: vault_dir)
            verify_only: Vérifier sans restaurer
        
        Returns:
            Tuple (succès, détails)
        """
        # Trouver le fichier backup
        backup_file = None
        for f in self.backup_dir.glob(f"*{self.BACKUP_EXTENSION}"):
            if backup_id in f.name:
                backup_file = f
                break
        
        if not backup_file:
            return False, {'error': f"Backup '{backup_id}' non trouvé"}
        
        # Charger et déchiffrer
        try:
            data = backup_file.read_bytes()
            decrypted = self._decrypt_backup_data(data)
            package = json.loads(decrypted.decode('utf-8'))
        except Exception as e:
            return False, {'error': f"Erreur déchiffrement: {e}"}
        
        # Reconstituer les fichiers
        files_data = {name: bytes.fromhex(hex_data) 
                      for name, hex_data in package['files'].items()}
        
        # Vérifier l'intégrité
        computed_hash = self._compute_backup_hash(files_data)
        expected_hash = package['metadata']['integrity_hash']
        
        if computed_hash != expected_hash:
            return False, {
                'error': 'Échec vérification intégrité',
                'expected': expected_hash,
                'computed': computed_hash
            }
        
        if verify_only:
            return True, {
                'verified': True,
                'files': list(files_data.keys()),
                'integrity_hash': computed_hash
            }
        
        # Restaurer
        target = Path(target_dir) if target_dir else self.vault_dir
        target.mkdir(parents=True, exist_ok=True)
        
        restored_files = []
        for name, data in files_data.items():
            filepath = target / name
            filepath.write_bytes(data)
            restored_files.append(str(filepath))
        
        return True, {
            'restored': True,
            'files': restored_files,
            'target_dir': str(target)
        }
    
    def verify_vault_integrity(self) -> Dict:
        """Vérifie l'intégrité des fichiers vault actuels"""
        results = {
            'status': 'ok',
            'files': [],
            'issues': []
        }
        
        for filepath in self.vault_dir.iterdir():
            if filepath.suffix in ('.enc', '.salt'):
                file_hash = self._compute_file_hash(filepath)
                results['files'].append({
                    'name': filepath.name,
                    'size': filepath.stat().st_size,
                    'hash': file_hash
                })
        
        if not results['files']:
            results['status'] = 'empty'
            results['issues'].append("Aucun fichier vault trouvé")
        
        return results


class VaultKeyExpiration:
    """
    Gestionnaire d'expiration des clés vault.
    
    Fournit des utilitaires pour configurer et vérifier l'expiration des clés.
    """
    
    # Durées prédéfinies
    EXPIRATION_PRESETS = {
        'session': 3600,           # 1 heure
        'daily': 86400,            # 24 heures
        'weekly': 604800,          # 7 jours
        'monthly': 2592000,        # 30 jours
        'quarterly': 7776000,      # 90 jours
        'yearly': 31536000,        # 365 jours
        'never': None              # Pas d'expiration
    }
    
    @classmethod
    def get_expiration_seconds(cls, preset: str) -> Optional[int]:
        """
        Retourne la durée d'expiration pour un preset donné.
        
        Args:
            preset: Nom du preset ('session', 'daily', 'weekly', etc.)
        
        Returns:
            Durée en secondes ou None pour pas d'expiration
        """
        return cls.EXPIRATION_PRESETS.get(preset.lower())
    
    @classmethod
    def calculate_expiry_date(cls, preset: str) -> Optional[str]:
        """Calcule la date d'expiration ISO"""
        seconds = cls.get_expiration_seconds(preset)
        if seconds is None:
            return None
        return (datetime.utcnow() + timedelta(seconds=seconds)).isoformat()
    
    @classmethod
    def is_expired(cls, expires_at: Optional[str]) -> bool:
        """Vérifie si une date d'expiration est passée"""
        if expires_at is None:
            return False
        return datetime.utcnow() > datetime.fromisoformat(expires_at)
    
    @classmethod
    def time_remaining(cls, expires_at: Optional[str]) -> Optional[timedelta]:
        """Retourne le temps restant avant expiration"""
        if expires_at is None:
            return None
        remaining = datetime.fromisoformat(expires_at) - datetime.utcnow()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)


def create_vault_backup(vault_dir: str, backup_password: str,
                        backup_dir: Optional[str] = None) -> BackupMetadata:
    """
    Fonction utilitaire pour créer un backup rapidement.
    
    Args:
        vault_dir: Répertoire du vault
        backup_password: Mot de passe de chiffrement du backup
        backup_dir: Répertoire de destination (optionnel)
    
    Returns:
        Métadonnées du backup
    
    Usage:
        from vault_storage.vault_backup import create_vault_backup
        
        backup = create_vault_backup(
            vault_dir="~/.poly_spinor_vault",
            backup_password="backup_secret_123"
        )
        print(f"Backup créé: {backup.backup_id}")
    """
    manager = VaultBackupManager(vault_dir, backup_dir, backup_password)
    return manager.create_backup()


def restore_vault_backup(backup_dir: str, backup_id: str,
                         backup_password: str,
                         target_dir: Optional[str] = None) -> Tuple[bool, Dict]:
    """
    Fonction utilitaire pour restaurer un backup.
    
    Args:
        backup_dir: Répertoire contenant les backups
        backup_id: ID du backup à restaurer
        backup_password: Mot de passe de déchiffrement
        target_dir: Répertoire cible (optionnel)
    
    Returns:
        Tuple (succès, détails)
    """
    manager = VaultBackupManager(backup_dir, backup_dir, backup_password)
    return manager.restore_backup(backup_id, target_dir)
