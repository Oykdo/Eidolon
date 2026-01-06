"""
Generateur de cles pour le SDK Poly-Spinor Nexus 7D
"""

import secrets
import hashlib
from dataclasses import dataclass
from typing import Optional, Tuple

from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from .exceptions import KeyError, ValidationError


@dataclass
class KeyPair:
    """Paire de cles"""
    vault_key: bytes
    public_key: int
    fingerprint: str
    entropy_bits: int
    
    def to_dict(self) -> dict:
        return {
            "vault_key_hex": self.vault_key.hex(),
            "public_key_hex": hex(self.public_key),
            "fingerprint": self.fingerprint,
            "entropy_bits": self.entropy_bits
        }


class KeyGenerator:
    """
    Generateur de cles securise.
    
    Usage:
        gen = KeyGenerator()
        
        # Generation simple
        vault_key = gen.generate()
        
        # Generation avec mot de passe
        vault_key = gen.from_password("mon_mot_de_passe")
        
        # Generation avec entropie externe
        vault_key = gen.from_entropy(my_entropy_bytes)
        
        # Generation complete avec paire
        key_pair = gen.generate_keypair()
    """
    
    KEY_SIZE = 32
    SCRYPT_N = 2**17
    SCRYPT_R = 8
    SCRYPT_P = 1
    
    def __init__(self, extra_entropy: Optional[bytes] = None):
        """
        Args:
            extra_entropy: Entropie supplementaire optionnelle
        """
        self._extra = extra_entropy or b""
    
    def generate(self) -> bytes:
        """
        Genere une cle vault aleatoire.
        
        Returns:
            Cle de 32 bytes
        """
        entropy = secrets.token_bytes(64) + self._extra
        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=b"PSNX_KEYGEN_v1",
            info=b"vault_master_key"
        )
        
        return hkdf.derive(entropy)
    
    def from_password(
        self,
        password: str,
        salt: Optional[bytes] = None
    ) -> Tuple[bytes, bytes]:
        """
        Derive une cle depuis un mot de passe via Scrypt.
        
        Args:
            password: Mot de passe
            salt: Sel optionnel (genere si non fourni)
        
        Returns:
            (vault_key, salt)
        """
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        
        if salt is None:
            salt = secrets.token_bytes(16)
        
        kdf = Scrypt(
            salt=salt,
            length=self.KEY_SIZE,
            n=self.SCRYPT_N,
            r=self.SCRYPT_R,
            p=self.SCRYPT_P
        )
        
        vault_key = kdf.derive(password.encode())
        return vault_key, salt
    
    def from_entropy(self, entropy: bytes, min_bits: int = 256) -> bytes:
        """
        Genere une cle depuis de l'entropie externe.
        
        Args:
            entropy: Entropie (min 32 bytes recommande)
            min_bits: Bits minimum requis
        
        Returns:
            Cle de 32 bytes
        """
        if len(entropy) * 8 < min_bits:
            raise ValidationError(f"Entropy must be at least {min_bits} bits")
        
        # Mixer avec entropie systeme
        combined = entropy + secrets.token_bytes(32) + self._extra
        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=b"PSNX_EXTERNAL_ENTROPY",
            info=b"vault_key_from_external"
        )
        
        return hkdf.derive(combined)
    
    def generate_keypair(self) -> KeyPair:
        """
        Genere une paire complete (vault_key + public_key ZKP).
        
        Returns:
            KeyPair avec toutes les informations
        """
        vault_key = self.generate()
        
        # Deriver la cle privee ZKP
        zkp_private = int.from_bytes(
            hashlib.sha256(b"ZKP_PRIVATE_" + vault_key).digest(),
            'big'
        )
        
        # Parametres du groupe (RFC 5114)
        P = int(
            "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
            "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
            "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
            "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
            "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
            "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
            "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
            "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
            "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
            "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
            "15728E5A8AACAA68FFFFFFFFFFFFFFFF", 16
        )
        Q = (P - 1) // 2
        G = 2
        
        # Cle privee mod Q
        x = zkp_private % Q
        if x == 0:
            x = 1
        
        # Cle publique
        public_key = pow(G, x, P)
        
        return KeyPair(
            vault_key=vault_key,
            public_key=public_key,
            fingerprint=hashlib.sha256(vault_key).hexdigest()[:16],
            entropy_bits=256
        )
    
    @staticmethod
    def verify_key(vault_key: bytes) -> bool:
        """Verifie qu'une cle est valide"""
        return len(vault_key) == 32 and vault_key != bytes(32)
