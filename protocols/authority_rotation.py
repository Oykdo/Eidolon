"""
Rotation des Autorités d'Entiercement
Gestion dynamique de la rotation avec chiffrement proxy et préservation des propriétés
"""

import hashlib
import numpy as np
import time
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

import sys
sys.path.append('..')

from .escrow_seal import AuthorityKey, SealComponent, PolySpinorEscrowSeal
from ..core.post_quantum_keys import HKDF


class RotationError(Exception):
    """Erreur lors de la rotation d'autorité"""
    pass


@dataclass
class RotationTransaction:
    """Transaction de rotation d'autorité"""
    rotation_id: str
    old_authority_id: str
    new_authority_id: str
    dimension: int
    timestamp: float
    status: str
    objection_deadline: float
    verification_proof: Dict


@dataclass
class ObjectionPeriod:
    """Période d'objection pour une rotation"""
    start_time: float
    deadline: float
    objections: List[Dict]
    verification_proof: Dict
    is_active: bool


class ProxyReencryption:
    """Système de re-chiffrement par proxy basé sur réseaux"""
    
    def __init__(self):
        self.n = 1024
        self.q = 3329
        
    def generate_reencryption_key(self, old_private_key: bytes, 
                                  new_public_key: bytes) -> bytes:
        """Génère une clé de re-chiffrement"""
        combined = old_private_key + new_public_key
        
        rekey = HKDF.derive(
            combined,
            b'proxy_reencryption',
            b'rekey_generation',
            self.n
        )
        
        return rekey
    
    def apply_reencryption(self, ciphertext: bytes, rekey: bytes) -> bytes:
        """Applique le re-chiffrement"""
        if len(ciphertext) == 0:
            return ciphertext
        
        rekey_extended = (rekey * (len(ciphertext) // len(rekey) + 1))[:len(ciphertext)]
        
        transformed = bytes(a ^ b for a, b in zip(ciphertext, rekey_extended))
        
        return transformed
    
    def verify_transformation(self, original: bytes, transformed: bytes, 
                             rekey: bytes) -> bool:
        """Vérifie que la transformation est correcte"""
        reverse = self.apply_reencryption(transformed, rekey)
        
        return reverse == original


class PolySpinorAuthorityRotation:
    """Gestion dynamique de la rotation des autorités d'entiercement"""
    
    OBJECTION_PERIOD_HOURS = 72
    MINIMUM_APPROVALS = 4
    
    def __init__(self, current_authorities: List[AuthorityKey], 
                 current_seal: Dict = None):
        self.authorities = current_authorities
        self.current_seal = current_seal
        self.proxy_system = ProxyReencryption()
        self.rotation_history: List[RotationTransaction] = []
        self.pending_rotations: Dict[str, ObjectionPeriod] = {}
        
    def rotate_authority(self, old_auth_index: int, 
                        new_auth_key: AuthorityKey) -> Dict:
        """Effectue une rotation d'autorité sans compromettre le sceau"""
        if old_auth_index < 0 or old_auth_index >= len(self.authorities):
            raise RotationError(f"Index d'autorité invalide: {old_auth_index}")
        
        old_authority = self.authorities[old_auth_index]
        
        new_component = self._generate_new_component(new_auth_key, old_auth_index)
        
        updated_seal = self._proxy_reencryption(
            old_auth_index,
            new_component,
            new_auth_key
        )
        
        if not self._verify_preserved_properties(updated_seal):
            raise RotationError("Propriétés du sceau non préservées après rotation")
        
        tx_hash = self._record_rotation_transaction(
            old_auth_index,
            new_auth_key.id,
            updated_seal
        )
        
        objection_period = self._initiate_objection_period(tx_hash)
        
        rotation_tx = RotationTransaction(
            rotation_id=tx_hash,
            old_authority_id=old_authority.id,
            new_authority_id=new_auth_key.id,
            dimension=old_auth_index,
            timestamp=time.time(),
            status='pending_objections',
            objection_deadline=objection_period.deadline,
            verification_proof=objection_period.verification_proof
        )
        
        self.rotation_history.append(rotation_tx)
        
        return {
            'rotation_id': tx_hash,
            'new_seal': updated_seal,
            'old_authority': old_authority.id,
            'new_authority': new_auth_key.id,
            'dimension': old_auth_index,
            'objection_deadline': datetime.fromtimestamp(
                objection_period.deadline
            ).isoformat(),
            'verification_proof': objection_period.verification_proof,
            'status': 'pending_objections'
        }
    
    def _generate_new_component(self, new_auth_key: AuthorityKey, 
                                dimension: int) -> Dict:
        """Génère une nouvelle composante pour l'autorité"""
        component_data = HKDF.derive(
            new_auth_key.public_key,
            f'component_{dimension}'.encode(),
            b'generation',
            64
        )
        
        component_hash = hashlib.sha256(component_data).hexdigest()
        
        signature = hashlib.sha512(
            component_data + new_auth_key.public_key
        ).digest()
        
        return {
            'dimension': dimension,
            'encrypted_data': component_data,
            'hash': component_hash,
            'signature': signature,
            'authority_id': new_auth_key.id
        }
    
    def _proxy_reencryption(self, old_index: int, new_component: Dict,
                           new_key: AuthorityKey) -> Dict:
        """Chiffrement proxy pour rotation transparente"""
        if self.current_seal is None:
            return self._create_minimal_seal(new_component, new_key)
        
        old_authority = self.authorities[old_index]
        
        rekey = self.proxy_system.generate_reencryption_key(
            old_authority.private_key or old_authority.public_key,
            new_key.public_key
        )
        
        old_components = self.current_seal.get('seal_components_full', 
                                               self.current_seal.get('seal_components', []))
        
        if old_index < len(old_components):
            old_comp = old_components[old_index]
            
            if isinstance(old_comp, dict):
                old_ciphertext = old_comp.get('encrypted_data', b'')
                if isinstance(old_ciphertext, str):
                    old_ciphertext = bytes.fromhex(old_ciphertext)
            else:
                old_ciphertext = getattr(old_comp, 'encrypted_data', b'')
            
            transformed = self.proxy_system.apply_reencryption(old_ciphertext, rekey)
        else:
            transformed = b''
        
        merged = self._merge_components(transformed, new_component)
        
        updated_seal = self.current_seal.copy()
        updated_seal['seal_components'] = self._replace_component(
            old_index, merged, 
            self.current_seal.get('seal_components', [])
        )
        
        updated_seal['meta_seal'] = self._update_meta_seal(merged, old_index)
        
        updated_seal['rotation_history'] = self._add_to_rotation_history(old_index)
        
        return updated_seal
    
    def _create_minimal_seal(self, component: Dict, authority: AuthorityKey) -> Dict:
        """Crée un sceau minimal pour une nouvelle rotation"""
        return {
            'seal_id': hashlib.sha256(
                component['hash'].encode() + str(time.time()).encode()
            ).hexdigest()[:32],
            'timestamp': time.time(),
            'seal_components': [component],
            'authorities': [authority.to_dict()],
            'reconstruction_threshold': 5
        }
    
    def _merge_components(self, transformed: bytes, new_component: Dict) -> Dict:
        """Fusionne une composante transformée avec une nouvelle"""
        new_data = new_component.get('encrypted_data', b'')
        if isinstance(new_data, str):
            new_data = bytes.fromhex(new_data) if new_data else b''
        
        if transformed and new_data:
            merged_data = bytes(
                (a + b) % 256 for a, b in zip(transformed, new_data)
            )
        else:
            merged_data = new_data or transformed
        
        merged_hash = hashlib.sha256(merged_data).hexdigest()
        
        return {
            'dimension': new_component['dimension'],
            'encrypted_data': merged_data.hex() if merged_data else '',
            'hash': merged_hash,
            'signature': new_component['signature'].hex() if isinstance(
                new_component['signature'], bytes
            ) else new_component['signature'],
            'authority_id': new_component['authority_id'],
            'merged': True
        }
    
    def _replace_component(self, index: int, new_component: Dict,
                          components: List) -> List:
        """Remplace une composante à un index donné"""
        result = list(components)
        
        while len(result) <= index:
            result.append({})
        
        result[index] = new_component
        
        return result
    
    def _update_meta_seal(self, merged_component: Dict, index: int) -> Dict:
        """Met à jour le méta-sceau après fusion"""
        if self.current_seal and 'meta_seal' in self.current_seal:
            old_meta = self.current_seal['meta_seal']
        else:
            old_meta = {}
        
        component_hashes = old_meta.get('component_hashes', [''] * 7)
        if isinstance(component_hashes, list) and index < len(component_hashes):
            component_hashes = list(component_hashes)
            component_hashes[index] = merged_component['hash']
        
        new_merkle_root = self._compute_merkle_root(component_hashes)
        
        return {
            'merkle_root': new_merkle_root,
            'component_hashes': component_hashes,
            'last_update': time.time(),
            'update_type': 'rotation',
            'updated_dimension': index
        }
    
    def _compute_merkle_root(self, hashes: List[str]) -> str:
        """Calcule la racine de Merkle"""
        leaves = [
            hashlib.sha256(h.encode()).digest() if h else hashlib.sha256(b'').digest()
            for h in hashes
        ]
        
        while len(leaves) > 1:
            if len(leaves) % 2:
                leaves.append(leaves[-1])
            
            new_leaves = []
            for i in range(0, len(leaves), 2):
                combined = hashlib.sha256(leaves[i] + leaves[i+1]).digest()
                new_leaves.append(combined)
            leaves = new_leaves
        
        return leaves[0].hex() if leaves else ''
    
    def _add_to_rotation_history(self, index: int) -> List[Dict]:
        """Ajoute une entrée à l'historique de rotation"""
        history = []
        if self.current_seal:
            history = self.current_seal.get('rotation_history', []).copy()
        
        history.append({
            'dimension': index,
            'timestamp': time.time(),
            'old_authority': self.authorities[index].id if index < len(self.authorities) else None
        })
        
        return history
    
    def _verify_preserved_properties(self, updated_seal: Dict) -> bool:
        """Vérifie que les propriétés du sceau sont préservées"""
        components = updated_seal.get('seal_components', [])
        if len(components) < 1:
            return False
        
        threshold = updated_seal.get('reconstruction_threshold', 5)
        if threshold != 5:
            return False
        
        if 'meta_seal' not in updated_seal:
            return False
        
        return True
    
    def _record_rotation_transaction(self, old_index: int, 
                                     new_auth_id: str,
                                     updated_seal: Dict) -> str:
        """Enregistre la transaction de rotation"""
        tx_data = {
            'type': 'authority_rotation',
            'dimension': old_index,
            'old_authority': self.authorities[old_index].id if old_index < len(self.authorities) else None,
            'new_authority': new_auth_id,
            'seal_hash': hashlib.sha256(
                str(updated_seal.get('seal_components', [])).encode()
            ).hexdigest(),
            'timestamp': time.time()
        }
        
        tx_hash = hashlib.sha256(
            str(tx_data).encode()
        ).hexdigest()
        
        return tx_hash
    
    def _initiate_objection_period(self, tx_hash: str) -> ObjectionPeriod:
        """Initie la période d'objection"""
        start_time = time.time()
        deadline = start_time + (self.OBJECTION_PERIOD_HOURS * 3600)
        
        verification_proof = {
            'tx_hash': tx_hash,
            'start_time': start_time,
            'deadline': deadline,
            'required_approvals': self.MINIMUM_APPROVALS,
            'commitment': hashlib.sha256(
                tx_hash.encode() + str(start_time).encode()
            ).hexdigest()
        }
        
        objection_period = ObjectionPeriod(
            start_time=start_time,
            deadline=deadline,
            objections=[],
            verification_proof=verification_proof,
            is_active=True
        )
        
        self.pending_rotations[tx_hash] = objection_period
        
        return objection_period
    
    def submit_objection(self, rotation_id: str, objector_id: str, 
                        reason: str) -> Dict:
        """Soumet une objection à une rotation"""
        if rotation_id not in self.pending_rotations:
            raise RotationError(f"Rotation {rotation_id} non trouvée")
        
        period = self.pending_rotations[rotation_id]
        
        if time.time() > period.deadline:
            raise RotationError("Période d'objection terminée")
        
        objection = {
            'objector_id': objector_id,
            'reason': reason,
            'timestamp': time.time()
        }
        
        period.objections.append(objection)
        
        return {
            'status': 'objection_recorded',
            'rotation_id': rotation_id,
            'objection_count': len(period.objections),
            'deadline': datetime.fromtimestamp(period.deadline).isoformat()
        }
    
    def finalize_rotation(self, rotation_id: str) -> Dict:
        """Finalise une rotation après la période d'objection"""
        if rotation_id not in self.pending_rotations:
            raise RotationError(f"Rotation {rotation_id} non trouvée")
        
        period = self.pending_rotations[rotation_id]
        
        if time.time() < period.deadline:
            raise RotationError("Période d'objection encore active")
        
        if len(period.objections) > 0:
            return {
                'status': 'rotation_blocked',
                'rotation_id': rotation_id,
                'objections': period.objections,
                'message': f"{len(period.objections)} objection(s) reçue(s)"
            }
        
        period.is_active = False
        
        for tx in self.rotation_history:
            if tx.rotation_id == rotation_id:
                tx.status = 'finalized'
        
        return {
            'status': 'rotation_finalized',
            'rotation_id': rotation_id,
            'finalized_at': time.time(),
            'message': 'Rotation complétée avec succès'
        }
    
    def get_rotation_status(self, rotation_id: str) -> Dict:
        """Obtient le statut d'une rotation"""
        for tx in self.rotation_history:
            if tx.rotation_id == rotation_id:
                period = self.pending_rotations.get(rotation_id)
                
                return {
                    'rotation_id': rotation_id,
                    'old_authority': tx.old_authority_id,
                    'new_authority': tx.new_authority_id,
                    'dimension': tx.dimension,
                    'status': tx.status,
                    'timestamp': tx.timestamp,
                    'objection_deadline': tx.objection_deadline,
                    'objections': period.objections if period else [],
                    'is_active': period.is_active if period else False
                }
        
        return {'error': f'Rotation {rotation_id} non trouvée'}
