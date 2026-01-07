"""
Zero-Knowledge Proofs pour le SDK Eidolon

Protocole de Schnorr pour prouver la possession d'une cle
sans la reveler.
"""

import secrets
import hashlib
import time
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

from .exceptions import AuthenticationError, ValidationError


@dataclass
class ZKPProof:
    """Preuve Zero-Knowledge"""
    commitment: int  # R = g^k
    challenge: int   # c = H(R, Y, m)
    response: int    # s = k + c*x
    public_key: int  # Y = g^x
    message: bytes
    timestamp: float
    
    def to_dict(self) -> Dict:
        return {
            "commitment": hex(self.commitment),
            "challenge": hex(self.challenge),
            "response": hex(self.response),
            "public_key": hex(self.public_key),
            "message": self.message.hex(),
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "ZKPProof":
        return cls(
            commitment=int(d["commitment"], 16),
            challenge=int(d["challenge"], 16),
            response=int(d["response"], 16),
            public_key=int(d["public_key"], 16),
            message=bytes.fromhex(d["message"]),
            timestamp=d["timestamp"]
        )


class ZKPParams:
    """Parametres du groupe pour Schnorr (RFC 5114)"""
    
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


class ZKPProver:
    """
    Prover pour Zero-Knowledge Proofs (cote client).
    
    Usage:
        prover = ZKPProver(vault_key)
        
        # Obtenir la cle publique
        public_key = prover.get_public_key()
        
        # Creer une preuve
        proof = prover.create_proof(challenge)
    """
    
    def __init__(self, vault_key: bytes):
        """
        Args:
            vault_key: Cle du vault (32 bytes)
        """
        if len(vault_key) != 32:
            raise ValidationError("vault_key must be 32 bytes")
        
        # Deriver la cle privee
        h = hashlib.sha256(b"PSNX_ZKP_PRIVATE_" + vault_key).digest()
        self._x = int.from_bytes(h, 'big') % ZKPParams.Q
        if self._x == 0:
            self._x = 1
        
        # Calculer la cle publique
        self._Y = pow(ZKPParams.G, self._x, ZKPParams.P)
        
        # Commitment temporaire
        self._k: Optional[int] = None
    
    def get_public_key(self) -> int:
        """Retourne la cle publique"""
        return self._Y
    
    def get_public_key_hex(self) -> str:
        """Retourne la cle publique en hex"""
        return hex(self._Y)
    
    def get_fingerprint(self) -> str:
        """Retourne l'empreinte"""
        return hashlib.sha256(
            self._Y.to_bytes((self._Y.bit_length() + 7) // 8, 'big')
        ).hexdigest()[:16]
    
    def create_proof(self, challenge: str) -> Dict:
        """
        Cree une preuve ZKP pour un challenge.
        
        Args:
            challenge: Challenge du serveur
        
        Returns:
            Preuve en format dict (pour API)
        """
        message = challenge.encode()
        
        # Commitment: R = g^k
        self._k = secrets.randbelow(ZKPParams.Q - 1) + 1
        R = pow(ZKPParams.G, self._k, ZKPParams.P)
        
        # Challenge: c = H(R || Y || m)
        c = self._compute_challenge(R, self._Y, message)
        
        # Response: s = k + c*x mod Q
        s = (self._k + c * self._x) % ZKPParams.Q
        
        # Effacer k
        self._k = None
        
        proof = ZKPProof(
            commitment=R,
            challenge=c,
            response=s,
            public_key=self._Y,
            message=message,
            timestamp=time.time()
        )
        
        return {
            "proof": proof.to_dict(),
            "challenge": challenge,
            "key_fingerprint": self.get_fingerprint(),
            "timestamp": proof.timestamp
        }
    
    def _compute_challenge(self, R: int, Y: int, message: bytes) -> int:
        """Calcule le challenge (Fiat-Shamir)"""
        r_bytes = R.to_bytes((R.bit_length() + 7) // 8, 'big')
        y_bytes = Y.to_bytes((Y.bit_length() + 7) // 8, 'big')
        
        data = r_bytes + y_bytes + message
        h = hashlib.sha256(data).digest()
        
        return int.from_bytes(h, 'big') % ZKPParams.Q


class ZKPVerifier:
    """
    Verifier pour Zero-Knowledge Proofs (cote serveur).
    
    Usage:
        # Verification d'une preuve
        valid = ZKPVerifier.verify(proof_dict, expected_challenge)
    """
    
    @staticmethod
    def verify(
        auth_data: Dict,
        expected_challenge: str,
        max_age_seconds: float = 300
    ) -> Tuple[bool, str]:
        """
        Verifie une preuve ZKP.
        
        Args:
            auth_data: Donnees d'authentification
            expected_challenge: Challenge attendu
            max_age_seconds: Age maximum de la preuve
        
        Returns:
            (valid, reason)
        """
        try:
            # Extraire la preuve
            proof = ZKPProof.from_dict(auth_data["proof"])
            
            # Verifier le challenge
            if auth_data.get("challenge") != expected_challenge:
                return False, "Challenge mismatch"
            
            # Verifier l'age
            age = time.time() - proof.timestamp
            if age > max_age_seconds:
                return False, f"Proof expired (age: {age:.1f}s)"
            if age < -60:
                return False, "Proof from future"
            
            # Recalculer le challenge attendu
            r_bytes = proof.commitment.to_bytes(
                (proof.commitment.bit_length() + 7) // 8, 'big'
            )
            y_bytes = proof.public_key.to_bytes(
                (proof.public_key.bit_length() + 7) // 8, 'big'
            )
            data = r_bytes + y_bytes + proof.message
            expected_c = int.from_bytes(
                hashlib.sha256(data).digest(), 'big'
            ) % ZKPParams.Q
            
            if expected_c != proof.challenge:
                return False, "Invalid challenge hash"
            
            # Verifier l'equation: g^s == R * Y^c mod p
            lhs = pow(ZKPParams.G, proof.response, ZKPParams.P)
            rhs = (
                proof.commitment *
                pow(proof.public_key, proof.challenge, ZKPParams.P)
            ) % ZKPParams.P
            
            if lhs != rhs:
                return False, "Cryptographic verification failed"
            
            return True, "OK"
            
        except Exception as e:
            return False, f"Verification error: {e}"
    
    @staticmethod
    def verify_public_key(public_key: int) -> bool:
        """Verifie qu'une cle publique est valide"""
        # Doit etre dans [2, P-2]
        if public_key < 2 or public_key >= ZKPParams.P - 1:
            return False
        
        # Doit etre dans le sous-groupe (Y^Q == 1 mod P)
        if pow(public_key, ZKPParams.Q, ZKPParams.P) != 1:
            return False
        
        return True
