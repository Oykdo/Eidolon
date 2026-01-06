"""
Utilitaires Mathématiques Quantiques Avancés
Opérations sur algèbres de Clifford, spineurs, matrices de densité et helpers quantiques
"""

import numpy as np
import scipy.linalg as la
from typing import Union, Tuple, List, Optional, Dict, Any
import itertools


class CliffordAlgebra:
    """Algèbre de Clifford Cl(p,q) avec focus sur Cl(0,7)"""

    def __init__(self, dimension: int = 7, signature: Tuple[int, int] = (0, 7)):
        self.dimension = dimension
        self.p, self.q = signature
        self.basis_vectors = self._generate_basis()
        self.gamma_matrices = self._generate_gamma_matrices()

    def _generate_basis(self) -> List[np.ndarray]:
        """Génère les vecteurs de base orthonormaux"""
        basis = []
        for i in range(self.dimension):
            vec = np.zeros(self.dimension)
            vec[i] = 1.0
            basis.append(vec)
        return basis

    def _generate_gamma_matrices(self) -> List[np.ndarray]:
        """Génère les matrices gamma pour Cl(0,7)"""
        sigma_x = np.array([[0, 1], [1, 0]], dtype=complex)
        sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        sigma_z = np.array([[1, 0], [0, -1]], dtype=complex)
        identity = np.eye(2, dtype=complex)
        
        gammas = []
        dim = 2 ** ((self.dimension + 1) // 2)
        
        for i in range(self.dimension):
            gamma = np.eye(1, dtype=complex)
            paulis = [sigma_x, sigma_y, sigma_z]
            
            for j in range((self.dimension + 1) // 2):
                if j < i // 2:
                    gamma = np.kron(gamma, sigma_z)
                elif j == i // 2:
                    gamma = np.kron(gamma, paulis[i % 3])
                else:
                    gamma = np.kron(gamma, identity)
            
            while gamma.shape[0] < dim:
                gamma = np.kron(gamma, identity)
            
            gammas.append(gamma[:dim, :dim])
        
        return gammas

    def geometric_product(self, a: np.ndarray, b: np.ndarray) -> Tuple[float, np.ndarray]:
        """Produit géométrique a * b = a·b + a∧b"""
        if len(a.shape) == 1 and len(b.shape) == 1:
            inner = np.dot(a, b)
            outer = self.wedge_product(a, b)
            return inner, outer
        return 0.0, np.zeros_like(a)

    def wedge_product(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Produit extérieur (wedge) a ∧ b"""
        return np.outer(a, b) - np.outer(b, a)

    def rotor(self, plane: Tuple[int, int], angle: float) -> Tuple[float, np.ndarray]:
        """Crée un rotor pour rotation dans un plan"""
        i, j = plane
        if i >= self.dimension or j >= self.dimension:
            raise ValueError("Indices de plan hors limites")

        bivector = self.wedge_product(self.basis_vectors[i], self.basis_vectors[j])
        cos_half = np.cos(angle / 2)
        sin_half = np.sin(angle / 2)
        return cos_half, -sin_half * bivector

    def apply_rotor(self, vector: np.ndarray, rotor: Tuple[float, np.ndarray]) -> np.ndarray:
        """Applique un rotor à un vecteur: R v R†"""
        scalar, bivector = rotor
        
        rotation_matrix = np.eye(self.dimension) * scalar
        rotation_matrix += bivector * (1 - scalar)
        
        return rotation_matrix @ vector


class SpinorMath:
    """Mathématiques des spineurs"""

    @staticmethod
    def create_spinor(dimension: int, state: Optional[np.ndarray] = None) -> np.ndarray:
        """Crée un spineur normalisé"""
        if state is None:
            state = np.random.randn(dimension) + 1j * np.random.randn(dimension)
        state = state / np.linalg.norm(state)
        return state

    @staticmethod
    def spinor_rotation(spinor: np.ndarray, rotation_matrix: np.ndarray) -> np.ndarray:
        """Applique une rotation à un spineur"""
        return rotation_matrix @ spinor

    @staticmethod
    def spinor_inner_product(phi: np.ndarray, psi: np.ndarray) -> complex:
        """Produit interne de Dirac <phi|psi>"""
        result = np.conj(phi).T @ psi
        if np.isscalar(result):
            return complex(float(np.real(result)), float(np.imag(result)))
        return complex(float(np.real(result.item())), float(np.imag(result.item())))

    @staticmethod
    def spinor_norm(spinor: np.ndarray) -> float:
        """Norme du spineur"""
        return float(np.sqrt(np.real(np.conj(spinor).T @ spinor)))

    @staticmethod
    def spinor_to_quaternion(spinor: np.ndarray) -> np.ndarray:
        """Convertit un spineur 2D en quaternion"""
        if len(spinor) >= 4:
            return spinor[:4] / np.linalg.norm(spinor[:4])
        
        a, b = spinor[0], spinor[1] if len(spinor) > 1 else 0
        return np.array([
            np.real(a),
            np.imag(a),
            np.real(b),
            np.imag(b)
        ])

    @staticmethod
    def quaternion_to_rotation_matrix(q: np.ndarray) -> np.ndarray:
        """Convertit un quaternion en matrice de rotation 3x3"""
        w, x, y, z = q / np.linalg.norm(q)
        
        return np.array([
            [1 - 2*(y**2 + z**2), 2*(x*y - z*w), 2*(x*z + y*w)],
            [2*(x*y + z*w), 1 - 2*(x**2 + z**2), 2*(y*z - x*w)],
            [2*(x*z - y*w), 2*(y*z + x*w), 1 - 2*(x**2 + y**2)]
        ])


class DensityMatrix:
    """Opérations sur les matrices de densité"""

    @staticmethod
    def from_state_vector(state: np.ndarray) -> np.ndarray:
        """Crée une matrice de densité depuis un état pur: rho = |psi><psi|"""
        return np.outer(state, np.conj(state))

    @staticmethod
    def trace(rho: np.ndarray) -> complex:
        """Trace de la matrice de densité"""
        return np.trace(rho)

    @staticmethod
    def partial_trace(rho: np.ndarray, subsystem_dims: List[int], 
                      keep_indices: List[int]) -> np.ndarray:
        """Trace partielle sur les sous-systèmes"""
        total_dim = np.prod(subsystem_dims)
        if rho.shape != (total_dim, total_dim):
            raise ValueError("Dimension de matrice de densité incorrecte")

        if len(subsystem_dims) != 2:
            raise NotImplementedError("Trace partielle pour >2 sous-systèmes non implémentée")

        d1, d2 = subsystem_dims
        
        if 0 in keep_indices:
            rho_reduced = np.zeros((d1, d1), dtype=complex)
            for i in range(d1):
                for j in range(d1):
                    for k in range(d2):
                        rho_reduced[i, j] += rho[i*d2 + k, j*d2 + k]
        else:
            rho_reduced = np.zeros((d2, d2), dtype=complex)
            for i in range(d2):
                for j in range(d2):
                    for k in range(d1):
                        rho_reduced[i, j] += rho[k*d2 + i, k*d2 + j]

        return rho_reduced

    @staticmethod
    def purity(rho: np.ndarray) -> float:
        """Pureté Tr(rho^2)"""
        rho_squared = rho @ rho
        return float(np.real(np.trace(rho_squared)))

    @staticmethod
    def fidelity(rho1: np.ndarray, rho2: np.ndarray) -> float:
        """Fidélité entre deux matrices de densité"""
        sqrt_rho1 = la.sqrtm(rho1)
        product = sqrt_rho1 @ rho2 @ sqrt_rho1
        sqrt_product = la.sqrtm(product)
        return float(np.real(np.trace(sqrt_product)) ** 2)

    @staticmethod
    def von_neumann_entropy(rho: np.ndarray) -> float:
        """Entropie de von Neumann S = -Tr(rho log rho)"""
        eigenvals = np.linalg.eigvals(rho)
        eigenvals = eigenvals[np.abs(eigenvals) > 1e-12]
        entropy = -np.sum(np.real(eigenvals * np.log2(eigenvals + 1e-15)))
        return float(entropy)

    @staticmethod
    def concurrence(rho: np.ndarray) -> float:
        """Calcule la concurrence pour un système à 2 qubits"""
        if rho.shape != (4, 4):
            raise ValueError("La concurrence nécessite une matrice 4x4")
        
        sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        sigma_yy = np.kron(sigma_y, sigma_y)
        
        rho_tilde = sigma_yy @ np.conj(rho) @ sigma_yy
        
        R = la.sqrtm(la.sqrtm(rho) @ rho_tilde @ la.sqrtm(rho))
        eigenvals = np.sort(np.real(np.linalg.eigvals(R)))[::-1]
        
        concurrence = max(0, eigenvals[0] - eigenvals[1] - eigenvals[2] - eigenvals[3])
        return float(concurrence)


class QuantumMathHelpers:
    """Helpers mathématiques quantiques"""

    @staticmethod
    def pauli_matrices() -> List[np.ndarray]:
        """Retourne les matrices de Pauli [I, X, Y, Z]"""
        I = np.eye(2, dtype=complex)
        X = np.array([[0, 1], [1, 0]], dtype=complex)
        Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        Z = np.array([[1, 0], [0, -1]], dtype=complex)
        return [I, X, Y, Z]

    @staticmethod
    def generalized_pauli(dim: int) -> List[np.ndarray]:
        """Matrices de Pauli généralisées pour qudits"""
        matrices = [np.eye(dim, dtype=complex)]
        
        omega = np.exp(2j * np.pi / dim)
        X = np.zeros((dim, dim), dtype=complex)
        Z = np.zeros((dim, dim), dtype=complex)

        for i in range(dim):
            X[i, (i+1) % dim] = 1
            Z[i, i] = omega ** i

        matrices.extend([X, Z])
        return matrices

    @staticmethod
    def gell_mann_matrices() -> List[np.ndarray]:
        """Matrices de Gell-Mann (générateurs SU(3))"""
        l1 = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 0]], dtype=complex)
        l2 = np.array([[0, -1j, 0], [1j, 0, 0], [0, 0, 0]], dtype=complex)
        l3 = np.array([[1, 0, 0], [0, -1, 0], [0, 0, 0]], dtype=complex)
        l4 = np.array([[0, 0, 1], [0, 0, 0], [1, 0, 0]], dtype=complex)
        l5 = np.array([[0, 0, -1j], [0, 0, 0], [1j, 0, 0]], dtype=complex)
        l6 = np.array([[0, 0, 0], [0, 0, 1], [0, 1, 0]], dtype=complex)
        l7 = np.array([[0, 0, 0], [0, 0, -1j], [0, 1j, 0]], dtype=complex)
        l8 = np.array([[1, 0, 0], [0, 1, 0], [0, 0, -2]], dtype=complex) / np.sqrt(3)
        
        return [l1, l2, l3, l4, l5, l6, l7, l8]

    @staticmethod
    def is_unitary(matrix: np.ndarray, tol: float = 1e-10) -> bool:
        """Vérifie si une matrice est unitaire"""
        if matrix.shape[0] != matrix.shape[1]:
            return False
        identity = np.eye(matrix.shape[0])
        product = matrix @ matrix.conj().T
        return np.allclose(product, identity, atol=tol)

    @staticmethod
    def is_hermitian(matrix: np.ndarray, tol: float = 1e-10) -> bool:
        """Vérifie si une matrice est hermitienne"""
        return np.allclose(matrix, matrix.conj().T, atol=tol)

    @staticmethod
    def expectation_value(operator: np.ndarray, state: np.ndarray) -> complex:
        """Valeur d'expectation <psi|O|psi>"""
        bra = np.conj(state).T
        result = bra @ operator @ state
        if np.isscalar(result):
            return complex(float(np.real(result)), float(np.imag(result)))
        return complex(float(np.real(result.item())), float(np.imag(result.item())))

    @staticmethod
    def commutator(A: np.ndarray, B: np.ndarray) -> np.ndarray:
        """Commutateur [A, B] = AB - BA"""
        return A @ B - B @ A

    @staticmethod
    def anticommutator(A: np.ndarray, B: np.ndarray) -> np.ndarray:
        """Anticommutateur {A, B} = AB + BA"""
        return A @ B + B @ A

    @staticmethod
    def tensor_product(*matrices: np.ndarray) -> np.ndarray:
        """Produit tensoriel de matrices"""
        result = matrices[0]
        for mat in matrices[1:]:
            result = np.kron(result, mat)
        return result

    @staticmethod
    def random_unitary(dim: int) -> np.ndarray:
        """Génère une matrice unitaire aléatoire (Haar)"""
        random_matrix = np.random.randn(dim, dim) + 1j * np.random.randn(dim, dim)
        Q, R = np.linalg.qr(random_matrix)
        D = np.diag(np.sign(np.diag(R)))
        return Q @ D

    @staticmethod
    def random_density_matrix(dim: int) -> np.ndarray:
        """Génère une matrice de densité aléatoire"""
        A = np.random.randn(dim, dim) + 1j * np.random.randn(dim, dim)
        rho = A @ A.conj().T
        return rho / np.trace(rho)

    @staticmethod
    def bloch_vector(rho: np.ndarray) -> np.ndarray:
        """Extrait le vecteur de Bloch d'une matrice de densité 2x2"""
        if rho.shape != (2, 2):
            raise ValueError("Nécessite une matrice 2x2")
        
        paulis = QuantumMathHelpers.pauli_matrices()
        return np.array([
            np.real(np.trace(rho @ paulis[1])),
            np.real(np.trace(rho @ paulis[2])),
            np.real(np.trace(rho @ paulis[3]))
        ])


def create_clifford_algebra(dimension: int = 7) -> CliffordAlgebra:
    """Crée une instance d'algèbre de Clifford"""
    return CliffordAlgebra(dimension)


def create_spinor(dimension: int) -> np.ndarray:
    """Crée un spineur normalisé aléatoire"""
    return SpinorMath.create_spinor(dimension)


def density_matrix_from_state(state: np.ndarray) -> np.ndarray:
    """Crée une matrice de densité depuis un vecteur d'état"""
    return DensityMatrix.from_state_vector(state)


def pauli_x() -> np.ndarray:
    return QuantumMathHelpers.pauli_matrices()[1]


def pauli_y() -> np.ndarray:
    return QuantumMathHelpers.pauli_matrices()[2]


def pauli_z() -> np.ndarray:
    return QuantumMathHelpers.pauli_matrices()[3]


def bell_state(state_type: str = 'phi_plus') -> np.ndarray:
    """Crée un état de Bell"""
    states = {
        'phi_plus': np.array([1, 0, 0, 1]) / np.sqrt(2),
        'phi_minus': np.array([1, 0, 0, -1]) / np.sqrt(2),
        'psi_plus': np.array([0, 1, 1, 0]) / np.sqrt(2),
        'psi_minus': np.array([0, 1, -1, 0]) / np.sqrt(2)
    }
    return states.get(state_type, states['phi_plus'])


def ghz_state(n_qubits: int) -> np.ndarray:
    """Crée un état GHZ à n qubits"""
    dim = 2 ** n_qubits
    state = np.zeros(dim, dtype=complex)
    state[0] = 1 / np.sqrt(2)
    state[-1] = 1 / np.sqrt(2)
    return state
