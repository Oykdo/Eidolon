"""
Shamir Secret Sharing pour le SDK Poly-Spinor Nexus 7D
"""

import secrets
import hashlib
import base64
from dataclasses import dataclass
from typing import List, Optional

from .exceptions import ShareError, ValidationError


@dataclass
class Share:
    """Une part du secret"""
    index: int
    data: bytes
    threshold: int
    total: int
    checksum: str
    
    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "data": base64.b64encode(self.data).decode(),
            "threshold": self.threshold,
            "total": self.total,
            "checksum": self.checksum
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "Share":
        return cls(
            index=d["index"],
            data=base64.b64decode(d["data"]),
            threshold=d["threshold"],
            total=d["total"],
            checksum=d["checksum"]
        )
    
    def verify(self) -> bool:
        """Verifie le checksum"""
        expected = hashlib.sha256(
            self.data + self.index.to_bytes(4, 'big')
        ).hexdigest()[:8]
        return self.checksum == expected


class SecretSharing:
    """
    Shamir Secret Sharing Scheme.
    
    Divise un secret en N parts, K necessaires pour reconstruire.
    
    Usage:
        ss = SecretSharing(threshold=3, total=5)
        
        # Diviser
        shares = ss.split(vault_key)
        
        # Reconstruire (avec 3+ parts)
        recovered = ss.reconstruct([shares[0], shares[2], shares[4]])
    """
    
    # Prime pour GF(p)
    PRIME = 2**256 - 189
    
    def __init__(self, threshold: int = 3, total: int = 5):
        """
        Args:
            threshold: K - minimum de parts pour reconstruire
            total: N - nombre total de parts
        """
        if threshold < 2:
            raise ValidationError("Threshold must be >= 2")
        if total < threshold:
            raise ValidationError("Total must be >= threshold")
        if total > 255:
            raise ValidationError("Maximum 255 shares")
        
        self.k = threshold
        self.n = total
    
    def split(self, secret: bytes) -> List[Share]:
        """
        Divise le secret en N parts.
        
        Args:
            secret: Secret a partager (max 32 bytes)
        
        Returns:
            Liste de N parts
        """
        if len(secret) > 32:
            raise ValidationError("Secret too large (max 32 bytes)")
        
        # Convertir en entier
        secret_int = int.from_bytes(secret, 'big')
        
        # Coefficients du polynome
        coefficients = [secret_int]
        for _ in range(self.k - 1):
            coefficients.append(secrets.randbelow(self.PRIME - 1) + 1)
        
        # Evaluer en N points
        shares = []
        for x in range(1, self.n + 1):
            y = self._evaluate(coefficients, x)
            y_bytes = y.to_bytes(32, 'big')
            
            checksum = hashlib.sha256(
                y_bytes + x.to_bytes(4, 'big')
            ).hexdigest()[:8]
            
            shares.append(Share(
                index=x,
                data=y_bytes,
                threshold=self.k,
                total=self.n,
                checksum=checksum
            ))
        
        return shares
    
    def reconstruct(self, shares: List[Share]) -> bytes:
        """
        Reconstruit le secret depuis K parts.
        
        Args:
            shares: Liste de K+ parts
        
        Returns:
            Secret original
        """
        if len(shares) < self.k:
            raise ShareError(f"Need {self.k} shares, got {len(shares)}")
        
        # Verifier les checksums
        for share in shares:
            if not share.verify():
                raise ShareError(f"Share {share.index} corrupted")
        
        # Utiliser K parts
        shares = shares[:self.k]
        
        # Verifier unicite
        indices = [s.index for s in shares]
        if len(set(indices)) != len(indices):
            raise ShareError("Duplicate shares")
        
        # Points (x, y)
        points = [(s.index, int.from_bytes(s.data, 'big')) for s in shares]
        
        # Interpolation de Lagrange
        secret_int = self._lagrange(points, 0)
        
        # Convertir en bytes
        return secret_int.to_bytes(32, 'big').lstrip(b'\x00') or b'\x00'
    
    def _evaluate(self, coefficients: List[int], x: int) -> int:
        """Evalue le polynome en x"""
        result = 0
        x_power = 1
        for coeff in coefficients:
            result = (result + coeff * x_power) % self.PRIME
            x_power = (x_power * x) % self.PRIME
        return result
    
    def _lagrange(self, points: List[tuple], x: int) -> int:
        """Interpolation de Lagrange"""
        result = 0
        for i, (xi, yi) in enumerate(points):
            num = 1
            den = 1
            for j, (xj, _) in enumerate(points):
                if i != j:
                    num = (num * (x - xj)) % self.PRIME
                    den = (den * (xi - xj)) % self.PRIME
            
            coeff = (num * pow(den, -1, self.PRIME)) % self.PRIME
            result = (result + yi * coeff) % self.PRIME
        
        return result
    
    @staticmethod
    def create_recovery_shares(
        vault_key: bytes,
        threshold: int = 2,
        total: int = 3
    ) -> List[dict]:
        """
        Fonction utilitaire pour creer des parts de recuperation.
        
        Returns:
            Liste de parts en format dict
        """
        ss = SecretSharing(threshold, total)
        shares = ss.split(vault_key)
        return [s.to_dict() for s in shares]
    
    @staticmethod
    def recover_from_shares(share_dicts: List[dict]) -> bytes:
        """
        Fonction utilitaire pour recuperer depuis des dicts.
        """
        shares = [Share.from_dict(d) for d in share_dicts]
        if not shares:
            raise ShareError("No shares provided")
        
        ss = SecretSharing(shares[0].threshold, shares[0].total)
        return ss.reconstruct(shares)
