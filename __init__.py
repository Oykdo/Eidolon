"""
Poly-Spinor Nexus 7D - Systeme Cryptographique Post-Quantique
Vault securise avec authentification double-cle et support EVM

Architecture:
- Capture spatiale 7D avec calibration EPR
- Triple chiffrement post-quantique (McEliece + HQC + ML-DSA)
- Verification Bell generalisee 7D
- Generation de cles complete (9 phases, 30,900 bits d'entropie)
- Wallet EVM integre (ERC20/ERC721/ERC1155)
- Interface GUI avec authentification .psnx + .blend_data
"""

__version__ = "3.0.0"
__author__ = "Quantum Cryptography Lab"

# Blender addon info
bl_info = {
    "name": "Poly-Spinor Nexus 7D",
    "author": __author__,
    "version": (3, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > UI > PolySpinor",
    "description": "Systeme cryptographique post-quantique 7D - 30,900 bits d'entropie",
    "category": "Object",
}

import sys
import os

module_dir = os.path.dirname(os.path.abspath(__file__))
if module_dir not in sys.path:
    sys.path.insert(0, module_dir)

# Blender disponible?
try:
    import bpy
    BLENDER_AVAILABLE = True
except ImportError:
    BLENDER_AVAILABLE = False

# ============================================================================
# IMPORTS CORE
# ============================================================================

from .core.spatial_capture import (
    SpatialCaptureSystem, QuantumDataFusion, Point7D, DieType
)

from .core.spinor_crypto import (
    SpinorCryptographicEngine, SpinorAlgebra
)

from .core.quantum_verification import (
    AdvancedBellVerification, BellViolation
)

from .core.poly_spinor_hash import (
    PolySpinorHash, Lancer3D, QuaternionMatrix
)

from .core.physics_engine import (
    PolyhedronPhysicsEngine, PolyhedronType, PhysicsState
)

from .core.material_database import (
    PolyhedronMaterialDatabase, SurfaceMaterialDatabase
)

from .core.blender_engine import (
    PolySpinorBlenderEngine, BLENDER_AVAILABLE as BLENDER_ENGINE_AVAILABLE
)

from .core.complete_key_generator import (
    CompletePolySpinorKeyGenerator,
    CompleteKeyFileGenerator,
    CompleteKeyData,
    generate_complete_key
)

from .core.secure_key_storage import (
    SecureKeyStorage, VaultKeyStorage, SecureKeyDerivation
)

# Post-quantique reel
from .core.real_post_quantum import (
    HybridPQCryptoSystem, check_pqcrypto_available
)

# Legacy post-quantique (pour compatibilite protocols)
from .core.post_quantum_keys import (
    PostQuantumMasterKey, QuantumUserID, HKDF
)

# EVM Wallet
try:
    from .core.evm_wallet import (
        VaultHDWallet, VaultAssetManager, EVMChain, WEB3_AVAILABLE
    )
    EVM_AVAILABLE = WEB3_AVAILABLE
except ImportError:
    EVM_AVAILABLE = False

# ============================================================================
# IMPORTS PROTOCOLS
# ============================================================================

from .protocols.escrow_seal import (
    PolySpinorEscrowSeal, AuthorityKey, create_authority_keys
)

from .protocols.document_escrow import (
    PolySpinorEscrow7D, SpinorSeal, EscrowReceipt
)

from .protocols.material_vault import (
    MaterialBasedVaultSystem, VaultCredentials
)

from .protocols.vault_monitoring import (
    VaultMonitoringSystem, create_vault_monitoring
)

# ============================================================================
# IMPORTS UI
# ============================================================================

from .ui.vault_gui_complete import (
    VaultCompleteGUI, DualKeyAuthenticator
)

# Blender UI
if BLENDER_AVAILABLE:
    try:
        from .ui.main_panel import POLYSPINOR_PT_MainPanel
        from .ui.visualization import POLYSPINOR_PT_QuantumVisualization
        from .ui.escrow_interface import POLYSPINOR_PT_EscrowPanel
    except ImportError:
        pass

# ============================================================================
# CLASSE PRINCIPALE
# ============================================================================

class PolySpinorNexus7D:
    """Classe principale du systeme Poly-Spinor Nexus 7D"""
    
    def __init__(self):
        self.spatial_capture = SpatialCaptureSystem()
        self.crypto_engine = SpinorCryptographicEngine()
        self.bell_verifier = AdvancedBellVerification()
        self.key_generator = CompletePolySpinorKeyGenerator()
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialise le systeme"""
        try:
            self.spatial_capture.quantum_calibration()
            self.crypto_engine.generate_key_pair()
            self.bell_verifier.prepare_7d_entangled_state()
            self._initialized = True
            return True
        except Exception as e:
            print(f"Erreur initialisation: {e}")
            return False
    
    def generate_complete_key(self, user_name: str, output_dir: str):
        """Genere une cle complete avec fichiers .psnx et .blend_data"""
        return generate_complete_key(
            user_name=user_name,
            output_dir=output_dir,
            enable_pq=check_pqcrypto_available()
        )


# Instance globale
poly_spinor_system = None


def register():
    """Enregistrement Blender"""
    global poly_spinor_system
    poly_spinor_system = PolySpinorNexus7D()
    
    print("=" * 60)
    print("  POLY-SPINOR NEXUS 7D v3.0.0")
    print("=" * 60)
    print(f"  Blender:      {'Oui' if BLENDER_AVAILABLE else 'Non'}")
    print(f"  PQCrypto:     {'Oui' if check_pqcrypto_available() else 'Non'}")
    print(f"  EVM/Web3:     {'Oui' if EVM_AVAILABLE else 'Non'}")
    print(f"  Entropie:     30,900 bits")
    print("=" * 60)


def unregister():
    """Desenregistrement Blender"""
    global poly_spinor_system
    poly_spinor_system = None


# Auto-register si execute directement
if __name__ == "__main__":
    register()
