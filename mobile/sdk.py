"""
Mobile SDK pour Eidolon
Support React Native et Flutter avec Secure Enclave

Features:
- API unifiee pour mobile
- Secure Enclave/TEE integration
- Biometric authentication
- Offline vault access
- Push notifications
- QR code operations
"""

import os
import json
import hashlib
import secrets
import base64
import struct
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
from abc import ABC, abstractmethod


# ============================================================================
# ENUMERATIONS
# ============================================================================

class Platform(Enum):
    """Plateformes mobiles supportees"""
    IOS = "ios"
    ANDROID = "android"
    REACT_NATIVE = "react_native"
    FLUTTER = "flutter"


class BiometricType(Enum):
    """Types d'authentification biometrique"""
    FACE_ID = "face_id"
    TOUCH_ID = "touch_id"
    FINGERPRINT = "fingerprint"
    IRIS = "iris"
    NONE = "none"


class SecureStorageType(Enum):
    """Types de stockage securise"""
    KEYCHAIN = "keychain"          # iOS Keychain
    KEYSTORE = "keystore"          # Android Keystore
    SECURE_ENCLAVE = "secure_enclave"  # iOS Secure Enclave
    STRONGBOX = "strongbox"        # Android StrongBox
    TEE = "tee"                    # Trusted Execution Environment


class SyncStatus(Enum):
    """Statut de synchronisation"""
    SYNCED = "synced"
    PENDING = "pending"
    SYNCING = "syncing"
    CONFLICT = "conflict"
    OFFLINE = "offline"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class DeviceInfo:
    """Informations sur l'appareil"""
    device_id: str
    platform: Platform
    os_version: str
    app_version: str
    
    # Security features
    has_secure_enclave: bool = False
    has_biometrics: bool = False
    biometric_type: BiometricType = BiometricType.NONE
    
    # Status
    is_jailbroken: bool = False
    is_rooted: bool = False
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['platform'] = self.platform.value
        d['biometric_type'] = self.biometric_type.value
        return d


@dataclass
class SecureKeyHandle:
    """Handle vers une cle dans le Secure Enclave"""
    key_id: str
    key_type: str  # asymmetric, symmetric
    algorithm: str
    created_at: str
    
    # Storage
    storage_type: SecureStorageType
    is_extractable: bool = False
    requires_biometric: bool = False
    
    # Metadata (non-sensitive)
    label: str = ""
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['storage_type'] = self.storage_type.value
        return d


@dataclass
class OfflineVault:
    """Vault accessible hors-ligne"""
    vault_id: str
    name: str
    cached_at: str
    expires_at: str
    
    # Sync
    sync_status: SyncStatus = SyncStatus.SYNCED
    last_synced: str = ""
    pending_changes: int = 0
    
    # Security
    encryption_key_id: str = ""
    access_count: int = 0
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['sync_status'] = self.sync_status.value
        return d


@dataclass
class MobileSession:
    """Session mobile"""
    session_id: str
    device_id: str
    user_id: str
    created_at: str
    expires_at: str
    
    # Authentication
    auth_method: str = "biometric"
    is_active: bool = True
    
    # Security
    session_key_id: str = ""
    refresh_token_hash: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================================
# SECURE ENCLAVE INTERFACE
# ============================================================================

class SecureEnclaveInterface(ABC):
    """Interface abstraite pour Secure Enclave/TEE"""
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifie si le Secure Enclave est disponible"""
        pass
    
    @abstractmethod
    def generate_key(self, key_id: str, algorithm: str,
                    requires_biometric: bool = False) -> SecureKeyHandle:
        """Genere une cle dans le Secure Enclave"""
        pass
    
    @abstractmethod
    def sign(self, key_id: str, data: bytes) -> bytes:
        """Signe des donnees avec une cle du Secure Enclave"""
        pass
    
    @abstractmethod
    def encrypt(self, key_id: str, plaintext: bytes) -> bytes:
        """Chiffre avec une cle du Secure Enclave"""
        pass
    
    @abstractmethod
    def decrypt(self, key_id: str, ciphertext: bytes) -> bytes:
        """Dechiffre avec une cle du Secure Enclave"""
        pass
    
    @abstractmethod
    def delete_key(self, key_id: str) -> bool:
        """Supprime une cle du Secure Enclave"""
        pass


class iOSSecureEnclave(SecureEnclaveInterface):
    """Implementation iOS Secure Enclave (simulation)"""
    
    def __init__(self):
        self._keys: Dict[str, Dict[str, Any]] = {}
    
    def is_available(self) -> bool:
        return True  # Simulated
    
    def generate_key(self, key_id: str, algorithm: str = "P-256",
                    requires_biometric: bool = False) -> SecureKeyHandle:
        # Simulate key generation in Secure Enclave
        self._keys[key_id] = {
            "algorithm": algorithm,
            "created": datetime.now().isoformat(),
            "private_key": secrets.token_bytes(32),  # Simulated
            "public_key": secrets.token_bytes(65),   # Simulated P-256
            "requires_biometric": requires_biometric
        }
        
        return SecureKeyHandle(
            key_id=key_id,
            key_type="asymmetric",
            algorithm=algorithm,
            created_at=datetime.now().isoformat(),
            storage_type=SecureStorageType.SECURE_ENCLAVE,
            is_extractable=False,
            requires_biometric=requires_biometric
        )
    
    def sign(self, key_id: str, data: bytes) -> bytes:
        key_data = self._keys.get(key_id)
        
        if not key_data:
            raise ValueError(f"Key {key_id} not found")
        
        # Simulated ECDSA signature
        signature = hashlib.sha256(
            data + key_data["private_key"]
        ).digest()
        
        return signature
    
    def encrypt(self, key_id: str, plaintext: bytes) -> bytes:
        key_data = self._keys.get(key_id)
        
        if not key_data:
            raise ValueError(f"Key {key_id} not found")
        
        # Simulated encryption
        nonce = secrets.token_bytes(12)
        
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        derived_key = hashlib.sha256(key_data["private_key"]).digest()
        aesgcm = AESGCM(derived_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        
        return nonce + ciphertext
    
    def decrypt(self, key_id: str, ciphertext: bytes) -> bytes:
        key_data = self._keys.get(key_id)
        
        if not key_data:
            raise ValueError(f"Key {key_id} not found")
        
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        nonce = ciphertext[:12]
        ct = ciphertext[12:]
        
        derived_key = hashlib.sha256(key_data["private_key"]).digest()
        aesgcm = AESGCM(derived_key)
        
        return aesgcm.decrypt(nonce, ct, None)
    
    def delete_key(self, key_id: str) -> bool:
        if key_id in self._keys:
            del self._keys[key_id]
            return True
        return False


class AndroidKeystore(SecureEnclaveInterface):
    """Implementation Android Keystore (simulation)"""
    
    def __init__(self):
        self._keys: Dict[str, Dict[str, Any]] = {}
    
    def is_available(self) -> bool:
        return True  # Simulated
    
    def generate_key(self, key_id: str, algorithm: str = "RSA-2048",
                    requires_biometric: bool = False) -> SecureKeyHandle:
        self._keys[key_id] = {
            "algorithm": algorithm,
            "created": datetime.now().isoformat(),
            "key_material": secrets.token_bytes(32),
            "requires_biometric": requires_biometric
        }
        
        return SecureKeyHandle(
            key_id=key_id,
            key_type="asymmetric",
            algorithm=algorithm,
            created_at=datetime.now().isoformat(),
            storage_type=SecureStorageType.KEYSTORE,
            is_extractable=False,
            requires_biometric=requires_biometric
        )
    
    def sign(self, key_id: str, data: bytes) -> bytes:
        key_data = self._keys.get(key_id)
        
        if not key_data:
            raise ValueError(f"Key {key_id} not found")
        
        return hashlib.sha256(data + key_data["key_material"]).digest()
    
    def encrypt(self, key_id: str, plaintext: bytes) -> bytes:
        key_data = self._keys.get(key_id)
        
        if not key_data:
            raise ValueError(f"Key {key_id} not found")
        
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        nonce = secrets.token_bytes(12)
        derived_key = hashlib.sha256(key_data["key_material"]).digest()
        aesgcm = AESGCM(derived_key)
        
        return nonce + aesgcm.encrypt(nonce, plaintext, None)
    
    def decrypt(self, key_id: str, ciphertext: bytes) -> bytes:
        key_data = self._keys.get(key_id)
        
        if not key_data:
            raise ValueError(f"Key {key_id} not found")
        
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        nonce = ciphertext[:12]
        ct = ciphertext[12:]
        
        derived_key = hashlib.sha256(key_data["key_material"]).digest()
        aesgcm = AESGCM(derived_key)
        
        return aesgcm.decrypt(nonce, ct, None)
    
    def delete_key(self, key_id: str) -> bool:
        if key_id in self._keys:
            del self._keys[key_id]
            return True
        return False


# ============================================================================
# BIOMETRIC AUTHENTICATION
# ============================================================================

class BiometricAuth:
    """Gestionnaire d'authentification biometrique"""
    
    def __init__(self, platform: Platform):
        self.platform = platform
        self._enrolled_biometrics: List[BiometricType] = []
    
    def get_available_biometrics(self) -> List[BiometricType]:
        """Recupere les biometries disponibles"""
        if self.platform == Platform.IOS:
            return [BiometricType.FACE_ID, BiometricType.TOUCH_ID]
        elif self.platform == Platform.ANDROID:
            return [BiometricType.FINGERPRINT, BiometricType.FACE_ID]
        else:
            return [BiometricType.FINGERPRINT]
    
    def is_enrolled(self, biometric_type: BiometricType) -> bool:
        """Verifie si un type de biometrie est configure"""
        return biometric_type in self._enrolled_biometrics
    
    def enroll(self, biometric_type: BiometricType) -> bool:
        """Enregistre un type de biometrie"""
        if biometric_type not in self._enrolled_biometrics:
            self._enrolled_biometrics.append(biometric_type)
        return True
    
    def authenticate(self, reason: str, 
                    allowed_types: List[BiometricType] = None) -> Tuple[bool, str]:
        """Authentifie l'utilisateur avec biometrie"""
        # Simulation - always succeeds
        # In production, would call native biometric APIs
        
        available = self.get_available_biometrics()
        
        if allowed_types:
            available = [t for t in available if t in allowed_types]
        
        if not available:
            return False, "No biometric available"
        
        # Simulated success
        return True, f"Authenticated with {available[0].value}"
    
    def cancel_authentication(self):
        """Annule l'authentification en cours"""
        pass


# ============================================================================
# OFFLINE VAULT MANAGER
# ============================================================================

class OfflineVaultManager:
    """Gestionnaire de vaults hors-ligne"""
    
    def __init__(self, secure_storage: SecureEnclaveInterface, 
                 cache_dir: str = "./offline_cache"):
        self.secure_storage = secure_storage
        self.cache_dir = cache_dir
        
        os.makedirs(cache_dir, exist_ok=True)
        
        self._vaults: Dict[str, OfflineVault] = {}
        self._pending_changes: Dict[str, List[Dict]] = {}
    
    def cache_vault(self, vault_id: str, vault_data: Dict[str, Any],
                   ttl_hours: int = 24) -> OfflineVault:
        """Cache un vault pour acces hors-ligne"""
        # Generate encryption key in Secure Enclave
        key_handle = self.secure_storage.generate_key(
            f"vault_{vault_id}_cache",
            "AES-256",
            requires_biometric=True
        )
        
        # Encrypt vault data
        vault_json = json.dumps(vault_data).encode()
        encrypted = self.secure_storage.encrypt(key_handle.key_id, vault_json)
        
        # Save encrypted cache
        cache_path = f"{self.cache_dir}/{vault_id}.cache"
        with open(cache_path, 'wb') as f:
            f.write(encrypted)
        
        now = datetime.now()
        
        vault = OfflineVault(
            vault_id=vault_id,
            name=vault_data.get("name", "Unnamed Vault"),
            cached_at=now.isoformat(),
            expires_at=(now + timedelta(hours=ttl_hours)).isoformat(),
            encryption_key_id=key_handle.key_id,
            sync_status=SyncStatus.SYNCED,
            last_synced=now.isoformat()
        )
        
        self._vaults[vault_id] = vault
        self._save_vault_meta(vault)
        
        return vault
    
    def get_vault(self, vault_id: str) -> Optional[Dict[str, Any]]:
        """Recupere un vault depuis le cache"""
        vault = self._vaults.get(vault_id)
        
        if not vault:
            return None
        
        # Check expiry
        if datetime.now() > datetime.fromisoformat(vault.expires_at):
            vault.sync_status = SyncStatus.OFFLINE
            return None
        
        # Load and decrypt
        cache_path = f"{self.cache_dir}/{vault_id}.cache"
        
        if not os.path.exists(cache_path):
            return None
        
        with open(cache_path, 'rb') as f:
            encrypted = f.read()
        
        try:
            decrypted = self.secure_storage.decrypt(vault.encryption_key_id, encrypted)
            vault.access_count += 1
            self._save_vault_meta(vault)
            
            return json.loads(decrypted.decode())
        except Exception as e:
            print(f"Decryption failed: {e}")
            return None
    
    def queue_change(self, vault_id: str, change: Dict[str, Any]):
        """Ajoute un changement a synchroniser"""
        if vault_id not in self._pending_changes:
            self._pending_changes[vault_id] = []
        
        change["queued_at"] = datetime.now().isoformat()
        self._pending_changes[vault_id].append(change)
        
        vault = self._vaults.get(vault_id)
        if vault:
            vault.sync_status = SyncStatus.PENDING
            vault.pending_changes = len(self._pending_changes[vault_id])
            self._save_vault_meta(vault)
    
    def get_pending_changes(self, vault_id: str) -> List[Dict]:
        """Recupere les changements en attente"""
        return self._pending_changes.get(vault_id, [])
    
    def sync_completed(self, vault_id: str):
        """Marque la synchronisation comme complete"""
        vault = self._vaults.get(vault_id)
        
        if vault:
            vault.sync_status = SyncStatus.SYNCED
            vault.last_synced = datetime.now().isoformat()
            vault.pending_changes = 0
            self._save_vault_meta(vault)
        
        if vault_id in self._pending_changes:
            del self._pending_changes[vault_id]
    
    def _save_vault_meta(self, vault: OfflineVault):
        """Sauvegarde les metadonnees du vault"""
        meta_path = f"{self.cache_dir}/{vault.vault_id}.meta"
        
        with open(meta_path, 'w') as f:
            json.dump(vault.to_dict(), f, indent=2)
    
    def list_cached_vaults(self) -> List[OfflineVault]:
        """Liste tous les vaults en cache"""
        return list(self._vaults.values())


# ============================================================================
# PUSH NOTIFICATIONS
# ============================================================================

class PushNotificationManager:
    """Gestionnaire de notifications push"""
    
    def __init__(self):
        self._device_token: Optional[str] = None
        self._handlers: Dict[str, Callable] = {}
    
    def register_device(self, token: str) -> bool:
        """Enregistre le token de l'appareil"""
        self._device_token = token
        return True
    
    def unregister_device(self):
        """Desenregistre l'appareil"""
        self._device_token = None
    
    def register_handler(self, notification_type: str, handler: Callable):
        """Enregistre un handler pour un type de notification"""
        self._handlers[notification_type] = handler
    
    def handle_notification(self, payload: Dict[str, Any]) -> bool:
        """Gere une notification recue"""
        notification_type = payload.get("type", "default")
        
        handler = self._handlers.get(notification_type)
        
        if handler:
            try:
                handler(payload)
                return True
            except Exception as e:
                print(f"Handler error: {e}")
                return False
        
        return False
    
    def get_notification_types(self) -> List[str]:
        """Types de notifications supportes"""
        return [
            "vault_access",
            "new_share",
            "transfer_complete",
            "security_alert",
            "sync_required",
            "key_expiring"
        ]


# ============================================================================
# QR CODE OPERATIONS
# ============================================================================

class QRCodeManager:
    """Gestionnaire d'operations QR code"""
    
    def __init__(self, secure_storage: SecureEnclaveInterface):
        self.secure_storage = secure_storage
    
    def generate_vault_share_qr(self, vault_id: str, 
                                permissions: List[str],
                                expires_in_minutes: int = 5) -> str:
        """Genere un QR code pour partager un vault"""
        share_data = {
            "type": "vault_share",
            "vault_id": vault_id,
            "permissions": permissions,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(minutes=expires_in_minutes)).isoformat(),
            "nonce": secrets.token_hex(16)
        }
        
        # Sign the share data
        signature = self.secure_storage.sign(
            f"device_signing_key",
            json.dumps(share_data, sort_keys=True).encode()
        )
        
        share_data["signature"] = base64.b64encode(signature).decode()
        
        # Encode as QR-friendly string
        qr_payload = base64.urlsafe_b64encode(
            json.dumps(share_data).encode()
        ).decode()
        
        return f"psnx://share/{qr_payload}"
    
    def parse_qr_code(self, qr_data: str) -> Optional[Dict[str, Any]]:
        """Parse un QR code"""
        if not qr_data.startswith("psnx://"):
            return None
        
        try:
            parts = qr_data[7:].split("/", 1)
            action = parts[0]
            payload = parts[1] if len(parts) > 1 else ""
            
            decoded = json.loads(base64.urlsafe_b64decode(payload))
            decoded["action"] = action
            
            return decoded
        except Exception:
            return None
    
    def generate_auth_qr(self, session_id: str, challenge: str) -> str:
        """Genere un QR code pour authentification"""
        auth_data = {
            "type": "auth_challenge",
            "session_id": session_id,
            "challenge": challenge,
            "timestamp": datetime.now().isoformat()
        }
        
        qr_payload = base64.urlsafe_b64encode(
            json.dumps(auth_data).encode()
        ).decode()
        
        return f"psnx://auth/{qr_payload}"
    
    def respond_to_auth_qr(self, qr_data: str, 
                          device_key_id: str) -> Optional[str]:
        """Repond a un QR code d'authentification"""
        parsed = self.parse_qr_code(qr_data)
        
        if not parsed or parsed.get("action") != "auth":
            return None
        
        challenge = parsed.get("challenge", "")
        
        # Sign challenge
        response = self.secure_storage.sign(device_key_id, challenge.encode())
        
        return base64.b64encode(response).decode()


# ============================================================================
# MOBILE SDK FACADE
# ============================================================================

class PSNXMobileSDK:
    """SDK Mobile complet pour Eidolon"""
    
    VERSION = "1.0.0"
    
    def __init__(self, platform: Platform, data_dir: str = "./mobile_data"):
        self.platform = platform
        self.data_dir = data_dir
        
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize components
        if platform == Platform.IOS:
            self.secure_storage = iOSSecureEnclave()
        else:
            self.secure_storage = AndroidKeystore()
        
        self.biometric = BiometricAuth(platform)
        self.offline_manager = OfflineVaultManager(self.secure_storage, f"{data_dir}/cache")
        self.push_manager = PushNotificationManager()
        self.qr_manager = QRCodeManager(self.secure_storage)
        
        # Device info
        self.device_info: Optional[DeviceInfo] = None
        
        # Session
        self._session: Optional[MobileSession] = None
    
    def initialize(self, device_id: str, os_version: str, 
                  app_version: str) -> DeviceInfo:
        """Initialise le SDK"""
        biometrics = self.biometric.get_available_biometrics()
        
        self.device_info = DeviceInfo(
            device_id=device_id,
            platform=self.platform,
            os_version=os_version,
            app_version=app_version,
            has_secure_enclave=self.secure_storage.is_available(),
            has_biometrics=len(biometrics) > 0,
            biometric_type=biometrics[0] if biometrics else BiometricType.NONE
        )
        
        # Generate device keys
        self.secure_storage.generate_key("device_signing_key", "P-256")
        self.secure_storage.generate_key("device_encryption_key", "AES-256")
        
        return self.device_info
    
    def authenticate(self, user_id: str, 
                    use_biometric: bool = True) -> Optional[MobileSession]:
        """Authentifie l'utilisateur"""
        if use_biometric:
            success, message = self.biometric.authenticate(
                "Authenticate to access your vault"
            )
            
            if not success:
                return None
        
        session_id = secrets.token_hex(16)
        now = datetime.now()
        
        self._session = MobileSession(
            session_id=session_id,
            device_id=self.device_info.device_id if self.device_info else "",
            user_id=user_id,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(hours=24)).isoformat(),
            auth_method="biometric" if use_biometric else "password",
            session_key_id=f"session_{session_id}"
        )
        
        # Generate session key
        self.secure_storage.generate_key(
            self._session.session_key_id,
            "AES-256",
            requires_biometric=False
        )
        
        return self._session
    
    def logout(self):
        """Deconnecte l'utilisateur"""
        if self._session:
            self.secure_storage.delete_key(self._session.session_key_id)
            self._session = None
    
    def is_authenticated(self) -> bool:
        """Verifie si l'utilisateur est authentifie"""
        if not self._session:
            return False
        
        return datetime.now() < datetime.fromisoformat(self._session.expires_at)
    
    def cache_vault_for_offline(self, vault_id: str, 
                               vault_data: Dict) -> OfflineVault:
        """Cache un vault pour acces hors-ligne"""
        return self.offline_manager.cache_vault(vault_id, vault_data)
    
    def get_offline_vault(self, vault_id: str) -> Optional[Dict]:
        """Recupere un vault depuis le cache"""
        return self.offline_manager.get_vault(vault_id)
    
    def generate_share_qr(self, vault_id: str, 
                         permissions: List[str]) -> str:
        """Genere un QR code de partage"""
        return self.qr_manager.generate_vault_share_qr(vault_id, permissions)
    
    def scan_qr(self, qr_data: str) -> Optional[Dict]:
        """Scanne et parse un QR code"""
        return self.qr_manager.parse_qr_code(qr_data)
    
    def get_sdk_info(self) -> Dict[str, Any]:
        """Informations sur le SDK"""
        return {
            "version": self.VERSION,
            "platform": self.platform.value,
            "device": self.device_info.to_dict() if self.device_info else None,
            "features": {
                "secure_enclave": self.secure_storage.is_available(),
                "biometric_auth": self.device_info.has_biometrics if self.device_info else False,
                "offline_access": True,
                "qr_operations": True,
                "push_notifications": True
            },
            "supported_operations": [
                "vault_cache",
                "biometric_auth",
                "qr_share",
                "qr_auth",
                "push_notifications",
                "offline_sync"
            ]
        }


# ============================================================================
# REACT NATIVE BRIDGE
# ============================================================================

class ReactNativeBridge:
    """Bridge pour React Native"""
    
    def __init__(self, sdk: PSNXMobileSDK):
        self.sdk = sdk
    
    def to_js_callback(self, result: Any) -> Dict[str, Any]:
        """Formate le resultat pour callback JS"""
        return {
            "success": True,
            "data": result if isinstance(result, dict) else {"value": result},
            "timestamp": datetime.now().isoformat()
        }
    
    def to_js_error(self, error: str) -> Dict[str, Any]:
        """Formate une erreur pour callback JS"""
        return {
            "success": False,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
    
    def export_methods(self) -> Dict[str, Callable]:
        """Exporte les methodes pour React Native"""
        return {
            "initialize": lambda args: self.to_js_callback(
                self.sdk.initialize(**args).to_dict()
            ),
            "authenticate": lambda args: self.to_js_callback(
                self.sdk.authenticate(**args).to_dict() if self.sdk.authenticate(**args) else None
            ),
            "logout": lambda: self.to_js_callback(self.sdk.logout()),
            "isAuthenticated": lambda: self.to_js_callback(self.sdk.is_authenticated()),
            "cacheVault": lambda args: self.to_js_callback(
                self.sdk.cache_vault_for_offline(**args).to_dict()
            ),
            "getOfflineVault": lambda args: self.to_js_callback(
                self.sdk.get_offline_vault(args["vault_id"])
            ),
            "generateShareQR": lambda args: self.to_js_callback(
                self.sdk.generate_share_qr(**args)
            ),
            "scanQR": lambda args: self.to_js_callback(
                self.sdk.scan_qr(args["qr_data"])
            ),
            "getSDKInfo": lambda: self.to_js_callback(self.sdk.get_sdk_info())
        }


# ============================================================================
# FLUTTER BRIDGE
# ============================================================================

class FlutterBridge:
    """Bridge pour Flutter via Method Channel"""
    
    def __init__(self, sdk: PSNXMobileSDK):
        self.sdk = sdk
    
    def handle_method_call(self, method: str, arguments: Dict) -> Dict[str, Any]:
        """Gere les appels de methode depuis Flutter"""
        try:
            if method == "initialize":
                result = self.sdk.initialize(**arguments)
                return {"result": result.to_dict()}
            
            elif method == "authenticate":
                result = self.sdk.authenticate(**arguments)
                return {"result": result.to_dict() if result else None}
            
            elif method == "logout":
                self.sdk.logout()
                return {"result": True}
            
            elif method == "isAuthenticated":
                return {"result": self.sdk.is_authenticated()}
            
            elif method == "cacheVault":
                result = self.sdk.cache_vault_for_offline(**arguments)
                return {"result": result.to_dict()}
            
            elif method == "getOfflineVault":
                result = self.sdk.get_offline_vault(arguments["vault_id"])
                return {"result": result}
            
            elif method == "generateShareQR":
                result = self.sdk.generate_share_qr(**arguments)
                return {"result": result}
            
            elif method == "scanQR":
                result = self.sdk.scan_qr(arguments["qr_data"])
                return {"result": result}
            
            elif method == "getSDKInfo":
                return {"result": self.sdk.get_sdk_info()}
            
            else:
                return {"error": f"Unknown method: {method}"}
        
        except Exception as e:
            return {"error": str(e)}


# ============================================================================
# FACTORY
# ============================================================================

def create_mobile_sdk(platform: str, data_dir: str = "./mobile_data") -> PSNXMobileSDK:
    """Cree une instance du SDK mobile"""
    platform_enum = Platform(platform.lower())
    return PSNXMobileSDK(platform_enum, data_dir)


def create_react_native_bridge(sdk: PSNXMobileSDK) -> ReactNativeBridge:
    """Cree un bridge React Native"""
    return ReactNativeBridge(sdk)


def create_flutter_bridge(sdk: PSNXMobileSDK) -> FlutterBridge:
    """Cree un bridge Flutter"""
    return FlutterBridge(sdk)
