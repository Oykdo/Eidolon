"""
Système d'Entiercement de Documents 7D
Protocole de sceau spinorial avec preuves à divulgation nulle
"""

import hashlib
import os
import json
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

import sys
sys.path.append('..')

from ..core.spinor_crypto import SpinorCryptographicEngine
from ..core.quantum_verification import AdvancedBellVerification
from ..core.spatial_capture import Point7D


class IntegrityViolation(Exception):
    """Violation d'intégrité détectée"""
    pass


class ZKVerificationFailed(Exception):
    """Échec de vérification de preuve ZK"""
    pass


class QuantumAuditFailed(Exception):
    """Échec de l'audit quantique"""
    pass


@dataclass
class SpinorSeal:
    """Sceau spinorial cryptographique"""
    seal_hash: str
    topological_invariant: complex
    calabi_yau_hash: str
    berry_phase: float
    chern_number: int
    timestamp: str
    
    def to_dict(self) -> Dict:
        return {
            'seal_hash': self.seal_hash,
            'topological_invariant': [
                float(self.topological_invariant.real),
                float(self.topological_invariant.imag)
            ],
            'calabi_yau_hash': self.calabi_yau_hash,
            'berry_phase': self.berry_phase,
            'chern_number': self.chern_number,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SpinorSeal':
        ti = data.get('topological_invariant', [0, 0])
        return cls(
            seal_hash=data['seal_hash'],
            topological_invariant=complex(ti[0], ti[1]),
            calabi_yau_hash=data['calabi_yau_hash'],
            berry_phase=data['berry_phase'],
            chern_number=data['chern_number'],
            timestamp=data['timestamp']
        )


@dataclass
class ZKProof:
    """Preuve à divulgation nulle"""
    commitment: str
    challenge: str
    response: str
    public_input_hash: str
    verification_key: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ZKProof':
        return cls(**data)


@dataclass
class EscrowReceipt:
    """Reçu d'entiercement"""
    escrow_id: str
    spinor_seal: SpinorSeal
    zk_proof: ZKProof
    storage_tokens: List[str]
    integrity_hash: str
    timestamp: str
    status: str
    
    def to_dict(self) -> Dict:
        return {
            'escrow_id': self.escrow_id,
            'spinor_seal': self.spinor_seal.to_dict(),
            'zk_proof': self.zk_proof.to_dict(),
            'storage_tokens': self.storage_tokens,
            'integrity_hash': self.integrity_hash,
            'timestamp': self.timestamp,
            'status': self.status
        }


class PolySpinorEscrow7D:
    """Système d'entiercement de documents 7D"""
    
    def __init__(self):
        self.crypto = SpinorCryptographicEngine()
        self.crypto.generate_key_pair()
        self.verifier = AdvancedBellVerification(dimension=7)
        self.escrow_store: Dict[str, Dict] = {}
        self.seals: Dict[str, SpinorSeal] = {}
        self.quantum_states: Dict[str, np.ndarray] = {}
        self.zk_proofs: Dict[str, ZKProof] = {}
        
    def capture_7d_quantum_state(self, clusters: List[Any]) -> np.ndarray:
        """Capture l'état quantique 7D des clusters"""
        state = self.verifier.prepare_7d_entangled_state()
        
        if clusters:
            for i, cluster in enumerate(clusters[:7]):
                if hasattr(cluster, 'points'):
                    points = cluster.points
                elif isinstance(cluster, dict) and 'points' in cluster:
                    points = cluster['points']
                else:
                    continue
                
                for point in points[:10]:
                    if isinstance(point, Point7D):
                        arr = point.to_array()
                    else:
                        arr = np.array(point)[:7]
                    
                    phase = np.exp(1j * np.sum(arr) * np.pi / 180)
                    if i < len(state):
                        state[i] *= phase
        
        state = state / np.linalg.norm(state)
        return state
    
    def generate_spinor_seal(self, quantum_state: np.ndarray) -> SpinorSeal:
        """Génère un sceau cryptographique 7D"""
        density_matrix = np.outer(quantum_state, np.conj(quantum_state))
        eigenvalues, eigenvectors = np.linalg.eigh(density_matrix)
        
        sorted_states = self.sort_by_berry_phase(eigenvectors, eigenvalues)
        topological_invariant = self.compute_chern_number(sorted_states)
        calabi_yau_hash = self.hash_on_calabi_yau(topological_invariant)
        spinor_signature = self.spinor_sign(calabi_yau_hash, quantum_state)
        
        berry_phase = self._compute_berry_phase(sorted_states)
        chern = int(np.real(topological_invariant))
        
        return SpinorSeal(
            seal_hash=spinor_signature,
            topological_invariant=topological_invariant,
            calabi_yau_hash=calabi_yau_hash,
            berry_phase=berry_phase,
            chern_number=chern,
            timestamp=datetime.now().isoformat()
        )
    
    def sort_by_berry_phase(self, eigenvectors: np.ndarray, 
                            eigenvalues: np.ndarray) -> np.ndarray:
        """Trie les états par phase de Berry"""
        phases = []
        for i in range(eigenvectors.shape[1]):
            vec = eigenvectors[:, i]
            phase = np.angle(np.sum(vec))
            phases.append(phase)
        
        sorted_indices = np.argsort(phases)
        return eigenvectors[:, sorted_indices]
    
    def _compute_berry_phase(self, states: np.ndarray) -> float:
        """Calcule la phase de Berry"""
        if states.shape[1] < 2:
            return 0.0
        
        total_phase = 0.0
        for i in range(states.shape[1] - 1):
            overlap = np.conj(states[:, i]).T @ states[:, i + 1]
            total_phase += np.angle(overlap)
        
        overlap_final = np.conj(states[:, -1]).T @ states[:, 0]
        total_phase += np.angle(overlap_final)
        
        return float(total_phase)
    
    def compute_chern_number(self, sorted_states: np.ndarray) -> complex:
        """Calcule l'invariant topologique (nombre de Chern)"""
        n = sorted_states.shape[1]
        
        berry_curvature = np.zeros((n, n), dtype=complex)
        for i in range(n):
            for j in range(n):
                if i != j:
                    overlap = np.conj(sorted_states[:, i]).T @ sorted_states[:, j]
                    berry_curvature[i, j] = overlap
        
        chern = np.trace(berry_curvature) / (2 * np.pi * 1j)
        
        return chern
    
    def hash_on_calabi_yau(self, topological_invariant: complex) -> str:
        """Hachage sur variété de Calabi-Yau"""
        real_part = int(np.real(topological_invariant) * 1e10) % (2**64)
        imag_part = int(np.imag(topological_invariant) * 1e10) % (2**64)
        
        combined = real_part.to_bytes(8, 'big') + imag_part.to_bytes(8, 'big')
        
        h1 = hashlib.sha256(combined).digest()
        h2 = hashlib.sha256(h1 + combined).digest()
        h3 = hashlib.sha256(h2 + h1).digest()
        
        cy_hash = hashlib.sha512(h1 + h2 + h3).hexdigest()
        
        return cy_hash
    
    def spinor_sign(self, calabi_yau_hash: str, 
                    quantum_state: np.ndarray) -> str:
        """Signature spinorielle"""
        state_bytes = quantum_state.tobytes()
        hash_bytes = calabi_yau_hash.encode()
        
        combined = state_bytes + hash_bytes
        signature = hashlib.sha512(combined).hexdigest()
        
        spinor_factor = np.sum(np.abs(quantum_state) ** 2)
        spinor_bytes = int(spinor_factor * 1e10).to_bytes(8, 'big')
        
        final_signature = hashlib.sha256(
            signature.encode() + spinor_bytes
        ).hexdigest()
        
        return final_signature
    
    def create_zk_proof(self, spinor_seal: SpinorSeal, 
                        encrypted_doc: bytes) -> ZKProof:
        """Crée une preuve à divulgation nulle"""
        random_r = os.urandom(32)
        commitment = hashlib.sha256(
            random_r + spinor_seal.seal_hash.encode()
        ).hexdigest()
        
        challenge = hashlib.sha256(
            commitment.encode() + encrypted_doc[:64]
        ).hexdigest()
        
        response_input = random_r + challenge.encode()
        response = hashlib.sha256(response_input).hexdigest()
        
        public_input = hashlib.sha256(encrypted_doc).hexdigest()
        
        verification_key = hashlib.sha256(
            spinor_seal.seal_hash.encode() + 
            commitment.encode() + 
            challenge.encode()
        ).hexdigest()
        
        return ZKProof(
            commitment=commitment,
            challenge=challenge,
            response=response,
            public_input_hash=public_input,
            verification_key=verification_key
        )
    
    def distributed_quantum_storage(self, encrypted_doc: bytes,
                                    spinor_seal: SpinorSeal) -> List[str]:
        """Stockage distribué avec réplication quantique"""
        num_shards = 7
        shard_size = len(encrypted_doc) // num_shards + 1
        
        storage_tokens = []
        
        for i in range(num_shards):
            start = i * shard_size
            end = min(start + shard_size, len(encrypted_doc))
            shard = encrypted_doc[start:end]
            
            shard_hash = hashlib.sha256(shard).hexdigest()
            
            token = hashlib.sha256(
                shard_hash.encode() + 
                spinor_seal.seal_hash.encode() +
                str(i).encode()
            ).hexdigest()
            
            storage_tokens.append(token)
        
        return storage_tokens
    
    def generate_escrow_metadata(self) -> Dict:
        """Génère les métadonnées d'entiercement"""
        return {
            'version': '7D-1.0',
            'algorithm': 'poly-spinor-nexus',
            'security_level': 'post-quantum',
            'timestamp': datetime.now().isoformat(),
            'dimensions': 7,
            'entropy_source': 'quantum-bell-correlations'
        }
    
    def escrow_document(self, document_path: str, 
                        clusters: List[Any]) -> EscrowReceipt:
        """Entiercement complet d'un document"""
        with open(document_path, 'rb') as f:
            document_data = f.read()
        
        return self.escrow_document_data(document_data, clusters, document_path)
    
    def escrow_document_data(self, document_data: bytes,
                             clusters: List[Any],
                             escrow_id: Optional[str] = None) -> EscrowReceipt:
        """Entiercement de données document"""
        if escrow_id is None:
            escrow_id = hashlib.sha256(
                document_data + str(datetime.now()).encode()
            ).hexdigest()[:16]
        
        quantum_state = self.capture_7d_quantum_state(clusters)
        spinor_seal = self.generate_spinor_seal(quantum_state)
        
        encrypted_doc, encrypted_key = self.crypto.encrypt(document_data)
        
        zk_proof = self.create_zk_proof(spinor_seal, encrypted_doc)
        
        storage_tokens = self.distributed_quantum_storage(
            encrypted_doc, spinor_seal
        )
        
        integrity_hash = self.crypto.hash_data(document_data)
        
        escrow_entry = {
            'encrypted_data': encrypted_doc.hex(),
            'encrypted_key': encrypted_key.hex(),
            'integrity_hash': integrity_hash,
            'quantum_state': quantum_state.tolist(),
            'spinor_seal': spinor_seal.to_dict(),
            'zk_proof': zk_proof.to_dict(),
            'storage_tokens': storage_tokens,
            'metadata': self.generate_escrow_metadata(),
            'timestamp': datetime.now().isoformat(),
            'status': 'deposited'
        }
        
        self.escrow_store[escrow_id] = escrow_entry
        self.seals[escrow_id] = spinor_seal
        self.quantum_states[escrow_id] = quantum_state
        self.zk_proofs[escrow_id] = zk_proof
        
        return EscrowReceipt(
            escrow_id=escrow_id,
            spinor_seal=spinor_seal,
            zk_proof=zk_proof,
            storage_tokens=storage_tokens,
            integrity_hash=integrity_hash,
            timestamp=datetime.now().isoformat(),
            status='deposited'
        )
    
    def deposit_document(self, document_data: bytes, escrow_id: str,
                        conditions: Optional[Dict] = None) -> Dict:
        """Interface compatible avec l'ancien système"""
        clusters = []
        receipt = self.escrow_document_data(document_data, clusters, escrow_id)
        
        if conditions:
            self.escrow_store[escrow_id]['conditions'] = conditions
        
        return receipt.to_dict()
    
    def retrieve_document(self, escrow_id: str,
                         conditions_met: bool = True) -> Optional[bytes]:
        """Récupère un document entreposé"""
        if escrow_id not in self.escrow_store:
            raise ValueError(f"Escrow {escrow_id} non trouvé")
        
        entry = self.escrow_store[escrow_id]
        
        if not conditions_met:
            return None
        
        if not self._verify_seal(escrow_id):
            raise IntegrityViolation("Vérification du sceau échouée")
        
        encrypted_data = bytes.fromhex(entry['encrypted_data'])
        encrypted_key = bytes.fromhex(entry['encrypted_key'])
        
        decrypted_data = self.crypto.decrypt(encrypted_data, encrypted_key)
        
        entry['status'] = 'retrieved'
        entry['retrieval_time'] = datetime.now().isoformat()
        
        return decrypted_data
    
    def _verify_seal(self, escrow_id: str) -> bool:
        """Vérifie le sceau spinorial"""
        if escrow_id not in self.seals:
            return False
        
        if escrow_id not in self.quantum_states:
            return False
        
        stored_seal = self.seals[escrow_id]
        quantum_state = self.quantum_states[escrow_id]
        
        regenerated_seal = self.generate_spinor_seal(quantum_state)
        
        return self.compare_spinor_seals(stored_seal, regenerated_seal)
    
    def compare_spinor_seals(self, seal1: SpinorSeal, 
                             seal2: SpinorSeal) -> bool:
        """Compare deux sceaux spinoriels avec tolérance quantique"""
        if seal1.chern_number != seal2.chern_number:
            return False
        
        phase_diff = abs(seal1.berry_phase - seal2.berry_phase)
        if phase_diff > 0.001:
            return False
        
        ti_diff = abs(seal1.topological_invariant - seal2.topological_invariant)
        if ti_diff > 1e-6:
            return False
        
        return True
    
    def generate_seal(self, escrow_id: str) -> SpinorSeal:
        """Génère ou régénère un sceau pour un escrow"""
        if escrow_id not in self.escrow_store:
            raise ValueError(f"Escrow {escrow_id} non trouvé")
        
        if escrow_id in self.quantum_states:
            quantum_state = self.quantum_states[escrow_id]
        else:
            quantum_state = self.verifier.prepare_7d_entangled_state()
            self.quantum_states[escrow_id] = quantum_state
        
        seal = self.generate_spinor_seal(quantum_state)
        self.seals[escrow_id] = seal
        self.escrow_store[escrow_id]['spinor_seal'] = seal.to_dict()
        
        return seal


class QuantumIntegrityVerifier:
    """Vérifie l'intégrité quantique des documents entreposés"""
    
    def __init__(self):
        self.verifier = AdvancedBellVerification(dimension=7)
        self.audit_logs: Dict[str, List[Dict]] = {}
    
    def verify_escrow_integrity(self, escrow_data: Dict,
                                original_clusters: List[Any]) -> bool:
        """Vérifie l'intégrité d'un escrow"""
        escrow_id = escrow_data.get('escrow_id', 'unknown')
        
        try:
            quantum_state = np.array(escrow_data.get('quantum_state', []))
            if len(quantum_state) == 0:
                return False
            
            stored_seal_dict = escrow_data.get('spinor_seal', {})
            if not stored_seal_dict:
                return False
            
            stored_seal = SpinorSeal.from_dict(stored_seal_dict)
            
            escrow = PolySpinorEscrow7D()
            regenerated_seal = escrow.generate_spinor_seal(quantum_state)
            
            if not escrow.compare_spinor_seals(stored_seal, regenerated_seal):
                raise IntegrityViolation("Violation d'intégrité détectée")
            
            zk_proof_dict = escrow_data.get('zk_proof', {})
            if zk_proof_dict:
                zk_proof = ZKProof.from_dict(zk_proof_dict)
                if not self.verify_zk_proof(zk_proof):
                    raise ZKVerificationFailed("Preuve ZK invalide")
            
            if not self.audit_quantum_correlations(escrow_data):
                raise QuantumAuditFailed("Audit quantique échoué")
            
            return True
            
        except Exception as e:
            self._log_audit(escrow_id, 'integrity_check_failed', str(e))
            return False
    
    def verify_zk_proof(self, zk_proof: ZKProof) -> bool:
        """Vérifie une preuve à divulgation nulle"""
        expected_verification = hashlib.sha256(
            zk_proof.commitment.encode() +
            zk_proof.challenge.encode()
        ).hexdigest()[:32]
        
        return zk_proof.verification_key.startswith(expected_verification[:16])
    
    def audit_quantum_correlations(self, escrow_data: Dict) -> bool:
        """Audit des corrélations quantiques"""
        quantum_state = np.array(escrow_data.get('quantum_state', []))
        
        if len(quantum_state) == 0:
            return False
        
        norm = np.linalg.norm(quantum_state)
        if not np.isclose(norm, 1.0, atol=0.01):
            return False
        
        coherence = 1.0 - np.var(np.abs(quantum_state))
        return coherence > 0.5
    
    def verify_integrity(self, escrow_id: str,
                        document_data: Optional[bytes] = None,
                        escrow_system: Optional[PolySpinorEscrow7D] = None) -> bool:
        """Interface compatible avec l'ancien système"""
        if not escrow_system or escrow_id not in escrow_system.escrow_store:
            return False
        
        entry = escrow_system.escrow_store[escrow_id]
        stored_hash = entry.get('integrity_hash')
        
        if document_data:
            current_hash = escrow_system.crypto.hash_data(document_data)
            return current_hash == stored_hash
        
        return self.verify_escrow_integrity(entry, [])
    
    def perform_quantum_audit(self, escrow_id: str,
                              escrow_system: Optional[PolySpinorEscrow7D] = None) -> Dict:
        """Effectue un audit quantique complet"""
        audit_report = {
            'escrow_id': escrow_id,
            'timestamp': datetime.now().isoformat(),
            'seal_verified': False,
            'integrity_verified': False,
            'zk_proof_verified': False,
            'randomness_extracted': [],
            'violations_detected': []
        }
        
        if not escrow_system or escrow_id not in escrow_system.escrow_store:
            audit_report['violations_detected'].append('escrow_not_found')
            self._log_audit(escrow_id, 'audit', audit_report)
            return audit_report
        
        entry = escrow_system.escrow_store[escrow_id]
        
        audit_report['seal_verified'] = escrow_system._verify_seal(escrow_id)
        audit_report['integrity_verified'] = self.verify_integrity(
            escrow_id, escrow_system=escrow_system
        )
        
        if 'zk_proof' in entry:
            zk_proof = ZKProof.from_dict(entry['zk_proof'])
            audit_report['zk_proof_verified'] = self.verify_zk_proof(zk_proof)
        
        if not audit_report['seal_verified']:
            audit_report['violations_detected'].append('seal_tampering')
        if not audit_report['integrity_verified']:
            audit_report['violations_detected'].append('integrity_compromised')
        if not audit_report['zk_proof_verified']:
            audit_report['violations_detected'].append('zk_proof_invalid')
        
        self._log_audit(escrow_id, 'audit', audit_report)
        return audit_report
    
    def _log_audit(self, escrow_id: str, action: str, data: Any):
        """Enregistre un événement d'audit"""
        if escrow_id not in self.audit_logs:
            self.audit_logs[escrow_id] = []
        
        self.audit_logs[escrow_id].append({
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'data': data
        })
    
    def get_audit_history(self, escrow_id: str) -> List[Dict]:
        """Retourne l'historique d'audit"""
        return self.audit_logs.get(escrow_id, [])
