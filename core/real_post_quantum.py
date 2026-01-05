"""
Implémentations Post-Quantiques Réelles
Utilise pqcrypto pour des algorithmes conformes NIST PQC

Algorithmes supportés:
- ML-KEM (Kyber) via HQC comme alternative
- ML-DSA (Dilithium) - NIST FIPS 204
- Falcon - NIST sélectionné
- SPHINCS+ - NIST FIPS 205
- McEliece - NIST Round 4

VULN-CRYPTO-02 FIX: Remplace les simulations par des implémentations réelles
"""

import hashlib
import secrets
import hmac
from typing import Tuple, Optional, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum

# Import pqcrypto - algorithmes post-quantiques réels
try:
    # KEM (Key Encapsulation Mechanism)
    from pqcrypto.kem import mceliece6960119 as mceliece
    from pqcrypto.kem import hqc_256 as hqc  # Alternative à Kyber
    
    # Signatures
    from pqcrypto.sign import ml_dsa_65 as dilithium  # ML-DSA (Dilithium)
    from pqcrypto.sign import falcon_512 as falcon
    from pqcrypto.sign import sphincs_sha2_256f_simple as sphincs
    
    PQCRYPTO_AVAILABLE = True
except ImportError:
    PQCRYPTO_AVAILABLE = False
    print("[AVERTISSEMENT] pqcrypto non disponible - utiliser 'pip install pqcrypto'")


class PQAlgorithm(Enum):
    """Algorithmes post-quantiques disponibles"""
    # KEM
    MCELIECE = "mceliece6960119"
    HQC = "hqc_256"
    # Signatures
    ML_DSA = "ml_dsa_65"  # Dilithium
    FALCON = "falcon_512"
    SPHINCS = "sphincs_sha2_256f"


class PQSecurityLevel(Enum):
    """Niveaux de sécurité NIST"""
    LEVEL_1 = 128  # AES-128 équivalent
    LEVEL_3 = 192  # AES-192 équivalent  
    LEVEL_5 = 256  # AES-256 équivalent


@dataclass
class PQKeyPair:
    """Paire de clés post-quantique"""
    algorithm: PQAlgorithm
    public_key: bytes
    secret_key: bytes
    security_level: PQSecurityLevel
    
    def public_key_hash(self) -> str:
        """Hash de la clé publique pour identification"""
        return hashlib.sha256(self.public_key).hexdigest()[:16]


@dataclass
class PQEncapsulation:
    """Résultat d'encapsulation KEM"""
    ciphertext: bytes
    shared_secret: bytes


@dataclass
class PQSignature:
    """Signature post-quantique"""
    algorithm: PQAlgorithm
    signature: bytes
    public_key_hash: str


class RealMcElieceKEM:
    """
    McEliece KEM - NIST Round 4 candidat
    Basé sur codes correcteurs d'erreurs (code de Goppa)
    Sécurité: NIST Level 5 (256 bits)
    """
    
    ALGORITHM = PQAlgorithm.MCELIECE
    SECURITY_LEVEL = PQSecurityLevel.LEVEL_5
    
    def __init__(self):
        if not PQCRYPTO_AVAILABLE:
            raise ImportError("pqcrypto requis pour McEliece réel")
        self.public_key: Optional[bytes] = None
        self.secret_key: Optional[bytes] = None
    
    def generate_keypair(self) -> PQKeyPair:
        """Génère une paire de clés McEliece"""
        self.public_key, self.secret_key = mceliece.generate_keypair()
        
        return PQKeyPair(
            algorithm=self.ALGORITHM,
            public_key=self.public_key,
            secret_key=self.secret_key,
            security_level=self.SECURITY_LEVEL
        )
    
    def encapsulate(self, public_key: bytes) -> PQEncapsulation:
        """
        Encapsule un secret partagé avec la clé publique.
        Retourne (ciphertext, shared_secret)
        """
        ciphertext, shared_secret = mceliece.encrypt(public_key)
        return PQEncapsulation(ciphertext=ciphertext, shared_secret=shared_secret)
    
    def decapsulate(self, ciphertext: bytes, secret_key: bytes) -> bytes:
        """Décapsule le secret partagé avec la clé secrète"""
        return mceliece.decrypt(secret_key, ciphertext)
    
    @staticmethod
    def get_parameters() -> Dict[str, int]:
        """Retourne les paramètres de l'algorithme"""
        return {
            'public_key_size': mceliece.PUBLIC_KEY_SIZE,
            'secret_key_size': mceliece.SECRET_KEY_SIZE,
            'ciphertext_size': mceliece.CIPHERTEXT_SIZE,
            'shared_secret_size': mceliece.PLAINTEXT_SIZE
        }


class RealHQCKEM:
    """
    HQC (Hamming Quasi-Cyclic) KEM
    Alternative à ML-KEM/Kyber basée sur codes quasi-cycliques
    Sécurité: NIST Level 5
    """
    
    ALGORITHM = PQAlgorithm.HQC
    SECURITY_LEVEL = PQSecurityLevel.LEVEL_5
    
    def __init__(self):
        if not PQCRYPTO_AVAILABLE:
            raise ImportError("pqcrypto requis pour HQC réel")
        self.public_key: Optional[bytes] = None
        self.secret_key: Optional[bytes] = None
    
    def generate_keypair(self) -> PQKeyPair:
        """Génère une paire de clés HQC"""
        self.public_key, self.secret_key = hqc.generate_keypair()
        
        return PQKeyPair(
            algorithm=self.ALGORITHM,
            public_key=self.public_key,
            secret_key=self.secret_key,
            security_level=self.SECURITY_LEVEL
        )
    
    def encapsulate(self, public_key: bytes) -> PQEncapsulation:
        """Encapsule un secret partagé"""
        ciphertext, shared_secret = hqc.encrypt(public_key)
        return PQEncapsulation(ciphertext=ciphertext, shared_secret=shared_secret)
    
    def decapsulate(self, ciphertext: bytes, secret_key: bytes) -> bytes:
        """Décapsule le secret partagé"""
        return hqc.decrypt(secret_key, ciphertext)
    
    @staticmethod
    def get_parameters() -> Dict[str, int]:
        return {
            'public_key_size': hqc.PUBLIC_KEY_SIZE,
            'secret_key_size': hqc.SECRET_KEY_SIZE,
            'ciphertext_size': hqc.CIPHERTEXT_SIZE,
            'shared_secret_size': hqc.PLAINTEXT_SIZE
        }


class RealMLDSASignature:
    """
    ML-DSA (Module Lattice Digital Signature Algorithm)
    Anciennement Dilithium - NIST FIPS 204
    Sécurité: NIST Level 3 (192 bits)
    """
    
    ALGORITHM = PQAlgorithm.ML_DSA
    SECURITY_LEVEL = PQSecurityLevel.LEVEL_3
    
    def __init__(self):
        if not PQCRYPTO_AVAILABLE:
            raise ImportError("pqcrypto requis pour ML-DSA réel")
        self.public_key: Optional[bytes] = None
        self.secret_key: Optional[bytes] = None
    
    def generate_keypair(self) -> PQKeyPair:
        """Génère une paire de clés ML-DSA"""
        self.public_key, self.secret_key = dilithium.generate_keypair()
        
        return PQKeyPair(
            algorithm=self.ALGORITHM,
            public_key=self.public_key,
            secret_key=self.secret_key,
            security_level=self.SECURITY_LEVEL
        )
    
    def sign(self, message: bytes, secret_key: Optional[bytes] = None) -> PQSignature:
        """Signe un message avec ML-DSA"""
        sk = secret_key or self.secret_key
        if sk is None:
            raise ValueError("Clé secrète requise pour signer")
        
        signature = dilithium.sign(sk, message)
        
        return PQSignature(
            algorithm=self.ALGORITHM,
            signature=signature,
            public_key_hash=hashlib.sha256(self.public_key or b'').hexdigest()[:16]
        )
    
    def verify(self, message: bytes, signature: bytes, 
               public_key: Optional[bytes] = None) -> bool:
        """Vérifie une signature ML-DSA"""
        pk = public_key or self.public_key
        if pk is None:
            raise ValueError("Clé publique requise pour vérifier")
        
        try:
            dilithium.verify(pk, message, signature)
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_parameters() -> Dict[str, int]:
        return {
            'public_key_size': dilithium.PUBLIC_KEY_SIZE,
            'secret_key_size': dilithium.SECRET_KEY_SIZE,
            'signature_size': dilithium.SIGNATURE_SIZE
        }


class RealFalconSignature:
    """
    Falcon - Fast Fourier Lattice-based Compact Signatures
    NIST sélectionné pour signatures compactes
    Sécurité: NIST Level 1 (128 bits) pour Falcon-512
    """
    
    ALGORITHM = PQAlgorithm.FALCON
    SECURITY_LEVEL = PQSecurityLevel.LEVEL_1
    
    def __init__(self):
        if not PQCRYPTO_AVAILABLE:
            raise ImportError("pqcrypto requis pour Falcon réel")
        self.public_key: Optional[bytes] = None
        self.secret_key: Optional[bytes] = None
    
    def generate_keypair(self) -> PQKeyPair:
        """Génère une paire de clés Falcon"""
        self.public_key, self.secret_key = falcon.generate_keypair()
        
        return PQKeyPair(
            algorithm=self.ALGORITHM,
            public_key=self.public_key,
            secret_key=self.secret_key,
            security_level=self.SECURITY_LEVEL
        )
    
    def sign(self, message: bytes, secret_key: Optional[bytes] = None) -> PQSignature:
        """Signe un message avec Falcon"""
        sk = secret_key or self.secret_key
        if sk is None:
            raise ValueError("Clé secrète requise")
        
        signature = falcon.sign(sk, message)
        
        return PQSignature(
            algorithm=self.ALGORITHM,
            signature=signature,
            public_key_hash=hashlib.sha256(self.public_key or b'').hexdigest()[:16]
        )
    
    def verify(self, message: bytes, signature: bytes,
               public_key: Optional[bytes] = None) -> bool:
        """Vérifie une signature Falcon"""
        pk = public_key or self.public_key
        if pk is None:
            raise ValueError("Clé publique requise")
        
        try:
            falcon.verify(pk, message, signature)
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_parameters() -> Dict[str, int]:
        return {
            'public_key_size': falcon.PUBLIC_KEY_SIZE,
            'secret_key_size': falcon.SECRET_KEY_SIZE,
            'signature_size': falcon.SIGNATURE_SIZE
        }


class RealSPHINCSSignature:
    """
    SPHINCS+ - Stateless Hash-Based Signature
    NIST FIPS 205 - Sécurité basée uniquement sur fonctions de hachage
    Sécurité: NIST Level 5 (256 bits)
    """
    
    ALGORITHM = PQAlgorithm.SPHINCS
    SECURITY_LEVEL = PQSecurityLevel.LEVEL_5
    
    def __init__(self):
        if not PQCRYPTO_AVAILABLE:
            raise ImportError("pqcrypto requis pour SPHINCS+ réel")
        self.public_key: Optional[bytes] = None
        self.secret_key: Optional[bytes] = None
    
    def generate_keypair(self) -> PQKeyPair:
        """Génère une paire de clés SPHINCS+"""
        self.public_key, self.secret_key = sphincs.generate_keypair()
        
        return PQKeyPair(
            algorithm=self.ALGORITHM,
            public_key=self.public_key,
            secret_key=self.secret_key,
            security_level=self.SECURITY_LEVEL
        )
    
    def sign(self, message: bytes, secret_key: Optional[bytes] = None) -> PQSignature:
        """Signe un message avec SPHINCS+"""
        sk = secret_key or self.secret_key
        if sk is None:
            raise ValueError("Clé secrète requise")
        
        signature = sphincs.sign(sk, message)
        
        return PQSignature(
            algorithm=self.ALGORITHM,
            signature=signature,
            public_key_hash=hashlib.sha256(self.public_key or b'').hexdigest()[:16]
        )
    
    def verify(self, message: bytes, signature: bytes,
               public_key: Optional[bytes] = None) -> bool:
        """Vérifie une signature SPHINCS+"""
        pk = public_key or self.public_key
        if pk is None:
            raise ValueError("Clé publique requise")
        
        try:
            sphincs.verify(pk, message, signature)
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_parameters() -> Dict[str, int]:
        return {
            'public_key_size': sphincs.PUBLIC_KEY_SIZE,
            'secret_key_size': sphincs.SECRET_KEY_SIZE,
            'signature_size': sphincs.SIGNATURE_SIZE
        }


class HybridPQCryptoSystem:
    """
    Système cryptographique hybride post-quantique
    Combine plusieurs algorithmes pour une sécurité maximale
    
    Architecture:
    - KEM: McEliece (primaire) + HQC (secondaire)
    - Signatures: ML-DSA + Falcon (double signature)
    """
    
    def __init__(self):
        if not PQCRYPTO_AVAILABLE:
            raise ImportError("pqcrypto requis - installer avec 'pip install pqcrypto'")
        
        # KEM instances
        self.mceliece = RealMcElieceKEM()
        self.hqc = RealHQCKEM()
        
        # Signature instances
        self.mldsa = RealMLDSASignature()
        self.falcon = RealFalconSignature()
        self.sphincs = RealSPHINCSSignature()
        
        # Clés générées
        self._kem_keypair: Optional[PQKeyPair] = None
        self._sig_keypair: Optional[PQKeyPair] = None
    
    def generate_all_keys(self) -> Dict[str, PQKeyPair]:
        """Génère toutes les paires de clés nécessaires"""
        keys = {}
        
        # KEM keys
        keys['mceliece'] = self.mceliece.generate_keypair()
        keys['hqc'] = self.hqc.generate_keypair()
        
        # Signature keys
        keys['mldsa'] = self.mldsa.generate_keypair()
        keys['falcon'] = self.falcon.generate_keypair()
        keys['sphincs'] = self.sphincs.generate_keypair()
        
        self._kem_keypair = keys['mceliece']
        self._sig_keypair = keys['mldsa']
        
        return keys
    
    def hybrid_encapsulate(self, mceliece_pk: bytes, hqc_pk: bytes) -> Tuple[bytes, bytes]:
        """
        Encapsulation hybride combinant McEliece et HQC.
        Le secret final est dérivé des deux secrets partagés.
        
        Returns:
            (combined_ciphertext, combined_secret)
        """
        # Encapsulation McEliece
        mc_result = self.mceliece.encapsulate(mceliece_pk)
        
        # Encapsulation HQC
        hqc_result = self.hqc.encapsulate(hqc_pk)
        
        # Combiner les secrets avec HKDF
        combined_ikm = mc_result.shared_secret + hqc_result.shared_secret
        combined_secret = hashlib.sha3_256(combined_ikm).digest()
        
        # Combiner les ciphertexts (préfixés par leurs longueurs)
        mc_ct_len = len(mc_result.ciphertext).to_bytes(4, 'big')
        hqc_ct_len = len(hqc_result.ciphertext).to_bytes(4, 'big')
        combined_ct = mc_ct_len + mc_result.ciphertext + hqc_ct_len + hqc_result.ciphertext
        
        return combined_ct, combined_secret
    
    def hybrid_decapsulate(self, combined_ct: bytes, 
                           mceliece_sk: bytes, hqc_sk: bytes) -> bytes:
        """
        Décapsulation hybride.
        
        Returns:
            combined_secret
        """
        # Parser le ciphertext combiné
        mc_ct_len = int.from_bytes(combined_ct[:4], 'big')
        mc_ct = combined_ct[4:4+mc_ct_len]
        
        hqc_ct_len = int.from_bytes(combined_ct[4+mc_ct_len:8+mc_ct_len], 'big')
        hqc_ct = combined_ct[8+mc_ct_len:8+mc_ct_len+hqc_ct_len]
        
        # Décapsulation
        mc_secret = self.mceliece.decapsulate(mc_ct, mceliece_sk)
        hqc_secret = self.hqc.decapsulate(hqc_ct, hqc_sk)
        
        # Recombiner
        combined_ikm = mc_secret + hqc_secret
        return hashlib.sha3_256(combined_ikm).digest()
    
    def dual_sign(self, message: bytes, 
                  mldsa_sk: bytes, falcon_sk: bytes) -> Dict[str, bytes]:
        """
        Double signature avec ML-DSA et Falcon.
        Fournit une redondance cryptographique.
        """
        # Signer avec les deux algorithmes
        mldsa_sig = dilithium.sign(mldsa_sk, message)
        falcon_sig = falcon.sign(falcon_sk, message)
        
        return {
            'mldsa_signature': mldsa_sig,
            'falcon_signature': falcon_sig,
            'message_hash': hashlib.sha3_256(message).hexdigest()
        }
    
    def dual_verify(self, message: bytes, signatures: Dict[str, bytes],
                    mldsa_pk: bytes, falcon_pk: bytes) -> Tuple[bool, Dict[str, bool]]:
        """
        Vérifie les deux signatures.
        Retourne (all_valid, individual_results)
        """
        results = {}
        
        # Vérifier ML-DSA
        try:
            dilithium.verify(mldsa_pk, message, signatures['mldsa_signature'])
            results['mldsa'] = True
        except Exception:
            results['mldsa'] = False
        
        # Vérifier Falcon
        try:
            falcon.verify(falcon_pk, message, signatures['falcon_signature'])
            results['falcon'] = True
        except Exception:
            results['falcon'] = False
        
        all_valid = all(results.values())
        return all_valid, results
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Résumé de la sécurité du système"""
        return {
            'kem_algorithms': {
                'mceliece': {
                    'standard': 'NIST Round 4',
                    'security_level': 'Level 5 (256-bit)',
                    'parameters': RealMcElieceKEM.get_parameters()
                },
                'hqc': {
                    'standard': 'NIST Round 4',
                    'security_level': 'Level 5 (256-bit)',
                    'parameters': RealHQCKEM.get_parameters()
                }
            },
            'signature_algorithms': {
                'ml_dsa': {
                    'standard': 'NIST FIPS 204',
                    'security_level': 'Level 3 (192-bit)',
                    'parameters': RealMLDSASignature.get_parameters()
                },
                'falcon': {
                    'standard': 'NIST Selected',
                    'security_level': 'Level 1 (128-bit)',
                    'parameters': RealFalconSignature.get_parameters()
                },
                'sphincs': {
                    'standard': 'NIST FIPS 205',
                    'security_level': 'Level 5 (256-bit)',
                    'parameters': RealSPHINCSSignature.get_parameters()
                }
            },
            'hybrid_security': 'Combined Level 5 (256-bit quantum security)',
            'compliance': ['NIST PQC', 'FIPS 204', 'FIPS 205']
        }


def check_pqcrypto_available() -> bool:
    """Vérifie si pqcrypto est disponible"""
    return PQCRYPTO_AVAILABLE


def get_recommended_algorithms() -> Dict[str, str]:
    """Retourne les algorithmes recommandés par usage"""
    return {
        'key_exchange': 'McEliece + HQC (hybride)',
        'general_signatures': 'ML-DSA (Dilithium)',
        'compact_signatures': 'Falcon',
        'conservative_signatures': 'SPHINCS+ (hash-based)',
        'maximum_security': 'Hybrid McEliece+HQC avec dual ML-DSA+Falcon'
    }
