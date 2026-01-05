"""
Stockage Sécurisé des Clés Cryptographiques
Protection des clés en mémoire et persistance chiffrée

VULN-CRYPTO-06 FIX: Les clés ne sont plus stockées en clair en mémoire.
Utilise le chiffrement AES-GCM avec clé dérivée de mot de passe via Argon2.
"""

import os
import json
import secrets
import hashlib
import tempfile
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import threading
import atexit

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.exceptions import InvalidTag


class SecureKeyStorageError(Exception):
    """Erreur de stockage sécurisé"""
    pass


class KeyNotFoundError(SecureKeyStorageError):
    """Clé non trouvée"""
    pass


class KeyAccessDeniedError(SecureKeyStorageError):
    """Accès à la clé refusé"""
    pass


class KeyExpiredError(SecureKeyStorageError):
    """Clé expirée"""
    pass


@dataclass
class KeyMetadata:
    """Métadonnées d'une clé stockée"""
    key_id: str
    created_at: str
    expires_at: Optional[str]
    purpose: str
    algorithm: str
    key_size_bits: int
    access_count: int = 0
    last_accessed: Optional[str] = None


@dataclass
class EncryptedKeyEntry:
    """Entrée de clé chiffrée"""
    encrypted_key: bytes
    nonce: bytes
    salt: bytes
    metadata: KeyMetadata
    checksum: str


class MemoryProtectedKey:
    """
    Clé protégée en mémoire avec effacement sécurisé.
    
    La clé est stockée XORée avec une clé de masquage aléatoire,
    et démasquée uniquement lors de l'utilisation.
    """
    
    def __init__(self, key_data: bytes):
        """
        Args:
            key_data: Données de clé à protéger
        """
        self._mask = secrets.token_bytes(len(key_data))
        self._masked_key = bytes(a ^ b for a, b in zip(key_data, self._mask))
        self._length = len(key_data)
        self._lock = threading.Lock()
        self._access_count = 0
        
        # Effacer les données originales (best effort en Python)
        # Note: Python ne garantit pas l'effacement mémoire complet
        del key_data
    
    def get_key(self) -> bytes:
        """
        Retourne la clé démasquée.
        
        ATTENTION: La clé retournée doit être utilisée immédiatement
        et ne pas être stockée dans des variables longue durée.
        """
        with self._lock:
            self._access_count += 1
            return bytes(a ^ b for a, b in zip(self._masked_key, self._mask))
    
    def rotate_mask(self):
        """Rotation du masque pour une protection supplémentaire"""
        with self._lock:
            # Récupérer la clé actuelle
            current_key = bytes(a ^ b for a, b in zip(self._masked_key, self._mask))
            
            # Nouveau masque
            new_mask = secrets.token_bytes(self._length)
            
            # Re-masquer
            self._masked_key = bytes(a ^ b for a, b in zip(current_key, new_mask))
            self._mask = new_mask
            
            # Effacer
            del current_key
    
    def secure_delete(self):
        """Effacement sécurisé de la clé"""
        with self._lock:
            # Écraser avec des zéros puis des données aléatoires
            self._masked_key = bytes(self._length)
            self._mask = bytes(self._length)
            self._masked_key = secrets.token_bytes(self._length)
            self._mask = secrets.token_bytes(self._length)
            self._length = 0
    
    @property
    def access_count(self) -> int:
        return self._access_count
    
    def __del__(self):
        """Effacement à la destruction"""
        try:
            self.secure_delete()
        except:
            pass


class SecureKeyDerivation:
    """Dérivation sécurisée de clés à partir de mots de passe"""
    
    # Paramètres Scrypt recommandés pour 2024+
    SCRYPT_N = 2**17  # CPU/memory cost
    SCRYPT_R = 8      # Block size
    SCRYPT_P = 1      # Parallelization
    
    @classmethod
    def derive_key_from_password(cls, password: str, salt: bytes,
                                  key_length: int = 32) -> bytes:
        """
        Dérive une clé à partir d'un mot de passe via Scrypt.
        
        Args:
            password: Mot de passe utilisateur
            salt: Sel aléatoire (16+ bytes recommandé)
            key_length: Longueur de clé souhaitée
        
        Returns:
            Clé dérivée
        """
        kdf = Scrypt(
            salt=salt,
            length=key_length,
            n=cls.SCRYPT_N,
            r=cls.SCRYPT_R,
            p=cls.SCRYPT_P
        )
        return kdf.derive(password.encode('utf-8'))
    
    @classmethod
    def derive_subkey(cls, master_key: bytes, purpose: str, 
                      key_length: int = 32) -> bytes:
        """
        Dérive une sous-clé pour un usage spécifique via HKDF.
        
        Args:
            master_key: Clé maître
            purpose: Description de l'usage
            key_length: Longueur souhaitée
        
        Returns:
            Sous-clé dérivée
        """
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=key_length,
            salt=None,
            info=purpose.encode('utf-8')
        )
        return hkdf.derive(master_key)


class SecureKeyStorage:
    """
    Stockage sécurisé des clés cryptographiques.
    
    Fonctionnalités:
    - Clés protégées en mémoire (masquage XOR)
    - Persistance chiffrée avec AES-256-GCM
    - Clé de chiffrement dérivée du mot de passe via Scrypt
    - Expiration automatique des clés
    - Rotation des masques mémoire
    - Effacement sécurisé
    """
    
    def __init__(self, storage_password: Optional[str] = None,
                 storage_path: Optional[str] = None,
                 auto_rotate_interval: int = 300):
        """
        Args:
            storage_password: Mot de passe pour le chiffrement persistant
            storage_path: Chemin du fichier de stockage (None = mémoire seule)
            auto_rotate_interval: Intervalle de rotation des masques (secondes)
        """
        self._keys: Dict[str, MemoryProtectedKey] = {}
        self._metadata: Dict[str, KeyMetadata] = {}
        self._storage_path = storage_path
        self._lock = threading.RLock()
        
        # Clé de chiffrement pour la persistance
        self._storage_salt: Optional[bytes] = None
        self._storage_key: Optional[bytes] = None
        
        if storage_password:
            self._init_storage_encryption(storage_password)
        
        # Rotation automatique des masques
        self._rotation_interval = auto_rotate_interval
        self._rotation_thread: Optional[threading.Thread] = None
        self._stop_rotation = threading.Event()
        
        if auto_rotate_interval > 0:
            self._start_rotation_thread()
        
        # Effacement à la sortie
        atexit.register(self.secure_clear_all)
    
    def _init_storage_encryption(self, password: str):
        """Initialise le chiffrement de stockage"""
        # Charger ou générer le sel
        if self._storage_path and os.path.exists(self._storage_path + '.salt'):
            with open(self._storage_path + '.salt', 'rb') as f:
                self._storage_salt = f.read()
        else:
            self._storage_salt = secrets.token_bytes(32)
            if self._storage_path:
                os.makedirs(os.path.dirname(self._storage_path) or '.', exist_ok=True)
                with open(self._storage_path + '.salt', 'wb') as f:
                    f.write(self._storage_salt)
        
        # Dériver la clé de stockage
        self._storage_key = SecureKeyDerivation.derive_key_from_password(
            password, self._storage_salt
        )
    
    def _start_rotation_thread(self):
        """Démarre le thread de rotation des masques"""
        def rotation_worker():
            while not self._stop_rotation.wait(self._rotation_interval):
                self._rotate_all_masks()
        
        self._rotation_thread = threading.Thread(target=rotation_worker, daemon=True)
        self._rotation_thread.start()
    
    def _rotate_all_masks(self):
        """Rotation de tous les masques de clés"""
        with self._lock:
            for key in self._keys.values():
                key.rotate_mask()
    
    def store_key(self, key_id: str, key_data: bytes, 
                  purpose: str = "general",
                  expires_in_seconds: Optional[int] = None,
                  algorithm: str = "AES-256") -> KeyMetadata:
        """
        Stocke une clé de manière sécurisée.
        
        Args:
            key_id: Identifiant unique de la clé
            key_data: Données de la clé
            purpose: But de la clé
            expires_in_seconds: Durée de validité (None = pas d'expiration)
            algorithm: Algorithme associé
        
        Returns:
            Métadonnées de la clé
        """
        with self._lock:
            # Créer les métadonnées
            now = datetime.utcnow()
            expires_at = None
            if expires_in_seconds:
                expires_at = (now + timedelta(seconds=expires_in_seconds)).isoformat()
            
            metadata = KeyMetadata(
                key_id=key_id,
                created_at=now.isoformat(),
                expires_at=expires_at,
                purpose=purpose,
                algorithm=algorithm,
                key_size_bits=len(key_data) * 8
            )
            
            # Stocker en mémoire protégée
            self._keys[key_id] = MemoryProtectedKey(key_data)
            self._metadata[key_id] = metadata
            
            # Persister si configuré
            if self._storage_path and self._storage_key:
                self._persist_key(key_id)
            
            return metadata
    
    def retrieve_key(self, key_id: str) -> bytes:
        """
        Récupère une clé.
        
        Args:
            key_id: Identifiant de la clé
        
        Returns:
            Données de la clé
        
        Raises:
            KeyNotFoundError: Si la clé n'existe pas
            KeyExpiredError: Si la clé a expiré
        """
        with self._lock:
            if key_id not in self._keys:
                # Tenter de charger depuis le stockage persistant
                if self._storage_path and self._storage_key:
                    self._load_key(key_id)
                
                if key_id not in self._keys:
                    raise KeyNotFoundError(f"Clé '{key_id}' non trouvée")
            
            # Vérifier l'expiration
            metadata = self._metadata[key_id]
            if metadata.expires_at:
                expires = datetime.fromisoformat(metadata.expires_at)
                if datetime.utcnow() > expires:
                    self.delete_key(key_id)
                    raise KeyExpiredError(f"Clé '{key_id}' expirée")
            
            # Mettre à jour les métadonnées
            metadata.access_count += 1
            metadata.last_accessed = datetime.utcnow().isoformat()
            
            return self._keys[key_id].get_key()
    
    def delete_key(self, key_id: str):
        """Supprime une clé de manière sécurisée"""
        with self._lock:
            if key_id in self._keys:
                self._keys[key_id].secure_delete()
                del self._keys[key_id]
            
            if key_id in self._metadata:
                del self._metadata[key_id]
            
            # Supprimer du stockage persistant
            if self._storage_path:
                key_file = f"{self._storage_path}.{key_id}.enc"
                if os.path.exists(key_file):
                    # Écraser avant suppression
                    with open(key_file, 'wb') as f:
                        f.write(secrets.token_bytes(1024))
                    os.remove(key_file)
    
    def _persist_key(self, key_id: str):
        """Persiste une clé de manière chiffrée"""
        if not self._storage_key:
            return
        
        key_data = self._keys[key_id].get_key()
        metadata = self._metadata[key_id]
        
        # Générer nonce et chiffrer
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(self._storage_key)
        
        # Données à chiffrer: clé + métadonnées JSON
        plaintext = json.dumps({
            'key': key_data.hex(),
            'metadata': {
                'key_id': metadata.key_id,
                'created_at': metadata.created_at,
                'expires_at': metadata.expires_at,
                'purpose': metadata.purpose,
                'algorithm': metadata.algorithm,
                'key_size_bits': metadata.key_size_bits
            }
        }).encode()
        
        ciphertext = aesgcm.encrypt(nonce, plaintext, key_id.encode())
        
        # Sauvegarder
        key_file = f"{self._storage_path}.{key_id}.enc"
        with open(key_file, 'wb') as f:
            f.write(nonce + ciphertext)
    
    def _load_key(self, key_id: str):
        """Charge une clé depuis le stockage persistant"""
        if not self._storage_key:
            return
        
        key_file = f"{self._storage_path}.{key_id}.enc"
        if not os.path.exists(key_file):
            return
        
        with open(key_file, 'rb') as f:
            data = f.read()
        
        nonce = data[:12]
        ciphertext = data[12:]
        
        aesgcm = AESGCM(self._storage_key)
        
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, key_id.encode())
            obj = json.loads(plaintext.decode())
            
            key_data = bytes.fromhex(obj['key'])
            meta = obj['metadata']
            
            self._keys[key_id] = MemoryProtectedKey(key_data)
            self._metadata[key_id] = KeyMetadata(
                key_id=meta['key_id'],
                created_at=meta['created_at'],
                expires_at=meta['expires_at'],
                purpose=meta['purpose'],
                algorithm=meta['algorithm'],
                key_size_bits=meta['key_size_bits']
            )
        except InvalidTag:
            raise KeyAccessDeniedError(f"Échec du déchiffrement de la clé '{key_id}'")
    
    def list_keys(self) -> List[KeyMetadata]:
        """Liste toutes les clés avec leurs métadonnées"""
        with self._lock:
            return list(self._metadata.values())
    
    def key_exists(self, key_id: str) -> bool:
        """Vérifie si une clé existe"""
        return key_id in self._keys
    
    def get_metadata(self, key_id: str) -> Optional[KeyMetadata]:
        """Récupère les métadonnées d'une clé"""
        return self._metadata.get(key_id)
    
    def secure_clear_all(self):
        """Efface toutes les clés de manière sécurisée"""
        with self._lock:
            for key in self._keys.values():
                key.secure_delete()
            self._keys.clear()
            self._metadata.clear()
            
            # Effacer la clé de stockage
            if self._storage_key:
                self._storage_key = secrets.token_bytes(32)
                self._storage_key = None
    
    def rotate_storage_password(self, old_password: str, new_password: str):
        """Change le mot de passe de stockage"""
        with self._lock:
            # Vérifier l'ancien mot de passe
            old_key = SecureKeyDerivation.derive_key_from_password(
                old_password, self._storage_salt
            )
            if old_key != self._storage_key:
                raise KeyAccessDeniedError("Mot de passe incorrect")
            
            # Nouveau sel et nouvelle clé
            new_salt = secrets.token_bytes(32)
            new_key = SecureKeyDerivation.derive_key_from_password(
                new_password, new_salt
            )
            
            # Re-chiffrer toutes les clés persistées
            old_storage_key = self._storage_key
            self._storage_key = new_key
            self._storage_salt = new_salt
            
            # Sauvegarder le nouveau sel
            if self._storage_path:
                with open(self._storage_path + '.salt', 'wb') as f:
                    f.write(new_salt)
            
            # Re-persister toutes les clés
            for key_id in self._keys:
                self._persist_key(key_id)
            
            # Effacer l'ancienne clé
            del old_key
            del old_storage_key
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop_rotation.set()
        self.secure_clear_all()
        return False


class VaultKeyStorage(SecureKeyStorage):
    """
    Extension de SecureKeyStorage spécifique pour le MaterialVault.
    
    Fournit des méthodes de convenance pour la gestion des clés vault.
    """
    
    def store_vault_key(self, user_id: str, vault_key: bytes,
                        access_level: str = "read") -> KeyMetadata:
        """Stocke une clé vault pour un utilisateur"""
        key_id = f"vault_{user_id}"
        return self.store_key(
            key_id=key_id,
            key_data=vault_key,
            purpose=f"vault_access_{access_level}",
            algorithm="AES-256-GCM"
        )
    
    def get_vault_key(self, user_id: str) -> bytes:
        """Récupère la clé vault d'un utilisateur"""
        key_id = f"vault_{user_id}"
        return self.retrieve_key(key_id)
    
    def delete_vault_key(self, user_id: str):
        """Supprime la clé vault d'un utilisateur"""
        key_id = f"vault_{user_id}"
        self.delete_key(key_id)
    
    def vault_key_exists(self, user_id: str) -> bool:
        """Vérifie si un utilisateur a une clé vault"""
        return self.key_exists(f"vault_{user_id}")


def create_secure_vault_storage(password: str, 
                                 storage_dir: Optional[str] = None) -> VaultKeyStorage:
    """
    Crée un stockage sécurisé pour les clés vault.
    
    Args:
        password: Mot de passe de protection
        storage_dir: Répertoire de stockage (None = temp)
    
    Returns:
        VaultKeyStorage configuré
    """
    if storage_dir is None:
        storage_dir = os.path.join(tempfile.gettempdir(), 'poly_spinor_vault')
    
    os.makedirs(storage_dir, exist_ok=True)
    storage_path = os.path.join(storage_dir, 'vault_keys')
    
    return VaultKeyStorage(
        storage_password=password,
        storage_path=storage_path,
        auto_rotate_interval=300  # Rotation toutes les 5 minutes
    )
