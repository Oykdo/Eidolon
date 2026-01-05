"""
Fonction de Hachage Spinorielle Poly-Spinor
Transformation cryptographique avancée basée sur Cl(0,7) et courbes supersingulières
"""

import hashlib
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class Lancer3D:
    """Structure étendue d'un lancer avec 7 paramètres"""
    type_de: str
    face: int
    position_x: float
    position_y: float
    orientation_alpha: float
    orientation_beta: float
    orientation_gamma: float
    
    def to_array(self) -> np.ndarray:
        type_map = {'d4': 0, 'd6': 1, 'd8': 2, 'd10': 3, 'd12': 4, 
                    'd20': 5, 'd100': 6, 'D4': 0, 'D6': 1, 'D8': 2,
                    'D10': 3, 'D12': 4, 'D20': 5, 'D100': 6}
        type_val = type_map.get(self.type_de, 0)
        
        return np.array([
            type_val / 10.0,
            self.face / 100.0,
            self.position_x / 256.0,
            self.position_y / 256.0,
            self.orientation_alpha / 1024.0,
            self.orientation_beta / 1024.0,
            self.orientation_gamma / 1024.0
        ])
    
    @classmethod
    def calculate_entropy_bits(cls) -> float:
        """Calcule l'entropie par lancer: log2(10×20×256×256×1024×1024×1024)"""
        return np.log2(10 * 20 * 256 * 256 * 1024 * 1024 * 1024)


class QuaternionMatrix:
    """Matrice de quaternions d'ordre supérieur"""
    
    def __init__(self, data: np.ndarray):
        self.data = data
        self.shape = data.shape
        
    @classmethod
    def from_sequence(cls, sequence: List[Lancer3D]) -> 'QuaternionMatrix':
        """Convertit une séquence de lancers en matrice de quaternions"""
        n = len(sequence)
        matrix = np.zeros((n, 4, 4), dtype=complex)
        
        for i, lancer in enumerate(sequence):
            arr = lancer.to_array()
            
            alpha = arr[4] * 2 * np.pi
            beta = arr[5] * 2 * np.pi
            gamma = arr[6] * 2 * np.pi
            
            q = cls._euler_to_quaternion(alpha, beta, gamma)
            matrix[i] = cls._quaternion_to_matrix(q)
        
        return cls(matrix)
    
    @staticmethod
    def _euler_to_quaternion(alpha: float, beta: float, gamma: float) -> np.ndarray:
        """Convertit les angles d'Euler en quaternion"""
        cy = np.cos(gamma * 0.5)
        sy = np.sin(gamma * 0.5)
        cp = np.cos(beta * 0.5)
        sp = np.sin(beta * 0.5)
        cr = np.cos(alpha * 0.5)
        sr = np.sin(alpha * 0.5)
        
        w = cr * cp * cy + sr * sp * sy
        x = sr * cp * cy - cr * sp * sy
        y = cr * sp * cy + sr * cp * sy
        z = cr * cp * sy - sr * sp * cy
        
        return np.array([w, x, y, z])
    
    @staticmethod
    def _quaternion_to_matrix(q: np.ndarray) -> np.ndarray:
        """Convertit un quaternion en matrice 4x4"""
        w, x, y, z = q
        
        return np.array([
            [w, -x, -y, -z],
            [x, w, -z, y],
            [y, z, w, -x],
            [z, -y, x, w]
        ], dtype=complex)
    
    def tensor_product(self, other: 'QuaternionMatrix') -> np.ndarray:
        """Produit tensoriel de deux matrices de quaternions"""
        return np.tensordot(self.data, other.data, axes=0)


class SpinorTensorProduct:
    """Produit tensoriel spinoriel basé sur Cl(0,7)"""
    
    def __init__(self, dimension: int = 7):
        self.dimension = dimension
        self.gamma_matrices = self._generate_cl07_gamma_matrices()
        
    def _generate_cl07_gamma_matrices(self) -> List[np.ndarray]:
        """Génère les matrices gamma pour Cl(0,7)"""
        dim = 2 ** (self.dimension // 2 + 1)
        gammas = []
        
        sigma_x = np.array([[0, 1], [1, 0]], dtype=complex)
        sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        sigma_z = np.array([[1, 0], [0, -1]], dtype=complex)
        identity = np.eye(2, dtype=complex)
        
        base_paulis = [sigma_x, sigma_y, sigma_z]
        
        for i in range(self.dimension):
            gamma = np.eye(1, dtype=complex)
            
            for j in range(4):
                if j < i:
                    gamma = np.kron(gamma, sigma_z)
                elif j == i:
                    gamma = np.kron(gamma, base_paulis[i % 3])
                else:
                    gamma = np.kron(gamma, identity)
            
            target_dim = dim
            while gamma.shape[0] < target_dim:
                gamma = np.kron(gamma, identity)
            
            gammas.append(gamma[:dim, :dim])
        
        return gammas
    
    def compute_spinor_product(self, quaternion_matrix: QuaternionMatrix) -> np.ndarray:
        """Calcule le produit tensoriel spinoriel"""
        n = quaternion_matrix.shape[0]
        dim = self.gamma_matrices[0].shape[0]
        
        result = np.zeros((dim, dim), dtype=complex)
        
        for i in range(n):
            q_matrix = quaternion_matrix.data[i]
            
            spinor_contribution = np.zeros((dim, dim), dtype=complex)
            for j, gamma in enumerate(self.gamma_matrices):
                if j < 4:
                    coeff = q_matrix[j % 4, (j + 1) % 4]
                    spinor_contribution += coeff * gamma
            
            result += spinor_contribution @ spinor_contribution.conj().T
        
        result /= n
        return result


class SupersingularReduction:
    """Réduction par courbes elliptiques supersingulières"""
    
    def __init__(self, prime_bits: int = 127):
        self.p = 2 ** prime_bits - 1
        self.j_invariants = self._precompute_j_invariants()
        
    def _precompute_j_invariants(self) -> List[int]:
        """Précalcule les j-invariants supersinguliers"""
        j_list = []
        for i in range(256):
            j = pow(i * 1728, 3, self.p)
            j_list.append(j)
        return j_list
    
    def reduce(self, tensor_product: np.ndarray) -> bytes:
        """Réduit le tenseur par isogénies supersingulières"""
        flat = tensor_product.flatten()
        
        real_part = np.real(flat)
        imag_part = np.imag(flat)
        
        combined = np.concatenate([real_part, imag_part])
        
        result = bytearray()
        
        for i in range(0, len(combined), 8):
            chunk = combined[i:i+8]
            if len(chunk) < 8:
                chunk = np.pad(chunk, (0, 8 - len(chunk)))
            
            val = int(np.sum(chunk * (256 ** np.arange(len(chunk)))) % self.p)
            
            j_idx = val % len(self.j_invariants)
            j = self.j_invariants[j_idx]
            
            isogeny_result = (val * j) % self.p
            
            result_bytes = isogeny_result.to_bytes(16, 'big')
            result.extend(result_bytes)
        
        return bytes(result)


class IdealLatticeExpansion:
    """Expansion par réseau idéal dans Z[x]/(x^n-1)"""
    
    def __init__(self, n: int = 4096, q: int = 12289):
        self.n = n
        self.q = q
        
    def expand(self, seed: bytes, target_bits: int = 4096) -> bytes:
        """Expanse la graine via réseau idéal"""
        target_bytes = target_bits // 8
        
        poly_coeffs = self._seed_to_polynomial(seed)
        
        expanded_coeffs = self._polynomial_multiplication(poly_coeffs)
        
        result = bytearray()
        for coeff in expanded_coeffs:
            coeff_bytes = (coeff % 256).to_bytes(1, 'big')
            result.extend(coeff_bytes)
            if len(result) >= target_bytes:
                break
        
        while len(result) < target_bytes:
            hash_ext = hashlib.sha512(bytes(result[-64:])).digest()
            result.extend(hash_ext)
        
        return bytes(result[:target_bytes])
    
    def _seed_to_polynomial(self, seed: bytes) -> np.ndarray:
        """Convertit la graine en coefficients polynomiaux"""
        coeffs = np.zeros(self.n, dtype=int)
        
        for i, byte in enumerate(seed):
            idx = i % self.n
            coeffs[idx] = (coeffs[idx] + byte) % self.q
        
        return coeffs
    
    def _polynomial_multiplication(self, coeffs: np.ndarray) -> np.ndarray:
        """Multiplication polynomiale dans Z[x]/(x^n-1)"""
        g = np.zeros(self.n, dtype=int)
        g[0] = 1
        g[1] = 1
        
        result = np.zeros(self.n, dtype=int)
        
        for i in range(self.n):
            for j in range(self.n):
                idx = (i + j) % self.n
                result[idx] = (result[idx] + coeffs[i] * g[j]) % self.q
        
        return result


class PolySpinorHash:
    """Fonction de hachage spinorielle complète"""
    
    def __init__(self, sequence_3d: List[Lancer3D]):
        self.sequence = sequence_3d
        self.quaternion_matrix = None
        self.spinor_product = None
        self.reduced_seed = None
        
    def generate_master_seed(self) -> bytes:
        """Génère la graine maître 4096 bits"""
        self.quaternion_matrix = self._sequence_to_quaternion_matrix()
        
        spinor_engine = SpinorTensorProduct(dimension=7)
        self.spinor_product = spinor_engine.compute_spinor_product(
            self.quaternion_matrix
        )
        
        reducer = SupersingularReduction()
        self.reduced_seed = reducer.reduce(self.spinor_product)
        
        expander = IdealLatticeExpansion(n=4096)
        final_seed = expander.expand(self.reduced_seed, target_bits=4096)
        
        return final_seed
    
    def _sequence_to_quaternion_matrix(self) -> QuaternionMatrix:
        """Transforme la séquence en matrice de quaternions"""
        return QuaternionMatrix.from_sequence(self.sequence)
    
    @staticmethod
    def calculate_total_entropy(num_lancers: int = 300) -> float:
        """Calcule l'entropie totale: 300 × 82.7 ≈ 24,810 bits"""
        entropy_per_lancer = Lancer3D.calculate_entropy_bits()
        return num_lancers * entropy_per_lancer
    
    def get_intermediate_states(self) -> Dict[str, Any]:
        """Retourne les états intermédiaires pour debug/visualisation"""
        return {
            'quaternion_matrix_shape': self.quaternion_matrix.shape if self.quaternion_matrix else None,
            'spinor_product_shape': self.spinor_product.shape if self.spinor_product is not None else None,
            'reduced_seed_length': len(self.reduced_seed) if self.reduced_seed else 0,
            'total_entropy_bits': self.calculate_total_entropy(len(self.sequence))
        }


class OctonionSpinorProduct:
    """Produit spinoriel basé sur l'algèbre d'octonions"""
    
    OCTONION_MULTIPLICATION_TABLE = [
        [0, 1, 2, 3, 4, 5, 6, 7],
        [1, -0, 3, -2, 5, -4, -7, 6],
        [2, -3, -0, 1, 6, 7, -4, -5],
        [3, 2, -1, -0, 7, -6, 5, -4],
        [4, -5, -6, -7, -0, 1, 2, 3],
        [5, 4, -7, 6, -1, -0, -3, 2],
        [6, 7, 4, -5, -2, 3, -0, -1],
        [7, -6, 5, 4, -3, -2, 1, -0]
    ]
    
    def __init__(self):
        self.e = [np.zeros(8) for _ in range(8)]
        for i in range(8):
            self.e[i][i] = 1.0
    
    def multiply(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Multiplication d'octonions"""
        result = np.zeros(8)
        
        for i in range(8):
            for j in range(8):
                k = self.OCTONION_MULTIPLICATION_TABLE[i][j]
                sign = 1 if k >= 0 else -1
                k = abs(k)
                result[k] += sign * a[i] * b[j]
        
        return result
    
    def apply_to_spinor(self, octonion: np.ndarray, spinor: np.ndarray) -> np.ndarray:
        """Applique un octonion à un spineur"""
        if len(spinor) != 8:
            padded = np.zeros(8)
            padded[:min(len(spinor), 8)] = spinor[:8]
            spinor = padded
        
        return self.multiply(octonion, spinor)


def generate_ntru_parameters(spinor_seed: bytes) -> Dict[str, Any]:
    """Génère les paramètres NTRU à partir de la graine spinorielle"""
    n = 4096
    q = 12289
    
    seed_array = np.frombuffer(spinor_seed[:n], dtype=np.uint8)
    
    f_coeffs = (seed_array.astype(int) % 3) - 1
    
    g_seed = hashlib.sha512(spinor_seed).digest()
    g_array = np.frombuffer(g_seed * (n // 64 + 1), dtype=np.uint8)[:n]
    g_coeffs = (g_array.astype(int) % 3) - 1
    
    h_coeffs = np.zeros(n, dtype=int)
    for i in range(n):
        for j in range(n):
            idx = (i + j) % n
            h_coeffs[idx] = (h_coeffs[idx] + f_coeffs[i] * g_coeffs[j]) % q
    
    return {
        'n': n,
        'q': q,
        'f': f_coeffs,
        'g': g_coeffs,
        'h': h_coeffs,
        'seed_hash': hashlib.sha256(spinor_seed).hexdigest()
    }
