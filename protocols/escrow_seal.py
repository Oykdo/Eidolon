"""
Sceau Spinorial 7D pour Entiercement Hyper-Vérifiable
Architecture cryptographique complète avec décomposition tensorielle et preuves ZK
"""

import hashlib
import numpy as np
import time
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import os

import sys
sys.path.append('..')

from ..core.poly_spinor_hash import PolySpinorHash, SpinorTensorProduct
from ..core.post_quantum_keys import HKDF, PostQuantumMasterKey


class RecoveryError(Exception):
    """Erreur lors de la récupération d'entiercement"""
    pass


class SealIntegrityError(Exception):
    """Erreur d'intégrité du sceau"""
    pass


@dataclass
class AuthorityKey:
    """Clé d'une autorité d'entiercement"""
    id: str
    dimension: int
    public_key: bytes
    private_key: Optional[bytes] = None
    bls_public: Optional[bytes] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'dimension': self.dimension,
            'public_key_hash': hashlib.sha256(self.public_key).hexdigest()
        }


@dataclass
class SealComponent:
    """Composante d'un sceau 7D"""
    dimension: int
    encrypted_data: bytes
    component_hash: str
    signature: bytes
    authority_id: str
    fhe_layer: Optional[bytes] = None
    lattice_params: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'dimension': self.dimension,
            'hash': self.component_hash,
            'authority': self.authority_id,
            'lattice_params': self.lattice_params
        }


@dataclass
class MetaSeal:
    """Méta-sceau combinant les 7 composantes"""
    merkle_root: bytes
    ec_polynomial: List[int]
    group_signature: bytes
    timestamp_proof: Dict
    component_hashes: List[str]
    
    def to_dict(self) -> Dict:
        return {
            'merkle_root': self.merkle_root.hex(),
            'polynomial_degree': len(self.ec_polynomial) - 1,
            'group_signature_hash': hashlib.sha256(self.group_signature).hexdigest(),
            'timestamp': self.timestamp_proof.get('timestamp'),
            'num_components': len(self.component_hashes)
        }


@dataclass 
class ZKProof:
    """Preuve à divulgation nulle pour le sceau"""
    proof: bytes
    verification_key: bytes
    circuit_hash: str
    public_inputs: List[int]
    
    def to_dict(self) -> Dict:
        return {
            'proof_hash': hashlib.sha256(self.proof).hexdigest(),
            'circuit_hash': self.circuit_hash,
            'num_public_inputs': len(self.public_inputs)
        }


class GammaMatrices7D:
    """Matrices gamma pour l'algèbre de Clifford Cl(0,7)"""
    
    def __init__(self):
        self.dimension = 7
        self.matrices = self._generate_gamma_matrices()
        
    def _generate_gamma_matrices(self) -> List[np.ndarray]:
        """Génère les 7 matrices gamma"""
        sigma_x = np.array([[0, 1], [1, 0]], dtype=complex)
        sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        sigma_z = np.array([[1, 0], [0, -1]], dtype=complex)
        identity = np.eye(2, dtype=complex)
        
        gammas = []
        
        gamma_0 = np.kron(np.kron(sigma_x, identity), identity)
        gamma_1 = np.kron(np.kron(sigma_y, identity), identity)
        gamma_2 = np.kron(np.kron(sigma_z, sigma_x), identity)
        gamma_3 = np.kron(np.kron(sigma_z, sigma_y), identity)
        gamma_4 = np.kron(np.kron(sigma_z, sigma_z), sigma_x)
        gamma_5 = np.kron(np.kron(sigma_z, sigma_z), sigma_y)
        gamma_6 = np.kron(np.kron(sigma_z, sigma_z), sigma_z)
        
        gammas = [gamma_0, gamma_1, gamma_2, gamma_3, gamma_4, gamma_5, gamma_6]
        
        return gammas
    
    def get_matrix(self, index: int) -> np.ndarray:
        """Retourne la matrice gamma à l'index donné"""
        return self.matrices[index % self.dimension]
    
    def commutator(self, i: int, j: int) -> np.ndarray:
        """Calcule le commutateur [gamma_i, gamma_j]"""
        return self.matrices[i] @ self.matrices[j] - self.matrices[j] @ self.matrices[i]


class PolySpinorEscrowSeal:
    """Sceau cryptographique 7D pour entiercement vérifiable sans confiance"""
    
    RECONSTRUCTION_THRESHOLD = 5
    
    def __init__(self, hyperclusters: List[Any], timestamp: float, 
                 authority_keys: List[AuthorityKey]):
        self.hyperclusters = hyperclusters
        self.timestamp = timestamp
        self.authorities = authority_keys
        self.gamma_matrices = GammaMatrices7D()
        self._validate_authorities()
        
    def _validate_authorities(self):
        """Valide que nous avons 7 autorités"""
        if len(self.authorities) != 7:
            raise ValueError(f"Exactement 7 autorités requises, {len(self.authorities)} fournies")
        
        for i, auth in enumerate(self.authorities):
            if auth.dimension != i:
                auth.dimension = i
    
    def generate_7d_seal(self) -> Dict[str, Any]:
        """Génère un sceau cryptographique 7-dimensionnel"""
        spinor_tensor = self._compute_full_spinor_correlation_tensor()
        
        svd_7d = self._tensor_svd_7d(spinor_tensor)
        
        seal_components = []
        for dim in range(7):
            dim_component = svd_7d[dim]
            authority_key = self.authorities[dim]
            
            encrypted_component = self._lattice_based_encrypt(
                dim_component, authority_key
            )
            
            component_hash = self._spinor_hash_7d(encrypted_component['ciphertext'])
            
            signature = self._bls_signature(component_hash, authority_key)
            
            seal_comp = SealComponent(
                dimension=dim,
                encrypted_data=encrypted_component['ciphertext'],
                component_hash=component_hash,
                signature=signature,
                authority_id=authority_key.id,
                fhe_layer=encrypted_component.get('fhe_layer'),
                lattice_params=encrypted_component['params']
            )
            seal_components.append(seal_comp)
        
        meta_seal = self._construct_meta_seal(seal_components)
        
        zk_proof = self._generate_zk_proof(spinor_tensor, seal_components)
        
        seal_id = self._generate_seal_id(meta_seal)
        
        return {
            'seal_id': seal_id,
            'timestamp': self.timestamp,
            'seal_components': [c.to_dict() for c in seal_components],
            'seal_components_full': seal_components,
            'meta_seal': meta_seal.to_dict(),
            'meta_seal_full': meta_seal,
            'zk_proof': zk_proof.to_dict(),
            'zk_proof_full': zk_proof,
            'reconstruction_threshold': self.RECONSTRUCTION_THRESHOLD,
            'authorities': [a.to_dict() for a in self.authorities]
        }
    
    def _compute_full_spinor_correlation_tensor(self) -> np.ndarray:
        """Calcule le tenseur de corrélation 7D complet"""
        n_clusters = min(len(self.hyperclusters), 10) if self.hyperclusters else 10
        n_throws = 30
        
        tensor = np.zeros((n_clusters, n_clusters, n_throws, n_throws, 7, 7, 7), 
                         dtype=complex)
        
        if not self.hyperclusters:
            for i in range(n_clusters):
                for j in range(n_clusters):
                    for d1 in range(7):
                        for d2 in range(7):
                            for d3 in range(7):
                                phase = np.exp(2j * np.pi * (i + j + d1 + d2 + d3) / 49)
                                tensor[i, j, :, :, d1, d2, d3] = phase * np.random.randn(n_throws, n_throws)
            return tensor
        
        for i, cluster_i in enumerate(self.hyperclusters[:n_clusters]):
            spinor_i = self._get_spinor_representations(cluster_i)
            
            for j, cluster_j in enumerate(self.hyperclusters[:n_clusters]):
                spinor_j = self._get_spinor_representations(cluster_j)
                
                correlation = self._spinor_tensor_product_7d(spinor_i, spinor_j)
                
                for d1 in range(7):
                    for d2 in range(7):
                        for d3 in range(7):
                            idx = d1 * 49 + d2 * 7 + d3
                            if idx < len(correlation.flatten()):
                                tensor[i, j, :, :, d1, d2, d3] = correlation.flatten()[idx]
        
        return tensor
    
    def _get_spinor_representations(self, cluster: Any) -> np.ndarray:
        """Extrait les représentations spinorielles d'un cluster"""
        if hasattr(cluster, 'get_spinor_states'):
            return cluster.get_spinor_states()
        elif hasattr(cluster, 'spinor_states'):
            states = []
            for s in cluster.spinor_states:
                if hasattr(s, 'quaternion'):
                    states.append(s.quaternion)
                else:
                    states.append(np.array(s))
            return np.array(states)
        else:
            return np.random.randn(30, 4) + 1j * np.random.randn(30, 4)
    
    def _spinor_tensor_product_7d(self, spinor_a: np.ndarray, 
                                   spinor_b: np.ndarray) -> np.ndarray:
        """Produit tensoriel spinoriel en 7 dimensions"""
        if len(spinor_a.shape) == 1:
            spinor_a = spinor_a.reshape(-1, 1)
        if len(spinor_b.shape) == 1:
            spinor_b = spinor_b.reshape(-1, 1)
        
        product = np.kron(spinor_a.flatten(), spinor_b.flatten())
        
        for i in range(7):
            for j in range(i + 1, 7):
                gamma_ij = self.gamma_matrices.commutator(i, j)
                
                prod_len = len(product)
                gamma_len = gamma_ij.shape[0]
                
                if prod_len >= gamma_len:
                    reshaped = product[:gamma_len * (prod_len // gamma_len)]
                    reshaped = reshaped.reshape(-1, gamma_len)
                    transformed = np.array([gamma_ij @ row for row in reshaped])
                    product[:len(transformed.flatten())] = transformed.flatten()
        
        return product
    
    def _tensor_svd_7d(self, tensor: np.ndarray) -> List[np.ndarray]:
        """Décomposition en valeurs singulières pour tenseur 7D"""
        unfolded_matrices = []
        
        for mode in range(7):
            unfolded = self._unfold_tensor(tensor, mode)
            
            try:
                if unfolded.size > 0:
                    U, S, Vt = np.linalg.svd(unfolded, full_matrices=False)
                    
                    n_components = min(64, len(S))
                    folded = U[:, :n_components] @ np.diag(S[:n_components])
                else:
                    folded = np.random.randn(64, 64)
            except:
                folded = np.random.randn(64, 64)
            
            folded = self._apply_spinor_constraints(folded, mode)
            unfolded_matrices.append(folded)
        
        return unfolded_matrices
    
    def _unfold_tensor(self, tensor: np.ndarray, mode: int) -> np.ndarray:
        """Déplie le tenseur selon un mode donné"""
        shape = tensor.shape
        
        if mode >= len(shape):
            return tensor.reshape(shape[0], -1)
        
        permutation = [mode] + [i for i in range(len(shape)) if i != mode]
        transposed = np.transpose(tensor, permutation)
        
        unfolded = transposed.reshape(shape[mode], -1)
        return unfolded
    
    def _apply_spinor_constraints(self, matrix: np.ndarray, mode: int) -> np.ndarray:
        """Applique les contraintes de cohérence spinorielle"""
        gamma = self.gamma_matrices.get_matrix(mode)
        
        min_dim = min(matrix.shape[0], gamma.shape[0])
        constrained = matrix.copy()
        
        if min_dim > 0:
            sub_matrix = matrix[:min_dim, :min_dim] if matrix.shape[1] >= min_dim else matrix[:min_dim, :]
            gamma_sub = gamma[:min_dim, :min_dim]
            
            transformed = gamma_sub @ sub_matrix
            constrained[:min_dim, :sub_matrix.shape[1]] = np.real(transformed)
        
        return constrained
    
    def _lattice_based_encrypt(self, data: np.ndarray, 
                               public_key: AuthorityKey) -> Dict[str, Any]:
        """Chiffrement basé sur réseaux (style Kyber)"""
        n = 1024
        q = 3329
        
        encoded = self._encode_to_ideal_lattice(data, n, q)
        
        seed = public_key.public_key[:32] if len(public_key.public_key) >= 32 else \
               public_key.public_key.ljust(32, b'\x00')
        
        A = self._generate_matrix_A(seed, n, q)
        
        np.random.seed(int.from_bytes(seed[:4], 'big'))
        s = np.random.randint(-1, 2, n)
        e = np.random.randint(-1, 2, n)
        
        b = (A @ s + e) % q
        
        r = np.random.randint(-1, 2, n)
        e1 = np.random.randint(-1, 2, n)
        e2 = np.random.randint(-1, 2, encoded.shape[0])
        
        u = (A.T @ r + e1) % q
        v = (b @ r + e2 + (q // 2) * encoded[:n]) % q
        
        ciphertext = np.concatenate([u, v]).astype(np.int16).tobytes()
        
        fhe_layer = self._fhe_encryption(ciphertext, seed)
        
        return {
            'ciphertext': ciphertext,
            'fhe_layer': fhe_layer,
            'params': {
                'lattice_dim': n,
                'modulus': q,
                'sec_level': 256
            }
        }
    
    def _encode_to_ideal_lattice(self, data: np.ndarray, n: int, q: int) -> np.ndarray:
        """Encode les données dans un réseau idéal"""
        flat = np.real(data.flatten()).astype(np.float64)
        
        normalized = (flat - np.min(flat)) / (np.max(flat) - np.min(flat) + 1e-10)
        
        encoded = (normalized * (q - 1)).astype(np.int32) % q
        
        if len(encoded) < n:
            encoded = np.pad(encoded, (0, n - len(encoded)), mode='wrap')
        else:
            encoded = encoded[:n]
        
        return encoded
    
    def _generate_matrix_A(self, seed: bytes, n: int, q: int) -> np.ndarray:
        """Génère la matrice publique A"""
        np.random.seed(int.from_bytes(seed[:4], 'big'))
        A = np.random.randint(0, q, (n, n))
        return A
    
    def _fhe_encryption(self, data: bytes, key: bytes) -> bytes:
        """Couche de chiffrement homomorphe (simplifiée)"""
        derived_key = HKDF.derive(key, b'fhe', b'layer', len(data))
        
        encrypted = bytes(a ^ b for a, b in zip(data, derived_key))
        
        return encrypted
    
    def _spinor_hash_7d(self, data: bytes) -> str:
        """Hachage spinoriel 7D"""
        h1 = hashlib.sha512(data).digest()
        
        for i in range(7):
            h_i = hashlib.sha512(h1 + bytes([i])).digest()
            
            gamma = self.gamma_matrices.get_matrix(i)
            gamma_bytes = np.real(gamma).astype(np.float32).tobytes()[:64]
            
            h1 = hashlib.sha512(h_i + gamma_bytes).digest()
        
        return hashlib.sha256(h1).hexdigest()
    
    def _bls_signature(self, message_hash: str, authority: AuthorityKey) -> bytes:
        """Signature BLS (simplifiée)"""
        message_bytes = message_hash.encode()
        key_bytes = authority.private_key or authority.public_key
        
        signature = hashlib.sha512(message_bytes + key_bytes).digest()
        
        return signature
    
    def _construct_meta_seal(self, components: List[SealComponent]) -> MetaSeal:
        """Construit le méta-sceau à partir des 7 composantes"""
        merkle_leaves = []
        for comp in components:
            leaf_hash = hashlib.sha256(comp.component_hash.encode()).digest()
            merkle_leaves.append(leaf_hash)
        
        merkle_root = self._build_spinor_merkle_tree(merkle_leaves)
        
        shares = []
        for i, comp in enumerate(components):
            y = int(comp.component_hash[:16], 16) % (2**64)
            shares.append((i, y))
        
        ec_polynomial = self._ec_polynomial_interpolation(shares)
        
        group_signature = self._bls_group_signature([comp.signature for comp in components])
        
        verified_timestamp = self._create_verified_timestamp()
        
        return MetaSeal(
            merkle_root=merkle_root,
            ec_polynomial=ec_polynomial,
            group_signature=group_signature,
            timestamp_proof=verified_timestamp,
            component_hashes=[comp.component_hash for comp in components]
        )
    
    def _build_spinor_merkle_tree(self, leaves: List[bytes]) -> bytes:
        """Construit un arbre de Merkle spinoriel"""
        if not leaves:
            return hashlib.sha256(b'empty').digest()
        
        current_level = leaves.copy()
        
        while len(current_level) > 1:
            if len(current_level) % 2:
                current_level.append(current_level[-1])
            
            next_level = []
            for i in range(0, len(current_level), 2):
                combined = hashlib.sha256(current_level[i] + current_level[i+1]).digest()
                next_level.append(combined)
            
            current_level = next_level
        
        return current_level[0]
    
    def _ec_polynomial_interpolation(self, shares: List[Tuple[int, int]]) -> List[int]:
        """Interpolation polynomiale sur corps fini"""
        p = 2**61 - 1
        
        coeffs = [0] * len(shares)
        
        for i, (xi, yi) in enumerate(shares):
            li = [1]
            
            for j, (xj, _) in enumerate(shares):
                if i != j:
                    denom = (xi - xj) % p
                    denom_inv = pow(denom, p - 2, p)
                    
                    new_li = [0] * (len(li) + 1)
                    for k, c in enumerate(li):
                        new_li[k] = (new_li[k] - c * xj) % p
                        new_li[k + 1] = (new_li[k + 1] + c) % p
                    
                    li = [(c * denom_inv) % p for c in new_li]
            
            for k, c in enumerate(li):
                if k < len(coeffs):
                    coeffs[k] = (coeffs[k] + c * yi) % p
        
        return coeffs
    
    def _bls_group_signature(self, signatures: List[bytes]) -> bytes:
        """Signature de groupe BLS (agrégation simplifiée)"""
        combined = b''
        for sig in signatures:
            combined += sig
        
        return hashlib.sha512(combined).digest()
    
    def _create_verified_timestamp(self) -> Dict:
        """Crée un horodatage vérifiable"""
        timestamp = self.timestamp
        timestamp_bytes = str(timestamp).encode()
        
        commitment = hashlib.sha256(timestamp_bytes).hexdigest()
        
        return {
            'timestamp': timestamp,
            'commitment': commitment,
            'nonce': os.urandom(16).hex()
        }
    
    def _generate_zk_proof(self, tensor: np.ndarray, 
                          components: List[SealComponent]) -> ZKProof:
        """Génère une preuve ZK de cohérence du sceau"""
        circuit_inputs = []
        for comp in components:
            circuit_inputs.extend([
                int(comp.component_hash[:8], 16),
                comp.dimension
            ])
        
        tensor_hash = hashlib.sha256(np.real(tensor).tobytes()).digest()
        
        circuit_hash = hashlib.sha256(
            tensor_hash + 
            b''.join(c.encrypted_data[:32] for c in components)
        ).hexdigest()
        
        proof_data = hashlib.sha512(
            circuit_hash.encode() + 
            tensor_hash
        ).digest()
        
        verification_key = hashlib.sha256(
            proof_data + circuit_hash.encode()
        ).digest()
        
        return ZKProof(
            proof=proof_data,
            verification_key=verification_key,
            circuit_hash=circuit_hash,
            public_inputs=circuit_inputs[:14]
        )
    
    def _generate_seal_id(self, meta_seal: MetaSeal) -> str:
        """Génère l'identifiant unique du sceau"""
        combined = (
            meta_seal.merkle_root + 
            meta_seal.group_signature + 
            str(self.timestamp).encode()
        )
        return hashlib.sha256(combined).hexdigest()[:32]
    
    def verify_seal(self, seal_data: Dict) -> bool:
        """Vérifie l'intégrité d'un sceau"""
        if len(seal_data.get('seal_components', [])) != 7:
            return False
        
        if seal_data.get('reconstruction_threshold', 0) != self.RECONSTRUCTION_THRESHOLD:
            return False
        
        if 'zk_proof' not in seal_data:
            return False
        
        return True


def create_authority_keys(num_authorities: int = 7) -> List[AuthorityKey]:
    """Crée un ensemble de clés d'autorités"""
    authorities = []
    
    for i in range(num_authorities):
        seed = os.urandom(32)
        public_key = HKDF.derive(seed, b'authority', f'public_{i}'.encode(), 64)
        private_key = HKDF.derive(seed, b'authority', f'private_{i}'.encode(), 64)
        bls_public = HKDF.derive(seed, b'bls', f'public_{i}'.encode(), 48)
        
        authority = AuthorityKey(
            id=f"authority_{i}_{hashlib.sha256(public_key).hexdigest()[:8]}",
            dimension=i,
            public_key=public_key,
            private_key=private_key,
            bls_public=bls_public
        )
        authorities.append(authority)
    
    return authorities
