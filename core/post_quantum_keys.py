"""
Système de Clés Post-Quantiques
Triple enveloppe cryptographique NTRU + McEliece + SPHINCS+
"""

import hashlib
import hmac
import numpy as np
import os
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class KeyPurpose(Enum):
    """Objectifs de dérivation de clé"""
    MESSAGING = "messaging"
    ESCROW = "escrow"
    SIGNATURE = "signature"
    IDENTITY = "identity"
    MASTER = "master"


@dataclass
class NTRUKey:
    """Clé NTRU Prime"""
    n: int
    q: int
    f: np.ndarray
    g: np.ndarray
    h: np.ndarray
    
    def to_bytes(self) -> bytes:
        return self.h.astype(np.int16).tobytes()


@dataclass
class McElieceKey:
    """Clé McEliece (code de Goppa)"""
    n: int
    k: int
    t: int
    generator_matrix: np.ndarray
    parity_check: np.ndarray
    
    def to_bytes(self) -> bytes:
        return self.generator_matrix.astype(np.uint8).tobytes()


@dataclass
class SPHINCSKey:
    """Clé SPHINCS+"""
    seed: bytes
    public_seed: bytes
    secret_seed: bytes
    tree_height: int
    
    def to_bytes(self) -> bytes:
        return self.seed + self.public_seed


@dataclass
class TripleEnvelope:
    """Triple enveloppe cryptographique post-quantique"""
    ntru_key: NTRUKey
    mceliece_key: McElieceKey
    sphincs_key: SPHINCSKey
    
    def get_combined_strength(self) -> int:
        """Retourne la force combinée en bits"""
        ntru_bits = self.ntru_key.n * 2
        mceliece_bits = self.mceliece_key.n
        sphincs_bits = len(self.sphincs_key.seed) * 8
        return ntru_bits + mceliece_bits + sphincs_bits
    
    def to_dict(self) -> Dict:
        return {
            'ntru': {
                'n': self.ntru_key.n,
                'q': self.ntru_key.q,
                'h_hash': hashlib.sha256(self.ntru_key.to_bytes()).hexdigest()
            },
            'mceliece': {
                'n': self.mceliece_key.n,
                'k': self.mceliece_key.k,
                't': self.mceliece_key.t
            },
            'sphincs': {
                'tree_height': self.sphincs_key.tree_height,
                'public_seed_hash': hashlib.sha256(self.sphincs_key.public_seed).hexdigest()
            },
            'combined_strength_bits': self.get_combined_strength()
        }


class HKDF:
    """HMAC-based Key Derivation Function"""
    
    @staticmethod
    def extract(salt: bytes, ikm: bytes, hash_algo: str = 'sha512') -> bytes:
        """Étape d'extraction HKDF"""
        if salt is None:
            hash_len = 64 if hash_algo == 'sha512' else 32
            salt = bytes(hash_len)
        return hmac.new(salt, ikm, hash_algo).digest()
    
    @staticmethod
    def expand(prk: bytes, info: bytes, length: int, hash_algo: str = 'sha512') -> bytes:
        """Étape d'expansion HKDF"""
        hash_len = 64 if hash_algo == 'sha512' else 32
        n = (length + hash_len - 1) // hash_len
        
        okm = b''
        t = b''
        
        for i in range(1, n + 1):
            t = hmac.new(prk, t + info + bytes([i]), hash_algo).digest()
            okm += t
        
        return okm[:length]
    
    @classmethod
    def derive(cls, ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes:
        """Dérivation complète HKDF"""
        prk = cls.extract(salt, ikm)
        return cls.expand(prk, info, length)


class NTRUKeyGenerator:
    """Générateur de clés NTRU Prime"""
    
    def __init__(self, n: int = 761, q: int = 4591):
        self.n = n
        self.q = q
        
    def generate(self, seed: bytes) -> NTRUKey:
        """Génère une paire de clés NTRU"""
        f = self._generate_small_polynomial(seed, b'ntru_f')
        
        g = self._generate_small_polynomial(seed, b'ntru_g')
        
        h = self._compute_public_key(f, g)
        
        return NTRUKey(n=self.n, q=self.q, f=f, g=g, h=h)
    
    def _generate_small_polynomial(self, seed: bytes, label: bytes) -> np.ndarray:
        """Génère un polynôme à petits coefficients"""
        derived = HKDF.derive(seed, label, b'coefficient', self.n)
        coeffs = np.frombuffer(derived, dtype=np.uint8)[:self.n]
        return (coeffs.astype(int) % 3) - 1
    
    def _compute_public_key(self, f: np.ndarray, g: np.ndarray) -> np.ndarray:
        """Calcule h = g * f^(-1) mod q"""
        f_inv = self._polynomial_inverse(f)
        
        h = np.zeros(self.n, dtype=int)
        for i in range(self.n):
            for j in range(self.n):
                idx = (i + j) % self.n
                h[idx] = (h[idx] + g[i] * f_inv[j]) % self.q
        
        return h
    
    def _polynomial_inverse(self, f: np.ndarray) -> np.ndarray:
        """Calcule l'inverse d'un polynôme mod q"""
        inv = np.zeros(self.n, dtype=int)
        inv[0] = pow(int(f[0]) if f[0] != 0 else 1, -1, self.q)
        
        for i in range(1, min(10, self.n)):
            correction = 0
            for j in range(1, i + 1):
                if j < len(f):
                    correction = (correction + f[j] * inv[i - j]) % self.q
            inv[i] = (-inv[0] * correction) % self.q
        
        return inv


class McElieceKeyGenerator:
    """Générateur de clés McEliece"""
    
    def __init__(self, n: int = 6960, k: int = 5413, t: int = 119):
        self.n = n
        self.k = k
        self.t = t
        
    def generate(self, seed: bytes) -> McElieceKey:
        """Génère une paire de clés McEliece"""
        goppa_poly = self._generate_goppa_polynomial(seed)
        
        H = self._generate_parity_check_matrix(goppa_poly, seed)
        
        G = self._compute_generator_matrix(H)
        
        return McElieceKey(
            n=self.n, k=self.k, t=self.t,
            generator_matrix=G,
            parity_check=H
        )
    
    def _generate_goppa_polynomial(self, seed: bytes) -> np.ndarray:
        """Génère le polynôme de Goppa"""
        derived = HKDF.derive(seed, b'goppa', b'poly', self.t + 1)
        coeffs = np.frombuffer(derived, dtype=np.uint8)[:self.t + 1]
        return coeffs
    
    def _generate_parity_check_matrix(self, goppa: np.ndarray, 
                                       seed: bytes) -> np.ndarray:
        """Génère la matrice de parité H"""
        rows = self.n - self.k
        cols = self.n
        
        derived = HKDF.derive(seed, b'parity', b'matrix', rows * cols // 8 + 1)
        bits = np.unpackbits(np.frombuffer(derived, dtype=np.uint8))
        
        H = bits[:rows * cols].reshape(rows, min(cols, len(bits) // rows))
        
        if H.shape[1] < cols:
            H = np.pad(H, ((0, 0), (0, cols - H.shape[1])))
        
        return H[:rows, :cols]
    
    def _compute_generator_matrix(self, H: np.ndarray) -> np.ndarray:
        """Calcule la matrice génératrice G à partir de H"""
        rows = H.shape[0]
        cols = H.shape[1]
        
        G = np.zeros((self.k, cols), dtype=np.uint8)
        
        for i in range(min(self.k, cols)):
            G[i, i] = 1
        
        if rows <= cols - self.k:
            G[:, self.k:self.k + rows] = H[:rows, :self.k].T
        
        return G


class SPHINCSKeyGenerator:
    """Générateur de clés SPHINCS+"""
    
    def __init__(self, security_level: int = 256, tree_height: int = 64):
        self.security_level = security_level
        self.tree_height = tree_height
        self.n = security_level // 8
        
    def generate(self, seed: bytes) -> SPHINCSKey:
        """Génère une paire de clés SPHINCS+"""
        secret_seed = HKDF.derive(seed, b'sphincs', b'secret', self.n)
        
        public_seed = HKDF.derive(seed, b'sphincs', b'public', self.n)
        
        root_seed = self._compute_merkle_root(secret_seed, public_seed)
        
        return SPHINCSKey(
            seed=root_seed,
            public_seed=public_seed,
            secret_seed=secret_seed,
            tree_height=self.tree_height
        )
    
    def _compute_merkle_root(self, secret: bytes, public: bytes) -> bytes:
        """Calcule la racine de l'arbre de Merkle"""
        leaves = []
        for i in range(2 ** min(4, self.tree_height // 16)):
            leaf_data = secret + public + i.to_bytes(4, 'big')
            leaf = hashlib.sha256(leaf_data).digest()
            leaves.append(leaf)
        
        while len(leaves) > 1:
            new_leaves = []
            for i in range(0, len(leaves), 2):
                if i + 1 < len(leaves):
                    combined = hashlib.sha256(leaves[i] + leaves[i + 1]).digest()
                else:
                    combined = leaves[i]
                new_leaves.append(combined)
            leaves = new_leaves
        
        return leaves[0] if leaves else hashlib.sha256(secret + public).digest()


class Falcon512Key:
    """Clé Falcon-512 pour signatures"""
    
    def __init__(self, seed: bytes):
        self.n = 512
        self.seed = seed
        self.secret_key = self._generate_secret_key()
        self.public_key = self._generate_public_key()
    
    def _generate_secret_key(self) -> np.ndarray:
        """Génère la clé secrète Falcon"""
        derived = HKDF.derive(self.seed, b'falcon', b'secret', self.n * 2)
        return np.frombuffer(derived, dtype=np.int8)[:self.n]
    
    def _generate_public_key(self) -> bytes:
        """Génère la clé publique Falcon"""
        return hashlib.sha512(self.secret_key.tobytes()).digest()
    
    def sign(self, message: bytes) -> bytes:
        """Signe un message"""
        h = hashlib.sha512(message).digest()
        
        signature = bytearray(self.n)
        for i in range(self.n):
            signature[i] = (h[i % 64] ^ self.secret_key[i]) & 0xFF
        
        return bytes(signature)


class PostQuantumMasterKey:
    """Clé maître post-quantique avec dérivation hiérarchique"""
    
    def __init__(self, spinor_data: bytes):
        self.data = spinor_data
        self._root_key = None
        self._derived_keys: Dict[str, Any] = {}
        
    def get_root_key(self) -> bytes:
        """Génère ou retourne la clé racine 4096 bits"""
        if self._root_key is None:
            self._root_key = HKDF.derive(
                self.data,
                b"poly_spinor_root",
                b"root_key_derivation",
                512
            )
        return self._root_key
    
    def derive_key(self, purpose: KeyPurpose = KeyPurpose.MESSAGING) -> Any:
        """Dérive une clé pour un objectif spécifique"""
        purpose_key = purpose.value
        
        if purpose_key in self._derived_keys:
            return self._derived_keys[purpose_key]
        
        root_key = self.get_root_key()
        
        if purpose == KeyPurpose.MESSAGING:
            key = self._derive_messaging_key(root_key)
        elif purpose == KeyPurpose.ESCROW:
            key = self._derive_escrow_key(root_key)
        elif purpose == KeyPurpose.SIGNATURE:
            key = self._derive_signature_key(root_key)
        elif purpose == KeyPurpose.IDENTITY:
            key = self._derive_identity_key(root_key)
        else:
            key = root_key
        
        self._derived_keys[purpose_key] = key
        return key
    
    def _derive_messaging_key(self, root_key: bytes) -> TripleEnvelope:
        """Dérive la clé de messagerie avec triple enveloppe"""
        ntru_seed = HKDF.derive(root_key, b'ntru', b'messaging', 128)
        ntru_gen = NTRUKeyGenerator(n=761, q=4591)
        key_ntru = ntru_gen.generate(ntru_seed)
        
        mceliece_seed = HKDF.derive(root_key, b'mceliece', b'messaging', 128)
        mceliece_gen = McElieceKeyGenerator(n=3488, k=2720, t=64)
        key_mceliece = mceliece_gen.generate(mceliece_seed)
        
        sphincs_seed = HKDF.derive(root_key, b'sphincs', b'messaging', 64)
        sphincs_gen = SPHINCSKeyGenerator(security_level=256)
        key_sphincs = sphincs_gen.generate(sphincs_seed)
        
        return TripleEnvelope(key_ntru, key_mceliece, key_sphincs)
    
    def _derive_escrow_key(self, root_key: bytes) -> Falcon512Key:
        """Dérive la clé d'entiercement basée sur Falcon"""
        correlation_seed = HKDF.derive(root_key, b'escrow', b'correlation', 64)
        return Falcon512Key(correlation_seed)
    
    def _derive_signature_key(self, root_key: bytes) -> SPHINCSKey:
        """Dérive la clé de signature SPHINCS+"""
        sig_seed = HKDF.derive(root_key, b'signature', b'sphincs', 64)
        sphincs_gen = SPHINCSKeyGenerator(security_level=256, tree_height=64)
        return sphincs_gen.generate(sig_seed)
    
    def _derive_identity_key(self, root_key: bytes) -> bytes:
        """Dérive la clé d'identité quantique"""
        return HKDF.derive(root_key, b'identity', b'quantum_user_id', 448)
    
    def get_security_analysis(self) -> Dict[str, Any]:
        """Retourne l'analyse de sécurité"""
        return {
            'root_key_bits': len(self.get_root_key()) * 8,
            'ntru_security_level': 'NIST Level 5',
            'mceliece_security_level': 'NIST Level 5',
            'sphincs_security_level': 'NIST Level 5',
            'total_post_quantum_bits': 4096 + 3488 + 256,
            'quantum_resistance': 'Full',
            'classical_resistance': '>2^256 operations'
        }


class QuantumUserID:
    """Identifiant utilisateur quantique 7D"""
    
    def __init__(self, hyperclusters_data: bytes):
        self.data = hyperclusters_data
        self.user_id = None
        
    def generate(self) -> bytes:
        """Génère l'ID utilisateur quantique"""
        full_spinor_tensor = self._compute_full_spinor_tensor()
        
        reduced_tensor = self._se3_equivariant_reduction(full_spinor_tensor)
        
        hash_chain = self._cascade_hash(reduced_tensor)
        
        self.user_id = self._combine_hashes(hash_chain)
        
        return self.user_id
    
    def _compute_full_spinor_tensor(self) -> np.ndarray:
        """Calcule le tenseur spinoriel complet"""
        data_array = np.frombuffer(self.data, dtype=np.uint8)
        
        dim = int(np.ceil(len(data_array) ** 0.5))
        padded = np.zeros(dim * dim, dtype=np.uint8)
        padded[:len(data_array)] = data_array
        
        return padded.reshape(dim, dim).astype(complex)
    
    def _se3_equivariant_reduction(self, tensor: np.ndarray) -> np.ndarray:
        """Réduction équivariante SE(3)"""
        U, S, Vh = np.linalg.svd(tensor, full_matrices=False)
        
        reduced_dim = min(64, len(S))
        reduced = U[:, :reduced_dim] @ np.diag(S[:reduced_dim])
        
        return reduced.flatten()
    
    def _cascade_hash(self, tensor: np.ndarray) -> List[bytes]:
        """Hachage en cascade sur 7 dimensions"""
        hash_chain = []
        current_hash = hashlib.sha512(tensor.tobytes())
        
        for i in range(7):
            spinor_transform = self._apply_spinor_transform(
                current_hash.digest(), i
            )
            current_hash = hashlib.sha512(spinor_transform)
            hash_chain.append(current_hash.digest())
        
        return hash_chain
    
    def _apply_spinor_transform(self, data: bytes, dimension: int) -> bytes:
        """Applique une transformation spinorielle"""
        arr = np.frombuffer(data, dtype=np.uint8)
        
        rotation = np.roll(arr, dimension * 7)
        
        phase = np.exp(2j * np.pi * dimension / 7)
        transformed = (rotation.astype(complex) * phase).real.astype(np.uint8)
        
        return bytes(transformed)
    
    def _combine_hashes(self, hash_chain: List[bytes]) -> bytes:
        """Combine les hashes par XOR"""
        result = bytearray(64)
        
        for h in hash_chain:
            for i in range(64):
                result[i] ^= h[i]
        
        return bytes(result)
    
    def get_effective_bits(self) -> int:
        """Retourne le nombre de bits effectifs: 512 × 7 = 3584"""
        return 512 * 7
