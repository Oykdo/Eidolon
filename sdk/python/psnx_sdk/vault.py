"""
Module Vault pour le SDK Poly-Spinor Nexus 7D

Chiffrement/dechiffrement local avec AES-256-GCM.
"""

import os
import base64
import hashlib
import secrets
from dataclasses import dataclass
from typing import Optional, Dict, Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from .exceptions import EncryptionError, DecryptionError, ValidationError


@dataclass
class EncryptedData:
    """Donnees chiffrees"""
    ciphertext: bytes
    nonce: bytes
    tag: bytes
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            "ciphertext": base64.b64encode(self.ciphertext).decode(),
            "nonce": base64.b64encode(self.nonce).decode(),
            "tag": base64.b64encode(self.tag).decode(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "EncryptedData":
        """Cree depuis un dictionnaire"""
        return cls(
            ciphertext=base64.b64decode(data["ciphertext"]),
            nonce=base64.b64decode(data["nonce"]),
            tag=base64.b64decode(data["tag"]),
            metadata=data.get("metadata")
        )
    
    def to_bytes(self) -> bytes:
        """Serialise en bytes"""
        import json
        return json.dumps(self.to_dict()).encode()
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "EncryptedData":
        """Deserialise depuis bytes"""
        import json
        return cls.from_dict(json.loads(data.decode()))


class Vault:
    """
    Vault local pour chiffrement/dechiffrement.
    
    Utilise AES-256-GCM pour le chiffrement authentifie.
    
    Usage:
        vault = Vault(vault_key)
        
        # Chiffrer
        encrypted = vault.encrypt(b"mes donnees")
        
        # Dechiffrer
        decrypted = vault.decrypt(encrypted)
        
        # Avec metadata
        encrypted = vault.encrypt(b"data", metadata={"type": "document"})
    """
    
    NONCE_SIZE = 12
    TAG_SIZE = 16
    KEY_SIZE = 32
    
    def __init__(self, vault_key: bytes):
        """
        Args:
            vault_key: Cle du vault (32 bytes)
        """
        if len(vault_key) != self.KEY_SIZE:
            raise ValidationError(f"vault_key must be {self.KEY_SIZE} bytes")
        
        self._master_key = vault_key
        self._encryption_key = self._derive_key(b"encryption")
        self._auth_key = self._derive_key(b"authentication")
    
    def _derive_key(self, purpose: bytes) -> bytes:
        """Derive une cle pour un usage specifique"""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=b"PSNX_SDK_v1",
            info=purpose
        )
        return hkdf.derive(self._master_key)
    
    def encrypt(
        self,
        plaintext: bytes,
        metadata: Optional[Dict[str, Any]] = None,
        associated_data: Optional[bytes] = None
    ) -> EncryptedData:
        """
        Chiffre des donnees avec AES-256-GCM.
        
        Args:
            plaintext: Donnees a chiffrer
            metadata: Metadonnees optionnelles (non chiffrees)
            associated_data: Donnees associees pour l'authentification
        
        Returns:
            EncryptedData avec ciphertext, nonce, tag
        """
        try:
            nonce = secrets.token_bytes(self.NONCE_SIZE)
            aesgcm = AESGCM(self._encryption_key)
            
            # Chiffrer (le tag est inclus dans le ciphertext)
            ciphertext_with_tag = aesgcm.encrypt(
                nonce, plaintext, associated_data
            )
            
            # Separer ciphertext et tag
            ciphertext = ciphertext_with_tag[:-self.TAG_SIZE]
            tag = ciphertext_with_tag[-self.TAG_SIZE:]
            
            return EncryptedData(
                ciphertext=ciphertext,
                nonce=nonce,
                tag=tag,
                metadata=metadata
            )
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}")
    
    def decrypt(
        self,
        encrypted: EncryptedData,
        associated_data: Optional[bytes] = None
    ) -> bytes:
        """
        Dechiffre des donnees.
        
        Args:
            encrypted: Donnees chiffrees
            associated_data: Donnees associees (doit correspondre au chiffrement)
        
        Returns:
            Donnees dechiffrees
        """
        try:
            aesgcm = AESGCM(self._encryption_key)
            
            # Recombiner ciphertext et tag
            ciphertext_with_tag = encrypted.ciphertext + encrypted.tag
            
            return aesgcm.decrypt(
                encrypted.nonce,
                ciphertext_with_tag,
                associated_data
            )
        except Exception as e:
            raise DecryptionError(f"Decryption failed: {e}")
    
    def encrypt_file(
        self,
        input_path: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Chiffre un fichier.
        
        Args:
            input_path: Chemin du fichier source
            output_path: Chemin de sortie (defaut: input_path + .enc)
        
        Returns:
            Chemin du fichier chiffre
        """
        if output_path is None:
            output_path = input_path + ".enc"
        
        with open(input_path, "rb") as f:
            plaintext = f.read()
        
        encrypted = self.encrypt(
            plaintext,
            metadata={"original_name": os.path.basename(input_path)}
        )
        
        with open(output_path, "wb") as f:
            f.write(encrypted.to_bytes())
        
        return output_path
    
    def decrypt_file(
        self,
        input_path: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Dechiffre un fichier.
        
        Args:
            input_path: Chemin du fichier chiffre
            output_path: Chemin de sortie
        
        Returns:
            Chemin du fichier dechiffre
        """
        with open(input_path, "rb") as f:
            data = f.read()
        
        encrypted = EncryptedData.from_bytes(data)
        plaintext = self.decrypt(encrypted)
        
        if output_path is None:
            if encrypted.metadata and "original_name" in encrypted.metadata:
                output_path = encrypted.metadata["original_name"]
            else:
                output_path = input_path.replace(".enc", "")
        
        with open(output_path, "wb") as f:
            f.write(plaintext)
        
        return output_path
    
    def get_fingerprint(self) -> str:
        """Retourne l'empreinte du vault (pour identification)"""
        return hashlib.sha256(self._master_key).hexdigest()[:16]
    
    def derive_subkey(self, purpose: str) -> bytes:
        """
        Derive une sous-cle pour un usage specifique.
        
        Args:
            purpose: Description de l'usage
        
        Returns:
            Sous-cle de 32 bytes
        """
        return self._derive_key(purpose.encode())
