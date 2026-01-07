"""
Poly-Spinor Nexus 7D - Avatar System
Avatars 3D uniques lies aux vaults avec tokenisation Bitcoin

SYSTEME PIONNIER:
- Seuls les 10,000 premiers vaults peuvent avoir un avatar
- Vaults #1-33 (Supreme): Rarete garantie mythical+, x2 attributs
- Vaults #34-100 (Legendary): Rarete garantie legendary+, x1.75 attributs
- Vaults #101-1000 (Elite): Rarete garantie epic+, x1.5 attributs
- Vaults #1001-10000 (Pioneer): Rarete garantie rare+, x1.25 attributs
- Vaults #10001+: PAS D'AVATAR DISPONIBLE
"""

from .avatar_generator import (
    QuantumAvatarGenerator, 
    AvatarDNA,
    PIONEER_AVATAR_LIMIT,
    PIONEER_TIERS,
    PIONEER_RARITY_BONUS,
    PIONEER_ATTRIBUTE_MULTIPLIER,
    PIONEER_MIN_RARITY,
    GEOMETRIC_TYPES,
    EXCLUSIVE_GEOMETRIC_TYPES,
    RARITY_TIERS
)
from .avatar_tokenizer import AvatarTokenizer, AvatarToken
from .avatar_manager import AvatarManager

__all__ = [
    # Classes principales
    'QuantumAvatarGenerator',
    'AvatarDNA', 
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
    'RARITY_TIERS'
]
