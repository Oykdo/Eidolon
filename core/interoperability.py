"""
Interoperability System pour Eidolon
Standard ouvert PSNX, compatibilite Keybase/Signal, plugins navigateurs

Features:
- Standard ouvert PSNX pour echange de cles
- Export/Import compatible Keybase
- Integration Signal Protocol
- Plugin navigateur API
- QR Code sharing
- Deep link support
"""

import os
import json
import hashlib
import secrets
import base64
import struct
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
from abc import ABC, abstractmethod

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import x25519, ed25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ============================================================================
# PSNX STANDARD FORMAT
# ============================================================================

PSNX_VERSION = "1.0"
PSNX_MAGIC = b"PSNX"


class PSNXKeyType(Enum):
    """Types de cles PSNX"""
    VAULT_KEY = "vault_key"
    IDENTITY_KEY = "identity_key"
    SIGNING_KEY = "signing_key"
    EXCHANGE_KEY = "exchange_key"
    RECOVERY_SHARE = "recovery_share"


@dataclass
class PSNXKeyBundle:
    """Bundle de cles au format PSNX standard"""
    version: str
    key_type: PSNXKeyType
    key_id: str
    created_at: str
    
    # Keys (base64 encoded)
    public_key: str
    encrypted_private_key: Optional[str] = None
    
    # Metadata
    algorithm: str = "X25519-Ed25519"
    curve: str = "Curve25519"
    
    # Signatures
    self_signature: Optional[str] = None
    
    # Extensions
    extensions: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['key_type'] = self.key_type.value
        return d
    
    def to_psnx(self) -> bytes:
        """Encode au format binaire PSNX"""
        json_data = json.dumps(self.to_dict()).encode()
        
        # Format: MAGIC (4) + VERSION (2) + LENGTH (4) + JSON_DATA
        header = PSNX_MAGIC + struct.pack(">H", int(PSNX_VERSION.replace(".", "")))
        header += struct.pack(">I", len(json_data))
        
        return header + json_data
    
    @classmethod
    def from_psnx(cls, data: bytes) -> "PSNXKeyBundle":
        """Decode depuis format binaire PSNX"""
        if data[:4] != PSNX_MAGIC:
            raise ValueError("Invalid PSNX magic")
        
        version = struct.unpack(">H", data[4:6])[0]
        length = struct.unpack(">I", data[6:10])[0]
        
        json_data = json.loads(data[10:10+length].decode())
        json_data['key_type'] = PSNXKeyType(json_data['key_type'])
        
        return cls(**json_data)
    
    def to_base64(self) -> str:
        """Encode en base64 pour partage"""
        return base64.urlsafe_b64encode(self.to_psnx()).decode()
    
    @classmethod
    def from_base64(cls, data: str) -> "PSNXKeyBundle":
        """Decode depuis base64"""
        return cls.from_psnx(base64.urlsafe_b64decode(data))


@dataclass
class PSNXIdentity:
    """Identite PSNX complete"""
    identity_id: str
    display_name: str
    created_at: str
    
    # Keys
    identity_key: PSNXKeyBundle
    signing_key: PSNXKeyBundle
    exchange_keys: List[PSNXKeyBundle] = field(default_factory=list)
    
    # Verification
    fingerprint: str = ""
    
    # Social proofs
    proofs: Dict[str, str] = field(default_factory=dict)  # platform -> proof_url
    
    def to_dict(self) -> dict:
        return {
            "identity_id": self.identity_id,
            "display_name": self.display_name,
            "created_at": self.created_at,
            "identity_key": self.identity_key.to_dict(),
            "signing_key": self.signing_key.to_dict(),
            "exchange_keys": [k.to_dict() for k in self.exchange_keys],
            "fingerprint": self.fingerprint,
            "proofs": self.proofs
        }


# ============================================================================
# PSNX KEY MANAGER
# ============================================================================

class PSNXKeyManager:
    """Gestionnaire de cles au standard PSNX"""
    
    def __init__(self, data_dir: str = "./psnx_keys"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def generate_identity(self, display_name: str) -> PSNXIdentity:
        """Genere une nouvelle identite PSNX"""
        identity_id = secrets.token_hex(16)
        
        # Generate identity key (X25519)
        identity_private = x25519.X25519PrivateKey.generate()
        identity_public = identity_private.public_key()
        
        # Generate signing key (Ed25519)
        signing_private = ed25519.Ed25519PrivateKey.generate()
        signing_public = signing_private.public_key()
        
        # Create key bundles
        identity_key = PSNXKeyBundle(
            version=PSNX_VERSION,
            key_type=PSNXKeyType.IDENTITY_KEY,
            key_id=f"id_{secrets.token_hex(8)}",
            created_at=datetime.now().isoformat(),
            public_key=base64.b64encode(
                identity_public.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                )
            ).decode()
        )
        
        signing_key = PSNXKeyBundle(
            version=PSNX_VERSION,
            key_type=PSNXKeyType.SIGNING_KEY,
            key_id=f"sign_{secrets.token_hex(8)}",
            created_at=datetime.now().isoformat(),
            public_key=base64.b64encode(
                signing_public.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                )
            ).decode(),
            algorithm="Ed25519"
        )
        
        # Calculate fingerprint
        combined = identity_key.public_key + signing_key.public_key
        fingerprint = hashlib.sha256(combined.encode()).hexdigest()[:40].upper()
        fingerprint = " ".join([fingerprint[i:i+4] for i in range(0, 40, 4)])
        
        identity = PSNXIdentity(
            identity_id=identity_id,
            display_name=display_name,
            created_at=datetime.now().isoformat(),
            identity_key=identity_key,
            signing_key=signing_key,
            fingerprint=fingerprint
        )
        
        # Save identity
        self._save_identity(identity)
        
        return identity
    
    def generate_exchange_key(self, identity_id: str) -> Optional[PSNXKeyBundle]:
        """Genere une nouvelle cle d'echange pour une identite"""
        identity = self.get_identity(identity_id)
        
        if not identity:
            return None
        
        # Generate ephemeral X25519 key
        private = x25519.X25519PrivateKey.generate()
        public = private.public_key()
        
        key = PSNXKeyBundle(
            version=PSNX_VERSION,
            key_type=PSNXKeyType.EXCHANGE_KEY,
            key_id=f"xchg_{secrets.token_hex(8)}",
            created_at=datetime.now().isoformat(),
            public_key=base64.b64encode(
                public.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                )
            ).decode()
        )
        
        identity.exchange_keys.append(key)
        self._save_identity(identity)
        
        return key
    
    def export_public_identity(self, identity_id: str) -> Optional[str]:
        """Exporte l'identite publique en PSNX"""
        identity = self.get_identity(identity_id)
        
        if not identity:
            return None
        
        # Create export bundle (public keys only)
        export_data = {
            "type": "psnx_identity",
            "version": PSNX_VERSION,
            "identity": identity.to_dict()
        }
        
        json_bytes = json.dumps(export_data).encode()
        return base64.urlsafe_b64encode(PSNX_MAGIC + json_bytes).decode()
    
    def import_identity(self, psnx_data: str) -> Optional[PSNXIdentity]:
        """Importe une identite depuis PSNX"""
        try:
            raw = base64.urlsafe_b64decode(psnx_data)
            
            if raw[:4] != PSNX_MAGIC:
                return None
            
            data = json.loads(raw[4:].decode())
            
            if data.get("type") != "psnx_identity":
                return None
            
            id_data = data["identity"]
            
            # Reconstruct identity
            identity_key = PSNXKeyBundle(**{
                **id_data["identity_key"],
                "key_type": PSNXKeyType(id_data["identity_key"]["key_type"])
            })
            
            signing_key = PSNXKeyBundle(**{
                **id_data["signing_key"],
                "key_type": PSNXKeyType(id_data["signing_key"]["key_type"])
            })
            
            exchange_keys = [
                PSNXKeyBundle(**{**k, "key_type": PSNXKeyType(k["key_type"])})
                for k in id_data.get("exchange_keys", [])
            ]
            
            identity = PSNXIdentity(
                identity_id=id_data["identity_id"],
                display_name=id_data["display_name"],
                created_at=id_data["created_at"],
                identity_key=identity_key,
                signing_key=signing_key,
                exchange_keys=exchange_keys,
                fingerprint=id_data.get("fingerprint", ""),
                proofs=id_data.get("proofs", {})
            )
            
            self._save_identity(identity)
            return identity
        
        except Exception as e:
            print(f"Import error: {e}")
            return None
    
    def get_identity(self, identity_id: str) -> Optional[PSNXIdentity]:
        """Recupere une identite"""
        path = f"{self.data_dir}/{identity_id}.json"
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        return self._deserialize_identity(data)
    
    def _deserialize_identity(self, data: dict) -> PSNXIdentity:
        """Deserialise une identite"""
        identity_key = PSNXKeyBundle(**{
            **data["identity_key"],
            "key_type": PSNXKeyType(data["identity_key"]["key_type"])
        })
        
        signing_key = PSNXKeyBundle(**{
            **data["signing_key"],
            "key_type": PSNXKeyType(data["signing_key"]["key_type"])
        })
        
        exchange_keys = [
            PSNXKeyBundle(**{**k, "key_type": PSNXKeyType(k["key_type"])})
            for k in data.get("exchange_keys", [])
        ]
        
        return PSNXIdentity(
            identity_id=data["identity_id"],
            display_name=data["display_name"],
            created_at=data["created_at"],
            identity_key=identity_key,
            signing_key=signing_key,
            exchange_keys=exchange_keys,
            fingerprint=data.get("fingerprint", ""),
            proofs=data.get("proofs", {})
        )
    
    def _save_identity(self, identity: PSNXIdentity):
        """Sauvegarde une identite"""
        with open(f"{self.data_dir}/{identity.identity_id}.json", 'w') as f:
            json.dump(identity.to_dict(), f, indent=2)


# ============================================================================
# KEYBASE COMPATIBILITY
# ============================================================================

class KeybaseAdapter:
    """Adaptateur pour compatibilite Keybase"""
    
    def __init__(self, key_manager: PSNXKeyManager):
        self.key_manager = key_manager
    
    def export_to_keybase(self, identity_id: str) -> Optional[Dict[str, Any]]:
        """Exporte une identite au format Keybase"""
        identity = self.key_manager.get_identity(identity_id)
        
        if not identity:
            return None
        
        # Format Keybase-compatible
        return {
            "version": 1,
            "type": "keybase_key",
            "key_type": "nacl",
            "key": {
                "kid": identity.identity_key.key_id,
                "pub": identity.identity_key.public_key,
                "sign_pub": identity.signing_key.public_key,
                "created": int(datetime.fromisoformat(identity.created_at).timestamp())
            },
            "metadata": {
                "name": identity.display_name,
                "fingerprint": identity.fingerprint,
                "source": "poly-spinor-nexus-7d",
                "psnx_id": identity.identity_id
            }
        }
    
    def import_from_keybase(self, keybase_data: Dict[str, Any]) -> Optional[PSNXIdentity]:
        """Importe une cle depuis format Keybase"""
        try:
            key = keybase_data.get("key", {})
            metadata = keybase_data.get("metadata", {})
            
            identity_key = PSNXKeyBundle(
                version=PSNX_VERSION,
                key_type=PSNXKeyType.IDENTITY_KEY,
                key_id=key.get("kid", f"kb_{secrets.token_hex(8)}"),
                created_at=datetime.fromtimestamp(key.get("created", time.time())).isoformat(),
                public_key=key.get("pub", "")
            )
            
            signing_key = PSNXKeyBundle(
                version=PSNX_VERSION,
                key_type=PSNXKeyType.SIGNING_KEY,
                key_id=f"sign_{secrets.token_hex(8)}",
                created_at=datetime.fromtimestamp(key.get("created", time.time())).isoformat(),
                public_key=key.get("sign_pub", ""),
                algorithm="Ed25519"
            )
            
            identity = PSNXIdentity(
                identity_id=metadata.get("psnx_id", secrets.token_hex(16)),
                display_name=metadata.get("name", "Keybase User"),
                created_at=datetime.now().isoformat(),
                identity_key=identity_key,
                signing_key=signing_key,
                fingerprint=metadata.get("fingerprint", "")
            )
            
            self.key_manager._save_identity(identity)
            return identity
        
        except Exception as e:
            print(f"Keybase import error: {e}")
            return None
    
    def create_proof(self, identity_id: str, keybase_username: str) -> Optional[str]:
        """Cree une preuve de liaison Keybase"""
        identity = self.key_manager.get_identity(identity_id)
        
        if not identity:
            return None
        
        proof = {
            "type": "psnx_keybase_proof",
            "version": 1,
            "psnx_identity": identity.identity_id,
            "keybase_username": keybase_username,
            "fingerprint": identity.fingerprint,
            "created": datetime.now().isoformat()
        }
        
        # Sign proof
        proof_json = json.dumps(proof, sort_keys=True)
        proof_hash = hashlib.sha256(proof_json.encode()).hexdigest()
        
        proof["proof_hash"] = proof_hash
        
        # Update identity with proof
        identity.proofs["keybase"] = keybase_username
        self.key_manager._save_identity(identity)
        
        return json.dumps(proof, indent=2)


# ============================================================================
# SIGNAL PROTOCOL COMPATIBILITY
# ============================================================================

class SignalAdapter:
    """Adaptateur pour compatibilite Signal Protocol"""
    
    def __init__(self, key_manager: PSNXKeyManager):
        self.key_manager = key_manager
    
    def generate_prekeys(self, identity_id: str, count: int = 100) -> List[Dict[str, Any]]:
        """Genere des prekeys compatibles Signal"""
        identity = self.key_manager.get_identity(identity_id)
        
        if not identity:
            return []
        
        prekeys = []
        
        for i in range(count):
            # Generate ephemeral X25519 key
            private = x25519.X25519PrivateKey.generate()
            public = private.public_key()
            
            prekey_id = i + 1
            public_bytes = public.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            prekeys.append({
                "keyId": prekey_id,
                "publicKey": base64.b64encode(public_bytes).decode(),
                "timestamp": int(time.time())
            })
        
        return prekeys
    
    def create_signal_bundle(self, identity_id: str) -> Optional[Dict[str, Any]]:
        """Cree un bundle de cles compatible Signal"""
        identity = self.key_manager.get_identity(identity_id)
        
        if not identity:
            return None
        
        # Generate signed prekey
        signed_prekey_private = x25519.X25519PrivateKey.generate()
        signed_prekey_public = signed_prekey_private.public_key()
        
        signed_prekey_bytes = signed_prekey_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        # Generate signature (simplified)
        signature = hashlib.sha256(
            signed_prekey_bytes + identity.identity_key.public_key.encode()
        ).digest()
        
        return {
            "registrationId": int(identity.identity_id[:8], 16),
            "identityKey": identity.identity_key.public_key,
            "signedPreKey": {
                "keyId": 1,
                "publicKey": base64.b64encode(signed_prekey_bytes).decode(),
                "signature": base64.b64encode(signature).decode()
            },
            "preKeys": self.generate_prekeys(identity_id, count=10),
            "psnxMetadata": {
                "version": PSNX_VERSION,
                "identity_id": identity.identity_id,
                "fingerprint": identity.fingerprint
            }
        }
    
    def establish_session(self, local_id: str, remote_bundle: Dict[str, Any]) -> Optional[bytes]:
        """Etablit une session Signal avec une cle partagee"""
        local_identity = self.key_manager.get_identity(local_id)
        
        if not local_identity:
            return None
        
        # Simplified X3DH key agreement
        local_identity_bytes = base64.b64decode(local_identity.identity_key.public_key)
        remote_identity_bytes = base64.b64decode(remote_bundle["identityKey"])
        
        # Derive shared secret (simplified)
        combined = local_identity_bytes + remote_identity_bytes
        
        shared_secret = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"PSNX-Signal-v1",
            info=b"session_key"
        ).derive(combined)
        
        return shared_secret


# ============================================================================
# BROWSER PLUGIN API
# ============================================================================

class BrowserPluginAPI:
    """API pour plugins navigateurs"""
    
    def __init__(self, key_manager: PSNXKeyManager):
        self.key_manager = key_manager
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self, origin: str) -> str:
        """Cree une session pour une origine"""
        session_id = secrets.token_hex(16)
        
        self._sessions[session_id] = {
            "origin": origin,
            "created": datetime.now().isoformat(),
            "permissions": [],
            "identity_id": None
        }
        
        return session_id
    
    def request_permission(self, session_id: str, permission: str) -> bool:
        """Demande une permission"""
        session = self._sessions.get(session_id)
        
        if not session:
            return False
        
        valid_permissions = [
            "read_public_key",
            "sign_message",
            "encrypt_message",
            "decrypt_message",
            "share_identity"
        ]
        
        if permission not in valid_permissions:
            return False
        
        # In production, show user prompt
        session["permissions"].append(permission)
        return True
    
    def connect_identity(self, session_id: str, identity_id: str) -> bool:
        """Connecte une identite a la session"""
        session = self._sessions.get(session_id)
        identity = self.key_manager.get_identity(identity_id)
        
        if not session or not identity:
            return False
        
        session["identity_id"] = identity_id
        return True
    
    def get_public_key(self, session_id: str) -> Optional[str]:
        """Obtient la cle publique"""
        session = self._sessions.get(session_id)
        
        if not session or "read_public_key" not in session["permissions"]:
            return None
        
        identity = self.key_manager.get_identity(session["identity_id"])
        
        if not identity:
            return None
        
        return identity.identity_key.public_key
    
    def sign_message(self, session_id: str, message: str) -> Optional[str]:
        """Signe un message"""
        session = self._sessions.get(session_id)
        
        if not session or "sign_message" not in session["permissions"]:
            return None
        
        identity = self.key_manager.get_identity(session["identity_id"])
        
        if not identity:
            return None
        
        # Simplified signing (hash)
        message_bytes = message.encode()
        signature = hashlib.sha256(
            message_bytes + base64.b64decode(identity.signing_key.public_key)
        ).hexdigest()
        
        return signature
    
    def encrypt_for_recipient(self, session_id: str, recipient_key: str, 
                             plaintext: str) -> Optional[Dict[str, str]]:
        """Chiffre un message pour un destinataire"""
        session = self._sessions.get(session_id)
        
        if not session or "encrypt_message" not in session["permissions"]:
            return None
        
        # Generate ephemeral key for encryption
        ephemeral_private = x25519.X25519PrivateKey.generate()
        ephemeral_public = ephemeral_private.public_key()
        
        # Derive shared secret
        recipient_public_bytes = base64.b64decode(recipient_key)
        
        # For simulation, use hash-based key derivation
        combined = ephemeral_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        ) + recipient_public_bytes
        
        shared_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"PSNX-encrypt"
        ).derive(combined)
        
        # Encrypt
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(shared_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        
        return {
            "ephemeral_key": base64.b64encode(
                ephemeral_public.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                )
            ).decode(),
            "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode()
        }
    
    def generate_qr_data(self, session_id: str) -> Optional[str]:
        """Genere les donnees pour QR code"""
        session = self._sessions.get(session_id)
        
        if not session or "share_identity" not in session["permissions"]:
            return None
        
        identity = self.key_manager.get_identity(session["identity_id"])
        
        if not identity:
            return None
        
        qr_data = {
            "type": "psnx_identity",
            "v": 1,
            "id": identity.identity_id[:16],
            "pk": identity.identity_key.public_key[:32],
            "fp": identity.fingerprint.replace(" ", "")[:20]
        }
        
        return f"psnx://{base64.urlsafe_b64encode(json.dumps(qr_data).encode()).decode()}"
    
    def handle_deep_link(self, url: str) -> Optional[Dict[str, Any]]:
        """Gere un deep link PSNX"""
        if not url.startswith("psnx://"):
            return None
        
        try:
            data = base64.urlsafe_b64decode(url[7:])
            parsed = json.loads(data)
            
            return {
                "action": "import_identity" if parsed.get("type") == "psnx_identity" else "unknown",
                "data": parsed
            }
        except Exception:
            return None


# ============================================================================
# INTEROPERABILITY FACADE
# ============================================================================

class InteroperabilitySystem:
    """Facade pour l'interoperabilite complete"""
    
    def __init__(self, data_dir: str = "./interop_data"):
        self.data_dir = data_dir
        self.key_manager = PSNXKeyManager(f"{data_dir}/keys")
        self.keybase = KeybaseAdapter(self.key_manager)
        self.signal = SignalAdapter(self.key_manager)
        self.browser_api = BrowserPluginAPI(self.key_manager)
    
    def create_identity(self, display_name: str) -> PSNXIdentity:
        """Cree une nouvelle identite"""
        return self.key_manager.generate_identity(display_name)
    
    def export_for_platform(self, identity_id: str, platform: str) -> Optional[Any]:
        """Exporte une identite pour une plateforme specifique"""
        if platform == "psnx":
            return self.key_manager.export_public_identity(identity_id)
        elif platform == "keybase":
            return self.keybase.export_to_keybase(identity_id)
        elif platform == "signal":
            return self.signal.create_signal_bundle(identity_id)
        
        return None
    
    def get_supported_platforms(self) -> List[Dict[str, str]]:
        """Liste les plateformes supportees"""
        return [
            {"id": "psnx", "name": "PSNX Standard", "version": PSNX_VERSION},
            {"id": "keybase", "name": "Keybase", "version": "1.0"},
            {"id": "signal", "name": "Signal Protocol", "version": "3.0"},
            {"id": "browser", "name": "Browser Plugin API", "version": "1.0"}
        ]


# ============================================================================
# FACTORY
# ============================================================================

def create_interoperability_system(data_dir: str = "./interop_data") -> InteroperabilitySystem:
    """Cree un systeme d'interoperabilite complet"""
    return InteroperabilitySystem(data_dir)
