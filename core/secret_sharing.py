"""
Shamir's Secret Sharing Scheme
Poly-Spinor Nexus 7D - Security Module

Implementation du partage de secret de Shamir pour:
- Vault multi-signatures
- Recuperation d'urgence
- Cles distribuees

Basee sur l'interpolation de Lagrange sur un corps fini GF(p)
"""

import secrets
import hashlib
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, asdict
import json
import base64


class SecretSharingError(Exception):
    """Erreur de partage de secret"""
    pass


@dataclass
class Share:
    """Une part du secret"""
    index: int           # x-coordinate (1 to n)
    data: bytes          # y-coordinate value
    threshold: int       # k - nombre minimum pour reconstruire
    total: int           # n - nombre total de parts
    checksum: str        # Verification
    version: int = 1
    
    def to_dict(self) -> dict:
        return {
            'index': self.index,
            'data': base64.b64encode(self.data).decode('ascii'),
            'threshold': self.threshold,
            'total': self.total,
            'checksum': self.checksum,
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> 'Share':
        return cls(
            index=d['index'],
            data=base64.b64decode(d['data']),
            threshold=d['threshold'],
            total=d['total'],
            checksum=d['checksum'],
            version=d.get('version', 1)
        )
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, s: str) -> 'Share':
        return cls.from_dict(json.loads(s))
    
    def verify_checksum(self) -> bool:
        """Verifie l'integrite de la part"""
        expected = hashlib.sha256(
            self.data + 
            self.index.to_bytes(4, 'big') +
            self.threshold.to_bytes(4, 'big')
        ).hexdigest()[:8]
        return self.checksum == expected


class ShamirSecretSharing:
    """
    Implementation de Shamir's Secret Sharing Scheme.
    
    Divise un secret en N parts, dont K sont necessaires
    pour reconstruire le secret original.
    
    Proprietes:
    - Information-theoretic security: K-1 parts ne revelent RIEN
    - Reconstruction parfaite avec exactement K parts
    - Basee sur l'interpolation polynomiale
    
    Usage:
        sss = ShamirSecretSharing(threshold=3, total_shares=5)
        shares = sss.split(secret_bytes)
        
        # Reconstruction avec 3 parts quelconques
        recovered = sss.reconstruct([shares[0], shares[2], shares[4]])
        assert recovered == secret_bytes
    """
    
    # Prime pour le corps fini GF(p)
    # Mersenne prime proche de 2^256 pour securite maximale
    PRIME = 2**256 - 189
    
    def __init__(self, threshold: int, total_shares: int):
        """
        Args:
            threshold: K - nombre minimum de parts pour reconstruire
            total_shares: N - nombre total de parts a generer
        """
        if threshold < 2:
            raise ValueError("Threshold doit etre >= 2")
        if total_shares < threshold:
            raise ValueError("Total shares doit etre >= threshold")
        if total_shares > 255:
            raise ValueError("Maximum 255 parts")
        
        self.k = threshold
        self.n = total_shares
    
    def split(self, secret: bytes) -> List[Share]:
        """
        Divise le secret en N parts.
        
        Args:
            secret: Le secret a partager (max 32 bytes pour un split direct)
        
        Returns:
            Liste de N parts
        
        Pour des secrets plus grands, utiliser split_large().
        """
        if len(secret) > 32:
            return self._split_large(secret)
        
        # Convertir le secret en entier
        secret_int = int.from_bytes(secret, 'big')
        
        if secret_int >= self.PRIME:
            raise ValueError("Secret trop grand pour le corps fini")
        
        # Generer K-1 coefficients aleatoires pour le polynome
        # P(x) = secret + a1*x + a2*x^2 + ... + a_{k-1}*x^{k-1}
        coefficients = [secret_int]
        for _ in range(self.k - 1):
            coeff = secrets.randbelow(self.PRIME - 1) + 1
            coefficients.append(coeff)
        
        # Evaluer le polynome en N points (x = 1, 2, ..., N)
        shares = []
        for x in range(1, self.n + 1):
            y = self._evaluate_polynomial(coefficients, x)
            
            # Convertir y en bytes (32 bytes pour supporter le prime)
            y_bytes = y.to_bytes(32, 'big')
            
            # Checksum
            checksum = hashlib.sha256(
                y_bytes + x.to_bytes(4, 'big') + self.k.to_bytes(4, 'big')
            ).hexdigest()[:8]
            
            share = Share(
                index=x,
                data=y_bytes,
                threshold=self.k,
                total=self.n,
                checksum=checksum
            )
            shares.append(share)
        
        return shares
    
    def _split_large(self, secret: bytes) -> List[Share]:
        """
        Divise un secret de taille arbitraire.
        Utilise le chiffrement XOR avec une cle partagee.
        """
        # Generer une cle aleatoire
        key = secrets.token_bytes(32)
        
        # Chiffrer le secret avec XOR (one-time pad si |key| >= |secret|)
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, secret, None)
        
        # Partager la cle avec Shamir
        key_shares = self.split(key)
        
        # Stocker le ciphertext et nonce dans chaque part
        shares = []
        for ks in key_shares:
            # Combiner: key_share || nonce || ciphertext
            combined = ks.data + nonce + ciphertext
            
            checksum = hashlib.sha256(
                combined + ks.index.to_bytes(4, 'big')
            ).hexdigest()[:8]
            
            share = Share(
                index=ks.index,
                data=combined,
                threshold=self.k,
                total=self.n,
                checksum=checksum,
                version=2  # Version 2 = large secret
            )
            shares.append(share)
        
        return shares
    
    def reconstruct(self, shares: List[Share]) -> bytes:
        """
        Reconstruit le secret a partir de K parts.
        
        Args:
            shares: Liste d'au moins K parts
        
        Returns:
            Le secret original
        """
        if len(shares) < self.k:
            raise SecretSharingError(
                f"Besoin d'au moins {self.k} parts, recu {len(shares)}"
            )
        
        # Verifier les checksums
        for share in shares:
            if not share.verify_checksum():
                raise SecretSharingError(f"Part {share.index} corrompue")
        
        # Verifier la version
        if shares[0].version == 2:
            return self._reconstruct_large(shares)
        
        # Utiliser exactement K parts
        shares = shares[:self.k]
        
        # Verifier l'unicite des indices
        indices = [s.index for s in shares]
        if len(set(indices)) != len(indices):
            raise SecretSharingError("Parts dupliquees")
        
        # Convertir en points (x, y)
        points = [
            (s.index, int.from_bytes(s.data, 'big'))
            for s in shares
        ]
        
        # Interpolation de Lagrange en x=0 pour retrouver le secret
        secret_int = self._lagrange_interpolation(points, 0)
        
        # Convertir en bytes (retirer le padding de zeros)
        secret_bytes = secret_int.to_bytes(32, 'big').lstrip(b'\x00')
        if not secret_bytes:
            secret_bytes = b'\x00'
        
        return secret_bytes
    
    def _reconstruct_large(self, shares: List[Share]) -> bytes:
        """Reconstruit un secret de grande taille"""
        # Extraire key_share, nonce, ciphertext de la premiere part
        # (tous ont le meme ciphertext)
        first = shares[0]
        key_share_data = first.data[:32]
        nonce = first.data[32:44]
        ciphertext = first.data[44:]
        
        # Reconstruire les key shares
        key_shares = []
        for share in shares[:self.k]:
            ks = Share(
                index=share.index,
                data=share.data[:32],
                threshold=share.threshold,
                total=share.total,
                checksum="",  # Skip verification
                version=1
            )
            # Recalculer le checksum
            ks.checksum = hashlib.sha256(
                ks.data + ks.index.to_bytes(4, 'big') + ks.threshold.to_bytes(4, 'big')
            ).hexdigest()[:8]
            key_shares.append(ks)
        
        # Reconstruire la cle
        temp_sss = ShamirSecretSharing(self.k, self.n)
        key = temp_sss.reconstruct(key_shares)
        
        # Padding si necessaire
        if len(key) < 32:
            key = key.rjust(32, b'\x00')
        
        # Dechiffrer
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(key)
        
        try:
            return aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as e:
            raise SecretSharingError(f"Dechiffrement echoue: {e}")
    
    def _evaluate_polynomial(self, coefficients: List[int], x: int) -> int:
        """
        Evalue le polynome P(x) = sum(coefficients[i] * x^i) mod PRIME
        """
        result = 0
        x_power = 1
        
        for coeff in coefficients:
            result = (result + coeff * x_power) % self.PRIME
            x_power = (x_power * x) % self.PRIME
        
        return result
    
    def _lagrange_interpolation(self, points: List[Tuple[int, int]], x: int) -> int:
        """
        Interpolation de Lagrange pour trouver P(x).
        
        P(x) = sum(y_i * L_i(x)) ou L_i(x) = prod((x - x_j)/(x_i - x_j), j != i)
        """
        result = 0
        
        for i, (xi, yi) in enumerate(points):
            # Calculer le coefficient de Lagrange L_i(x)
            numerator = 1
            denominator = 1
            
            for j, (xj, _) in enumerate(points):
                if i != j:
                    numerator = (numerator * (x - xj)) % self.PRIME
                    denominator = (denominator * (xi - xj)) % self.PRIME
            
            # Division modulaire: a/b mod p = a * b^(-1) mod p
            inv_denominator = pow(denominator, -1, self.PRIME)
            lagrange_coeff = (numerator * inv_denominator) % self.PRIME
            
            result = (result + yi * lagrange_coeff) % self.PRIME
        
        return result


class VaultKeySharing:
    """
    Partage de cle vault avec Shamir's Secret Sharing.
    
    Cas d'usage:
    - Multi-signature: 3/5 administrateurs requis
    - Recuperation: 2/3 cles de backup
    - Heritage: Distribution aux heritiers
    
    Usage:
        vks = VaultKeySharing()
        
        # Creer une cle partagee 3/5
        share_config = vks.create_shared_vault(vault_key, threshold=3, total=5)
        
        # Distribuer les parts
        for share in share_config['shares']:
            distribute_to_guardian(share)
        
        # Recuperation avec 3 parts
        recovered = vks.recover_vault_key([share1, share3, share5])
    """
    
    def __init__(self):
        pass
    
    def create_shared_vault(
        self,
        vault_key: bytes,
        threshold: int = 3,
        total: int = 5,
        guardian_names: Optional[List[str]] = None
    ) -> Dict:
        """
        Cree une configuration de vault partagee.
        
        Args:
            vault_key: Cle du vault a partager
            threshold: Nombre minimum de parts pour reconstruire
            total: Nombre total de parts
            guardian_names: Noms optionnels des gardiens
        
        Returns:
            Configuration complete avec les parts
        """
        sss = ShamirSecretSharing(threshold, total)
        shares = sss.split(vault_key)
        
        # Assigner les noms si fournis
        guardian_names = guardian_names or [f"Guardian_{i+1}" for i in range(total)]
        if len(guardian_names) < total:
            guardian_names.extend([f"Guardian_{i+1}" for i in range(len(guardian_names), total)])
        
        # Creer la configuration
        config = {
            'scheme': 'shamir',
            'version': 1,
            'threshold': threshold,
            'total': total,
            'vault_key_hash': hashlib.sha256(vault_key).hexdigest(),
            'created_at': __import__('time').time(),
            'shares': [
                {
                    'guardian': guardian_names[i],
                    'share': share.to_dict()
                }
                for i, share in enumerate(shares)
            ]
        }
        
        return config
    
    def recover_vault_key(self, shares: List[Share]) -> bytes:
        """
        Recupere la cle vault depuis les parts.
        
        Args:
            shares: Liste de parts (au moins threshold)
        
        Returns:
            Cle vault reconstruite
        """
        if not shares:
            raise SecretSharingError("Aucune part fournie")
        
        # Utiliser les parametres de la premiere part
        threshold = shares[0].threshold
        total = shares[0].total
        
        sss = ShamirSecretSharing(threshold, total)
        return sss.reconstruct(shares)
    
    def verify_share(self, share: Share, expected_hash: str) -> bool:
        """
        Verifie qu'une part est valide (checksum ok).
        Ne peut pas verifier si elle correspond au bon secret
        sans les autres parts.
        """
        return share.verify_checksum()
    
    def export_share(self, share: Share, password: Optional[str] = None) -> str:
        """
        Exporte une part de maniere securisee.
        
        Args:
            share: Part a exporter
            password: Mot de passe optionnel pour chiffrer
        
        Returns:
            JSON encodé (potentiellement chiffre)
        """
        share_json = share.to_json()
        
        if password:
            # Chiffrer avec le mot de passe
            from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            
            salt = secrets.token_bytes(16)
            kdf = Scrypt(salt=salt, length=32, n=2**17, r=8, p=1)
            key = kdf.derive(password.encode())
            
            nonce = secrets.token_bytes(12)
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, share_json.encode(), None)
            
            return json.dumps({
                'encrypted': True,
                'salt': base64.b64encode(salt).decode(),
                'nonce': base64.b64encode(nonce).decode(),
                'data': base64.b64encode(ciphertext).decode()
            })
        
        return share_json
    
    def import_share(self, exported: str, password: Optional[str] = None) -> Share:
        """
        Importe une part exportee.
        """
        data = json.loads(exported)
        
        if data.get('encrypted'):
            if not password:
                raise SecretSharingError("Mot de passe requis")
            
            from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            
            salt = base64.b64decode(data['salt'])
            nonce = base64.b64decode(data['nonce'])
            ciphertext = base64.b64decode(data['data'])
            
            kdf = Scrypt(salt=salt, length=32, n=2**17, r=8, p=1)
            key = kdf.derive(password.encode())
            
            aesgcm = AESGCM(key)
            share_json = aesgcm.decrypt(nonce, ciphertext, None).decode()
            
            return Share.from_json(share_json)
        
        return Share.from_dict(data)


def create_recovery_shares(
    vault_key: bytes,
    num_shares: int = 3,
    threshold: int = 2
) -> List[str]:
    """
    Fonction utilitaire pour creer des parts de recuperation.
    
    Args:
        vault_key: Cle vault
        num_shares: Nombre de parts (defaut: 3)
        threshold: Minimum requis (defaut: 2)
    
    Returns:
        Liste de parts JSON
    """
    vks = VaultKeySharing()
    config = vks.create_shared_vault(vault_key, threshold, num_shares)
    return [
        json.dumps(s['share'])
        for s in config['shares']
    ]


def recover_from_shares(share_jsons: List[str]) -> bytes:
    """
    Fonction utilitaire pour recuperer depuis des parts JSON.
    """
    shares = [Share.from_json(s) for s in share_jsons]
    vks = VaultKeySharing()
    return vks.recover_vault_key(shares)
