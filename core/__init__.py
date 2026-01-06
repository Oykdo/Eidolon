"""
Core modules for Poly-Spinor Nexus 7D

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
"""

__version__ = "1.0.0"
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
        SecurityConfig,
        BackupConfig,
        NetworkConfig,
        UIConfig,
        TransferConfig
    )
    VAULT_CONFIG_AVAILABLE = True
except ImportError:
    VAULT_CONFIG_AVAILABLE = False
