"""
Format de Fichier Authentifie HMAC-SHA256
Poly-Spinor Nexus 7D - Security Module

Features:
- Authentification HMAC-SHA256
- Detection de modification
- Versioning integre
- Compression optionnelle
"""

import hmac
import hashlib
import struct
import json
import zlib
import time
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class FileFormatError(Exception):
    """Erreur de format de fichier"""
    pass


class AuthenticationError(Exception):
    """Erreur d'authentification (fichier modifie)"""
    pass


class FileVersion(Enum):
    """Versions du format de fichier"""
    V1 = 1  # Initial
    V2 = 2  # Avec compression
    V3 = 3  # Avec audit fixes
    V4 = 4  # Avec HMAC authentification


@dataclass
class FileMetadata:
    """Metadonnees du fichier"""
    version: int
    created_at: float
    key_id: str
    file_type: str  # 'psnx' ou 'blend_data'
    compressed: bool
    original_size: int
    checksum_sha256: str
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FileMetadata':
        return cls(**data)


class AuthenticatedFileFormat:
    """
    Format de fichier avec authentification HMAC-SHA256.
    
    Structure du fichier:
    ┌────────────────────────────────────────────┐
    │ Magic: "PSNX" (4 bytes)                    │
    ├────────────────────────────────────────────┤
    │ Version: uint8 (1 byte)                    │
    ├────────────────────────────────────────────┤
    │ Flags: uint8 (1 byte)                      │
    │   bit 0: compressed                        │
    │   bit 1: encrypted (future)                │
    │   bit 2-7: reserved                        │
    ├────────────────────────────────────────────┤
    │ Metadata length: uint32 BE (4 bytes)       │
    ├────────────────────────────────────────────┤
    │ Metadata: JSON (variable)                  │
    ├────────────────────────────────────────────┤
    │ Data length: uint32 BE (4 bytes)           │
    ├────────────────────────────────────────────┤
    │ Data: bytes (variable)                     │
    ├────────────────────────────────────────────┤
    │ HMAC-SHA256: (32 bytes)                    │
    └────────────────────────────────────────────┘
    
    Usage:
        # Ecriture
        aff = AuthenticatedFileFormat(auth_key)
        aff.write_file(path, data, metadata)
        
        # Lecture
        metadata, data = aff.read_file(path)
    """
    
    MAGIC = b'PSNX'
    CURRENT_VERSION = FileVersion.V4.value
    HEADER_SIZE = 10  # Magic(4) + Version(1) + Flags(1) + MetaLen(4)
    HMAC_SIZE = 32
    
    # Flags
    FLAG_COMPRESSED = 0x01
    FLAG_ENCRYPTED = 0x02  # Future use
    
    def __init__(self, auth_key: bytes):
        """
        Args:
            auth_key: Cle d'authentification HMAC (32 bytes recommande)
        """
        if len(auth_key) < 16:
            raise ValueError("Cle d'authentification trop courte (min 16 bytes)")
        self.auth_key = auth_key
    
    def create_file(
        self,
        data: bytes,
        file_type: str,
        key_id: str,
        compress: bool = True
    ) -> bytes:
        """
        Cree un fichier authentifie.
        
        Args:
            data: Donnees a stocker
            file_type: Type de fichier ('psnx' ou 'blend_data')
            key_id: Identifiant de la cle
            compress: Compresser les donnees
        
        Returns:
            Contenu du fichier pret a etre ecrit
        """
        original_size = len(data)
        
        # Compression optionnelle
        if compress:
            compressed_data = zlib.compress(data, level=9)
            # Ne compresser que si ca reduit la taille
            if len(compressed_data) < original_size:
                data = compressed_data
            else:
                compress = False
        
        # Calculer le checksum des donnees originales
        checksum = hashlib.sha256(data).hexdigest()
        
        # Creer les metadonnees
        metadata = FileMetadata(
            version=self.CURRENT_VERSION,
            created_at=time.time(),
            key_id=key_id,
            file_type=file_type,
            compressed=compress,
            original_size=original_size,
            checksum_sha256=checksum
        )
        
        metadata_bytes = json.dumps(metadata.to_dict()).encode('utf-8')
        
        # Construire les flags
        flags = 0
        if compress:
            flags |= self.FLAG_COMPRESSED
        
        # Construire le payload (sans HMAC)
        payload = (
            self.MAGIC +
            struct.pack('>B', self.CURRENT_VERSION) +
            struct.pack('>B', flags) +
            struct.pack('>I', len(metadata_bytes)) +
            metadata_bytes +
            struct.pack('>I', len(data)) +
            data
        )
        
        # Calculer HMAC
        file_hmac = hmac.new(self.auth_key, payload, hashlib.sha256).digest()
        
        return payload + file_hmac
    
    def parse_file(self, file_data: bytes) -> Tuple[FileMetadata, bytes]:
        """
        Parse et verifie un fichier authentifie.
        
        Args:
            file_data: Contenu du fichier
        
        Returns:
            (metadata, data) si authentification reussie
        
        Raises:
            AuthenticationError: Si le fichier a ete modifie
            FileFormatError: Si le format est invalide
        """
        min_size = self.HEADER_SIZE + self.HMAC_SIZE
        if len(file_data) < min_size:
            raise FileFormatError(f"Fichier trop court ({len(file_data)} < {min_size})")
        
        # Separer payload et HMAC
        payload = file_data[:-self.HMAC_SIZE]
        stored_hmac = file_data[-self.HMAC_SIZE:]
        
        # Verifier HMAC (comparaison en temps constant)
        computed_hmac = hmac.new(self.auth_key, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(stored_hmac, computed_hmac):
            raise AuthenticationError(
                "Authentification echouee - fichier corrompu ou modifie!"
            )
        
        # Parser le header
        offset = 0
        
        # Magic
        magic = payload[offset:offset+4]
        if magic != self.MAGIC:
            raise FileFormatError(f"Magic invalide: {magic}")
        offset += 4
        
        # Version
        version = struct.unpack('>B', payload[offset:offset+1])[0]
        offset += 1
        
        # Flags
        flags = struct.unpack('>B', payload[offset:offset+1])[0]
        offset += 1
        
        # Metadata
        meta_len = struct.unpack('>I', payload[offset:offset+4])[0]
        offset += 4
        
        if offset + meta_len > len(payload):
            raise FileFormatError("Longueur metadata invalide")
        
        metadata_bytes = payload[offset:offset+meta_len]
        offset += meta_len
        
        try:
            metadata_dict = json.loads(metadata_bytes.decode('utf-8'))
            metadata = FileMetadata.from_dict(metadata_dict)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise FileFormatError(f"Metadata invalide: {e}")
        
        # Data
        data_len = struct.unpack('>I', payload[offset:offset+4])[0]
        offset += 4
        
        if offset + data_len > len(payload):
            raise FileFormatError("Longueur data invalide")
        
        data = payload[offset:offset+data_len]
        
        # Verifier checksum
        if hashlib.sha256(data).hexdigest() != metadata.checksum_sha256:
            raise AuthenticationError("Checksum invalide - donnees corrompues")
        
        # Decompresser si necessaire
        if flags & self.FLAG_COMPRESSED:
            try:
                data = zlib.decompress(data)
            except zlib.error as e:
                raise FileFormatError(f"Erreur decompression: {e}")
        
        return metadata, data
    
    def write_file(
        self,
        path: str,
        data: bytes,
        file_type: str,
        key_id: str,
        compress: bool = True
    ) -> FileMetadata:
        """
        Ecrit un fichier authentifie.
        
        Args:
            path: Chemin du fichier
            data: Donnees a stocker
            file_type: Type ('psnx' ou 'blend_data')
            key_id: Identifiant de la cle
            compress: Compresser les donnees
        
        Returns:
            Metadonnees du fichier cree
        """
        file_content = self.create_file(data, file_type, key_id, compress)
        
        with open(path, 'wb') as f:
            f.write(file_content)
        
        # Retourner les metadonnees
        _, metadata_bytes_end = self._find_metadata_bounds(file_content)
        metadata_start = self.HEADER_SIZE - 4
        meta_len = struct.unpack('>I', file_content[6:10])[0]
        metadata_bytes = file_content[10:10+meta_len]
        return FileMetadata.from_dict(json.loads(metadata_bytes.decode('utf-8')))
    
    def read_file(self, path: str) -> Tuple[FileMetadata, bytes]:
        """
        Lit et verifie un fichier authentifie.
        
        Args:
            path: Chemin du fichier
        
        Returns:
            (metadata, data)
        """
        with open(path, 'rb') as f:
            file_data = f.read()
        
        return self.parse_file(file_data)
    
    def _find_metadata_bounds(self, file_content: bytes) -> Tuple[int, int]:
        """Trouve les limites des metadonnees"""
        meta_len = struct.unpack('>I', file_content[6:10])[0]
        return 10, 10 + meta_len
    
    @staticmethod
    def derive_auth_key(master_key: bytes, purpose: str = "file_auth") -> bytes:
        """
        Derive une cle d'authentification depuis la cle maitre.
        
        Args:
            master_key: Cle maitre
            purpose: Usage de la cle derivee
        
        Returns:
            Cle d'authentification 32 bytes
        """
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives import hashes
        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'PSNX_AUTH_KEY_v4',
            info=purpose.encode('utf-8')
        )
        return hkdf.derive(master_key)


class SecurePSNXFile:
    """
    Wrapper haut niveau pour fichiers PSNX securises.
    """
    
    def __init__(self, vault_key: bytes):
        """
        Args:
            vault_key: Cle du vault
        """
        self.auth_key = AuthenticatedFileFormat.derive_auth_key(
            vault_key, "psnx_file_auth"
        )
        self.aff = AuthenticatedFileFormat(self.auth_key)
    
    def save_key_data(
        self,
        path: str,
        key_data: dict,
        key_id: str
    ) -> FileMetadata:
        """Sauvegarde les donnees de cle"""
        data = json.dumps(key_data, default=str).encode('utf-8')
        return self.aff.write_file(path, data, 'psnx', key_id)
    
    def load_key_data(self, path: str) -> Tuple[FileMetadata, dict]:
        """Charge les donnees de cle"""
        metadata, data = self.aff.read_file(path)
        key_data = json.loads(data.decode('utf-8'))
        return metadata, key_data
    
    def save_blend_data(
        self,
        path: str,
        blend_data: dict,
        key_id: str
    ) -> FileMetadata:
        """Sauvegarde les donnees Blender"""
        data = json.dumps(blend_data, default=str).encode('utf-8')
        return self.aff.write_file(path, data, 'blend_data', key_id)
    
    def load_blend_data(self, path: str) -> Tuple[FileMetadata, dict]:
        """Charge les donnees Blender"""
        metadata, data = self.aff.read_file(path)
        blend_data = json.loads(data.decode('utf-8'))
        return metadata, blend_data


def verify_file_integrity(path: str, auth_key: bytes) -> bool:
    """
    Verifie l'integrite d'un fichier sans le charger completement.
    
    Args:
        path: Chemin du fichier
        auth_key: Cle d'authentification
    
    Returns:
        True si le fichier est authentique
    """
    try:
        aff = AuthenticatedFileFormat(auth_key)
        aff.read_file(path)
        return True
    except (AuthenticationError, FileFormatError):
        return False
