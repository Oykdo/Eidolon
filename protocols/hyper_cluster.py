"""
Système HyperCluster et Vérification Bell Avancée 7D
Architecture de corrélations quantiques simulées
"""

import hashlib
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import math

import sys
sys.path.append('..')

from ..core.poly_spinor_hash import Lancer3D, PolySpinorHash
from ..core.post_quantum_keys import PostQuantumMasterKey, QuantumUserID


class SecurityException(Exception):
    """Exception de sécurité pour violations quantiques"""
    pass


class DieType(Enum):
    """Types de dés polyédriques"""
    D4 = (4, 'tetrahedron')
    D6 = (6, 'cube')
    D8 = (8, 'octahedron')
    D10 = (10, 'pentagonal_trapezohedron')
    D12 = (12, 'dodecahedron')
    D20 = (20, 'icosahedron')
    D100 = (100, 'sphere')
    
    @property
    def faces(self) -> int:
        return self.value[0]
    
    @property
    def polyhedron(self) -> str:
        return self.value[1]


@dataclass
class SpinorState:
    """État spinoriel d'un lancer"""
    quaternion: np.ndarray
    phase: complex
    entanglement_index: float
    
    @classmethod
    def from_lancer(cls, lancer: Lancer3D) -> 'SpinorState':
        """Crée un état spinoriel depuis un lancer"""
        alpha = lancer.orientation_alpha * np.pi / 512
        beta = lancer.orientation_beta * np.pi / 512
        gamma = lancer.orientation_gamma * np.pi / 512
        
        cy = np.cos(gamma * 0.5)
        sy = np.sin(gamma * 0.5)
        cp = np.cos(beta * 0.5)
        sp = np.sin(beta * 0.5)
        cr = np.cos(alpha * 0.5)
        sr = np.sin(alpha * 0.5)
        
        quaternion = np.array([
            cr * cp * cy + sr * sp * sy,
            sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy
        ])
        
        phase = np.exp(1j * (alpha + beta + gamma))
        
        entanglement = np.abs(quaternion[0] * quaternion[3] - 
                             quaternion[1] * quaternion[2])
        
        return cls(quaternion=quaternion, phase=phase, 
                   entanglement_index=entanglement)


@dataclass
class HyperCluster:
    """Cluster 7D d'un type de dé"""
    die_type: DieType
    lancers: List[Lancer3D]
    spinor_states: List[SpinorState] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.spinor_states:
            self.spinor_states = [
                SpinorState.from_lancer(l) for l in self.lancers
            ]
    
    def get_spinor_states(self) -> np.ndarray:
        """Retourne la matrice des états spinoriels"""
        n = len(self.spinor_states)
        states = np.zeros((n, 4), dtype=complex)
        
        for i, state in enumerate(self.spinor_states):
            states[i] = state.quaternion * state.phase
        
        return states
    
    def compute_cluster_entropy(self) -> float:
        """Calcule l'entropie du cluster"""
        states = self.get_spinor_states()
        
        cov = np.cov(np.abs(states).T)
        eigenvalues = np.linalg.eigvalsh(cov)
        eigenvalues = eigenvalues[eigenvalues > 1e-10]
        
        if len(eigenvalues) == 0:
            return 0.0
        
        eigenvalues = eigenvalues / np.sum(eigenvalues)
        entropy = -np.sum(eigenvalues * np.log2(eigenvalues + 1e-10))
        
        return float(entropy)
    
    def get_mean_entanglement(self) -> float:
        """Retourne l'intrication moyenne"""
        if not self.spinor_states:
            return 0.0
        return np.mean([s.entanglement_index for s in self.spinor_states])


class SpinorCorrelationCalculator:
    """Calculateur de corrélations spinorielles"""
    
    @staticmethod
    def compute_spinor_correlation(states_i: np.ndarray, 
                                   states_j: np.ndarray) -> np.ndarray:
        """Calcule la corrélation spinorielle entre deux ensembles d'états"""
        n_i, n_j = len(states_i), len(states_j)
        correlation = np.zeros((n_i, n_j), dtype=complex)
        
        for i in range(n_i):
            for j in range(n_j):
                psi_i = states_i[i] / (np.linalg.norm(states_i[i]) + 1e-10)
                psi_j = states_j[j] / (np.linalg.norm(states_j[j]) + 1e-10)
                
                correlation[i, j] = np.conj(psi_i) @ psi_j
        
        return correlation


class GeneralizedBellInequalities:
    """Inégalités de Bell généralisées pour 7 dimensions"""
    
    CHSH_BOUND = 2.0
    QUANTUM_BOUND = 2 * np.sqrt(2)
    
    def __init__(self, dimension: int = 7):
        self.dimension = dimension
        
    def compute_chsh_operator(self, correlation: np.ndarray) -> float:
        """Calcule l'opérateur CHSH"""
        n = correlation.shape[0]
        
        if n < 4:
            return 0.0
        
        E_00 = np.real(np.mean(correlation[:n//2, :n//2]))
        E_01 = np.real(np.mean(correlation[:n//2, n//2:]))
        E_10 = np.real(np.mean(correlation[n//2:, :n//2]))
        E_11 = np.real(np.mean(correlation[n//2:, n//2:]))
        
        S = E_00 - E_01 + E_10 + E_11
        
        return abs(S)
    
    def compute_cglmp_inequality(self, correlation: np.ndarray) -> float:
        """Calcule l'inégalité CGLMP pour qudits"""
        d = self.dimension
        n = correlation.shape[0]
        
        I_d = 0.0
        for k in range(min(d, n)):
            weight = 1 - 2 * k / (d - 1) if d > 1 else 1
            I_d += weight * np.real(np.mean(correlation[k, :]))
        
        return abs(I_d)
    
    def compute_mermin_inequality(self, correlations: List[np.ndarray]) -> float:
        """Calcule l'inégalité de Mermin pour N parties"""
        n = len(correlations)
        if n < 2:
            return 0.0
        
        mermin = 0.0
        for i, corr in enumerate(correlations):
            sign = (-1) ** i
            mermin += sign * np.real(np.mean(corr))
        
        return abs(mermin)
    
    def verify(self, correlation: np.ndarray) -> Tuple[bool, Dict[str, float]]:
        """Vérifie toutes les inégalités"""
        chsh = self.compute_chsh_operator(correlation)
        cglmp = self.compute_cglmp_inequality(correlation)
        
        results = {
            'chsh': chsh,
            'cglmp': cglmp,
            'chsh_violation': chsh > self.CHSH_BOUND,
            'quantum_signature': chsh > self.CHSH_BOUND * 1.2
        }
        
        is_quantum = results['chsh_violation'] or cglmp > 1.5
        
        return is_quantum, results


class AdvancedBellVerification7D:
    """Vérification Bell avancée sur 7 dimensions"""
    
    def __init__(self, clusters: List[HyperCluster]):
        self.clusters = clusters
        self.correlation_matrix = None
        self.bell_results = None
        
    def verify_all_correlations(self) -> Tuple[bool, Dict]:
        """Vérifie les corrélations quantiques entre tous les clusters"""
        n_clusters = len(self.clusters)
        
        self.correlation_matrix = np.zeros(
            (n_clusters, n_clusters, 30, 30), 
            dtype=complex
        )
        
        correlator = SpinorCorrelationCalculator()
        bell_checker = GeneralizedBellInequalities(dimension=7)
        
        all_violations = []
        
        for i in range(n_clusters):
            states_i = self.clusters[i].get_spinor_states()
            
            for j in range(n_clusters):
                if i != j:
                    states_j = self.clusters[j].get_spinor_states()
                    
                    corr = correlator.compute_spinor_correlation(states_i, states_j)
                    
                    min_n = min(30, corr.shape[0], corr.shape[1])
                    self.correlation_matrix[i, j, :min_n, :min_n] = corr[:min_n, :min_n]
                    
                    is_quantum, results = bell_checker.verify(corr)
                    
                    if not is_quantum:
                        all_violations.append({
                            'cluster_i': i,
                            'cluster_j': j,
                            'results': results
                        })
        
        if len(all_violations) > n_clusters * (n_clusters - 1) // 4:
            raise SecurityException(
                f"Violation des corrélations quantiques: "
                f"{len(all_violations)} paires classiques détectées"
            )
        
        self.bell_results = {
            'total_pairs': n_clusters * (n_clusters - 1),
            'violations': len(all_violations),
            'quantum_signature_strength': self._compute_signature_strength()
        }
        
        return True, self.bell_results
    
    def _compute_signature_strength(self) -> float:
        """Calcule la force de la signature quantique"""
        if self.correlation_matrix is None:
            return 0.0
        
        flat_corr = np.abs(self.correlation_matrix.flatten())
        flat_corr = flat_corr[flat_corr > 0]
        
        if len(flat_corr) == 0:
            return 0.0
        
        mean_corr = np.mean(flat_corr)
        std_corr = np.std(flat_corr)
        
        return float(mean_corr + std_corr)
    
    def extract_key_from_correlations(self) -> bytes:
        """Extrait une clé finale des corrélations"""
        if self.correlation_matrix is None:
            raise ValueError("Corrélations non calculées")
        
        flat = self.correlation_matrix.flatten()
        real_part = np.real(flat)
        imag_part = np.imag(flat)
        
        combined = np.concatenate([real_part, imag_part])
        
        normalized = (combined - np.min(combined)) / (np.max(combined) - np.min(combined) + 1e-10)
        
        bits = (normalized > 0.5).astype(np.uint8)
        
        key_bytes = np.packbits(bits[:4096])
        
        return bytes(key_bytes)


@dataclass
class SpinorialSeal7D:
    """Sceau Spinorial 7D pour entiercement hyper-vérifiable"""
    seal_id: str
    correlation_hash: str
    bell_signature: Dict[str, float]
    spinor_commitment: bytes
    merkle_root: bytes
    timestamp: str
    
    def to_dict(self) -> Dict:
        return {
            'seal_id': self.seal_id,
            'correlation_hash': self.correlation_hash,
            'bell_signature': self.bell_signature,
            'spinor_commitment_hash': hashlib.sha256(self.spinor_commitment).hexdigest(),
            'merkle_root_hash': hashlib.sha256(self.merkle_root).hexdigest(),
            'timestamp': self.timestamp
        }
    
    def verify_commitment(self, original_data: bytes) -> bool:
        """Vérifie le commitment spinoriel"""
        expected_commitment = hashlib.sha512(original_data).digest()
        return hmac_compare(self.spinor_commitment, expected_commitment)


def hmac_compare(a: bytes, b: bytes) -> bool:
    """Comparaison à temps constant"""
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0


class HyperVerifiableEscrow:
    """Système d'entiercement hyper-vérifiable"""
    
    def __init__(self, clusters: List[HyperCluster]):
        self.clusters = clusters
        self.bell_verifier = AdvancedBellVerification7D(clusters)
        self.seals: Dict[str, SpinorialSeal7D] = {}
        
    def create_spinorial_seal(self, document_data: bytes) -> SpinorialSeal7D:
        """Crée un sceau spinorial 7D"""
        is_quantum, bell_results = self.bell_verifier.verify_all_correlations()
        
        if not is_quantum:
            raise SecurityException("Signature quantique insuffisante")
        
        correlation_key = self.bell_verifier.extract_key_from_correlations()
        correlation_hash = hashlib.sha512(correlation_key).hexdigest()
        
        spinor_commitment = self._compute_spinor_commitment(document_data)
        
        merkle_root = self._build_merkle_tree(document_data)
        
        from datetime import datetime
        seal_id = hashlib.sha256(
            correlation_hash.encode() + 
            str(datetime.now()).encode()
        ).hexdigest()[:32]
        
        seal = SpinorialSeal7D(
            seal_id=seal_id,
            correlation_hash=correlation_hash,
            bell_signature=bell_results,
            spinor_commitment=spinor_commitment,
            merkle_root=merkle_root,
            timestamp=datetime.now().isoformat()
        )
        
        self.seals[seal_id] = seal
        return seal
    
    def _compute_spinor_commitment(self, data: bytes) -> bytes:
        """Calcule le commitment spinoriel"""
        base_hash = hashlib.sha512(data).digest()
        
        spinor_data = np.zeros(64, dtype=complex)
        for cluster in self.clusters:
            states = cluster.get_spinor_states()
            for i, state in enumerate(states.flatten()[:64]):
                spinor_data[i % 64] += state
        
        spinor_bytes = np.abs(spinor_data).astype(np.float32).tobytes()
        
        commitment = hashlib.sha512(base_hash + spinor_bytes).digest()
        
        return commitment
    
    def _build_merkle_tree(self, data: bytes) -> bytes:
        """Construit l'arbre de Merkle"""
        chunk_size = 1024
        chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
        
        if not chunks:
            chunks = [data]
        
        leaves = [hashlib.sha256(chunk).digest() for chunk in chunks]
        
        while len(leaves) > 1:
            if len(leaves) % 2:
                leaves.append(leaves[-1])
            
            new_leaves = []
            for i in range(0, len(leaves), 2):
                combined = hashlib.sha256(leaves[i] + leaves[i+1]).digest()
                new_leaves.append(combined)
            leaves = new_leaves
        
        return leaves[0] if leaves else hashlib.sha256(data).digest()
    
    def verify_seal(self, seal_id: str, document_data: bytes) -> bool:
        """Vérifie un sceau spinorial"""
        if seal_id not in self.seals:
            return False
        
        seal = self.seals[seal_id]
        
        expected_commitment = self._compute_spinor_commitment(document_data)
        if not hmac_compare(seal.spinor_commitment, expected_commitment):
            return False
        
        expected_merkle = self._build_merkle_tree(document_data)
        if not hmac_compare(seal.merkle_root, expected_merkle):
            return False
        
        is_quantum, _ = self.bell_verifier.verify_all_correlations()
        if not is_quantum:
            return False
        
        return True


def create_visual_representation(cluster: HyperCluster) -> Dict[str, Any]:
    """Crée une représentation visuelle 7D pour Blender"""
    objects = []
    
    for i, lancer in enumerate(cluster.lancers):
        spinor = cluster.spinor_states[i] if i < len(cluster.spinor_states) else None
        
        z = 0.0
        if spinor:
            z = (spinor.quaternion[0] ** 2 - spinor.quaternion[3] ** 2) * 2
        
        obj = {
            'type': cluster.die_type.polyhedron,
            'location': (
                lancer.position_x / 256.0,
                lancer.position_y / 256.0,
                z
            ),
            'rotation_quaternion': (
                spinor.quaternion[0] if spinor else 1.0,
                spinor.quaternion[1] if spinor else 0.0,
                spinor.quaternion[2] if spinor else 0.0,
                spinor.quaternion[3] if spinor else 0.0
            ),
            'scale': compute_scale_from_spinor(spinor) if spinor else (1, 1, 1),
            'color_hsv': compute_hsv_from_lancer(lancer),
            'spinor_phase': float(np.angle(spinor.phase)) if spinor else 0.0
        }
        
        objects.append(obj)
    
    return {
        'cluster_name': f"Cluster_{cluster.die_type.name}",
        'objects': objects,
        'entropy': cluster.compute_cluster_entropy(),
        'mean_entanglement': cluster.get_mean_entanglement()
    }


def compute_scale_from_spinor(spinor: SpinorState) -> Tuple[float, float, float]:
    """Calcule l'échelle depuis l'état spinoriel"""
    base = 0.5 + spinor.entanglement_index * 0.5
    
    q = spinor.quaternion
    sx = base * (1 + 0.2 * q[1])
    sy = base * (1 + 0.2 * q[2])
    sz = base * (1 + 0.2 * q[3])
    
    return (float(sx), float(sy), float(sz))


def compute_hsv_from_lancer(lancer: Lancer3D) -> Tuple[float, float, float]:
    """Calcule la couleur HSV depuis un lancer"""
    arr = lancer.to_array()
    
    h = (arr[4] + arr[5] + arr[6]) / 3.0
    s = 0.7 + 0.3 * arr[1]
    v = 0.8 + 0.2 * arr[2]
    
    return (float(h), float(s), float(v))
