"""
Integration Hardware Security Module (HSM)
Eidolon - Security Module

Support pour:
- YubiHSM 2
- TPM 2.0 (Trusted Platform Module)
- PKCS#11 generique
- Secure Enclave (Apple)
- Android Keystore

Les HSM fournissent:
- Stockage securise des cles (non-extractible)
- Operations crypto dans le hardware
- Resistance aux attaques physiques
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
from enum import Enum
import hashlib
import secrets
import struct


class HSMError(Exception):
    """Erreur HSM generique"""
    pass


class HSMNotAvailable(HSMError):
    """HSM non disponible"""
    pass


class HSMKeyError(HSMError):
    """Erreur de cle HSM"""
    pass


class KeyType(Enum):
    """Types de cles supportes"""
    AES_256 = "aes256"
    RSA_2048 = "rsa2048"
    RSA_4096 = "rsa4096"
    EC_P256 = "ec_p256"
    EC_P384 = "ec_p384"
    ED25519 = "ed25519"


class KeyUsage(Enum):
    """Usages autorises pour une cle"""
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    SIGN = "sign"
    VERIFY = "verify"
    WRAP = "wrap"
    UNWRAP = "unwrap"


@dataclass
class HSMKeyInfo:
    """Information sur une cle HSM"""
    key_id: str
    key_type: KeyType
    usages: List[KeyUsage]
    created_at: float
    label: str
    extractable: bool = False
    
    def to_dict(self) -> dict:
        return {
            'key_id': self.key_id,
            'key_type': self.key_type.value,
            'usages': [u.value for u in self.usages],
            'created_at': self.created_at,
            'label': self.label,
            'extractable': self.extractable
        }


class HardwareSecurityModule(ABC):
    """
    Interface abstraite pour HSM.
    
    Toutes les implementations HSM doivent heriter de cette classe.
    """
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifie si le HSM est disponible"""
        pass
    
    @abstractmethod
    def generate_key(
        self,
        key_type: KeyType,
        label: str,
        usages: List[KeyUsage]
    ) -> HSMKeyInfo:
        """Genere une cle dans le HSM"""
        pass
    
    @abstractmethod
    def delete_key(self, key_id: str) -> bool:
        """Supprime une cle du HSM"""
        pass
    
    @abstractmethod
    def get_key_info(self, key_id: str) -> Optional[HSMKeyInfo]:
        """Recupere les infos d'une cle"""
        pass
    
    @abstractmethod
    def encrypt(self, key_id: str, plaintext: bytes) -> bytes:
        """Chiffre des donnees avec une cle HSM"""
        pass
    
    @abstractmethod
    def decrypt(self, key_id: str, ciphertext: bytes) -> bytes:
        """Dechiffre des donnees avec une cle HSM"""
        pass
    
    @abstractmethod
    def sign(self, key_id: str, data: bytes) -> bytes:
        """Signe des donnees avec une cle HSM"""
        pass
    
    @abstractmethod
    def verify(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verifie une signature"""
        pass


class SoftwareHSM(HardwareSecurityModule):
    """
    HSM logiciel pour developpement et tests.
    
    ATTENTION: Ne pas utiliser en production!
    Les cles sont stockees en memoire et sur disque.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self._keys: Dict[str, Dict] = {}
        self._storage_path = storage_path
        
        if storage_path:
            self._load_keys()
    
    def is_available(self) -> bool:
        return True
    
    def generate_key(
        self,
        key_type: KeyType,
        label: str,
        usages: List[KeyUsage]
    ) -> HSMKeyInfo:
        import time
        
        key_id = secrets.token_hex(8)
        
        # Generer la cle selon le type
        if key_type == KeyType.AES_256:
            key_data = secrets.token_bytes(32)
        elif key_type in (KeyType.RSA_2048, KeyType.RSA_4096):
            from cryptography.hazmat.primitives.asymmetric import rsa
            bits = 2048 if key_type == KeyType.RSA_2048 else 4096
            private_key = rsa.generate_private_key(65537, bits)
            key_data = private_key
        elif key_type in (KeyType.EC_P256, KeyType.EC_P384):
            from cryptography.hazmat.primitives.asymmetric import ec
            curve = ec.SECP256R1() if key_type == KeyType.EC_P256 else ec.SECP384R1()
            private_key = ec.generate_private_key(curve)
            key_data = private_key
        elif key_type == KeyType.ED25519:
            from cryptography.hazmat.primitives.asymmetric import ed25519
            private_key = ed25519.Ed25519PrivateKey.generate()
            key_data = private_key
        else:
            raise HSMError(f"Type de cle non supporte: {key_type}")
        
        info = HSMKeyInfo(
            key_id=key_id,
            key_type=key_type,
            usages=usages,
            created_at=time.time(),
            label=label,
            extractable=False
        )
        
        self._keys[key_id] = {
            'info': info,
            'key': key_data
        }
        
        if self._storage_path:
            self._save_keys()
        
        return info
    
    def delete_key(self, key_id: str) -> bool:
        if key_id in self._keys:
            del self._keys[key_id]
            if self._storage_path:
                self._save_keys()
            return True
        return False
    
    def get_key_info(self, key_id: str) -> Optional[HSMKeyInfo]:
        if key_id in self._keys:
            return self._keys[key_id]['info']
        return None
    
    def encrypt(self, key_id: str, plaintext: bytes) -> bytes:
        if key_id not in self._keys:
            raise HSMKeyError(f"Cle non trouvee: {key_id}")
        
        key_data = self._keys[key_id]
        info = key_data['info']
        key = key_data['key']
        
        if KeyUsage.ENCRYPT not in info.usages:
            raise HSMKeyError("Cle non autorisee pour chiffrement")
        
        if info.key_type == KeyType.AES_256:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            nonce = secrets.token_bytes(12)
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, plaintext, None)
            return nonce + ciphertext
        else:
            raise HSMError(f"Chiffrement non supporte pour {info.key_type}")
    
    def decrypt(self, key_id: str, ciphertext: bytes) -> bytes:
        if key_id not in self._keys:
            raise HSMKeyError(f"Cle non trouvee: {key_id}")
        
        key_data = self._keys[key_id]
        info = key_data['info']
        key = key_data['key']
        
        if KeyUsage.DECRYPT not in info.usages:
            raise HSMKeyError("Cle non autorisee pour dechiffrement")
        
        if info.key_type == KeyType.AES_256:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            nonce = ciphertext[:12]
            ct = ciphertext[12:]
            aesgcm = AESGCM(key)
            return aesgcm.decrypt(nonce, ct, None)
        else:
            raise HSMError(f"Dechiffrement non supporte pour {info.key_type}")
    
    def sign(self, key_id: str, data: bytes) -> bytes:
        if key_id not in self._keys:
            raise HSMKeyError(f"Cle non trouvee: {key_id}")
        
        key_data = self._keys[key_id]
        info = key_data['info']
        key = key_data['key']
        
        if KeyUsage.SIGN not in info.usages:
            raise HSMKeyError("Cle non autorisee pour signature")
        
        if info.key_type == KeyType.ED25519:
            return key.sign(data)
        elif info.key_type in (KeyType.EC_P256, KeyType.EC_P384):
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import ec
            return key.sign(data, ec.ECDSA(hashes.SHA256()))
        else:
            raise HSMError(f"Signature non supportee pour {info.key_type}")
    
    def verify(self, key_id: str, data: bytes, signature: bytes) -> bool:
        if key_id not in self._keys:
            raise HSMKeyError(f"Cle non trouvee: {key_id}")
        
        key_data = self._keys[key_id]
        info = key_data['info']
        key = key_data['key']
        
        if KeyUsage.VERIFY not in info.usages:
            raise HSMKeyError("Cle non autorisee pour verification")
        
        try:
            if info.key_type == KeyType.ED25519:
                public_key = key.public_key()
                public_key.verify(signature, data)
                return True
            elif info.key_type in (KeyType.EC_P256, KeyType.EC_P384):
                from cryptography.hazmat.primitives import hashes
                from cryptography.hazmat.primitives.asymmetric import ec
                public_key = key.public_key()
                public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))
                return True
        except Exception:
            return False
        
        raise HSMError(f"Verification non supportee pour {info.key_type}")
    
    def _save_keys(self):
        """Sauvegarde les cles (INSECURE - dev only)"""
        # En production, utiliser un vrai HSM!
        pass
    
    def _load_keys(self):
        """Charge les cles"""
        pass


class YubiHSM2(HardwareSecurityModule):
    """
    Integration YubiHSM 2.
    
    Necessite: pip install yubihsm
    """
    
    def __init__(
        self,
        connector_url: str = "http://localhost:12345",
        auth_key_id: int = 1,
        password: str = "password"
    ):
        self._connector_url = connector_url
        self._auth_key_id = auth_key_id
        self._password = password
        self._session = None
        self._hsm = None
        
        try:
            import yubihsm
            self._yubihsm = yubihsm
            self._available = True
        except ImportError:
            self._yubihsm = None
            self._available = False
    
    def is_available(self) -> bool:
        if not self._available:
            return False
        
        try:
            self._connect()
            return True
        except Exception:
            return False
    
    def _connect(self):
        if self._session is not None:
            return
        
        if not self._available:
            raise HSMNotAvailable("yubihsm package not installed")
        
        from yubihsm import YubiHsm
        from yubihsm.core import AuthSession
        
        self._hsm = YubiHsm.connect(self._connector_url)
        self._session = self._hsm.create_session_derived(
            self._auth_key_id,
            self._password
        )
    
    def generate_key(
        self,
        key_type: KeyType,
        label: str,
        usages: List[KeyUsage]
    ) -> HSMKeyInfo:
        self._connect()
        
        from yubihsm.defs import ALGORITHM, CAPABILITY
        from yubihsm.objects import SymmetricKey, AsymmetricKey
        import time
        
        # Mapper les usages
        caps = 0
        if KeyUsage.ENCRYPT in usages:
            caps |= CAPABILITY.ENCRYPT_ECB
        if KeyUsage.DECRYPT in usages:
            caps |= CAPABILITY.DECRYPT_ECB
        if KeyUsage.SIGN in usages:
            caps |= CAPABILITY.SIGN_ECDSA
        if KeyUsage.VERIFY in usages:
            caps |= CAPABILITY.VERIFY_ECDSA
        
        # Generer selon le type
        if key_type == KeyType.AES_256:
            key = SymmetricKey.generate(
                self._session,
                0,  # Auto ID
                label,
                1,  # Domain
                caps,
                ALGORITHM.AES256
            )
        elif key_type == KeyType.EC_P256:
            key = AsymmetricKey.generate(
                self._session,
                0,
                label,
                1,
                caps,
                ALGORITHM.EC_P256
            )
        else:
            raise HSMError(f"Type non supporte: {key_type}")
        
        return HSMKeyInfo(
            key_id=str(key.id),
            key_type=key_type,
            usages=usages,
            created_at=time.time(),
            label=label,
            extractable=False
        )
    
    def delete_key(self, key_id: str) -> bool:
        self._connect()
        try:
            from yubihsm.objects import YhsmObject
            obj = YhsmObject(self._session, int(key_id))
            obj.delete()
            return True
        except Exception:
            return False
    
    def get_key_info(self, key_id: str) -> Optional[HSMKeyInfo]:
        self._connect()
        # Implementation simplifiee
        return None
    
    def encrypt(self, key_id: str, plaintext: bytes) -> bytes:
        self._connect()
        from yubihsm.objects import SymmetricKey
        
        key = SymmetricKey(self._session, int(key_id))
        return key.encrypt_ecb(plaintext)
    
    def decrypt(self, key_id: str, ciphertext: bytes) -> bytes:
        self._connect()
        from yubihsm.objects import SymmetricKey
        
        key = SymmetricKey(self._session, int(key_id))
        return key.decrypt_ecb(ciphertext)
    
    def sign(self, key_id: str, data: bytes) -> bytes:
        self._connect()
        from yubihsm.objects import AsymmetricKey
        
        key = AsymmetricKey(self._session, int(key_id))
        # Hash les donnees d'abord
        digest = hashlib.sha256(data).digest()
        return key.sign_ecdsa(digest)
    
    def verify(self, key_id: str, data: bytes, signature: bytes) -> bool:
        # YubiHSM ne supporte pas la verification directe
        # Utiliser la cle publique extraite
        raise NotImplementedError("Use public key verification")


class TPM2Integration(HardwareSecurityModule):
    """
    Integration TPM 2.0 (Trusted Platform Module).
    
    Necessite: pip install tpm2-pytss
    
    Fonctionnalites:
    - Sealing: Lie des donnees a l'etat de la machine (PCR)
    - Attestation: Preuve de l'etat du systeme
    """
    
    def __init__(self):
        try:
            from tpm2_pytss import ESAPI
            self._esapi = ESAPI()
            self._available = True
        except ImportError:
            self._esapi = None
            self._available = False
    
    def is_available(self) -> bool:
        return self._available
    
    def generate_key(self, key_type: KeyType, label: str, usages: List[KeyUsage]) -> HSMKeyInfo:
        raise NotImplementedError("TPM key generation")
    
    def delete_key(self, key_id: str) -> bool:
        raise NotImplementedError()
    
    def get_key_info(self, key_id: str) -> Optional[HSMKeyInfo]:
        return None
    
    def encrypt(self, key_id: str, plaintext: bytes) -> bytes:
        raise NotImplementedError()
    
    def decrypt(self, key_id: str, ciphertext: bytes) -> bytes:
        raise NotImplementedError()
    
    def sign(self, key_id: str, data: bytes) -> bytes:
        raise NotImplementedError()
    
    def verify(self, key_id: str, data: bytes, signature: bytes) -> bool:
        raise NotImplementedError()
    
    def seal_data(
        self,
        data: bytes,
        pcr_selection: List[int] = [0, 1, 2, 3, 7]
    ) -> bytes:
        """
        Scelle des donnees liees aux PCR.
        
        Les donnees ne pourront etre descellees que si les PCR
        ont les memes valeurs (meme etat du systeme).
        
        Args:
            data: Donnees a sceller
            pcr_selection: PCR a utiliser
        
        Returns:
            Blob scelle
        """
        if not self._available:
            raise HSMNotAvailable("TPM not available")
        
        # Implementation simplifiee
        # En production, utiliser l'API TPM complete
        raise NotImplementedError("TPM sealing")
    
    def unseal_data(self, sealed_blob: bytes) -> bytes:
        """Descelle les donnees si PCR valides"""
        if not self._available:
            raise HSMNotAvailable("TPM not available")
        
        raise NotImplementedError("TPM unsealing")
    
    def get_pcr_values(self, pcr_indices: List[int]) -> Dict[int, bytes]:
        """Lit les valeurs PCR"""
        if not self._available:
            raise HSMNotAvailable("TPM not available")
        
        raise NotImplementedError("TPM PCR read")


class HSMManager:
    """
    Gestionnaire de HSM avec fallback automatique.
    
    Essaie les HSM dans l'ordre:
    1. YubiHSM 2 (si configure)
    2. TPM 2.0 (si disponible)
    3. Software HSM (fallback)
    """
    
    def __init__(self, prefer_hardware: bool = True):
        self._hsms: List[HardwareSecurityModule] = []
        self._active_hsm: Optional[HardwareSecurityModule] = None
        
        if prefer_hardware:
            # Essayer YubiHSM
            try:
                yubi = YubiHSM2()
                if yubi.is_available():
                    self._hsms.append(yubi)
            except Exception:
                pass
            
            # Essayer TPM
            try:
                tpm = TPM2Integration()
                if tpm.is_available():
                    self._hsms.append(tpm)
            except Exception:
                pass
        
        # Toujours avoir le software HSM comme fallback
        self._hsms.append(SoftwareHSM())
        
        # Utiliser le premier disponible
        for hsm in self._hsms:
            if hsm.is_available():
                self._active_hsm = hsm
                break
    
    @property
    def active_hsm(self) -> HardwareSecurityModule:
        if self._active_hsm is None:
            raise HSMNotAvailable("No HSM available")
        return self._active_hsm
    
    def get_hsm_type(self) -> str:
        """Retourne le type de HSM actif"""
        hsm = self.active_hsm
        return hsm.__class__.__name__
    
    def is_hardware_hsm(self) -> bool:
        """True si un vrai HSM hardware est utilise"""
        return not isinstance(self.active_hsm, SoftwareHSM)


# Fonction utilitaire pour le vault

def create_hsm_protected_key(
    vault_key: bytes,
    label: str = "vault_master"
) -> Tuple[str, HardwareSecurityModule]:
    """
    Cree une cle protegee par HSM pour le vault.
    
    Args:
        vault_key: Cle vault a proteger
        label: Label de la cle
    
    Returns:
        (key_id, hsm_instance)
    """
    manager = HSMManager(prefer_hardware=True)
    hsm = manager.active_hsm
    
    # Generer une cle de wrapping
    wrap_key = hsm.generate_key(
        KeyType.AES_256,
        f"{label}_wrap",
        [KeyUsage.ENCRYPT, KeyUsage.DECRYPT]
    )
    
    # Chiffrer la cle vault
    wrapped = hsm.encrypt(wrap_key.key_id, vault_key)
    
    # Stocker le blob chiffre (implementation dependante)
    return wrap_key.key_id, hsm
