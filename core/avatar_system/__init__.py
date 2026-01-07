"""
Eidolon - Avatar System
Avatars 3D uniques lies aux vaults avec tokenisation Bitcoin

SYSTEME PIONNIER:
- Seuls les 10,000 premiers vaults peuvent avoir un avatar
- Vaults #1-33 (Supreme): Rarete garantie mythical+, x2 attributs
- Vaults #34-100 (Legendary): Rarete garantie legendary+, x1.75 attributs
- Vaults #101-1000 (Elite): Rarete garantie epic+, x1.5 attributs
- Vaults #1001-10000 (Pioneer): Rarete garantie rare+, x1.25 attributs
- Vaults #10001+: PAS D'AVATAR DISPONIBLE

CLASSES DE PERSONNAGE:
- 8 classes avec affinites d'items uniques
- Quantum Sage reservee aux vaults Supreme (#1-33)
- Chaque classe a des bonus de stats et abilities
"""

from .avatar_generator import (
    QuantumAvatarGenerator, 
    AvatarDNA,
    AvatarStats,
    AvatarClass,
    # Constantes pionniers
    PIONEER_AVATAR_LIMIT,
    PIONEER_TIERS,
    PIONEER_RARITY_BONUS,
    PIONEER_ATTRIBUTE_MULTIPLIER,
    PIONEER_MIN_RARITY,
    # Constantes avatars
    GEOMETRIC_TYPES,
    EXCLUSIVE_GEOMETRIC_TYPES,
    RARITY_TIERS,
    # Constantes stats
    PRIMARY_STATS,
    SECONDARY_STATS,
    QUANTUM_STATS,
    RARITY_STAT_MULTIPLIER,
    PIONEER_STAT_BONUS,
    MAX_LEVEL,
    # Constantes classes
    AVATAR_CLASSES,
    GEOMETRIC_CLASS_AFFINITY,
    ITEM_CATEGORIES,
)
from .avatar_tokenizer import AvatarTokenizer, AvatarToken
from .avatar_manager import AvatarManager
from .threejs_renderer import ThreeJSAvatarRenderer, render_avatar_threejs
from .avatar_evolution import (
    AvatarEvolutionSystem,
    AvatarEvolutionState,
    EvolutionStage,
    EvolutionPath,
    get_evolution_system,
)

__all__ = [
    # Classes principales
    'QuantumAvatarGenerator',
    'AvatarDNA',
    'AvatarStats',
    'AvatarClass',
    'AvatarTokenizer',
    'AvatarToken',
    'AvatarManager',
    # Constantes pionniers
    'PIONEER_AVATAR_LIMIT',
    'PIONEER_TIERS',
    'PIONEER_RARITY_BONUS',
    'PIONEER_ATTRIBUTE_MULTIPLIER',
    'PIONEER_MIN_RARITY',
    # Constantes avatars
    'GEOMETRIC_TYPES',
    'EXCLUSIVE_GEOMETRIC_TYPES',
    'RARITY_TIERS',
    # Constantes stats
    'PRIMARY_STATS',
    'SECONDARY_STATS',
    'QUANTUM_STATS',
    'RARITY_STAT_MULTIPLIER',
    'PIONEER_STAT_BONUS',
    'MAX_LEVEL',
    # Constantes classes
    'AVATAR_CLASSES',
    'GEOMETRIC_CLASS_AFFINITY',
    'ITEM_CATEGORIES',
    # Three.js Renderer
    'ThreeJSAvatarRenderer',
    'render_avatar_threejs',
    # Evolution System
    'AvatarEvolutionSystem',
    'AvatarEvolutionState',
    'EvolutionStage',
    'EvolutionPath',
    'get_evolution_system',
]
