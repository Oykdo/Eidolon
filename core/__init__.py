"""
Core modules for Eidolon

Modules:
- spatial_capture: Capture spatiale 7D avec calibration EPR
- spinor_crypto: Chiffrement base sur algebre de Clifford Cl(0,7)
- quantum_verification: Verification des correlations Bell 7D
- poly_spinor_hash: Hash spinoriel composite
- physics_engine: Simulation physique des polyedres
- material_database: Base de donnees des materiaux
- blender_engine: Moteur de visualisation Blender
- complete_key_generator: Generateur de cles complet (9 phases)
- evm_wallet: Wallet EVM pour tokens ERC20/NFTs
- real_post_quantum: Algorithmes post-quantiques reels (pqcrypto)
- secure_key_storage: Stockage securise des cles
- persistent_vault: Gestionnaire de vault persistant
- vault_config: Configuration du vault

Security Suite (v10/10):
- secure_memory: Protection memoire avancee
- authenticated_files: Fichiers authentifies HMAC
- quantum_entropy: Sources d'entropie quantique
- secret_sharing: Shamir Secret Sharing
- constant_time: Operations en temps constant
- zkp_auth: Zero-Knowledge Proofs
- hardware_security: Integration HSM
- security_suite: Suite integree
"""

__version__ = "2.0.0"
__author__ = "Poly-Spinor Team"
__license__ = "MIT"

# Capture et verification
from .spatial_capture import SpatialCaptureSystem, QuantumDataFusion, Point7D, DieType
from .spinor_crypto import SpinorCryptographicEngine, SpinorAlgebra
from .quantum_verification import AdvancedBellVerification, BellViolation

# Hash et crypto
from .poly_spinor_hash import PolySpinorHash, Lancer3D, QuaternionMatrix
from .post_quantum_keys import PostQuantumMasterKey, QuantumUserID, HKDF
from .real_post_quantum import HybridPQCryptoSystem, check_pqcrypto_available
from .secure_key_storage import SecureKeyStorage, SecureKeyDerivation

# Simulation physique
from .physics_engine import PolyhedronPhysicsEngine, PolyhedronType, Trajectory
from .material_database import PolyhedronMaterialDatabase, SurfaceMaterialDatabase, MATERIAL_DB
from .material_fingerprint import MaterialFingerprint, MaterialFingerprintExtractor
from .material_simulation_pipeline import CompleteMaterialSimulationPipeline

# Generateur complet
from .complete_key_generator import (
    CompletePolySpinorKeyGenerator,
    CompleteKeyFileGenerator,
    generate_complete_key
)

# Visualisation
from .blender_engine import PolySpinorBlenderEngine, BLENDER_AVAILABLE

# EVM Wallet (optionnel)
try:
    from .evm_wallet import VaultHDWallet, VaultAssetManager, EVMChain, WEB3_AVAILABLE
except ImportError:
    WEB3_AVAILABLE = False

# Alchemy Integration (optionnel)
try:
    from .alchemy_integration import (
        AlchemyClient,
        AlchemyNetwork,
        AlchemyVaultIntegration,
        AlchemyWebhookManager,
        AlchemyNFT,
        AlchemyToken,
        AlchemyTransfer,
        AlchemyGasEstimate,
        create_alchemy_client
    )
    ALCHEMY_AVAILABLE = True
except ImportError:
    ALCHEMY_AVAILABLE = False

# Vault Persistant
try:
    from .persistent_vault import (
        PersistentVaultManager,
        VaultAsset,
        VaultDocument,
        VaultToken,
        VaultTransfer,
        create_vault,
        open_vault
    )
    PERSISTENT_VAULT_AVAILABLE = True
except ImportError:
    PERSISTENT_VAULT_AVAILABLE = False

# Configuration du Vault
try:
    from .vault_config import (
        VaultConfigManager,
        VaultConfiguration,
        SecurityConfig as VaultSecurityConfig,
        BackupConfig,
        NetworkConfig,
        UIConfig,
        TransferConfig
    )
    VAULT_CONFIG_AVAILABLE = True
except ImportError:
    VAULT_CONFIG_AVAILABLE = False

# =============================================================================
# SECURITY SUITE v10/10
# =============================================================================

# Secure Memory
try:
    from .secure_memory import (
        SecureBuffer,
        SecureKeyStorage as SecureMemoryStorage,
        SecureZeroMethod,
        MemoryStats
    )
    SECURE_MEMORY_AVAILABLE = True
except ImportError:
    SECURE_MEMORY_AVAILABLE = False

# Authenticated Files
try:
    from .authenticated_files import (
        AuthenticatedFileFormat,
        SecurePSNXFile,
        FileMetadata,
        AuthenticationError,
        verify_file_integrity
    )
    AUTHENTICATED_FILES_AVAILABLE = True
except ImportError:
    AUTHENTICATED_FILES_AVAILABLE = False

# Quantum Entropy
try:
    from .quantum_entropy import (
        HybridEntropyPool,
        QuantumEntropyManager,
        get_quantum_entropy,
        EntropyQuality,
        ANUQuantumSource,
        OSEntropySource
    )
    QUANTUM_ENTROPY_AVAILABLE = True
except ImportError:
    QUANTUM_ENTROPY_AVAILABLE = False

# Secret Sharing (Shamir)
try:
    from .secret_sharing import (
        ShamirSecretSharing,
        VaultKeySharing,
        Share,
        create_recovery_shares,
        recover_from_shares
    )
    SECRET_SHARING_AVAILABLE = True
except ImportError:
    SECRET_SHARING_AVAILABLE = False

# Constant Time Operations
try:
    from .constant_time import (
        constant_time_compare,
        constant_time_select,
        secure_key_compare,
        ConstantTimeHMAC,
        BlindedScalarOperations
    )
    CONSTANT_TIME_AVAILABLE = True
except ImportError:
    CONSTANT_TIME_AVAILABLE = False

# Zero-Knowledge Proofs
try:
    from .zkp_auth import (
        VaultZKPAuth,
        SchnorrZKP,
        SchnorrProof,
        create_vault_zkp_credentials,
        verify_vault_ownership,
        MultiPartyZKP
    )
    ZKP_AVAILABLE = True
except ImportError:
    ZKP_AVAILABLE = False

# Hardware Security Module
try:
    from .hardware_security import (
        HSMManager,
        HardwareSecurityModule,
        SoftwareHSM,
        YubiHSM2,
        TPM2Integration,
        KeyType,
        KeyUsage,
        HSMKeyInfo
    )
    HSM_AVAILABLE = True
except ImportError:
    HSM_AVAILABLE = False

# Security Suite (integrated)
try:
    from .security_suite import (
        SecureVaultManager,
        SecurityConfig,
        create_secure_vault
    )
    SECURITY_SUITE_AVAILABLE = True
except ImportError:
    SECURITY_SUITE_AVAILABLE = False
