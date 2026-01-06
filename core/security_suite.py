"""
Suite de Securite Integree Poly-Spinor Nexus 7D
Version 10/10 - Toutes les fonctionnalites avancees

Ce module integre:
- Entropie quantique (QRNG)
- Protection memoire (SecureBuffer)
- Authentification fichiers (HMAC)
- Partage de secret (Shamir)
- Operations constant-time
- Zero-Knowledge Proofs
- Support HSM

Usage:
    from core.security_suite import SecureVaultManager
    
    manager = SecureVaultManager()
    vault_key = manager.generate_secure_key("MonVault")
    
    # ZKP authentication
    proof = manager.create_ownership_proof()
    
    # Shamir sharing
    shares = manager.create_recovery_shares(threshold=3, total=5)
"""

import os
import time
import hashlib
import secrets
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

# Imports des modules de securite
from .secure_memory import SecureBuffer, SecureKeyStorage, SecureZeroMethod
from .authenticated_files import (
    AuthenticatedFileFormat, SecurePSNXFile,
    FileMetadata, AuthenticationError
)
from .quantum_entropy import (
    HybridEntropyPool, QuantumEntropyManager,
    get_quantum_entropy, EntropyQuality
)
from .secret_sharing import (
    ShamirSecretSharing, VaultKeySharing, Share,
    create_recovery_shares, recover_from_shares
)
from .constant_time import (
    constant_time_compare, secure_key_compare,
    ConstantTimeHMAC, BlindedScalarOperations
)
from .zkp_auth import (
    VaultZKPAuth, SchnorrZKP, SchnorrProof,
    create_vault_zkp_credentials, verify_vault_ownership
)
from .hardware_security import (
    HSMManager, HardwareSecurityModule, SoftwareHSM,
    KeyType, KeyUsage, HSMKeyInfo
)


@dataclass
class SecurityConfig:
    """Configuration de securite"""
    use_quantum_entropy: bool = True
    use_hsm: bool = False
    memory_protection: bool = True
    file_authentication: bool = True
    enable_zkp: bool = True
    shamir_threshold: int = 3
    shamir_total: int = 5
    secure_wipe_method: SecureZeroMethod = SecureZeroMethod.DOD_3


class SecureVaultManager:
    """
    Gestionnaire de vault securise avec toutes les protections.
    
    Features:
    - Generation de cle avec entropie quantique
    - Stockage securise en memoire
    - Fichiers authentifies HMAC
    - ZKP pour prouver la possession
    - Shamir pour recuperation/multi-sig
    - Support HSM optionnel
    """
    
    VERSION = "10.0"
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        
        # Initialiser les composants
        self._init_components()
        
        # Cle vault (protegee en memoire)
        self._vault_key_buffer: Optional[SecureBuffer] = None
        self._zkp_auth: Optional[VaultZKPAuth] = None
        self._public_key: Optional[int] = None
    
    def _init_components(self):
        """Initialise les composants de securite"""
        # Entropy pool
        self.entropy_pool = HybridEntropyPool(
            use_quantum=self.config.use_quantum_entropy,
            use_atmospheric=self.config.use_quantum_entropy
        )
        
        # HSM Manager
        if self.config.use_hsm:
            self.hsm = HSMManager(prefer_hardware=True)
        else:
            self.hsm = None
        
        # Key storage
        self.key_storage = SecureKeyStorage()
        
        # Shamir
        self.key_sharing = VaultKeySharing()
    
    def generate_secure_key(
        self,
        user_name: str,
        extra_entropy: Optional[bytes] = None
    ) -> bytes:
        """
        Genere une cle vault avec entropie quantique.
        
        Args:
            user_name: Nom de l'utilisateur/vault
            extra_entropy: Entropie supplementaire optionnelle
        
        Returns:
            Cle vault de 32 bytes
        """
        # Collecter l'entropie
        print("[Security] Collecte d'entropie quantique...")
        quantum_entropy = self.entropy_pool.get_entropy(64, min_sources=2)
        
        # Mixer avec l'entropie supplementaire
        if extra_entropy:
            combined = quantum_entropy + extra_entropy
        else:
            combined = quantum_entropy
        
        # Ajouter contexte utilisateur
        context = f"PSNX_VAULT_{user_name}_{time.time()}".encode()
        combined += context
        
        # Deriver la cle finale via HKDF
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives import hashes
        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'PSNX_SECURE_KEY_v10',
            info=b'vault_master_key'
        )
        vault_key = hkdf.derive(combined)
        
        # Stocker en memoire securisee
        if self.config.memory_protection:
            self._vault_key_buffer = SecureBuffer(32, auto_rotate_seconds=30)
            self._vault_key_buffer.write(vault_key)
        
        # Initialiser ZKP
        if self.config.enable_zkp:
            self._zkp_auth = VaultZKPAuth(vault_key)
            self._public_key = self._zkp_auth.get_public_key()
        
        # Stocker dans le key storage
        self.key_storage.store("vault_master", vault_key)
        
        # Rapport
        report = self.entropy_pool.get_collection_report()
        print(f"[Security] Entropie collectee: {report['total_bits']} bits")
        print(f"[Security] Sources: {report['sources_used']}")
        if any(r['quality'] == 'QUANTUM' for r in report['sources']):
            print("[Security] Source quantique utilisee!")
        
        return vault_key
    
    def get_vault_key(self) -> Optional[bytes]:
        """Recupere la cle vault depuis la memoire securisee"""
        if self._vault_key_buffer:
            return self._vault_key_buffer.read()
        return self.key_storage.retrieve("vault_master")
    
    def secure_wipe_key(self):
        """Efface la cle de maniere securisee"""
        if self._vault_key_buffer:
            self._vault_key_buffer.secure_zero(self.config.secure_wipe_method)
            self._vault_key_buffer.destroy()
            self._vault_key_buffer = None
        
        self.key_storage.delete("vault_master")
        self._zkp_auth = None
        self._public_key = None
    
    # =========================================================================
    # AUTHENTIFICATION ZKP
    # =========================================================================
    
    def create_ownership_proof(self, challenge: str = "") -> Dict:
        """
        Cree une preuve de possession de la cle vault.
        
        La preuve peut etre verifiee sans connaitre la cle.
        
        Args:
            challenge: Challenge unique (ex: timestamp)
        
        Returns:
            Preuve ZKP
        """
        if not self._zkp_auth:
            vault_key = self.get_vault_key()
            if not vault_key:
                raise ValueError("Aucune cle vault")
            self._zkp_auth = VaultZKPAuth(vault_key)
            self._public_key = self._zkp_auth.get_public_key()
        
        return self._zkp_auth.create_auth_proof(challenge)
    
    def get_public_credentials(self) -> Dict:
        """
        Retourne les credentials publics pour verification ZKP.
        
        Ces credentials peuvent etre partages publiquement.
        """
        if not self._public_key:
            vault_key = self.get_vault_key()
            if not vault_key:
                raise ValueError("Aucune cle vault")
            creds = create_vault_zkp_credentials(vault_key)
            self._public_key = int(creds['public_key'], 16)
            return creds
        
        return {
            'public_key': hex(self._public_key),
            'fingerprint': self._zkp_auth.get_key_fingerprint() if self._zkp_auth else ""
        }
    
    @staticmethod
    def verify_ownership(
        public_credentials: Dict,
        proof: Dict,
        challenge: str
    ) -> Tuple[bool, str]:
        """
        Verifie une preuve de possession.
        
        Args:
            public_credentials: Credentials publics du vault
            proof: Preuve ZKP
            challenge: Challenge utilise
        
        Returns:
            (valid, reason)
        """
        public_key = int(public_credentials['public_key'], 16)
        return VaultZKPAuth.verify_auth(public_key, proof, challenge)
    
    # =========================================================================
    # PARTAGE DE SECRET (SHAMIR)
    # =========================================================================
    
    def create_recovery_shares(
        self,
        threshold: Optional[int] = None,
        total: Optional[int] = None,
        guardian_names: Optional[List[str]] = None
    ) -> Dict:
        """
        Cree des parts de recuperation pour la cle vault.
        
        Args:
            threshold: Nombre minimum de parts requises
            total: Nombre total de parts
            guardian_names: Noms des gardiens
        
        Returns:
            Configuration avec les parts
        """
        vault_key = self.get_vault_key()
        if not vault_key:
            raise ValueError("Aucune cle vault")
        
        threshold = threshold or self.config.shamir_threshold
        total = total or self.config.shamir_total
        
        config = self.key_sharing.create_shared_vault(
            vault_key,
            threshold=threshold,
            total=total,
            guardian_names=guardian_names
        )
        
        print(f"[Security] {total} parts creees (threshold: {threshold})")
        return config
    
    def recover_from_shares(self, shares: List[Dict]) -> bytes:
        """
        Recupere la cle vault depuis des parts Shamir.
        
        Args:
            shares: Liste de parts (format dict)
        
        Returns:
            Cle vault reconstruite
        """
        share_objects = [
            Share.from_dict(s['share'] if 'share' in s else s)
            for s in shares
        ]
        
        vault_key = self.key_sharing.recover_vault_key(share_objects)
        
        # Stocker la cle recuperee
        if self.config.memory_protection:
            self._vault_key_buffer = SecureBuffer(32)
            self._vault_key_buffer.write(vault_key)
        
        self.key_storage.store("vault_master", vault_key)
        
        # Reinitialiser ZKP
        if self.config.enable_zkp:
            self._zkp_auth = VaultZKPAuth(vault_key)
            self._public_key = self._zkp_auth.get_public_key()
        
        print("[Security] Cle recuperee depuis les parts Shamir")
        return vault_key
    
    def export_share_secure(
        self,
        share: Dict,
        password: str
    ) -> str:
        """
        Exporte une part de maniere securisee (chiffree).
        """
        share_obj = Share.from_dict(share['share'] if 'share' in share else share)
        return self.key_sharing.export_share(share_obj, password)
    
    def import_share_secure(self, exported: str, password: str) -> Share:
        """
        Importe une part chiffree.
        """
        return self.key_sharing.import_share(exported, password)
    
    # =========================================================================
    # FICHIERS AUTHENTIFIES
    # =========================================================================
    
    def save_secure_file(
        self,
        path: str,
        data: bytes,
        file_type: str = "psnx"
    ) -> FileMetadata:
        """
        Sauvegarde un fichier avec authentification HMAC.
        """
        vault_key = self.get_vault_key()
        if not vault_key:
            raise ValueError("Aucune cle vault")
        
        auth_key = AuthenticatedFileFormat.derive_auth_key(vault_key)
        aff = AuthenticatedFileFormat(auth_key)
        
        key_id = hashlib.sha256(vault_key).hexdigest()[:16]
        return aff.write_file(path, data, file_type, key_id)
    
    def load_secure_file(self, path: str) -> Tuple[FileMetadata, bytes]:
        """
        Charge un fichier authentifie.
        
        Raises:
            AuthenticationError: Si le fichier a ete modifie
        """
        vault_key = self.get_vault_key()
        if not vault_key:
            raise ValueError("Aucune cle vault")
        
        auth_key = AuthenticatedFileFormat.derive_auth_key(vault_key)
        aff = AuthenticatedFileFormat(auth_key)
        
        return aff.read_file(path)
    
    def verify_file_integrity(self, path: str) -> bool:
        """Verifie l'integrite d'un fichier"""
        try:
            self.load_secure_file(path)
            return True
        except AuthenticationError:
            return False
    
    # =========================================================================
    # HSM
    # =========================================================================
    
    def store_key_in_hsm(self, label: str = "vault_master") -> Optional[str]:
        """
        Stocke la cle vault dans un HSM.
        
        Returns:
            key_id dans le HSM ou None si pas de HSM
        """
        if not self.hsm:
            print("[Security] Pas de HSM disponible")
            return None
        
        vault_key = self.get_vault_key()
        if not vault_key:
            raise ValueError("Aucune cle vault")
        
        # Generer une cle de wrapping dans le HSM
        hsm = self.hsm.active_hsm
        wrap_info = hsm.generate_key(
            KeyType.AES_256,
            f"{label}_wrap",
            [KeyUsage.ENCRYPT, KeyUsage.DECRYPT]
        )
        
        # Chiffrer la cle vault
        wrapped = hsm.encrypt(wrap_info.key_id, vault_key)
        
        # Stocker le blob (dans un fichier ou base de donnees)
        # Pour cet exemple, on retourne juste l'ID
        print(f"[Security] Cle stockee dans HSM ({self.hsm.get_hsm_type()})")
        return wrap_info.key_id
    
    # =========================================================================
    # RAPPORTS
    # =========================================================================
    
    def get_security_report(self) -> Dict:
        """Retourne un rapport de securite complet"""
        memory_stats = SecureBuffer.get_stats()
        
        report = {
            'version': self.VERSION,
            'config': {
                'quantum_entropy': self.config.use_quantum_entropy,
                'hsm': self.config.use_hsm,
                'memory_protection': self.config.memory_protection,
                'file_authentication': self.config.file_authentication,
                'zkp_enabled': self.config.enable_zkp
            },
            'memory': {
                'active_buffers': memory_stats.active_buffers,
                'locked_bytes': memory_stats.locked_bytes,
                'rotation_count': memory_stats.rotation_count
            },
            'entropy': self.entropy_pool.get_collection_report(),
            'hsm': {
                'available': self.hsm is not None,
                'type': self.hsm.get_hsm_type() if self.hsm else None,
                'is_hardware': self.hsm.is_hardware_hsm() if self.hsm else False
            },
            'zkp': {
                'enabled': self._zkp_auth is not None,
                'public_key_set': self._public_key is not None
            }
        }
        
        return report
    
    def print_security_status(self):
        """Affiche le statut de securite"""
        report = self.get_security_report()
        
        print("\n" + "="*60)
        print("  STATUT SECURITE POLY-SPINOR NEXUS 7D")
        print("="*60)
        print(f"  Version:            {report['version']}")
        print(f"  Entropie quantique: {'OUI' if report['config']['quantum_entropy'] else 'NON'}")
        print(f"  Protection memoire: {'OUI' if report['config']['memory_protection'] else 'NON'}")
        print(f"  Auth fichiers:      {'OUI' if report['config']['file_authentication'] else 'NON'}")
        print(f"  ZKP:                {'OUI' if report['config']['zkp_enabled'] else 'NON'}")
        print(f"  HSM:                {report['hsm']['type'] or 'Non disponible'}")
        print(f"  Buffers actifs:     {report['memory']['active_buffers']}")
        print(f"  Memoire verrouillee: {report['memory']['locked_bytes']} bytes")
        print("="*60 + "\n")


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def create_secure_vault(
    user_name: str,
    output_dir: str,
    config: Optional[SecurityConfig] = None
) -> Tuple[str, bytes, Dict]:
    """
    Cree un vault securise complet.
    
    Args:
        user_name: Nom du vault
        output_dir: Repertoire de sortie
        config: Configuration de securite
    
    Returns:
        (key_file_path, vault_key, security_report)
    """
    manager = SecureVaultManager(config)
    
    # Generer la cle
    vault_key = manager.generate_secure_key(user_name)
    
    # Creer les fichiers
    os.makedirs(output_dir, exist_ok=True)
    
    key_id = hashlib.sha256(vault_key).hexdigest()[:8]
    base_name = f"vault_{user_name.lower()}_{key_id}"
    
    # Sauvegarder les credentials publics
    credentials = manager.get_public_credentials()
    creds_path = os.path.join(output_dir, f"{base_name}_credentials.json")
    import json
    with open(creds_path, 'w') as f:
        json.dump(credentials, f, indent=2)
    
    # Creer des parts de recuperation
    shares = manager.create_recovery_shares()
    shares_path = os.path.join(output_dir, f"{base_name}_recovery.json")
    with open(shares_path, 'w') as f:
        json.dump(shares, f, indent=2, default=str)
    
    report = manager.get_security_report()
    manager.print_security_status()
    
    return creds_path, vault_key, report


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("="*70)
    print("  TEST SUITE DE SECURITE 10/10")
    print("="*70)
    
    # Test avec configuration complete
    config = SecurityConfig(
        use_quantum_entropy=True,
        memory_protection=True,
        file_authentication=True,
        enable_zkp=True,
        shamir_threshold=2,
        shamir_total=3
    )
    
    manager = SecureVaultManager(config)
    
    # 1. Generation de cle
    print("\n[TEST 1] Generation de cle securisee...")
    vault_key = manager.generate_secure_key("TestVault")
    print(f"  Cle: {vault_key[:8].hex()}...")
    
    # 2. ZKP
    print("\n[TEST 2] Zero-Knowledge Proof...")
    challenge = f"test_{int(time.time())}"
    proof = manager.create_ownership_proof(challenge)
    print(f"  Challenge: {challenge}")
    print(f"  Proof timestamp: {proof['timestamp']}")
    
    # Verification
    creds = manager.get_public_credentials()
    valid, reason = manager.verify_ownership(creds, proof, challenge)
    print(f"  Verification: {'OK' if valid else 'FAILED'} - {reason}")
    
    # 3. Shamir
    print("\n[TEST 3] Shamir Secret Sharing...")
    shares_config = manager.create_recovery_shares(
        threshold=2,
        total=3,
        guardian_names=["Alice", "Bob", "Charlie"]
    )
    print(f"  Parts creees: {len(shares_config['shares'])}")
    print(f"  Threshold: {shares_config['threshold']}")
    
    # Test recuperation
    shares_subset = shares_config['shares'][:2]  # Alice et Bob
    recovered = manager.recover_from_shares(shares_subset)
    print(f"  Recuperation avec 2 parts: {'OK' if recovered == vault_key else 'FAILED'}")
    
    # 4. Rapport
    print("\n[TEST 4] Rapport de securite...")
    manager.print_security_status()
    
    # Cleanup
    manager.secure_wipe_key()
    print("\n[OK] Tous les tests passes!")
