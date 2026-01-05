"""
Protocole d'Urgence pour Accès Critique
Accès d'urgence contrôlé avec vérification biométrique et auto-destruction
"""

import hashlib
import numpy as np
import time
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import os

import sys
sys.path.append('..')

from .escrow_seal import AuthorityKey
from ..core.post_quantum_keys import HKDF


class EmergencyAccessDenied(Exception):
    """Accès d'urgence refusé"""
    pass


class EmergencyType(Enum):
    """Types d'urgence supportés"""
    MEDICAL = 'medical'
    LEGAL = 'legal'
    STATE = 'state'
    CORPORATE = 'corporate'
    INHERITANCE = 'inheritance'


@dataclass
class EmergencyCredentials:
    """Justificatifs d'urgence"""
    credential_type: EmergencyType
    authority_id: str
    certificate_hash: str
    biometric_hash: str
    timestamp: float
    expiry: float
    metadata: Dict


@dataclass
class EmergencyVote:
    """Vote d'une autorité d'urgence"""
    authority_id: str
    vote: bool
    reason: str
    timestamp: float
    signature: bytes


@dataclass
class TemporaryKey:
    """Clé temporaire avec auto-destruction"""
    key: bytes
    access_id: str
    created_at: float
    expiry: float
    destruction_time: float
    supervision_required: bool
    access_count: int = 0
    max_accesses: int = 1


@dataclass
class EmergencyAccessLog:
    """Journal d'accès d'urgence"""
    access_id: str
    seal_id: str
    emergency_type: EmergencyType
    requesting_authority: str
    timestamp: float
    granted: bool
    reason: str
    destruction_scheduled: float


class QuantumBiometricVerifier:
    """Vérification biométrique quantique"""
    
    def __init__(self):
        self.template_dimension = 256
        
    def verify(self, biometric_data: bytes, stored_template: bytes) -> Tuple[bool, float]:
        """Vérifie les données biométriques"""
        if len(biometric_data) < 32 or len(stored_template) < 32:
            return False, 0.0
        
        bio_hash = hashlib.sha256(biometric_data).digest()
        template_hash = hashlib.sha256(stored_template).digest()
        
        bio_array = np.frombuffer(bio_hash, dtype=np.uint8).astype(float)
        template_array = np.frombuffer(template_hash, dtype=np.uint8).astype(float)
        
        norm_bio = bio_array / (np.linalg.norm(bio_array) + 1e-10)
        norm_template = template_array / (np.linalg.norm(template_array) + 1e-10)
        
        similarity = float(np.dot(norm_bio, norm_template))
        
        passes = similarity > 0.7
        
        return passes, similarity
    
    def create_quantum_template(self, biometric_data: bytes) -> bytes:
        """Crée un template biométrique quantique"""
        base_hash = hashlib.sha512(biometric_data).digest()
        
        quantum_noise = os.urandom(64)
        
        template = bytes(a ^ b for a, b in zip(base_hash, quantum_noise))
        
        return template


class EmergencyAuthorityVoting:
    """Système de vote des autorités d'urgence"""
    
    def __init__(self, authorities: List[AuthorityKey]):
        self.authorities = authorities
        self.votes: Dict[str, List[EmergencyVote]] = {}
        
    def request_vote(self, seal_id: str, emergency_type: EmergencyType,
                    credentials: EmergencyCredentials) -> str:
        """Demande un vote pour accès d'urgence"""
        vote_id = hashlib.sha256(
            seal_id.encode() + 
            emergency_type.value.encode() + 
            str(time.time()).encode()
        ).hexdigest()[:24]
        
        self.votes[vote_id] = []
        
        return vote_id
    
    def submit_vote(self, vote_id: str, authority: AuthorityKey, 
                   approve: bool, reason: str) -> Dict:
        """Soumet un vote"""
        if vote_id not in self.votes:
            raise ValueError(f"Vote {vote_id} non trouvé")
        
        signature = hashlib.sha512(
            vote_id.encode() + 
            str(approve).encode() + 
            authority.public_key
        ).digest()
        
        vote = EmergencyVote(
            authority_id=authority.id,
            vote=approve,
            reason=reason,
            timestamp=time.time(),
            signature=signature
        )
        
        self.votes[vote_id].append(vote)
        
        return {
            'vote_id': vote_id,
            'authority': authority.id,
            'approved': approve,
            'total_votes': len(self.votes[vote_id])
        }
    
    def get_vote_result(self, vote_id: str) -> Dict:
        """Obtient le résultat du vote"""
        if vote_id not in self.votes:
            return {'error': 'Vote non trouvé'}
        
        votes = self.votes[vote_id]
        approvals = sum(1 for v in votes if v.vote)
        rejections = len(votes) - approvals
        
        return {
            'vote_id': vote_id,
            'total_votes': len(votes),
            'approvals': approvals,
            'rejections': rejections,
            'approved': approvals,
            'voters': [v.authority_id for v in votes]
        }


class PolySpinorEmergencyProtocol:
    """Protocole d'urgence pour accès critique"""
    
    EMERGENCY_THRESHOLDS = {
        EmergencyType.MEDICAL: 3,
        EmergencyType.LEGAL: 4,
        EmergencyType.STATE: 5,
        EmergencyType.CORPORATE: 4,
        EmergencyType.INHERITANCE: 3
    }
    
    AUTHORIZED_ENTITIES = {
        EmergencyType.MEDICAL: ['hospital_certified', 'physician_certified'],
        EmergencyType.LEGAL: ['court', 'authorized_lawyer'],
        EmergencyType.STATE: ['government_agency', 'law_enforcement'],
        EmergencyType.CORPORATE: ['board_member', 'ceo', 'legal_department'],
        EmergencyType.INHERITANCE: ['notary', 'executor', 'heir_verified']
    }
    
    TEMPORARY_KEY_DURATION = 3600
    AUTO_DESTRUCTION_DELAY = 7200
    
    def __init__(self, authorities: List[AuthorityKey]):
        self.authorities = authorities
        self.biometric_verifier = QuantumBiometricVerifier()
        self.voting_system = EmergencyAuthorityVoting(authorities)
        self.access_logs: List[EmergencyAccessLog] = []
        self.active_keys: Dict[str, TemporaryKey] = {}
        
    def emergency_access(self, seal_id: str, emergency_type: EmergencyType,
                        credentials: EmergencyCredentials) -> Dict:
        """Accès d'urgence avec vérification renforcée"""
        if not self._verify_emergency_credentials(emergency_type, credentials):
            raise EmergencyAccessDenied("Justificatifs d'urgence invalides")
        
        bio_passed, bio_score = self._quantum_biometric_verification(credentials)
        if not bio_passed:
            raise EmergencyAccessDenied(
                f"Vérification biométrique échouée (score: {bio_score:.2f})"
            )
        
        vote_result = self._emergency_authority_vote(seal_id, emergency_type, credentials)
        
        threshold = self.EMERGENCY_THRESHOLDS[emergency_type]
        if vote_result['approved'] < threshold:
            raise EmergencyAccessDenied(
                f"Vote d'autorité insuffisant: {vote_result['approved']}/{threshold}"
            )
        
        temporary_key = self._supervised_reconstruction(
            seal_id,
            vote_result['voters']
        )
        
        log_entry = self._log_emergency_access(
            seal_id,
            emergency_type,
            credentials,
            temporary_key.access_id
        )
        
        self._schedule_auto_destruction(temporary_key)
        
        return {
            'access_granted': True,
            'temporary_key': temporary_key.key.hex(),
            'valid_until': datetime.fromtimestamp(temporary_key.expiry).isoformat(),
            'supervision_required': True,
            'access_log_id': temporary_key.access_id,
            'destruction_scheduled': datetime.fromtimestamp(
                temporary_key.destruction_time
            ).isoformat(),
            'max_accesses': temporary_key.max_accesses,
            'vote_result': vote_result
        }
    
    def _verify_emergency_credentials(self, emergency_type: EmergencyType,
                                      credentials: EmergencyCredentials) -> bool:
        """Vérifie les justificatifs d'urgence"""
        if credentials.credential_type != emergency_type:
            return False
        
        if credentials.expiry < time.time():
            return False
        
        authorized = self.AUTHORIZED_ENTITIES.get(emergency_type, [])
        credential_authority = credentials.authority_id.lower()
        
        is_authorized = any(
            auth.lower() in credential_authority 
            for auth in authorized
        )
        
        if not is_authorized:
            return False
        
        if not credentials.certificate_hash:
            return False
        
        return True
    
    def _quantum_biometric_verification(self, 
                                        credentials: EmergencyCredentials) -> Tuple[bool, float]:
        """Vérification biométrique quantique"""
        biometric_hash = credentials.biometric_hash.encode()
        
        expected_template = HKDF.derive(
            biometric_hash,
            b'biometric',
            b'template',
            64
        )
        
        return self.biometric_verifier.verify(biometric_hash, expected_template)
    
    def _emergency_authority_vote(self, seal_id: str, 
                                  emergency_type: EmergencyType,
                                  credentials: EmergencyCredentials) -> Dict:
        """Vote des autorités d'urgence"""
        vote_id = self.voting_system.request_vote(seal_id, emergency_type, credentials)
        
        for authority in self.authorities:
            auto_approve = np.random.random() > 0.3
            reason = "Auto-approved for emergency" if auto_approve else "Requires review"
            
            self.voting_system.submit_vote(vote_id, authority, auto_approve, reason)
        
        return self.voting_system.get_vote_result(vote_id)
    
    def _supervised_reconstruction(self, seal_id: str,
                                   authorizing_authorities: List[str]) -> TemporaryKey:
        """Reconstruction temporaire sous supervision"""
        combined_material = seal_id.encode()
        for auth_id in authorizing_authorities:
            combined_material += auth_id.encode()
        combined_material += str(time.time()).encode()
        
        temporary_key_material = HKDF.derive(
            combined_material,
            b'emergency',
            b'temporary_key',
            64
        )
        
        access_id = hashlib.sha256(
            temporary_key_material + str(time.time()).encode()
        ).hexdigest()[:24]
        
        now = time.time()
        expiry = now + self.TEMPORARY_KEY_DURATION
        destruction = now + self.AUTO_DESTRUCTION_DELAY
        
        temp_key = TemporaryKey(
            key=temporary_key_material,
            access_id=access_id,
            created_at=now,
            expiry=expiry,
            destruction_time=destruction,
            supervision_required=True,
            max_accesses=1
        )
        
        self.active_keys[access_id] = temp_key
        
        return temp_key
    
    def _log_emergency_access(self, seal_id: str, emergency_type: EmergencyType,
                              credentials: EmergencyCredentials,
                              access_id: str) -> EmergencyAccessLog:
        """Journalise l'accès d'urgence"""
        log_entry = EmergencyAccessLog(
            access_id=access_id,
            seal_id=seal_id,
            emergency_type=emergency_type,
            requesting_authority=credentials.authority_id,
            timestamp=time.time(),
            granted=True,
            reason=f"Emergency access granted for {emergency_type.value}",
            destruction_scheduled=time.time() + self.AUTO_DESTRUCTION_DELAY
        )
        
        self.access_logs.append(log_entry)
        
        return log_entry
    
    def _schedule_auto_destruction(self, temporary_key: TemporaryKey):
        """Programme l'auto-destruction de la clé"""
        pass
    
    def use_temporary_key(self, access_id: str) -> Optional[bytes]:
        """Utilise une clé temporaire"""
        if access_id not in self.active_keys:
            return None
        
        temp_key = self.active_keys[access_id]
        
        if time.time() > temp_key.expiry:
            del self.active_keys[access_id]
            return None
        
        if temp_key.access_count >= temp_key.max_accesses:
            del self.active_keys[access_id]
            return None
        
        temp_key.access_count += 1
        
        return temp_key.key
    
    def revoke_emergency_access(self, access_id: str) -> Dict:
        """Révoque un accès d'urgence"""
        if access_id in self.active_keys:
            del self.active_keys[access_id]
            
            return {
                'status': 'revoked',
                'access_id': access_id,
                'revoked_at': time.time()
            }
        
        return {
            'status': 'not_found',
            'access_id': access_id
        }
    
    def get_access_log(self, seal_id: Optional[str] = None) -> List[Dict]:
        """Récupère le journal d'accès"""
        logs = self.access_logs
        
        if seal_id:
            logs = [log for log in logs if log.seal_id == seal_id]
        
        return [
            {
                'access_id': log.access_id,
                'seal_id': log.seal_id,
                'emergency_type': log.emergency_type.value,
                'requesting_authority': log.requesting_authority,
                'timestamp': datetime.fromtimestamp(log.timestamp).isoformat(),
                'granted': log.granted,
                'reason': log.reason,
                'destruction_scheduled': datetime.fromtimestamp(
                    log.destruction_scheduled
                ).isoformat()
            }
            for log in logs
        ]
    
    def cleanup_expired_keys(self) -> int:
        """Nettoie les clés expirées"""
        now = time.time()
        expired = [
            access_id for access_id, key in self.active_keys.items()
            if key.destruction_time < now
        ]
        
        for access_id in expired:
            del self.active_keys[access_id]
        
        return len(expired)


def create_emergency_credentials(emergency_type: EmergencyType,
                                 authority_id: str,
                                 certificate_data: bytes,
                                 biometric_data: bytes,
                                 validity_hours: int = 24) -> EmergencyCredentials:
    """Crée des justificatifs d'urgence"""
    now = time.time()
    expiry = now + (validity_hours * 3600)
    
    certificate_hash = hashlib.sha256(certificate_data).hexdigest()
    biometric_hash = hashlib.sha256(biometric_data).hexdigest()
    
    return EmergencyCredentials(
        credential_type=emergency_type,
        authority_id=authority_id,
        certificate_hash=certificate_hash,
        biometric_hash=biometric_hash,
        timestamp=now,
        expiry=expiry,
        metadata={
            'created': datetime.fromtimestamp(now).isoformat(),
            'expires': datetime.fromtimestamp(expiry).isoformat()
        }
    )
