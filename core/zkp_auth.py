"""
Zero-Knowledge Proof Authentication
Poly-Spinor Nexus 7D - Security Module

Protocoles ZKP pour prouver la connaissance d'un secret
sans le reveler:
- Schnorr Protocol (identification)
- Fiat-Shamir Transform (non-interactif)
- Challenge-Response pour vault

Applications:
- Authentification sans exposer la cle vault
- Verification de possession de parts Shamir
- Delegation de verification
"""

import hashlib
import secrets
import struct
import time
from typing import Tuple, Dict, Optional, List
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import json


class ZKPError(Exception):
    """Erreur ZKP"""
    pass


class VerificationFailed(ZKPError):
    """Verification de preuve echouee"""
    pass


@dataclass
class SchnorrProof:
    """Preuve de Schnorr"""
    commitment: int      # R = g^k
    challenge: int       # c = H(R, Y, m)
    response: int        # s = k + c*x
    public_key: int      # Y = g^x
    message: bytes       # Message optionnel
    timestamp: float
    
    def to_dict(self) -> dict:
        return {
            'commitment': hex(self.commitment),
            'challenge': hex(self.challenge),
            'response': hex(self.response),
            'public_key': hex(self.public_key),
            'message': self.message.hex(),
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> 'SchnorrProof':
        return cls(
            commitment=int(d['commitment'], 16),
            challenge=int(d['challenge'], 16),
            response=int(d['response'], 16),
            public_key=int(d['public_key'], 16),
            message=bytes.fromhex(d['message']),
            timestamp=d['timestamp']
        )
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, s: str) -> 'SchnorrProof':
        return cls.from_dict(json.loads(s))


class SchnorrZKP:
    """
    Protocole de Schnorr pour Zero-Knowledge Proof.
    
    Permet de prouver la connaissance d'un secret x
    tel que Y = g^x mod p, sans reveler x.
    
    Securite basee sur le probleme du logarithme discret.
    
    Usage (Prover):
        zkp = SchnorrZKP.from_secret(secret_bytes)
        proof = zkp.create_proof(message=b"challenge")
    
    Usage (Verifier):
        valid = SchnorrZKP.verify_proof(proof)
    """
    
    # Parametres RFC 5114 - 2048-bit MODP Group
    # Safe prime p = 2q + 1
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
    
    # Ordre q = (p-1)/2
    Q = (P - 1) // 2
    
    # Generateur (2 est un generateur pour ce groupe)
    G = 2
    
    def __init__(self, private_key: int, public_key: Optional[int] = None):
        """
        Args:
            private_key: Cle privee x (secret)
            public_key: Cle publique Y = g^x (calculee si non fournie)
        """
        self.x = private_key % self.Q
        self.Y = public_key if public_key else pow(self.G, self.x, self.P)
        
        # Commitment ephemere
        self._k: Optional[int] = None
        self._R: Optional[int] = None
    
    @classmethod
    def from_secret(cls, secret: bytes) -> 'SchnorrZKP':
        """
        Cree un prover depuis un secret (bytes).
        
        Args:
            secret: Secret de 32 bytes (cle vault)
        
        Returns:
            Instance SchnorrZKP
        """
        # Deriver une cle privee depuis le secret
        h = hashlib.sha256(b'PSNX_ZKP_KEY_' + secret).digest()
        private_key = int.from_bytes(h, 'big') % cls.Q
        
        if private_key == 0:
            private_key = 1
        
        return cls(private_key)
    
    def get_public_key(self) -> int:
        """Retourne la cle publique (peut etre partagee)"""
        return self.Y
    
    def create_commitment(self) -> int:
        """
        Etape 1: Prover cree un engagement aleatoire.
        
        Genere k aleatoire et calcule R = g^k mod p
        
        Returns:
            R (commitment)
        """
        # k aleatoire dans [1, Q-1]
        self._k = secrets.randbelow(self.Q - 1) + 1
        self._R = pow(self.G, self._k, self.P)
        return self._R
    
    def create_response(self, challenge: int) -> int:
        """
        Etape 3: Prover repond au challenge.
        
        Calcule s = k + c*x mod Q
        
        Args:
            challenge: Challenge c du verifier
        
        Returns:
            s (response)
        """
        if self._k is None:
            raise ZKPError("Commitment non genere")
        
        s = (self._k + challenge * self.x) % self.Q
        
        # Effacer k pour securite
        self._k = None
        
        return s
    
    def create_proof(self, message: bytes = b'') -> SchnorrProof:
        """
        Cree une preuve complete (non-interactive via Fiat-Shamir).
        
        Utilise la transformation de Fiat-Shamir pour rendre
        le protocole non-interactif: c = H(R || Y || m)
        
        Args:
            message: Message optionnel a lier a la preuve
        
        Returns:
            Preuve complete
        """
        # Commitment
        R = self.create_commitment()
        
        # Challenge (Fiat-Shamir)
        c = self._fiat_shamir_challenge(R, self.Y, message)
        
        # Response
        s = self.create_response(c)
        
        return SchnorrProof(
            commitment=R,
            challenge=c,
            response=s,
            public_key=self.Y,
            message=message,
            timestamp=time.time()
        )
    
    def _fiat_shamir_challenge(self, R: int, Y: int, message: bytes) -> int:
        """Calcule le challenge via Fiat-Shamir transform"""
        # Utiliser une taille suffisante pour les grands nombres
        r_bytes = R.to_bytes((R.bit_length() + 7) // 8, 'big')
        y_bytes = Y.to_bytes((Y.bit_length() + 7) // 8, 'big')
        data = (
            r_bytes +
            y_bytes +
            message
        )
        h = hashlib.sha256(data).digest()
        return int.from_bytes(h, 'big') % self.Q
    
    @classmethod
    def verify_proof(cls, proof: SchnorrProof) -> bool:
        """
        Verifie une preuve de Schnorr.
        
        Verifie que: g^s == R * Y^c mod p
        
        Args:
            proof: Preuve a verifier
        
        Returns:
            True si la preuve est valide
        """
        # Recalculer le challenge
        expected_c = cls._compute_challenge(
            proof.commitment,
            proof.public_key,
            proof.message
        )
        
        # Verifier que le challenge correspond
        if expected_c != proof.challenge:
            return False
        
        # Verifier l'equation: g^s == R * Y^c
        lhs = pow(cls.G, proof.response, cls.P)
        rhs = (proof.commitment * pow(proof.public_key, proof.challenge, cls.P)) % cls.P
        
        return lhs == rhs
    
    @classmethod
    def _compute_challenge(cls, R: int, Y: int, message: bytes) -> int:
        """Calcule le challenge attendu"""
        r_bytes = R.to_bytes((R.bit_length() + 7) // 8, 'big')
        y_bytes = Y.to_bytes((Y.bit_length() + 7) // 8, 'big')
        data = (
            r_bytes +
            y_bytes +
            message
        )
        h = hashlib.sha256(data).digest()
        return int.from_bytes(h, 'big') % cls.Q


class VaultZKPAuth:
    """
    Authentification du vault via Zero-Knowledge Proof.
    
    Permet de prouver la possession de la cle vault sans
    jamais exposer la cle elle-meme.
    
    Usage:
        # Cote vault (possesseur de la cle)
        auth = VaultZKPAuth(vault_key)
        proof = auth.create_auth_proof(challenge="login_2024")
        
        # Cote verifieur (ne connait pas la cle)
        public_key = auth.get_public_key()
        # ... stocker public_key ...
        valid = VaultZKPAuth.verify_auth(public_key, proof, "login_2024")
    """
    
    def __init__(self, vault_key: bytes):
        """
        Args:
            vault_key: Cle du vault (32 bytes)
        """
        self.zkp = SchnorrZKP.from_secret(vault_key)
        self._vault_key_hash = hashlib.sha256(vault_key).hexdigest()
    
    def get_public_key(self) -> int:
        """
        Retourne la cle publique pour verification.
        
        Cette cle peut etre stockee publiquement et utilisee
        pour verifier les preuves sans connaitre la cle vault.
        """
        return self.zkp.get_public_key()
    
    def get_key_fingerprint(self) -> str:
        """Retourne une empreinte de la cle (pour identification)"""
        return self._vault_key_hash[:16]
    
    def create_auth_proof(
        self,
        challenge: str = "",
        include_timestamp: bool = True
    ) -> Dict:
        """
        Cree une preuve d'authentification.
        
        Args:
            challenge: Challenge unique (ex: "login_" + timestamp)
            include_timestamp: Inclure timestamp pour anti-replay
        
        Returns:
            Dictionnaire avec la preuve
        """
        # Construire le message
        message_parts = [challenge.encode()]
        
        if include_timestamp:
            ts = struct.pack('>d', time.time())
            message_parts.append(ts)
        
        message = b''.join(message_parts)
        
        # Creer la preuve
        proof = self.zkp.create_proof(message)
        
        return {
            'proof': proof.to_dict(),
            'challenge': challenge,
            'key_fingerprint': self.get_key_fingerprint(),
            'timestamp': proof.timestamp
        }
    
    @staticmethod
    def verify_auth(
        public_key: int,
        auth_data: Dict,
        expected_challenge: str = "",
        max_age_seconds: float = 300
    ) -> Tuple[bool, str]:
        """
        Verifie une preuve d'authentification.
        
        Args:
            public_key: Cle publique du vault
            auth_data: Donnees d'authentification
            expected_challenge: Challenge attendu
            max_age_seconds: Age maximum de la preuve
        
        Returns:
            (valid, reason)
        """
        try:
            # Reconstruire la preuve
            proof = SchnorrProof.from_dict(auth_data['proof'])
            
            # Verifier le challenge
            if auth_data.get('challenge') != expected_challenge:
                return False, "Challenge mismatch"
            
            # Verifier l'age (anti-replay)
            age = time.time() - proof.timestamp
            if age > max_age_seconds:
                return False, f"Proof expired (age: {age:.1f}s)"
            
            if age < -60:  # Tolerance de 1 minute pour clock skew
                return False, "Proof from future"
            
            # Verifier que la cle publique correspond
            if proof.public_key != public_key:
                return False, "Public key mismatch"
            
            # Verifier la preuve cryptographique
            if not SchnorrZKP.verify_proof(proof):
                return False, "Cryptographic verification failed"
            
            return True, "OK"
            
        except Exception as e:
            return False, f"Verification error: {e}"


class MultiPartyZKP:
    """
    ZKP pour systeme multi-parties (Shamir).
    
    Permet a plusieurs detenteurs de parts de prouver
    collectivement leur possession sans reveler les parts.
    """
    
    def __init__(self, threshold: int, total: int):
        self.threshold = threshold
        self.total = total
    
    def create_partial_proof(
        self,
        share: bytes,
        share_index: int,
        challenge: bytes
    ) -> Dict:
        """
        Cree une preuve partielle pour une part.
        
        Args:
            share: Part Shamir
            share_index: Index de la part
            challenge: Challenge commun
        
        Returns:
            Preuve partielle
        """
        zkp = SchnorrZKP.from_secret(share)
        proof = zkp.create_proof(challenge)
        
        return {
            'index': share_index,
            'proof': proof.to_dict(),
            'public_key': zkp.get_public_key()
        }
    
    def verify_partial_proofs(
        self,
        partial_proofs: List[Dict],
        challenge: bytes
    ) -> Tuple[bool, List[int]]:
        """
        Verifie un ensemble de preuves partielles.
        
        Args:
            partial_proofs: Liste de preuves partielles
            challenge: Challenge commun
        
        Returns:
            (all_valid, valid_indices)
        """
        if len(partial_proofs) < self.threshold:
            return False, []
        
        valid_indices = []
        
        for pp in partial_proofs:
            proof = SchnorrProof.from_dict(pp['proof'])
            
            # Verifier que le challenge correspond
            if proof.message != challenge:
                continue
            
            # Verifier la preuve
            if SchnorrZKP.verify_proof(proof):
                valid_indices.append(pp['index'])
        
        all_valid = len(valid_indices) >= self.threshold
        return all_valid, valid_indices


class ChallengeResponseAuth:
    """
    Authentification challenge-response simple.
    
    Pour des cas ou ZKP complet n'est pas necessaire
    mais on veut eviter le replay.
    """
    
    def __init__(self, secret: bytes):
        self.secret = secret
    
    def generate_challenge(self) -> bytes:
        """Genere un challenge aleatoire"""
        return secrets.token_bytes(32)
    
    def respond_to_challenge(self, challenge: bytes) -> bytes:
        """
        Repond a un challenge.
        
        Response = HMAC(secret, challenge || timestamp)
        """
        ts = struct.pack('>d', time.time())
        data = challenge + ts
        
        response = hashlib.new(
            'sha256',
            self.secret + data
        ).digest()
        
        return response + ts
    
    def verify_response(
        self,
        challenge: bytes,
        response: bytes,
        max_age: float = 60
    ) -> bool:
        """Verifie une reponse"""
        if len(response) < 40:  # 32 (hash) + 8 (timestamp)
            return False
        
        response_hash = response[:32]
        ts_bytes = response[32:40]
        ts = struct.unpack('>d', ts_bytes)[0]
        
        # Verifier l'age
        if time.time() - ts > max_age:
            return False
        
        # Recalculer la reponse attendue
        data = challenge + ts_bytes
        expected = hashlib.new(
            'sha256',
            self.secret + data
        ).digest()
        
        # Comparaison en temps constant
        import hmac
        return hmac.compare_digest(response_hash, expected)


# Fonctions utilitaires

def create_vault_zkp_credentials(vault_key: bytes) -> Dict:
    """
    Cree les credentials ZKP pour un vault.
    
    Returns:
        {
            'public_key': ...,
            'fingerprint': ...,
            'created_at': ...
        }
    """
    auth = VaultZKPAuth(vault_key)
    
    return {
        'public_key': hex(auth.get_public_key()),
        'fingerprint': auth.get_key_fingerprint(),
        'created_at': time.time()
    }


def verify_vault_ownership(
    public_key_hex: str,
    proof_json: str,
    challenge: str
) -> bool:
    """
    Verifie la possession d'un vault.
    
    Args:
        public_key_hex: Cle publique en hex
        proof_json: Preuve JSON
        challenge: Challenge utilise
    
    Returns:
        True si le prover possede la cle vault
    """
    public_key = int(public_key_hex, 16)
    auth_data = json.loads(proof_json)
    
    valid, _ = VaultZKPAuth.verify_auth(
        public_key,
        auth_data,
        challenge
    )
    
    return valid
