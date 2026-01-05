"""
Extracteur d'Empreintes Matérielles Uniques
Signature cryptographique basée sur les propriétés physiques des matériaux
"""

import hashlib
import numpy as np
import json
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .material_database import MaterialProperties, PolyhedronMaterialDatabase
from .physics_engine import Trajectory, PolyhedronPhysicsEngine


@dataclass
class MaterialFingerprint:
    """Empreinte matérielle cryptographique"""
    static_hash: str
    interaction_hash: str
    dynamic_signature: str
    composite_fingerprint: str
    timestamp: str
    metadata: Dict
    
    def to_dict(self) -> Dict:
        return {
            'static_hash': self.static_hash,
            'interaction_hash': self.interaction_hash,
            'dynamic_signature': self.dynamic_signature,
            'composite_fingerprint': self.composite_fingerprint,
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }
    
    def verify(self, other: 'MaterialFingerprint', tolerance: float = 0.001) -> Tuple[bool, float]:
        """Vérifie si deux empreintes correspondent"""
        if self.static_hash != other.static_hash:
            return False, 0.0
        
        # Comparaison des signatures dynamiques
        similarity = MaterialFingerprintExtractor.compare_dynamic_signatures(
            self.dynamic_signature, other.dynamic_signature
        )
        
        return similarity > (1 - tolerance), similarity


class MaterialFingerprintExtractor:
    """Extrait une empreinte unique basée sur les propriétés matérielles"""
    
    def __init__(self, material_db: Optional[PolyhedronMaterialDatabase] = None):
        self.material_db = material_db or PolyhedronMaterialDatabase()
    
    def extract_from_simulation_results(self, 
                                        simulation_results: List[Dict]) -> MaterialFingerprint:
        """Extrait une empreinte des résultats de simulation"""
        
        # 1. Collecte des données matérielles statiques
        material_data = self._collect_material_data(simulation_results)
        static_hash = self._hash_static_properties(material_data)
        
        # 2. Calcul de la matrice d'interactions
        interaction_matrix = self._calculate_material_interactions(material_data)
        interaction_hash = self._hash_interaction_matrix(interaction_matrix)
        
        # 3. Signature dynamique des trajectoires
        dynamic_signature = self._extract_dynamic_signature(simulation_results)
        
        # 4. Combinaison en empreinte finale
        composite = self._combine_fingerprints(
            static_hash, interaction_hash, dynamic_signature
        )
        
        return MaterialFingerprint(
            static_hash=static_hash,
            interaction_hash=interaction_hash,
            dynamic_signature=dynamic_signature,
            composite_fingerprint=composite,
            timestamp=datetime.now().isoformat(),
            metadata={
                'num_simulations': len(simulation_results),
                'materials_used': [d.get('material_name', 'unknown') for d in material_data]
            }
        )
    
    def _collect_material_data(self, simulation_results: List[Dict]) -> List[Dict]:
        """Collecte les données matérielles de chaque simulation"""
        material_data = []
        
        for i, sim in enumerate(simulation_results):
            material_entry = {
                'index': i,
                'material_name': sim.get('material', {}).get('name', f'material_{i}'),
                'density': sim.get('material', {}).get('density', 1000),
                'elasticity': sim.get('material', {}).get('elasticity', 0.5),
                'friction': sim.get('material', {}).get('friction', 0.4),
                'roughness': sim.get('material', {}).get('roughness', 0.1),
                'final_face': sim.get('final_face', 1),
                'energy_loss': sim.get('material_specific_data', {}).get('energy_loss_profile', 0),
                'simulation_hash': sim.get('simulation_hash', '')
            }
            material_data.append(material_entry)
        
        return material_data
    
    def _hash_static_properties(self, material_data: List[Dict]) -> str:
        """Hash des propriétés statiques"""
        # Trier pour garantir la reproductibilité
        sorted_data = sorted(material_data, key=lambda x: x['index'])
        
        # Créer une représentation canonique
        canonical = []
        for entry in sorted_data:
            canonical.append({
                'density': round(entry['density'], 2),
                'elasticity': round(entry['elasticity'], 4),
                'friction': round(entry['friction'], 4),
                'roughness': round(entry['roughness'], 4)
            })
        
        data_str = json.dumps(canonical, sort_keys=True)
        return hashlib.sha3_512(data_str.encode()).hexdigest()
    
    def _calculate_material_interactions(self, material_data: List[Dict]) -> np.ndarray:
        """Calcule la matrice d'interactions entre matériaux"""
        n = len(material_data)
        interaction_matrix = np.zeros((n, n, 4))
        
        for i in range(n):
            for j in range(i + 1, n):
                mi = material_data[i]
                mj = material_data[j]
                
                # 1. Ratio de densité
                density_ratio = mi['density'] / (mj['density'] + 1e-10)
                
                # 2. Compatibilité élastique
                elasticity_compat = 1 - abs(mi['elasticity'] - mj['elasticity'])
                
                # 3. Coefficient de restitution effectif
                restitution = np.sqrt(mi['elasticity'] * mj['elasticity'])
                
                # 4. Transfert d'énergie (basé sur les pertes)
                energy_transfer = abs(mi['energy_loss'] - mj['energy_loss']) / \
                                 (max(mi['energy_loss'], mj['energy_loss']) + 1e-10)
                
                interaction_matrix[i, j] = [
                    density_ratio, elasticity_compat, restitution, energy_transfer
                ]
                interaction_matrix[j, i] = interaction_matrix[i, j]
        
        return interaction_matrix
    
    def _hash_interaction_matrix(self, matrix: np.ndarray) -> str:
        """Hash de la matrice d'interactions"""
        # Quantification pour tolérance aux erreurs numériques
        quantized = np.round(matrix * 10000).astype(np.int32)
        return hashlib.sha3_512(quantized.tobytes()).hexdigest()
    
    def _extract_dynamic_signature(self, simulation_results: List[Dict]) -> str:
        """Extrait une signature des comportements dynamiques"""
        signature_parts = []
        
        for sim in simulation_results:
            trajectory = sim.get('trajectory')
            
            if trajectory and hasattr(trajectory, 'collisions'):
                # Nombre de collisions
                num_collisions = len(trajectory.collisions)
                
                # Énergie totale perdue
                total_energy = trajectory.total_energy_loss()
                
                # Position finale
                final_state = trajectory.get_final_state()
                if final_state:
                    final_pos = tuple(np.round(final_state.position, 4))
                else:
                    final_pos = (0, 0, 0)
                
                signature_parts.append(f"{num_collisions}:{total_energy:.4f}:{final_pos}")
            else:
                # Signature basée sur les données disponibles
                face = sim.get('final_face', 0)
                energy = sim.get('material_specific_data', {}).get('energy_loss_profile', 0)
                signature_parts.append(f"{face}:{energy:.4f}")
        
        combined = '|'.join(signature_parts)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _combine_fingerprints(self, static: str, interactions: str, 
                              dynamic: str) -> str:
        """Combine les signatures en empreinte finale via arbre de Merkle"""
        leaves = [
            hashlib.sha3_512(static.encode()).digest(),
            hashlib.sha3_512(interactions.encode()).digest(),
            hashlib.sha3_512(dynamic.encode()).digest()
        ]
        
        # Construction de l'arbre
        while len(leaves) > 1:
            new_leaves = []
            for i in range(0, len(leaves), 2):
                if i + 1 < len(leaves):
                    combined = hashlib.sha3_512(leaves[i] + leaves[i + 1]).digest()
                else:
                    combined = leaves[i]
                new_leaves.append(combined)
            leaves = new_leaves
        
        return leaves[0].hex()
    
    @staticmethod
    def compare_dynamic_signatures(sig1: str, sig2: str) -> float:
        """Compare deux signatures dynamiques"""
        if sig1 == sig2:
            return 1.0
        
        # Distance de Hamming normalisée
        bytes1 = bytes.fromhex(sig1)
        bytes2 = bytes.fromhex(sig2)
        
        if len(bytes1) != len(bytes2):
            return 0.0
        
        diff_bits = sum(bin(b1 ^ b2).count('1') for b1, b2 in zip(bytes1, bytes2))
        total_bits = len(bytes1) * 8
        
        return 1 - (diff_bits / total_bits)
    
    def verify_fingerprint(self, fingerprint: MaterialFingerprint,
                          simulation_results: List[Dict]) -> Tuple[bool, float]:
        """Vérifie une empreinte contre des résultats de simulation"""
        # Recalculer l'empreinte
        new_fingerprint = self.extract_from_simulation_results(simulation_results)
        
        # Comparer
        return fingerprint.verify(new_fingerprint)


class MaterialSignatureAnalyzer:
    """Analyse et valide les signatures matérielles"""
    
    def __init__(self):
        self.extractor = MaterialFingerprintExtractor()
    
    def analyze_material_uniqueness(self, 
                                    fingerprints: List[MaterialFingerprint]) -> Dict:
        """Analyse l'unicité d'un ensemble d'empreintes"""
        n = len(fingerprints)
        similarity_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i + 1, n):
                _, similarity = fingerprints[i].verify(fingerprints[j])
                similarity_matrix[i, j] = similarity
                similarity_matrix[j, i] = similarity
        
        # Statistiques
        off_diag = similarity_matrix[np.triu_indices(n, k=1)]
        
        return {
            'num_fingerprints': n,
            'mean_similarity': float(np.mean(off_diag)) if len(off_diag) > 0 else 0,
            'max_similarity': float(np.max(off_diag)) if len(off_diag) > 0 else 0,
            'min_similarity': float(np.min(off_diag)) if len(off_diag) > 0 else 0,
            'std_similarity': float(np.std(off_diag)) if len(off_diag) > 0 else 0,
            'all_unique': bool(np.max(off_diag) < 0.99) if len(off_diag) > 0 else True
        }
    
    def generate_material_proof(self, fingerprint: MaterialFingerprint) -> Dict:
        """Génère une preuve matérielle pour vérification"""
        proof_data = {
            'fingerprint_hash': hashlib.sha256(
                fingerprint.composite_fingerprint.encode()
            ).hexdigest(),
            'timestamp': fingerprint.timestamp,
            'proof_type': 'material_physical',
            'verification_method': 'merkle_tree_sha3_512'
        }
        
        # Signature de la preuve
        proof_signature = hashlib.sha512(
            json.dumps(proof_data, sort_keys=True).encode()
        ).hexdigest()
        
        return {
            **proof_data,
            'proof_signature': proof_signature
        }
    
    def validate_proof(self, proof: Dict, fingerprint: MaterialFingerprint) -> bool:
        """Valide une preuve matérielle"""
        expected_hash = hashlib.sha256(
            fingerprint.composite_fingerprint.encode()
        ).hexdigest()
        
        return proof.get('fingerprint_hash') == expected_hash


class CryptoVertexCalculator:
    """Calcule le vertex cryptographique à partir des empreintes matérielles"""
    
    @staticmethod
    def calculate_crypto_vertex(fingerprint: MaterialFingerprint,
                               simulation_results: List[Dict]) -> str:
        """Calcule un vertex cryptographique unique"""
        # Combiner empreinte et faces finales
        faces = [str(sim.get('final_face', 0)) for sim in simulation_results]
        faces_str = '-'.join(faces)
        
        combined = f"{fingerprint.composite_fingerprint}:{faces_str}"
        
        # Multi-hash pour sécurité
        h1 = hashlib.sha256(combined.encode()).digest()
        h2 = hashlib.sha512(h1).digest()
        h3 = hashlib.sha3_256(h2).digest()
        
        return h3.hex()
    
    @staticmethod
    def verify_crypto_vertex(vertex: str, fingerprint: MaterialFingerprint,
                            simulation_results: List[Dict]) -> bool:
        """Vérifie un vertex cryptographique"""
        expected = CryptoVertexCalculator.calculate_crypto_vertex(
            fingerprint, simulation_results
        )
        return vertex == expected
