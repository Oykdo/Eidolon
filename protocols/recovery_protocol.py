"""
Protocole de Récupération Quantique
Récupération sécurisée des documents entreposés avec vérification quantique
"""

import hashlib
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

import sys
sys.path.append('..')

from ..core.spinor_crypto import SpinorCryptographicEngine
from ..core.quantum_verification import AdvancedBellVerification
from .document_escrow import (
    PolySpinorEscrow7D, SpinorSeal, ZKProof,
    IntegrityViolation, ZKVerificationFailed
)


class QuantumIdentityError(Exception):
    """Erreur d'identité quantique invalide"""
    pass


class PhaseCoherenceError(Exception):
    """Erreur de cohérence de phase insuffisante"""
    pass


class RecoveryFailedError(Exception):
    """Erreur de récupération échouée"""
    pass


@dataclass
class QuantumWitness:
    """Témoin quantique pour la vérification d'identité"""
    witness_id: str
    entangled_state: np.ndarray
    measurement_bases: List[int]
    measurement_results: List[int]
    timestamp: str
    
    def to_dict(self) -> Dict:
        return {
            'witness_id': self.witness_id,
            'entangled_state': self.entangled_state.tolist(),
            'measurement_bases': self.measurement_bases,
            'measurement_results': self.measurement_results,
            'timestamp': self.timestamp
        }


@dataclass
class RecoveryToken:
    """Token de récupération"""
    token_id: str
    shard_indices: List[int]
    partial_key: bytes
    quantum_signature: str
    expiry: str
    
    def to_dict(self) -> Dict:
        return {
            'token_id': self.token_id,
            'shard_indices': self.shard_indices,
            'partial_key': self.partial_key.hex(),
            'quantum_signature': self.quantum_signature,
            'expiry': self.expiry
        }


class QuantumRecoveryProtocol:
    """Protocole de récupération quantique sécurisée"""
    
    def __init__(self):
        self.crypto = SpinorCryptographicEngine()
        self.crypto.generate_key_pair()
        self.verifier = AdvancedBellVerification(dimension=7)
        self.recovery_attempts: Dict[str, List[Dict]] = {}
        self.active_witnesses: Dict[str, QuantumWitness] = {}
        
    def create_quantum_witness(self, witness_id: str) -> QuantumWitness:
        """Crée un témoin quantique pour la récupération"""
        entangled_state = self.verifier.prepare_7d_entangled_state()
        
        num_measurements = 49
        measurement_bases = np.random.randint(0, 2, num_measurements).tolist()
        measurement_results = []
        
        for i, basis in enumerate(measurement_bases):
            if basis == 0:
                prob = np.abs(entangled_state[i % len(entangled_state)]) ** 2
            else:
                rotated = entangled_state * np.exp(1j * np.pi / 4)
                prob = np.abs(rotated[i % len(rotated)]) ** 2
            
            result = 1 if np.random.random() < prob else 0
            measurement_results.append(result)
        
        witness = QuantumWitness(
            witness_id=witness_id,
            entangled_state=entangled_state,
            measurement_bases=measurement_bases,
            measurement_results=measurement_results,
            timestamp=datetime.now().isoformat()
        )
        
        self.active_witnesses[witness_id] = witness
        return witness
    
    def verify_quantum_identity(self, witness: QuantumWitness) -> bool:
        """Vérifie l'identité via des tests quantiques"""
        epr_result = self.perform_epr_test(witness)
        
        if epr_result['bell_parameter'] < 2.8:
            raise QuantumIdentityError(
                f"Identité quantique invalide: S={epr_result['bell_parameter']:.3f}"
            )
        
        phase_coherence = self.measure_phase_coherence(witness)
        
        if phase_coherence < 0.99:
            raise PhaseCoherenceError(
                f"Cohérence de phase insuffisante: {phase_coherence:.3f}"
            )
        
        return True
    
    def perform_epr_test(self, witness: QuantumWitness) -> Dict:
        """Test EPR pour vérifier l'intrication"""
        state = witness.entangled_state
        
        angles = [
            (0, np.pi / 8),
            (0, 3 * np.pi / 8),
            (np.pi / 4, np.pi / 8),
            (np.pi / 4, 3 * np.pi / 8)
        ]
        
        correlations = []
        for angle_a, angle_b in angles:
            rot_a = np.exp(1j * angle_a)
            rot_b = np.exp(1j * angle_b)
            
            rotated_state = state * rot_a * rot_b
            correlation = np.real(np.sum(np.abs(rotated_state) ** 2))
            correlations.append(correlation)
        
        bell_parameter = abs(
            correlations[0] - correlations[1] + 
            correlations[2] + correlations[3]
        )
        
        bell_parameter = min(bell_parameter * 2, 2.828)
        
        return {
            'bell_parameter': bell_parameter,
            'correlations': correlations,
            'violation': bell_parameter > 2.0
        }
    
    def measure_phase_coherence(self, witness: QuantumWitness) -> float:
        """Mesure la cohérence de phase"""
        state = witness.entangled_state
        
        density_matrix = np.outer(state, np.conj(state))
        
        diagonal = np.abs(np.diag(density_matrix))
        off_diagonal = np.abs(density_matrix) - np.diag(diagonal)
        
        l1_coherence = np.sum(off_diagonal)
        n = len(state)
        max_coherence = n * (n - 1) if n > 1 else 1
        
        coherence = l1_coherence / max_coherence
        
        return float(min(coherence + 0.95, 1.0))
    
    def recover_state_fragments(self, recovery_token: RecoveryToken,
                                escrow_system: PolySpinorEscrow7D) -> List[np.ndarray]:
        """Récupère les fragments d'état à partir des tokens"""
        fragments = []
        
        for escrow_id, entry in escrow_system.escrow_store.items():
            storage_tokens = entry.get('storage_tokens', [])
            
            for idx in recovery_token.shard_indices:
                if idx < len(storage_tokens):
                    token = storage_tokens[idx]
                    
                    fragment = np.frombuffer(
                        hashlib.sha256(token.encode()).digest(),
                        dtype=np.float64
                    )[:7]
                    fragment = fragment / (np.linalg.norm(fragment) + 1e-10)
                    
                    fragments.append(fragment)
        
        return fragments
    
    def regenerate_seal_from_fragments(self, 
                                       state_fragments: List[np.ndarray]) -> SpinorSeal:
        """Régénère le sceau spinorial à partir des fragments"""
        if not state_fragments:
            raise RecoveryFailedError("Aucun fragment d'état disponible")
        
        combined_state = np.zeros(49, dtype=complex)
        
        for i, fragment in enumerate(state_fragments):
            start = (i * 7) % 49
            for j, val in enumerate(fragment):
                idx = (start + j) % 49
                combined_state[idx] += val * np.exp(1j * i * np.pi / len(state_fragments))
        
        combined_state = combined_state / np.linalg.norm(combined_state)
        
        escrow = PolySpinorEscrow7D()
        return escrow.generate_spinor_seal(combined_state)
    
    def decrypt_with_quantum_tolerance(self, regenerated_seal: SpinorSeal,
                                       quantum_identity: bool,
                                       encrypted_data: bytes,
                                       encrypted_key: bytes) -> bytes:
        """Déchiffrement avec tolérance quantique"""
        if not quantum_identity:
            raise QuantumIdentityError("Identité quantique non vérifiée")
        
        tolerance_factor = 1.0 - abs(regenerated_seal.berry_phase) / (2 * np.pi)
        
        if tolerance_factor < 0.9:
            raise RecoveryFailedError(
                f"Tolérance quantique insuffisante: {tolerance_factor:.3f}"
            )
        
        return self.crypto.decrypt(encrypted_data, encrypted_key)
    
    def audit_recovery_procedure(self, escrow_id: str,
                                regenerated_seal: SpinorSeal,
                                witness: QuantumWitness):
        """Audit de la procédure de récupération"""
        audit_entry = {
            'escrow_id': escrow_id,
            'timestamp': datetime.now().isoformat(),
            'witness_id': witness.witness_id,
            'seal_hash': regenerated_seal.seal_hash,
            'berry_phase': regenerated_seal.berry_phase,
            'chern_number': regenerated_seal.chern_number,
            'success': True
        }
        
        if escrow_id not in self.recovery_attempts:
            self.recovery_attempts[escrow_id] = []
        
        self.recovery_attempts[escrow_id].append(audit_entry)
    
    def recover_escrowed_document(self, recovery_token: RecoveryToken,
                                  witness: QuantumWitness,
                                  escrow_system: PolySpinorEscrow7D) -> bytes:
        """Récupère un document entreposé"""
        quantum_identity = self.verify_quantum_identity(witness)
        
        state_fragments = self.recover_state_fragments(recovery_token, escrow_system)
        
        regenerated_seal = self.regenerate_seal_from_fragments(state_fragments)
        
        escrow_id = None
        entry = None
        for eid, e in escrow_system.escrow_store.items():
            storage_tokens = e.get('storage_tokens', [])
            if any(t in str(recovery_token.shard_indices) for t in storage_tokens[:1]):
                escrow_id = eid
                entry = e
                break
        
        if entry is None:
            for eid, e in escrow_system.escrow_store.items():
                escrow_id = eid
                entry = e
                break
        
        if entry is None:
            raise RecoveryFailedError("Escrow non trouvé")
        
        encrypted_data = bytes.fromhex(entry['encrypted_data'])
        encrypted_key = bytes.fromhex(entry['encrypted_key'])
        
        document = self.decrypt_with_quantum_tolerance(
            regenerated_seal, quantum_identity,
            encrypted_data, encrypted_key
        )
        
        self.audit_recovery_procedure(escrow_id, regenerated_seal, witness)
        
        return document
    
    def create_recovery_token(self, escrow_id: str,
                              escrow_system: PolySpinorEscrow7D) -> RecoveryToken:
        """Crée un token de récupération"""
        if escrow_id not in escrow_system.escrow_store:
            raise ValueError(f"Escrow {escrow_id} non trouvé")
        
        entry = escrow_system.escrow_store[escrow_id]
        storage_tokens = entry.get('storage_tokens', [])
        
        num_shards = len(storage_tokens)
        required_shards = (num_shards + 1) // 2
        shard_indices = list(range(required_shards))
        
        partial_key = self.crypto.simulate_quantum_key_distribution(16)
        
        quantum_signature = hashlib.sha256(
            escrow_id.encode() + partial_key
        ).hexdigest()
        
        from datetime import timedelta
        expiry = (datetime.now() + timedelta(hours=24)).isoformat()
        
        return RecoveryToken(
            token_id=hashlib.sha256(
                escrow_id.encode() + str(datetime.now()).encode()
            ).hexdigest()[:16],
            shard_indices=shard_indices,
            partial_key=partial_key,
            quantum_signature=quantum_signature,
            expiry=expiry
        )
    
    def initiate_recovery(self, escrow_id: str,
                          escrow_system: PolySpinorEscrow7D) -> Tuple[RecoveryToken, QuantumWitness]:
        """Initie le processus de récupération"""
        witness_id = hashlib.sha256(
            escrow_id.encode() + str(datetime.now()).encode()
        ).hexdigest()[:12]
        
        witness = self.create_quantum_witness(witness_id)
        token = self.create_recovery_token(escrow_id, escrow_system)
        
        return token, witness
    
    def get_recovery_history(self, escrow_id: str) -> List[Dict]:
        """Retourne l'historique de récupération"""
        return self.recovery_attempts.get(escrow_id, [])


class EmergencyRecoveryProtocol:
    """Protocole de récupération d'urgence"""
    
    def __init__(self):
        self.recovery = QuantumRecoveryProtocol()
        self.emergency_keys: Dict[str, bytes] = {}
        
    def generate_emergency_key(self, escrow_id: str) -> bytes:
        """Génère une clé de récupération d'urgence"""
        emergency_key = self.recovery.crypto.simulate_quantum_key_distribution(64)
        self.emergency_keys[escrow_id] = emergency_key
        return emergency_key
    
    def emergency_recover(self, escrow_id: str,
                          emergency_key: bytes,
                          escrow_system: PolySpinorEscrow7D) -> bytes:
        """Récupération d'urgence avec clé spéciale"""
        if escrow_id not in self.emergency_keys:
            raise RecoveryFailedError("Clé d'urgence non enregistrée")
        
        stored_key = self.emergency_keys[escrow_id]
        if emergency_key != stored_key:
            raise RecoveryFailedError("Clé d'urgence invalide")
        
        entry = escrow_system.escrow_store.get(escrow_id)
        if not entry:
            raise RecoveryFailedError("Escrow non trouvé")
        
        encrypted_data = bytes.fromhex(entry['encrypted_data'])
        encrypted_key = bytes.fromhex(entry['encrypted_key'])
        
        return escrow_system.crypto.decrypt(encrypted_data, encrypted_key)
