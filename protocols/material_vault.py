"""
Système de Vault Basé sur les Empreintes Matérielles
Authentification et accès sécurisé via signatures physiques
"""

import hashlib
import json
import time
import os
import secrets
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import numpy as np

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from ..core.material_database import PolyhedronMaterialDatabase, MaterialProperties
    from ..core.material_fingerprint import (
        MaterialFingerprint, MaterialFingerprintExtractor,
        MaterialSignatureAnalyzer, CryptoVertexCalculator
    )
    from ..core.post_quantum_keys import HKDF, PostQuantumMasterKey
except ImportError:
    from core.material_database import PolyhedronMaterialDatabase, MaterialProperties
    from core.material_fingerprint import (
        MaterialFingerprint, MaterialFingerprintExtractor,
        MaterialSignatureAnalyzer, CryptoVertexCalculator
    )
    from core.post_quantum_keys import HKDF, PostQuantumMasterKey


class VaultAccessDenied(Exception):
    """Accès au vault refusé"""
    pass


class VaultIntegrityError(Exception):
    """Erreur d'intégrité du vault"""
    pass


class AccessLevel(Enum):
    """Niveaux d'accès au vault"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    OWNER = "owner"


@dataclass
class VaultCredentials:
    """Identifiants pour accès au vault"""
    user_id: str
    material_fingerprint: MaterialFingerprint
    crypto_vertex: str
    access_level: AccessLevel
    created_at: str
    last_access: Optional[str] = None


@dataclass
class VaultAccessLog:
    """Journal d'accès au vault"""
    user_id: str
    timestamp: str
    access_type: str
    success: bool
    match_score: float
    material_proof: Dict
    ip_address: Optional[str] = None


@dataclass
class MaterialProof:
    """Preuve matérielle pour authentification"""
    fingerprint_hash: str
    simulation_hash: str
    timestamp: str
    proof_signature: str
    verification_data: Dict


class MaterialBasedVaultSystem:
    """Système de vault basé sur les empreintes matérielles"""
    
    MATCH_THRESHOLD = 0.999  # 99.9% de correspondance requise
    
    def __init__(self):
        self.fingerprint_extractor = MaterialFingerprintExtractor()
        self.signature_analyzer = MaterialSignatureAnalyzer()
        self.registered_users: Dict[str, VaultCredentials] = {}
        self.access_logs: List[VaultAccessLog] = []
        self.vault_keys: Dict[str, bytes] = {}
        
    def register_user(self, user_id: str, 
                      simulation_results: List[Dict],
                      access_level: AccessLevel = AccessLevel.READ) -> VaultCredentials:
        """Enregistre un nouvel utilisateur avec son empreinte matérielle"""
        
        # Extraire l'empreinte matérielle
        fingerprint = self.fingerprint_extractor.extract_from_simulation_results(
            simulation_results
        )
        
        # Calculer le vertex cryptographique
        crypto_vertex = CryptoVertexCalculator.calculate_crypto_vertex(
            fingerprint, simulation_results
        )
        
        # Créer les identifiants
        credentials = VaultCredentials(
            user_id=user_id,
            material_fingerprint=fingerprint,
            crypto_vertex=crypto_vertex,
            access_level=access_level,
            created_at=datetime.now().isoformat()
        )
        
        # Générer la clé du vault
        vault_key = self._derive_vault_key_from_fingerprint(fingerprint)
        
        # Enregistrer
        self.registered_users[user_id] = credentials
        self.vault_keys[user_id] = vault_key
        
        return credentials
    
    def unlock_vault(self, user_id: str,
                     simulation_results: List[Dict],
                     blend_file_path: Optional[str] = None) -> Dict:
        """Déverrouille le vault en validant l'empreinte matérielle"""
        
        # Vérifier que l'utilisateur existe
        if user_id not in self.registered_users:
            self._log_access(user_id, "unlock", False, 0.0, {})
            raise VaultAccessDenied(f"Utilisateur {user_id} non enregistré")
        
        stored_credentials = self.registered_users[user_id]
        
        # Extraire l'empreinte du fichier/simulation fourni
        extracted_fingerprint = self.fingerprint_extractor.extract_from_simulation_results(
            simulation_results
        )
        
        # Comparer les empreintes
        match_score = self._compare_material_fingerprints(
            extracted_fingerprint,
            stored_credentials.material_fingerprint
        )
        
        # Générer la preuve matérielle
        material_proof = self.signature_analyzer.generate_material_proof(
            extracted_fingerprint
        )
        
        # Vérifier le seuil
        if match_score < self.MATCH_THRESHOLD:
            self._log_access(user_id, "unlock", False, match_score, material_proof)
            raise VaultAccessDenied(
                f"Empreinte matérielle non valide. Score: {match_score:.4f} "
                f"(requis: {self.MATCH_THRESHOLD})"
            )
        
        # Vérifier le crypto vertex
        expected_vertex = CryptoVertexCalculator.calculate_crypto_vertex(
            extracted_fingerprint, simulation_results
        )
        
        if expected_vertex != stored_credentials.crypto_vertex:
            # Tolérance: vérifier la similarité
            vertex_match = self._compare_vertices(
                expected_vertex, stored_credentials.crypto_vertex
            )
            if vertex_match < 0.95:
                self._log_access(user_id, "unlock", False, match_score, material_proof)
                raise VaultAccessDenied("Vertex cryptographique non valide")
        
        # Succès - extraire la clé
        vault_key = self.vault_keys.get(user_id)
        
        if not vault_key:
            vault_key = self._derive_vault_key_from_fingerprint(extracted_fingerprint)
        
        # Mettre à jour le dernier accès
        stored_credentials.last_access = datetime.now().isoformat()
        
        # Logger l'accès
        self._log_access(user_id, "unlock", True, match_score, material_proof)
        
        return {
            'access_granted': True,
            'vault_key': vault_key.hex(),
            'match_score': match_score,
            'material_proof': material_proof,
            'access_level': stored_credentials.access_level.value,
            'crypto_vertex': stored_credentials.crypto_vertex[:32] + '...'
        }
    
    def _compare_material_fingerprints(self, fp1: MaterialFingerprint,
                                       fp2: MaterialFingerprint) -> float:
        """Compare deux empreintes matérielles avec métrique avancée"""
        
        # Composants statiques (doivent correspondre exactement)
        static_match = 1.0 if fp1.static_hash == fp2.static_hash else 0.0
        
        # Matrice d'interaction (similarité avec tolérance)
        interaction_similarity = self._compare_hashes_with_tolerance(
            fp1.interaction_hash, fp2.interaction_hash, tolerance=0.01
        )
        
        # Signature dynamique (distance normalisée)
        dynamic_similarity = MaterialFingerprintExtractor.compare_dynamic_signatures(
            fp1.dynamic_signature, fp2.dynamic_signature
        )
        
        # Moyenne pondérée
        weights = {'static': 0.4, 'interaction': 0.4, 'dynamic': 0.2}
        total_score = (
            weights['static'] * static_match +
            weights['interaction'] * interaction_similarity +
            weights['dynamic'] * dynamic_similarity
        )
        
        return total_score
    
    def _compare_hashes_with_tolerance(self, hash1: str, hash2: str,
                                       tolerance: float) -> float:
        """Compare deux hashes avec tolérance"""
        if hash1 == hash2:
            return 1.0
        
        # Distance de Hamming
        bytes1 = bytes.fromhex(hash1)
        bytes2 = bytes.fromhex(hash2)
        
        if len(bytes1) != len(bytes2):
            return 0.0
        
        diff_bits = sum(bin(b1 ^ b2).count('1') for b1, b2 in zip(bytes1, bytes2))
        total_bits = len(bytes1) * 8
        
        similarity = 1 - (diff_bits / total_bits)
        return similarity
    
    def _compare_vertices(self, v1: str, v2: str) -> float:
        """Compare deux vertices cryptographiques"""
        if v1 == v2:
            return 1.0
        
        bytes1 = bytes.fromhex(v1)
        bytes2 = bytes.fromhex(v2)
        
        min_len = min(len(bytes1), len(bytes2))
        matching = sum(1 for i in range(min_len) if bytes1[i] == bytes2[i])
        
        return matching / min_len
    
    def _derive_vault_key_from_fingerprint(self, fingerprint: MaterialFingerprint) -> bytes:
        """Dérive une clé de vault depuis l'empreinte matérielle"""
        # Combiner les composants de l'empreinte
        combined = (
            fingerprint.static_hash +
            fingerprint.interaction_hash +
            fingerprint.dynamic_signature +
            fingerprint.composite_fingerprint
        ).encode()
        
        # Dérivation HKDF
        vault_key = HKDF.derive(
            combined,
            b'material_vault_key',
            b'derivation',
            64
        )
        
        return vault_key
    
    def _log_access(self, user_id: str, access_type: str,
                    success: bool, match_score: float,
                    material_proof: Dict):
        """Journalise un accès au vault"""
        log_entry = VaultAccessLog(
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            access_type=access_type,
            success=success,
            match_score=match_score,
            material_proof=material_proof
        )
        
        self.access_logs.append(log_entry)
    
    def get_access_logs(self, user_id: Optional[str] = None) -> List[Dict]:
        """Récupère les journaux d'accès"""
        logs = self.access_logs
        
        if user_id:
            logs = [log for log in logs if log.user_id == user_id]
        
        return [
            {
                'user_id': log.user_id,
                'timestamp': log.timestamp,
                'access_type': log.access_type,
                'success': log.success,
                'match_score': log.match_score
            }
            for log in logs
        ]
    
    def revoke_access(self, user_id: str) -> bool:
        """Révoque l'accès d'un utilisateur"""
        if user_id in self.registered_users:
            del self.registered_users[user_id]
        
        if user_id in self.vault_keys:
            del self.vault_keys[user_id]
        
        self._log_access(user_id, "revoke", True, 0.0, {})
        return True
    
    def update_fingerprint(self, user_id: str,
                          new_simulation_results: List[Dict]) -> VaultCredentials:
        """Met à jour l'empreinte d'un utilisateur"""
        if user_id not in self.registered_users:
            raise VaultAccessDenied(f"Utilisateur {user_id} non trouvé")
        
        old_credentials = self.registered_users[user_id]
        
        # Créer de nouveaux identifiants avec le même niveau d'accès
        new_credentials = self.register_user(
            user_id,
            new_simulation_results,
            old_credentials.access_level
        )
        
        return new_credentials


class VaultKeyManager:
    """Gestionnaire de clés de vault"""
    
    def __init__(self, vault_system: MaterialBasedVaultSystem):
        self.vault_system = vault_system
        self.derived_keys: Dict[str, Dict[str, bytes]] = {}
    
    def derive_subkey(self, user_id: str, purpose: str) -> bytes:
        """Dérive une sous-clé pour un usage spécifique"""
        if user_id not in self.vault_system.vault_keys:
            raise VaultAccessDenied(f"Pas de clé vault pour {user_id}")
        
        master_key = self.vault_system.vault_keys[user_id]
        
        subkey = HKDF.derive(
            master_key,
            f'subkey_{purpose}'.encode(),
            user_id.encode(),
            32
        )
        
        if user_id not in self.derived_keys:
            self.derived_keys[user_id] = {}
        self.derived_keys[user_id][purpose] = subkey
        
        return subkey
    
    def encrypt_with_vault_key(self, user_id: str, data: bytes, 
                               associated_data: Optional[bytes] = None) -> bytes:
        """
        Chiffre des données avec la clé du vault en utilisant AES-256-GCM.
        
        Format de sortie: nonce (12 bytes) || ciphertext || tag (16 bytes)
        
        Args:
            user_id: Identifiant de l'utilisateur
            data: Données à chiffrer
            associated_data: Données authentifiées mais non chiffrées (AAD)
        
        Returns:
            Données chiffrées avec nonce préfixé
        """
        if user_id not in self.vault_system.vault_keys:
            raise VaultAccessDenied(f"Pas de clé vault pour {user_id}")
        
        # Extraire une clé AES-256 (32 bytes) depuis la clé vault
        key = self.vault_system.vault_keys[user_id][:32]
        
        # Générer un nonce cryptographiquement sécurisé (96 bits recommandé pour GCM)
        nonce = secrets.token_bytes(12)
        
        # Créer le chiffreur AES-GCM
        aesgcm = AESGCM(key)
        
        # Chiffrer avec authentification
        # Le tag d'authentification (16 bytes) est automatiquement ajouté
        ciphertext = aesgcm.encrypt(nonce, data, associated_data)
        
        # Retourner nonce || ciphertext (qui inclut le tag)
        return nonce + ciphertext
    
    def decrypt_with_vault_key(self, user_id: str, encrypted_data: bytes,
                               associated_data: Optional[bytes] = None) -> bytes:
        """
        Déchiffre des données avec la clé du vault en utilisant AES-256-GCM.
        
        Args:
            user_id: Identifiant de l'utilisateur
            encrypted_data: Données chiffrées (nonce || ciphertext || tag)
            associated_data: Données authentifiées (doit correspondre au chiffrement)
        
        Returns:
            Données déchiffrées
            
        Raises:
            VaultAccessDenied: Si l'utilisateur n'a pas de clé
            VaultIntegrityError: Si l'authentification échoue (données corrompues/modifiées)
        """
        if user_id not in self.vault_system.vault_keys:
            raise VaultAccessDenied(f"Pas de clé vault pour {user_id}")
        
        if len(encrypted_data) < 28:  # 12 (nonce) + 16 (tag minimum)
            raise VaultIntegrityError("Données chiffrées trop courtes")
        
        # Extraire la clé AES-256
        key = self.vault_system.vault_keys[user_id][:32]
        
        # Extraire le nonce (12 premiers bytes)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        
        # Créer le déchiffreur AES-GCM
        aesgcm = AESGCM(key)
        
        try:
            # Déchiffrer et vérifier l'authenticité
            plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)
            return plaintext
        except InvalidTag:
            raise VaultIntegrityError(
                "Échec de l'authentification: données corrompues ou clé incorrecte"
            )


class MaterialVaultBlendfileHandler:
    """Gestionnaire de fichiers .blend pour le vault matériel"""
    
    def __init__(self, vault_system: MaterialBasedVaultSystem):
        self.vault_system = vault_system
        self.fingerprint_extractor = MaterialFingerprintExtractor()
    
    def extract_fingerprint_from_blend(self, blend_file_path: str) -> MaterialFingerprint:
        """Extrait l'empreinte matérielle d'un fichier .blend"""
        # Simulation: lire les métadonnées du fichier
        # En production, utiliserait bpy pour charger le fichier
        
        with open(blend_file_path, 'rb') as f:
            file_data = f.read(1024)  # Lire l'en-tête
        
        # Créer une empreinte basée sur le contenu
        file_hash = hashlib.sha256(file_data).hexdigest()
        
        return MaterialFingerprint(
            static_hash=file_hash,
            interaction_hash=hashlib.sha512(file_data).hexdigest(),
            dynamic_signature=hashlib.sha3_256(file_data).hexdigest(),
            composite_fingerprint=hashlib.sha3_512(file_data).hexdigest(),
            timestamp=datetime.now().isoformat(),
            metadata={'source': 'blend_file', 'path': blend_file_path}
        )
    
    def save_blend_with_fingerprint(self, blend_file_path: str,
                                    fingerprint: MaterialFingerprint,
                                    metadata: Dict) -> str:
        """Sauvegarde un fichier .blend avec métadonnées d'empreinte"""
        # En production, utiliserait bpy pour sauvegarder
        
        metadata_json = json.dumps({
            'fingerprint': fingerprint.to_dict(),
            'vault_metadata': metadata,
            'timestamp': datetime.now().isoformat()
        })
        
        # Écrire les métadonnées dans un fichier compagnon
        metadata_path = blend_file_path + '.vault_meta'
        with open(metadata_path, 'w') as f:
            f.write(metadata_json)
        
        return metadata_path
    
    def validate_blend_file(self, blend_file_path: str, 
                           user_id: str) -> Tuple[bool, float]:
        """Valide un fichier .blend pour un utilisateur"""
        if user_id not in self.vault_system.registered_users:
            return False, 0.0
        
        stored_credentials = self.vault_system.registered_users[user_id]
        extracted = self.extract_fingerprint_from_blend(blend_file_path)
        
        # Comparer
        valid, score = stored_credentials.material_fingerprint.verify(extracted)
        
        return valid, score
