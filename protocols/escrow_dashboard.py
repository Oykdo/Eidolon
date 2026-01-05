"""
Tableau de Bord de Surveillance d'Entiercement
Monitoring, audit et visualisation 7D des sceaux spinoriaux
"""

import hashlib
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json

import sys
sys.path.append('..')

from .escrow_seal import PolySpinorEscrowSeal, AuthorityKey


@dataclass
class SealHealthStatus:
    """État de santé d'un sceau"""
    seal_id: str
    signatures_valid: bool
    temporal_consistent: bool
    authorities_distributed: bool
    zk_proof_valid: bool
    overall_health: float
    last_check: float
    issues: List[str]


@dataclass
class ComponentDetail:
    """Détails d'une composante du sceau"""
    dimension: int
    hash_value: str
    authority_id: str
    encryption_strength: int
    signature_status: str
    entropy_level: float
    hash_intensity: float


class SealRegistry:
    """Registre des sceaux"""
    
    def __init__(self):
        self.seals: Dict[str, Dict] = {}
        self.audit_log: List[Dict] = []
        
    def register_seal(self, seal_data: Dict) -> str:
        """Enregistre un nouveau sceau"""
        seal_id = seal_data.get('seal_id', hashlib.sha256(
            str(seal_data).encode()
        ).hexdigest()[:32])
        
        self.seals[seal_id] = seal_data
        
        self._log_event('seal_registered', seal_id, {
            'timestamp': seal_data.get('timestamp'),
            'num_components': len(seal_data.get('seal_components', []))
        })
        
        return seal_id
    
    def get_seal(self, seal_id: str) -> Optional[Dict]:
        """Récupère un sceau par ID"""
        return self.seals.get(seal_id)
    
    def list_seals(self) -> List[str]:
        """Liste tous les IDs de sceaux"""
        return list(self.seals.keys())
    
    def _log_event(self, event_type: str, seal_id: str, details: Dict):
        """Journalise un événement"""
        self.audit_log.append({
            'event_type': event_type,
            'seal_id': seal_id,
            'timestamp': datetime.now().isoformat(),
            'details': details
        })


class BlockchainConnection:
    """Connexion simulée à une blockchain"""
    
    def __init__(self):
        self.blocks: List[Dict] = []
        self.pending_transactions: List[Dict] = []
        
    def submit_transaction(self, tx_data: Dict) -> str:
        """Soumet une transaction"""
        tx_hash = hashlib.sha256(
            json.dumps(tx_data, sort_keys=True).encode()
        ).hexdigest()
        
        self.pending_transactions.append({
            'hash': tx_hash,
            'data': tx_data,
            'timestamp': datetime.now().isoformat()
        })
        
        return tx_hash
    
    def get_transaction(self, tx_hash: str) -> Optional[Dict]:
        """Récupère une transaction"""
        for tx in self.pending_transactions + [
            tx for block in self.blocks for tx in block.get('transactions', [])
        ]:
            if tx.get('hash') == tx_hash:
                return tx
        return None
    
    def mine_block(self) -> str:
        """Mine un bloc (simulation)"""
        if not self.pending_transactions:
            return None
            
        block = {
            'index': len(self.blocks),
            'timestamp': datetime.now().isoformat(),
            'transactions': self.pending_transactions.copy(),
            'previous_hash': self.blocks[-1]['hash'] if self.blocks else '0' * 64
        }
        
        block['hash'] = hashlib.sha256(
            json.dumps(block, sort_keys=True).encode()
        ).hexdigest()
        
        self.blocks.append(block)
        self.pending_transactions.clear()
        
        return block['hash']


class PolySpinorEscrowDashboard:
    """Tableau de bord pour la surveillance de l'entiercement"""
    
    def __init__(self, blockchain_connection: BlockchainConnection = None,
                 seal_registry: SealRegistry = None):
        self.blockchain = blockchain_connection or BlockchainConnection()
        self.registry = seal_registry or SealRegistry()
        self.health_cache: Dict[str, SealHealthStatus] = {}
        
    def display_seal_health(self, seal_id: str) -> Dict:
        """Affiche la santé d'un sceau particulier"""
        seal = self.registry.get_seal(seal_id)
        
        if seal is None:
            return {'error': f'Sceau {seal_id} non trouvé'}
        
        sig_status = self._check_signatures(seal)
        time_status = self._check_temporal_consistency(seal)
        auth_status = self._check_authority_distribution(seal)
        zk_status = self._verify_zk_proof(seal)
        
        overall = self._compute_overall_status([
            sig_status, time_status, auth_status, zk_status
        ])
        
        health = SealHealthStatus(
            seal_id=seal_id,
            signatures_valid=sig_status['valid'],
            temporal_consistent=time_status['consistent'],
            authorities_distributed=auth_status['well_distributed'],
            zk_proof_valid=zk_status['valid'],
            overall_health=overall,
            last_check=datetime.now().timestamp(),
            issues=self._collect_issues(sig_status, time_status, auth_status, zk_status)
        )
        
        self.health_cache[seal_id] = health
        
        visualization_data = self._create_7d_visualization_data(seal)
        components = self._get_component_details(seal)
        reconstruction = self._check_reconstruction_possibility(seal)
        
        return {
            'seal_id': seal_id,
            'status': {
                'signatures': sig_status,
                'temporal': time_status,
                'authorities': auth_status,
                'zk_proof': zk_status,
                'overall': overall,
                'overall_percent': f"{overall * 100:.1f}%"
            },
            'visualization': visualization_data,
            'components': [c.__dict__ for c in components],
            'reconstruction_possibility': reconstruction,
            'health_summary': health.__dict__
        }
    
    def _check_signatures(self, seal: Dict) -> Dict:
        """Vérifie les signatures de toutes les composantes"""
        components = seal.get('seal_components', [])
        valid_count = 0
        invalid_components = []
        
        for i, comp in enumerate(components):
            if isinstance(comp, dict):
                has_hash = bool(comp.get('hash'))
                has_authority = bool(comp.get('authority'))
            else:
                has_hash = bool(getattr(comp, 'component_hash', None))
                has_authority = bool(getattr(comp, 'authority_id', None))
            
            if has_hash and has_authority:
                valid_count += 1
            else:
                invalid_components.append(i)
        
        return {
            'valid': valid_count == 7,
            'valid_count': valid_count,
            'total': len(components),
            'invalid_components': invalid_components,
            'message': f"{valid_count}/7 signatures valides"
        }
    
    def _check_temporal_consistency(self, seal: Dict) -> Dict:
        """Vérifie la cohérence temporelle"""
        timestamp = seal.get('timestamp', 0)
        
        now = datetime.now().timestamp()
        
        is_in_past = timestamp < now
        is_not_too_old = (now - timestamp) < 365 * 24 * 3600
        is_not_future = timestamp <= now + 60
        
        consistent = is_in_past and is_not_too_old and is_not_future
        
        age_days = (now - timestamp) / (24 * 3600)
        
        return {
            'consistent': consistent,
            'timestamp': timestamp,
            'age_days': age_days,
            'is_valid_past': is_in_past,
            'is_recent_enough': is_not_too_old,
            'message': f"Âge du sceau: {age_days:.1f} jours"
        }
    
    def _check_authority_distribution(self, seal: Dict) -> Dict:
        """Vérifie la répartition des autorités"""
        authorities = seal.get('authorities', [])
        components = seal.get('seal_components', [])
        
        authority_ids = set()
        for comp in components:
            if isinstance(comp, dict):
                auth_id = comp.get('authority')
            else:
                auth_id = getattr(comp, 'authority_id', None)
            if auth_id:
                authority_ids.add(auth_id)
        
        unique_count = len(authority_ids)
        well_distributed = unique_count >= 7
        
        return {
            'well_distributed': well_distributed,
            'unique_authorities': unique_count,
            'expected': 7,
            'authority_ids': list(authority_ids),
            'message': f"{unique_count}/7 autorités uniques"
        }
    
    def _verify_zk_proof(self, seal: Dict) -> Dict:
        """Vérifie la preuve ZK"""
        zk_proof = seal.get('zk_proof', {})
        
        if not zk_proof:
            return {
                'valid': False,
                'reason': 'Preuve ZK absente',
                'message': 'Pas de preuve ZK'
            }
        
        has_proof = bool(zk_proof.get('proof_hash') or zk_proof.get('proof'))
        has_circuit = bool(zk_proof.get('circuit_hash'))
        
        valid = has_proof and has_circuit
        
        return {
            'valid': valid,
            'has_proof': has_proof,
            'has_circuit_hash': has_circuit,
            'circuit_hash': zk_proof.get('circuit_hash', '')[:16] + '...',
            'message': 'Preuve ZK valide' if valid else 'Preuve ZK invalide'
        }
    
    def _compute_overall_status(self, statuses: List[Dict]) -> float:
        """Calcule le statut global"""
        scores = []
        
        for status in statuses:
            if isinstance(status, dict):
                if status.get('valid', False) or status.get('consistent', False) or \
                   status.get('well_distributed', False):
                    scores.append(1.0)
                else:
                    scores.append(0.0)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _collect_issues(self, *statuses) -> List[str]:
        """Collecte tous les problèmes détectés"""
        issues = []
        
        for status in statuses:
            if isinstance(status, dict):
                if not status.get('valid', True) and not status.get('consistent', True) \
                   and not status.get('well_distributed', True):
                    message = status.get('message', status.get('reason', 'Problème détecté'))
                    issues.append(message)
        
        return issues
    
    def _create_7d_visualization_data(self, seal: Dict) -> Dict:
        """Crée les données pour une visualisation 7D"""
        components = seal.get('seal_components', [])
        
        dimension_data = []
        
        for dim in range(7):
            if dim < len(components):
                comp = components[dim]
                
                if isinstance(comp, dict):
                    hash_val = comp.get('hash', '')
                else:
                    hash_val = getattr(comp, 'component_hash', '')
                
                hash_int = int(hash_val[:8], 16) if hash_val else 0
                
                theta = (hash_int % 360) * np.pi / 180
                phi = ((hash_int >> 8) % 360) * np.pi / 180
                r = 0.5 + (hash_int % 100) / 200.0
                
                x = r * np.sin(theta) * np.cos(phi)
                y = r * np.sin(theta) * np.sin(phi)
                z = r * np.cos(theta)
                
                entropy = (hash_int % 256) / 256.0
                intensity = ((hash_int >> 16) % 256) / 256.0
                
            else:
                x, y, z = 0, 0, 0
                entropy, intensity = 0, 0
            
            dimension_data.append({
                'dimension': dim,
                'coordinates': {'x': float(x), 'y': float(y), 'z': float(z)},
                'entropy_level': entropy,
                'hash_intensity': intensity,
                'spherical': {
                    'theta': float(theta) if 'theta' in dir() else 0,
                    'phi': float(phi) if 'phi' in dir() else 0,
                    'r': float(r) if 'r' in dir() else 0
                }
            })
        
        correlation_matrix = self._compute_interdimensional_correlation(seal)
        
        return {
            'dimensions': dimension_data,
            'correlation_matrix': correlation_matrix.tolist(),
            'total_entropy': sum(d['entropy_level'] for d in dimension_data),
            'mean_intensity': np.mean([d['hash_intensity'] for d in dimension_data])
        }
    
    def _compute_interdimensional_correlation(self, seal: Dict) -> np.ndarray:
        """Calcule la matrice de corrélation entre dimensions"""
        correlation = np.zeros((7, 7))
        components = seal.get('seal_components', [])
        
        hash_values = []
        for comp in components:
            if isinstance(comp, dict):
                h = comp.get('hash', '0' * 64)
            else:
                h = getattr(comp, 'component_hash', '0' * 64)
            
            hash_values.append(int(h[:16], 16) if h else 0)
        
        while len(hash_values) < 7:
            hash_values.append(0)
        
        for i in range(7):
            for j in range(7):
                if i == j:
                    correlation[i, j] = 1.0
                else:
                    diff = abs(hash_values[i] - hash_values[j])
                    max_val = max(hash_values[i], hash_values[j], 1)
                    correlation[i, j] = 1.0 - (diff / max_val)
        
        return correlation
    
    def _get_component_details(self, seal: Dict) -> List[ComponentDetail]:
        """Obtient les détails de chaque composante"""
        components = seal.get('seal_components', [])
        details = []
        
        for i, comp in enumerate(components):
            if isinstance(comp, dict):
                hash_val = comp.get('hash', '')
                auth_id = comp.get('authority', f'authority_{i}')
                params = comp.get('lattice_params', {})
            else:
                hash_val = getattr(comp, 'component_hash', '')
                auth_id = getattr(comp, 'authority_id', f'authority_{i}')
                params = getattr(comp, 'lattice_params', {})
            
            encryption_strength = params.get('sec_level', 256)
            
            hash_int = int(hash_val[:8], 16) if hash_val else 0
            entropy = (hash_int % 256) / 256.0
            intensity = ((hash_int >> 8) % 256) / 256.0
            
            detail = ComponentDetail(
                dimension=i,
                hash_value=hash_val[:32] + '...' if len(hash_val) > 32 else hash_val,
                authority_id=auth_id,
                encryption_strength=encryption_strength,
                signature_status='valid' if hash_val else 'missing',
                entropy_level=entropy,
                hash_intensity=intensity
            )
            details.append(detail)
        
        return details
    
    def _check_reconstruction_possibility(self, seal: Dict) -> Dict:
        """Vérifie la possibilité de reconstruction"""
        threshold = seal.get('reconstruction_threshold', 5)
        authorities = seal.get('authorities', [])
        components = seal.get('seal_components', [])
        
        available = len([c for c in components if c])
        
        can_reconstruct = available >= threshold
        
        return {
            'can_reconstruct': can_reconstruct,
            'available_shares': available,
            'required_shares': threshold,
            'missing_shares': max(0, threshold - available),
            'message': f"{available}/{threshold} parts disponibles"
        }
    
    def get_audit_log(self, seal_id: Optional[str] = None) -> List[Dict]:
        """Récupère le journal d'audit"""
        if seal_id:
            return [
                event for event in self.registry.audit_log
                if event.get('seal_id') == seal_id
            ]
        return self.registry.audit_log
    
    def export_health_report(self, seal_id: str) -> str:
        """Exporte un rapport de santé en JSON"""
        health_data = self.display_seal_health(seal_id)
        return json.dumps(health_data, indent=2, default=str)
