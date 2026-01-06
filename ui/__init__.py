"""
UI components for Poly-Spinor Nexus 7D
- vault_gui_complete.py: Interface principale du vault (tkinter)
- vault_monitor.py: Interface de monitoring du vault (tkinter)
- main_panel.py: Panneau Blender pour generation de cles
- visualization.py: Visualisation quantique Blender
- escrow_interface.py: Interface d'entiercement Blender
"""

# Interface principale Vault (tkinter)
from .vault_gui_complete import VaultCompleteGUI, DualKeyAuthenticator

# Interface de monitoring (tkinter)
try:
    from .vault_monitor import VaultMonitorGUI, SecureVaultManager
    VAULT_MONITOR_AVAILABLE = True
except ImportError:
    VAULT_MONITOR_AVAILABLE = False

# Interfaces Blender (optionnelles)
try:
    from .main_panel import (
        POLYSPINOR_OT_Generate7DKey,
        POLYSPINOR_OT_VisualizeQuantum,
        POLYSPINOR_OT_CalibrateSystem,
        POLYSPINOR_OT_VerifyBell,
        POLYSPINOR_PT_MainPanel
    )
    from .visualization import (
        POLYSPINOR_OT_ShowBellCorrelations,
        POLYSPINOR_OT_ShowEntanglement,
        POLYSPINOR_PT_QuantumVisualization
    )
    from .escrow_interface import (
        POLYSPINOR_OT_DepositDocument,
        POLYSPINOR_OT_RetrieveDocument,
        POLYSPINOR_PT_EscrowPanel
    )
    BLENDER_UI_AVAILABLE = True
except ImportError:
    BLENDER_UI_AVAILABLE = False
