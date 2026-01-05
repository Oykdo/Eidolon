"""
Protocols for Poly-Spinor Nexus 7D

Modules:
- document_escrow: Entiercement de documents avec sceau spinoriel
- escrow_seal: Sceau d'entiercement multi-autorites
- escrow_recovery: Recuperation avec verification Bell
- escrow_dashboard: Monitoring et audit des sceaux
- authority_rotation: Rotation des autorites
- emergency_protocol: Acces d'urgence controle
- recovery_protocol: Recuperation quantique
- hyper_cluster: Clusters hyper-verifiables 7D
- material_vault: Vault base sur signatures materielles
- vault_monitoring: Surveillance du vault
"""

import sys
import os

# Ajouter le chemin parent pour les imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Imports avec gestion d'erreur pour compatibilite
try:
    from .document_escrow import PolySpinorEscrow7D, EscrowReceipt, SpinorSeal
    from .escrow_seal import PolySpinorEscrowSeal, AuthorityKey, create_authority_keys
    from .escrow_recovery import PolySpinorEscrowRecovery
    from .escrow_dashboard import PolySpinorEscrowDashboard
    from .recovery_protocol import QuantumRecoveryProtocol, EmergencyRecoveryProtocol
    from .authority_rotation import PolySpinorAuthorityRotation
    from .emergency_protocol import PolySpinorEmergencyProtocol
    from .material_vault import MaterialBasedVaultSystem, VaultCredentials
    from .vault_monitoring import VaultMonitoringSystem, create_vault_monitoring
    from .hyper_cluster import HyperCluster, HyperVerifiableEscrow
except ImportError as e:
    print(f"[WARN] Import partiel protocols: {e}")
