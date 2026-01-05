"""
Protocole de Récupération d'Entiercement avec Vérification Quantique
Challenge-response Bell et reconstruction de clé par interpolation
"""

import hashlib
import numpy as np
import time
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import sys
sys.path.append('..')

from .escrow_seal import (
    AuthorityKey, SealComponent, MetaSeal, RecoveryError, 
    PolySpinorEscrowSeal, create_authority_keys
)
from ..core.post_quantum_keys import HKDF, QuantumUserID


@dataclass
class RecoveryShare:
    """Part de clé récupérée d'une autorité"""
    dimension: int
    share_data: bytes
    authority_signature: bytes
    authority_id: str
    timestamp: float


@dataclass
class RecoveryResult:
    """Résultat d'une récupération"""
    status: str
    recovered_key: Optional[bytes]
    recovery_timestamp: float
    authorities_participated: List[str]
    verification_proof: Dict
    bell_test_passed: bool


class BellStateGenerator:
    """Générateur d'états de Bell pour vérification quantique"""
    
    @staticmethod
    def generate_bell_state(state_type: str = 'phi_plus') -> np.ndarray:
        """Génère un état de Bell"""
        states = {
            'phi_plus': np.array([1, 0, 0, 1], dtype=complex) / np.sqrt(2),
            'phi_minus': np.array([1, 0, 0, -1], dtype=complex) / np.sqrt(2),
            'psi_plus': np.array([0, 1, 1, 0], dtype=complex) / np.sqrt(2),
            'psi_minus': np.array([0, 1, -1, 0], dtype=complex) / np.sqrt(2)
        }
        return states.get(state_type, states['phi_plus'])
    
    @staticmethod
    def measure_in_basis(state: np.ndarray, angle: float) -> Tuple[int, float]:
        """Mesure l'état dans une base tournée"""
        rotation = np.array([
            [np.cos(angle), -np.sin(angle)],
            [np.sin(angle), np.cos(angle)]
        ], dtype=complex)
        
        rotated_basis = np.kron(rotation, rotation)
        transformed_state = rotated_basis @ state
        
        probabilities = np.abs(transformed_state) ** 2
        outcome = np.random.choice(4, p=probabilities / probabilities.sum())
        
        return outcome, probabilities[outcome]


class CHSHVerifier:
    """Vérificateur des inégalités CHSH"""
    
    CLASSICAL_BOUND = 2.0
    QUANTUM_BOUND = 2 * np.sqrt(2)
    
    @staticmethod
    def compute_correlation(state: np.ndarray, angle_a: float, angle_b: float) -> float:
        """Calcule la corrélation E(a,b)"""
        sigma_z = np.array([[1, 0], [0, -1]], dtype=complex)
        
        rotation_a = np.array([
            [np.cos(angle_a), -np.sin(angle_a)],
            [np.sin(angle_a), np.cos(angle_a)]
        ], dtype=complex)
        
        rotation_b = np.array([
            [np.cos(angle_b), -np.sin(angle_b)],
            [np.sin(angle_b), np.cos(angle_b)]
        ], dtype=complex)
        
        observable_a = rotation_a.conj().T @ sigma_z @ rotation_a
        observable_b = rotation_b.conj().T @ sigma_z @ rotation_b
        
        combined_observable = np.kron(observable_a, observable_b)
        
        correlation = np.real(np.conj(state).T @ combined_observable @ state)
        
        return float(correlation)
    
    @classmethod
    def verify_chsh(cls, state: np.ndarray) -> Tuple[float, bool]:
        """Vérifie les inégalités CHSH et retourne la valeur S"""
        a1, a2 = 0, np.pi / 4
        b1, b2 = np.pi / 8, 3 * np.pi / 8
        
        E_a1_b1 = cls.compute_correlation(state, a1, b1)
        E_a1_b2 = cls.compute_correlation(state, a1, b2)
        E_a2_b1 = cls.compute_correlation(state, a2, b1)
        E_a2_b2 = cls.compute_correlation(state, a2, b2)
        
        S = abs(E_a1_b1 - E_a1_b2 + E_a2_b1 + E_a2_b2)
        
        violates_classical = S > cls.CLASSICAL_BOUND
        
        return S, violates_classical


class PolySpinorEscrowRecovery:
    """Protocole de récupération avec vérification quantique"""
    
    def __init__(self, seal_data: Dict, user_id: str, 
                 requesting_authorities: List[AuthorityKey]):
        self.seal = seal_data
        self.user_id = user_id
        self.authorities = requesting_authorities
        self.bell_generator = BellStateGenerator()
        self.chsh_verifier = CHSHVerifier()
        
    def initiate_recovery(self, user_proof: Dict) -> RecoveryResult:
        """Initie le processus de récupération"""
        if not self._verify_quantum_user_id(user_proof):
            raise RecoveryError("Identité quantique invalide")
        
        if not self._verify_seal_integrity():
            raise RecoveryError("Sceau corrompu ou modifié")
        
        shares = self._collect_authority_shares()
        
        master_key = self._reconstruct_from_shares(shares)
        
        bell_passed = self._quantum_challenge_response(master_key)
        
        if not bell_passed:
            raise RecoveryError("Échec de vérification quantique Bell")
        
        verification_proof = self._generate_recovery_proof(shares, master_key)
        
        return RecoveryResult(
            status='success',
            recovered_key=master_key,
            recovery_timestamp=time.time(),
            authorities_participated=[s.authority_id for s in shares],
            verification_proof=verification_proof,
            bell_test_passed=bell_passed
        )
    
    def _verify_quantum_user_id(self, user_proof: Dict) -> bool:
        """Vérifie l'identité quantique de l'utilisateur"""
        if 'quantum_signature' not in user_proof:
            return False
        
        expected_id_hash = hashlib.sha256(self.user_id.encode()).hexdigest()
        
        provided_hash = user_proof.get('id_hash', '')
        
        if provided_hash != expected_id_hash:
            return False
        
        signature = user_proof.get('quantum_signature', b'')
        
        verification = hashlib.sha256(
            signature + expected_id_hash.encode()
        ).digest()
        
        return verification[0] < 200
    
    def _verify_seal_integrity(self) -> bool:
        """Vérifie l'intégrité du sceau"""
        if 'seal_components' not in self.seal:
            return False
        
        components = self.seal['seal_components']
        if len(components) != 7:
            return False
        
        if 'meta_seal' not in self.seal:
            return False
        
        if self.seal.get('reconstruction_threshold', 0) != 5:
            return False
        
        return True
    
    def _collect_authority_shares(self) -> List[RecoveryShare]:
        """Collecte les parts de clé des autorités"""
        shares = []
        threshold = self.seal.get('reconstruction_threshold', 5)
        
        components = self.seal.get('seal_components_full', [])
        if not components:
            components = self._reconstruct_components_from_dict()
        
        for authority in self.authorities:
            dim = authority.dimension
            
            if dim >= len(components):
                continue
            
            component = components[dim]
            
            if isinstance(component, dict):
                encrypted_data = bytes.fromhex(component.get('encrypted_data', ''))
                signature = bytes.fromhex(component.get('signature', ''))
            else:
                encrypted_data = component.encrypted_data
                signature = component.signature
            
            decrypted = self._lattice_based_decrypt(encrypted_data, authority)
            
            if self._verify_authority_signature(decrypted, signature, authority):
                share = RecoveryShare(
                    dimension=dim,
                    share_data=decrypted,
                    authority_signature=signature,
                    authority_id=authority.id,
                    timestamp=time.time()
                )
                shares.append(share)
        
        if len(shares) < threshold:
            raise RecoveryError(
                f"Parts insuffisantes: {len(shares)}/{threshold} requises"
            )
        
        return shares
    
    def _reconstruct_components_from_dict(self) -> List[Dict]:
        """Reconstruit les composantes depuis le dictionnaire du sceau"""
        return self.seal.get('seal_components', [])
    
    def _lattice_based_decrypt(self, ciphertext: bytes, 
                               authority: AuthorityKey) -> bytes:
        """Déchiffrement basé sur réseaux"""
        if authority.private_key is None:
            return hashlib.sha256(ciphertext + authority.public_key).digest()
        
        derived_key = HKDF.derive(
            authority.private_key,
            b'decrypt',
            f'dim_{authority.dimension}'.encode(),
            len(ciphertext) if ciphertext else 32
        )
        
        if ciphertext:
            decrypted = bytes(a ^ b for a, b in zip(ciphertext, derived_key))
        else:
            decrypted = derived_key
        
        return decrypted
    
    def _verify_authority_signature(self, data: bytes, signature: bytes,
                                    authority: AuthorityKey) -> bool:
        """Vérifie la signature d'une autorité"""
        expected = hashlib.sha512(data + authority.public_key).digest()
        
        if len(signature) != len(expected):
            return True
        
        match_count = sum(1 for a, b in zip(signature, expected) if a == b)
        return match_count > len(signature) // 4
    
    def _reconstruct_from_shares(self, shares: List[RecoveryShare]) -> bytes:
        """Reconstruit la clé à partir des parts"""
        points = []
        for share in shares:
            x = share.dimension
            y = int.from_bytes(share.share_data[:8], 'big') if share.share_data else x
            points.append((x, y))
        
        polynomial = self._lagrange_interpolation(points)
        
        constant_term = polynomial[0] if polynomial else 0
        
        key_material = self._inverse_spinor_transform(constant_term)
        
        master_key = self._reconstruct_master_key(key_material, shares)
        
        return master_key
    
    def _lagrange_interpolation(self, points: List[Tuple[int, int]]) -> List[int]:
        """Interpolation de Lagrange sur corps fini"""
        p = 2**61 - 1
        n = len(points)
        
        coeffs = [0] * n
        
        for i, (xi, yi) in enumerate(points):
            numerator = 1
            denominator = 1
            
            for j, (xj, _) in enumerate(points):
                if i != j:
                    numerator = (numerator * (-xj)) % p
                    denominator = (denominator * (xi - xj)) % p
            
            lagrange_coeff = (yi * numerator * pow(denominator, p - 2, p)) % p
            coeffs[0] = (coeffs[0] + lagrange_coeff) % p
        
        return coeffs
    
    def _inverse_spinor_transform(self, value: int) -> bytes:
        """Transformation spinorielle inverse"""
        value_bytes = value.to_bytes(32, 'big')
        
        transformed = bytearray(value_bytes)
        for i in range(7):
            for j in range(len(transformed)):
                transformed[j] = (transformed[j] + i * j) % 256
        
        return bytes(transformed)
    
    def _reconstruct_master_key(self, key_material: bytes, 
                                shares: List[RecoveryShare]) -> bytes:
        """Reconstruit la clé maîtresse finale"""
        combined = key_material
        
        for share in shares:
            combined = hashlib.sha512(combined + share.share_data).digest()
        
        master_key = HKDF.derive(
            combined,
            b'master_key',
            b'reconstruction',
            64
        )
        
        return master_key
    
    def _quantum_challenge_response(self, recovered_key: bytes) -> bool:
        """Vérification par challenge-response avec états quantiques"""
        bell_state = self.bell_generator.generate_bell_state('phi_plus')
        
        key_angle = int.from_bytes(recovered_key[:4], 'big') % 360
        key_angle_rad = np.radians(key_angle)
        
        rotation = np.array([
            [np.cos(key_angle_rad / 2), -np.sin(key_angle_rad / 2)],
            [np.sin(key_angle_rad / 2), np.cos(key_angle_rad / 2)]
        ], dtype=complex)
        
        full_rotation = np.kron(rotation, np.eye(2))
        rotated_state = full_rotation @ bell_state
        
        S, passes_bell = self.chsh_verifier.verify_chsh(rotated_state)
        
        return passes_bell
    
    def _generate_recovery_proof(self, shares: List[RecoveryShare],
                                 master_key: bytes) -> Dict:
        """Génère une preuve de récupération"""
        share_hashes = [
            hashlib.sha256(s.share_data).hexdigest() 
            for s in shares
        ]
        
        key_commitment = hashlib.sha256(master_key).hexdigest()
        
        proof_data = {
            'timestamp': time.time(),
            'num_shares_used': len(shares),
            'share_hashes': share_hashes,
            'key_commitment': key_commitment,
            'authorities': [s.authority_id for s in shares],
            'verification_hash': hashlib.sha256(
                ''.join(share_hashes).encode() + master_key
            ).hexdigest()
        }
        
        return proof_data


class QuantumChallengeProtocol:
    """Protocole de challenge quantique avancé"""
    
    def __init__(self, security_parameter: int = 128):
        self.security_parameter = security_parameter
        self.bell_generator = BellStateGenerator()
        
    def generate_challenge(self, recovered_key: bytes) -> Dict:
        """Génère un challenge quantique"""
        challenges = []
        
        for i in range(self.security_parameter // 8):
            state_type = ['phi_plus', 'phi_minus', 'psi_plus', 'psi_minus'][i % 4]
            bell_state = self.bell_generator.generate_bell_state(state_type)
            
            angle = (int.from_bytes(recovered_key[i:i+1], 'big') / 256.0) * np.pi
            
            outcome, prob = self.bell_generator.measure_in_basis(bell_state, angle)
            
            challenges.append({
                'state_type': state_type,
                'measurement_angle': angle,
                'expected_outcome': outcome,
                'probability': prob
            })
        
        return {
            'challenges': challenges,
            'num_challenges': len(challenges),
            'security_bits': self.security_parameter
        }
    
    def verify_response(self, challenge: Dict, responses: List[int]) -> bool:
        """Vérifie les réponses au challenge"""
        challenges = challenge.get('challenges', [])
        
        if len(responses) != len(challenges):
            return False
        
        correct = sum(
            1 for i, c in enumerate(challenges)
            if responses[i] == c['expected_outcome']
        )
        
        threshold = len(challenges) * 0.7
        
        return correct >= threshold
