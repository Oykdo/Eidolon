#!/usr/bin/env python3
"""
Generateur d'avatars 3D uniques bases sur les donnees cryptographiques du vault
Chaque avatar est un NFT unique lie perpetuellement au vault
"""

import hashlib
import json
import struct
import math
import secrets
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ============================================================================
# CONSTANTES
# ============================================================================

AVATAR_VERSION = 1

# Limite des vaults pionniers pouvant obtenir un avatar
PIONEER_AVATAR_LIMIT = 10000  # Seuls les 10,000 premiers vaults peuvent avoir un avatar

# Tiers de pionniers avec bonus RNG
PIONEER_TIERS = {
    "supreme": (1, 33),        # Supreme Architects - RNG maximal
    "legendary": (34, 100),    # Legendary Pioneers - Tres haut RNG
    "elite": (101, 1000),      # Elite Pioneers - Haut RNG
    "pioneer": (1001, 10000),  # Standard Pioneers - RNG normal ameliore
}

# Bonus de rarete par tier de pionnier
PIONEER_RARITY_BONUS = {
    "supreme": 50.0,     # +50 points de rarete (garantit mythical/primordial)
    "legendary": 35.0,   # +35 points (garantit legendary+)
    "elite": 20.0,       # +20 points (garantit epic+)
    "pioneer": 10.0,     # +10 points (ameliore les chances)
}

# Multiplicateurs d'attributs par tier
PIONEER_ATTRIBUTE_MULTIPLIER = {
    "supreme": 2.0,      # x2 sur tous les attributs
    "legendary": 1.75,   # x1.75
    "elite": 1.5,        # x1.5
    "pioneer": 1.25,     # x1.25
}

GEOMETRIC_TYPES = [
    "quantum_sphere",
    "spinor_torus", 
    "bell_polyhedron",
    "clifford_lattice",
    "entropy_fractal",
    "7d_projection",
    "hybrid_form",
    "nexus_crystal"
]

# Types geometriques exclusifs par tier
EXCLUSIVE_GEOMETRIC_TYPES = {
    "supreme": ["nexus_crystal", "7d_projection", "hybrid_form"],  # Types les plus rares
    "legendary": ["nexus_crystal", "7d_projection", "hybrid_form", "entropy_fractal"],
    "elite": GEOMETRIC_TYPES,  # Tous les types
    "pioneer": GEOMETRIC_TYPES,
}

RARITY_TIERS = {
    "common": (0, 20),
    "uncommon": (20, 40),
    "rare": (40, 60),
    "epic": (60, 75),
    "legendary": (75, 90),
    "mythical": (90, 97),
    "primordial": (97, 100)
}

# Rarete minimum garantie par tier
PIONEER_MIN_RARITY = {
    "supreme": "mythical",    # Au minimum mythical
    "legendary": "legendary", # Au minimum legendary
    "elite": "epic",          # Au minimum epic
    "pioneer": "rare",        # Au minimum rare
}

# ============================================================================
# STATS DE PERSONNAGE
# ============================================================================

# Stats primaires (base 1-100, affectees par rarete et tier)
PRIMARY_STATS = [
    "strength",      # Force - degats physiques
    "agility",       # Agilite - esquive, vitesse
    "intelligence", # Intelligence - degats magiques, mana
    "vitality",      # Vitalite - points de vie
    "luck",          # Chance - critiques, drops
    "charisma",      # Charisme - commerce, diplomatie
]

# Stats secondaires (derivees des primaires)
SECONDARY_STATS = [
    "hp",            # Points de vie (vitality * 10 + base)
    "mp",            # Points de mana (intelligence * 5 + base)
    "attack",        # Attaque physique (strength * 2)
    "magic_attack",  # Attaque magique (intelligence * 2)
    "defense",       # Defense physique (vitality + strength/2)
    "magic_defense", # Defense magique (intelligence + vitality/2)
    "speed",         # Vitesse (agility * 1.5)
    "crit_rate",     # Taux critique % (luck / 2)
    "crit_damage",   # Degats critiques % (150 + luck)
    "evasion",       # Esquive % (agility / 3)
    "accuracy",      # Precision % (agility / 2 + luck / 4)
]

# Stats speciales (uniques aux avatars quantiques)
QUANTUM_STATS = [
    "quantum_power",      # Puissance quantique (pour abilities speciales)
    "dimensional_sync",   # Synchronisation dimensionnelle
    "entropy_resistance", # Resistance a l'entropie
    "temporal_flux",      # Flux temporel (cooldown reduction)
    "nexus_affinity",     # Affinite avec le Nexus
]

# Bonus de stats par rarete
RARITY_STAT_MULTIPLIER = {
    "common": 1.0,
    "uncommon": 1.15,
    "rare": 1.3,
    "epic": 1.5,
    "legendary": 1.75,
    "mythical": 2.0,
    "primordial": 2.5,
}

# ============================================================================
# BASE STAT ROLL RANGES BY RARITY
# ============================================================================
# Each stat is rolled within a range based on avatar rarity
# Format: (min, max) - determines the base stat before multipliers

RARITY_STAT_RANGES = {
    # Common: Low base stats (5-15)
    "common": {
        "min": 5,
        "max": 15,
        "variance": 5,      # Random variance
        "guaranteed_high": 0,  # Number of stats guaranteed to be high
    },
    # Uncommon: Slightly better (8-20)
    "uncommon": {
        "min": 8,
        "max": 20,
        "variance": 6,
        "guaranteed_high": 1,
    },
    # Rare: Good base stats (12-25)
    "rare": {
        "min": 12,
        "max": 25,
        "variance": 7,
        "guaranteed_high": 1,
    },
    # Epic: High base stats (18-35)
    "epic": {
        "min": 18,
        "max": 35,
        "variance": 8,
        "guaranteed_high": 2,
    },
    # Legendary: Very high (25-50)
    "legendary": {
        "min": 25,
        "max": 50,
        "variance": 10,
        "guaranteed_high": 2,
    },
    # Mythical: Exceptional (35-70)
    "mythical": {
        "min": 35,
        "max": 70,
        "variance": 15,
        "guaranteed_high": 3,
    },
    # Primordial: Maximum potential (50-100)
    "primordial": {
        "min": 50,
        "max": 100,
        "variance": 20,
        "guaranteed_high": 4,
    },
}

# Stat affinities by geometric type (which stats are naturally higher)
GEOMETRIC_STAT_AFFINITY = {
    "quantum_sphere": ["intelligence", "luck"],
    "spinor_torus": ["agility", "charisma"],
    "bell_polyhedron": ["vitality", "strength"],
    "clifford_lattice": ["intelligence", "vitality"],
    "entropy_fractal": ["luck", "agility"],
    "7d_projection": ["intelligence", "charisma", "luck"],
    "hybrid_form": ["strength", "agility", "vitality"],
    "nexus_crystal": ["intelligence", "luck", "charisma"],
}

# Bonus for affine stats
AFFINITY_BONUS = 0.25  # +25% to affine stats

# Bonus de stats par tier pionnier
PIONEER_STAT_BONUS = {
    "supreme": {"base": 20, "multiplier": 1.5},     # +20 base, x1.5
    "legendary": {"base": 15, "multiplier": 1.35},  # +15 base, x1.35
    "elite": {"base": 10, "multiplier": 1.2},       # +10 base, x1.2
    "pioneer": {"base": 5, "multiplier": 1.1},      # +5 base, x1.1
}

# Niveau max et XP
MAX_LEVEL = 100
XP_PER_LEVEL = [100 * (level ** 1.5) for level in range(1, MAX_LEVEL + 1)]


# ============================================================================
# CLASSES DE PERSONNAGE
# ============================================================================

# Categories d'items (doivent correspondre a AlchemicalCategory)
ITEM_CATEGORIES = [
    "potion", "elixir", "rune", "scroll", "essence",
    "talisman", "orb", "seal", "sigil", "crystal"
]

# Classes disponibles
AVATAR_CLASSES = {
    "alchemist": {
        "name": "Alchimiste",
        "description": "Maitre des transmutations et des potions",
        "icon": "⚗️",
        "color": "#00ff88",
        "primary_stat": "intelligence",
        "secondary_stat": "luck",
        "item_affinities": {
            "potion": 2.0,      # +100% efficacite potions
            "elixir": 1.8,      # +80% elixirs
            "essence": 1.5,     # +50% essences
            "crystal": 1.3,     # +30% cristaux
            "scroll": 1.0,
            "rune": 0.9,
            "talisman": 0.8,
            "orb": 1.0,
            "seal": 0.7,
            "sigil": 0.8,
        },
        "abilities": ["transmutation_mastery", "potion_enhancement", "essence_extraction"],
        "stat_bonuses": {"intelligence": 10, "luck": 5, "charisma": 3},
    },
    "runemaster": {
        "name": "Maitre des Runes",
        "description": "Inscripteur de symboles de pouvoir ancestraux",
        "icon": "ᚱ",
        "color": "#ff6600",
        "primary_stat": "intelligence",
        "secondary_stat": "vitality",
        "item_affinities": {
            "rune": 2.0,        # +100% runes
            "sigil": 1.8,       # +80% sigils
            "scroll": 1.5,      # +50% parchemins
            "seal": 1.4,        # +40% sceaux
            "crystal": 1.2,
            "potion": 0.8,
            "elixir": 0.9,
            "essence": 1.0,
            "talisman": 1.1,
            "orb": 1.0,
        },
        "abilities": ["rune_inscription", "sigil_activation", "ancient_knowledge"],
        "stat_bonuses": {"intelligence": 8, "vitality": 5, "strength": 2},
    },
    "crystalmancer": {
        "name": "Cristallomancien",
        "description": "Canalise l'energie a travers les cristaux",
        "icon": "💎",
        "color": "#00ffff",
        "primary_stat": "intelligence",
        "secondary_stat": "charisma",
        "item_affinities": {
            "crystal": 2.0,     # +100% cristaux
            "orb": 1.8,         # +80% orbes
            "essence": 1.5,     # +50% essences
            "talisman": 1.3,
            "potion": 1.0,
            "elixir": 1.1,
            "rune": 1.0,
            "scroll": 0.9,
            "seal": 0.8,
            "sigil": 1.0,
        },
        "abilities": ["crystal_resonance", "energy_amplification", "gem_fusion"],
        "stat_bonuses": {"intelligence": 7, "charisma": 6, "luck": 4},
    },
    "guardian": {
        "name": "Gardien",
        "description": "Protecteur utilisant talismans et sceaux",
        "icon": "🛡️",
        "color": "#4488ff",
        "primary_stat": "vitality",
        "secondary_stat": "strength",
        "item_affinities": {
            "talisman": 2.0,    # +100% talismans
            "seal": 1.8,        # +80% sceaux
            "orb": 1.4,         # +40% orbes
            "rune": 1.3,
            "crystal": 1.1,
            "potion": 1.2,
            "elixir": 1.0,
            "essence": 0.9,
            "scroll": 0.8,
            "sigil": 1.0,
        },
        "abilities": ["protective_ward", "seal_mastery", "damage_absorption"],
        "stat_bonuses": {"vitality": 10, "strength": 5, "defense": 10},
    },
    "shadow_weaver": {
        "name": "Tisseur d'Ombre",
        "description": "Manipule les sigils et les energies sombres",
        "icon": "🌑",
        "color": "#8800aa",
        "primary_stat": "agility",
        "secondary_stat": "luck",
        "item_affinities": {
            "sigil": 2.0,       # +100% sigils
            "seal": 1.6,        # +60% sceaux
            "scroll": 1.5,      # +50% parchemins
            "essence": 1.4,
            "potion": 1.2,
            "rune": 1.0,
            "crystal": 0.9,
            "talisman": 0.8,
            "orb": 1.0,
            "elixir": 1.1,
        },
        "abilities": ["shadow_step", "mark_of_doom", "essence_drain"],
        "stat_bonuses": {"agility": 10, "luck": 6, "crit_rate": 5},
    },
    "elementalist": {
        "name": "Elementaliste",
        "description": "Controle les essences elementaires",
        "icon": "🔥",
        "color": "#ff4400",
        "primary_stat": "intelligence",
        "secondary_stat": "agility",
        "item_affinities": {
            "essence": 2.0,     # +100% essences
            "orb": 1.7,         # +70% orbes
            "crystal": 1.5,     # +50% cristaux
            "scroll": 1.3,
            "potion": 1.2,
            "rune": 1.1,
            "elixir": 1.0,
            "talisman": 0.9,
            "seal": 0.8,
            "sigil": 1.0,
        },
        "abilities": ["elemental_mastery", "essence_infusion", "elemental_burst"],
        "stat_bonuses": {"intelligence": 8, "agility": 5, "magic_attack": 10},
    },
    "oracle": {
        "name": "Oracle",
        "description": "Lit l'avenir dans les parchemins anciens",
        "icon": "📜",
        "color": "#ffdd00",
        "primary_stat": "luck",
        "secondary_stat": "intelligence",
        "item_affinities": {
            "scroll": 2.0,      # +100% parchemins
            "sigil": 1.6,       # +60% sigils
            "crystal": 1.4,     # +40% cristaux
            "rune": 1.3,
            "elixir": 1.2,
            "potion": 1.1,
            "essence": 1.0,
            "talisman": 1.0,
            "orb": 0.9,
            "seal": 0.8,
        },
        "abilities": ["prophecy", "fate_manipulation", "ancient_wisdom"],
        "stat_bonuses": {"luck": 12, "intelligence": 5, "crit_damage": 20},
    },
    "quantum_sage": {
        "name": "Sage Quantique",
        "description": "Maitre des dimensions et du Nexus (Supreme uniquement)",
        "icon": "🌀",
        "color": "#ff00ff",
        "primary_stat": "intelligence",
        "secondary_stat": "vitality",
        "item_affinities": {
            # Affinite equilibree mais elevee partout
            "potion": 1.5,
            "elixir": 1.5,
            "rune": 1.5,
            "scroll": 1.5,
            "essence": 1.5,
            "talisman": 1.5,
            "orb": 1.8,         # Specialite: orbes
            "seal": 1.5,
            "sigil": 1.5,
            "crystal": 1.8,     # Specialite: cristaux
        },
        "abilities": ["dimensional_rift", "quantum_manipulation", "nexus_communion", "reality_warp"],
        "abilities_supreme_only": True,
        "stat_bonuses": {"intelligence": 15, "vitality": 10, "quantum_power": 50},
        "supreme_only": True,  # Reservee aux vaults 1-33
    },
}

# Classes par type geometrique (affinite naturelle)
GEOMETRIC_CLASS_AFFINITY = {
    "quantum_sphere": ["crystalmancer", "elementalist"],
    "spinor_torus": ["runemaster", "oracle"],
    "bell_polyhedron": ["guardian", "alchemist"],
    "clifford_lattice": ["runemaster", "guardian"],
    "entropy_fractal": ["shadow_weaver", "elementalist"],
    "7d_projection": ["quantum_sage", "oracle"],
    "hybrid_form": ["alchemist", "crystalmancer"],
    "nexus_crystal": ["quantum_sage", "crystalmancer"],
}


# ============================================================================
# STRUCTURES DE DONNEES
# ============================================================================

@dataclass
class AvatarClass:
    """Classe du personnage avec affinites d'items"""
    class_id: str
    name: str
    description: str
    icon: str
    color: str
    primary_stat: str
    secondary_stat: str
    item_affinities: Dict[str, float] = field(default_factory=dict)
    abilities: List[str] = field(default_factory=list)
    stat_bonuses: Dict[str, int] = field(default_factory=dict)
    is_supreme_only: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AvatarClass':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def from_class_id(cls, class_id: str) -> Optional['AvatarClass']:
        """Cree une instance depuis l'ID de classe"""
        if class_id not in AVATAR_CLASSES:
            return None
        
        class_data = AVATAR_CLASSES[class_id]
        return cls(
            class_id=class_id,
            name=class_data["name"],
            description=class_data["description"],
            icon=class_data["icon"],
            color=class_data["color"],
            primary_stat=class_data["primary_stat"],
            secondary_stat=class_data["secondary_stat"],
            item_affinities=class_data.get("item_affinities", {}),
            abilities=class_data.get("abilities", []),
            stat_bonuses=class_data.get("stat_bonuses", {}),
            is_supreme_only=class_data.get("supreme_only", False)
        )
    
    def get_item_affinity(self, item_category: str) -> float:
        """Retourne le multiplicateur d'affinite pour une categorie d'item"""
        return self.item_affinities.get(item_category.lower(), 1.0)
    
    def get_affinity_bonus_text(self, item_category: str) -> str:
        """Retourne le texte du bonus pour une categorie"""
        affinity = self.get_item_affinity(item_category)
        if affinity > 1.0:
            return f"+{int((affinity - 1) * 100)}%"
        elif affinity < 1.0:
            return f"-{int((1 - affinity) * 100)}%"
        return "0%"


@dataclass
class AvatarStats:
    """Stats de combat/RPG du personnage"""
    # Niveau et XP
    level: int = 1
    xp: int = 0
    xp_to_next: int = 100
    
    # Stats primaires (base)
    strength: int = 10
    agility: int = 10
    intelligence: int = 10
    vitality: int = 10
    luck: int = 10
    charisma: int = 10
    
    # Stats secondaires (calculees)
    hp: int = 100
    hp_max: int = 100
    mp: int = 50
    mp_max: int = 50
    attack: int = 20
    magic_attack: int = 20
    defense: int = 15
    magic_defense: int = 15
    speed: int = 15
    crit_rate: float = 5.0
    crit_damage: float = 150.0
    evasion: float = 3.0
    accuracy: float = 90.0
    
    # Stats quantiques (speciales)
    quantum_power: int = 0
    dimensional_sync: float = 0.0
    entropy_resistance: float = 0.0
    temporal_flux: float = 0.0
    nexus_affinity: float = 0.0
    
    # Points de stats disponibles
    stat_points: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AvatarStats':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def recalculate_secondary(self):
        """Recalcule les stats secondaires a partir des primaires"""
        self.hp_max = self.vitality * 10 + 100
        self.mp_max = self.intelligence * 5 + 50
        self.attack = self.strength * 2
        self.magic_attack = self.intelligence * 2
        self.defense = self.vitality + self.strength // 2
        self.magic_defense = self.intelligence + self.vitality // 2
        self.speed = int(self.agility * 1.5)
        self.crit_rate = round(self.luck / 2, 1)
        self.crit_damage = round(150 + self.luck, 1)
        self.evasion = round(self.agility / 3, 1)
        self.accuracy = round(90 + self.agility / 2 + self.luck / 4, 1)
    
    def add_xp(self, amount: int) -> List[str]:
        """Ajoute de l'XP et gere le level up. Retourne les messages."""
        messages = []
        self.xp += amount
        
        while self.xp >= self.xp_to_next and self.level < MAX_LEVEL:
            self.xp -= self.xp_to_next
            self.level += 1
            self.stat_points += 5  # 5 points par niveau
            self.xp_to_next = int(100 * (self.level ** 1.5))
            
            # Bonus de stats auto
            self.vitality += 2
            self.strength += 1
            self.agility += 1
            self.intelligence += 1
            
            self.recalculate_secondary()
            self.hp = self.hp_max  # Full heal on level up
            self.mp = self.mp_max
            
            messages.append(f"Level Up! Niveau {self.level}")
        
        return messages
    
    def allocate_stat(self, stat_name: str, points: int = 1) -> bool:
        """Alloue des points de stats. Retourne True si succes."""
        if self.stat_points < points:
            return False
        
        if stat_name not in PRIMARY_STATS:
            return False
        
        current = getattr(self, stat_name)
        setattr(self, stat_name, current + points)
        self.stat_points -= points
        self.recalculate_secondary()
        return True


@dataclass
class AvatarDNA:
    """ADN cryptographique de l'avatar"""
    vault_hash: str
    seed_values: List[int]
    geometric_type: int
    geometric_name: str
    color_palette: List[str]
    attributes: Dict[str, float]
    rarity_score: float
    rarity_tier: str
    generation: int
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AvatarDNA':
        return cls(**data)


@dataclass
class Avatar3D:
    """Representation complete d'un avatar 3D"""
    avatar_id: str
    vault_id: str
    dna: AvatarDNA
    
    # Geometrie
    vertices: List[List[float]] = field(default_factory=list)
    faces: List[List[int]] = field(default_factory=list)
    normals: List[List[float]] = field(default_factory=list)
    uvs: List[List[float]] = field(default_factory=list)
    
    # Fichiers
    obj_path: Optional[str] = None
    texture_path: Optional[str] = None
    preview_path: Optional[str] = None
    
    # Metadata
    created_at: str = ""
    version: int = AVATAR_VERSION
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['dna'] = self.dna.to_dict()
        return d


# ============================================================================
# GENERATEUR D'AVATARS
# ============================================================================

class QuantumAvatarGenerator:
    """Generateur d'avatars 3D base sur l'entropie quantique du vault"""
    
    def __init__(self, vault_data: bytes = None, vault_id: str = None, 
                 vault_path: str = None, generation: int = 1,
                 vault_number: int = None):
        """
        Initialise le generateur d'avatar.
        
        Args:
            vault_data: Donnees brutes du vault (bytes)
            vault_id: ID du vault
            vault_path: Chemin vers le fichier .blend_data
            generation: Generation de l'avatar
            vault_number: Numero du vault (1-10000 pour les pionniers)
        """
        self.generation = generation
        self.vault_id = vault_id or secrets.token_hex(8)
        self.vault_number = vault_number
        
        # Determiner le tier du pionnier
        self.pioneer_tier = self._get_pioneer_tier(vault_number)
        
        # Charger les donnees
        if vault_data:
            self.raw_data = vault_data
        elif vault_path:
            with open(vault_path, 'rb') as f:
                self.raw_data = f.read()
        else:
            # Generer des donnees aleatoires pour demo
            self.raw_data = secrets.token_bytes(1024)
        
        # Extraire l'ADN
        self.dna = self._extract_dna()
        self.avatar: Optional[Avatar3D] = None
    
    @staticmethod
    def can_have_avatar(vault_number: int) -> Tuple[bool, str]:
        """
        Verifie si un vault peut avoir un avatar.
        Seuls les 10,000 premiers vaults peuvent en avoir un.
        
        Returns:
            (can_have, reason)
        """
        if vault_number is None:
            return False, "Numero de vault requis"
        
        if vault_number < 1:
            return False, "Numero de vault invalide"
        
        if vault_number > PIONEER_AVATAR_LIMIT:
            return False, f"Seuls les {PIONEER_AVATAR_LIMIT:,} premiers vaults peuvent avoir un avatar"
        
        return True, "OK"
    
    def _get_pioneer_tier(self, vault_number: int) -> Optional[str]:
        """Determine le tier du pionnier selon son numero de vault"""
        if vault_number is None:
            return None
        
        for tier, (min_num, max_num) in PIONEER_TIERS.items():
            if min_num <= vault_number <= max_num:
                return tier
        
        return None
    
    def _extract_dna(self) -> AvatarDNA:
        """Extrait l'ADN cryptographique des donnees du vault avec bonus pionnier"""
        # Hash principal
        data = self.raw_data if isinstance(self.raw_data, bytes) else self.raw_data.encode('utf-8')
        vault_hash = hashlib.sha256(data).hexdigest()
        
        # Generer des valeurs de seed
        seed_bytes = bytes.fromhex(vault_hash[:32])
        seed_values = [int(b) for b in seed_bytes[:16]]
        
        # Type geometrique (avec restriction pour certains tiers)
        geometric_name = self._select_geometric_type(seed_values)
        geometric_type = GEOMETRIC_TYPES.index(geometric_name)
        
        # Palette de couleurs (amelioree pour pionniers)
        color_palette = self._generate_color_palette(vault_hash)
        
        # Attributs (avec multiplicateur pionnier)
        attributes = self._calculate_attributes(seed_values)
        
        # Rarete (avec bonus pionnier)
        rarity_score = self._calculate_rarity(seed_values, vault_hash)
        rarity_tier = self._get_rarity_tier(rarity_score)
        
        return AvatarDNA(
            vault_hash=vault_hash,
            seed_values=seed_values,
            geometric_type=geometric_type,
            geometric_name=geometric_name,
            color_palette=color_palette,
            attributes=attributes,
            rarity_score=rarity_score,
            rarity_tier=rarity_tier,
            generation=self.generation
        )
    
    def _select_geometric_type(self, seed_values: List[int]) -> str:
        """Selectionne le type geometrique selon le tier"""
        if self.pioneer_tier and self.pioneer_tier in EXCLUSIVE_GEOMETRIC_TYPES:
            available_types = EXCLUSIVE_GEOMETRIC_TYPES[self.pioneer_tier]
        else:
            available_types = GEOMETRIC_TYPES
        
        # Selection basee sur le seed
        type_index = sum(seed_values[:4]) % len(available_types)
        return available_types[type_index]
    
    def _generate_color_palette(self, vault_hash: str) -> List[str]:
        """Genere une palette de couleurs unique"""
        colors = []
        
        # 3 couleurs primaires du hash
        for i in range(0, 18, 6):
            hex_color = vault_hash[i:i+6]
            colors.append(f'#{hex_color}')
        
        # Couleur complementaire
        base_r = int(vault_hash[0:2], 16)
        base_g = int(vault_hash[2:4], 16)
        base_b = int(vault_hash[4:6], 16)
        
        comp_r = 255 - base_r
        comp_g = 255 - base_g
        comp_b = 255 - base_b
        colors.append(f'#{comp_r:02x}{comp_g:02x}{comp_b:02x}')
        
        # Couleur accentuee
        accent_r = (base_r + 128) % 256
        accent_g = (base_g + 64) % 256
        accent_b = (base_b + 192) % 256
        colors.append(f'#{accent_r:02x}{accent_g:02x}{accent_b:02x}')
        
        return colors[:5]
    
    def _calculate_attributes(self, seed_values: List[int]) -> Dict[str, float]:
        """Calcule les attributs de l'avatar avec multiplicateur pionnier"""
        # Multiplicateur selon le tier
        multiplier = 1.0
        if self.pioneer_tier and self.pioneer_tier in PIONEER_ATTRIBUTE_MULTIPLIER:
            multiplier = PIONEER_ATTRIBUTE_MULTIPLIER[self.pioneer_tier]
        
        # Attributs de base
        base_attrs = {
            'quantum_entropy': (sum(seed_values[:4]) / 1024) * 100,
            'spinor_complexity': (seed_values[4] / 255) * 100,
            'bell_verification': (seed_values[5] / 255) * 100,
            'polyhedral_symmetry': (seed_values[6] / 255) * 100,
            'cryptographic_strength': (seed_values[7] / 255) * 100,
            'temporal_stability': (seed_values[8] / 255) * 100,
            'spatial_coherence': (seed_values[9] / 255) * 100,
            'dimensional_depth': (seed_values[10] / 255) * 7,
            'fractal_dimension': 1.0 + (seed_values[11] / 255) * 2,
            'energy_resonance': (seed_values[12] / 255) * 100
        }
        
        # Appliquer le multiplicateur (cap a 100 sauf pour certains attributs)
        result = {}
        for attr, value in base_attrs.items():
            boosted = value * multiplier
            if attr in ['dimensional_depth', 'fractal_dimension']:
                result[attr] = round(boosted, 3)
            else:
                result[attr] = round(min(100, boosted), 2)
        
        # Bonus special pour les Supreme (1-33)
        if self.pioneer_tier == "supreme":
            result['pioneer_blessing'] = 100.0  # Attribut exclusif
            result['dimensional_depth'] = 7.0   # Maximum
        
        return result
    
    def _calculate_rarity(self, seed_values: List[int], vault_hash: str) -> float:
        """Calcule le score de rarete (0-100) avec bonus pionnier"""
        # Base sur les valeurs extremes
        extreme_count = sum(1 for v in seed_values if v < 10 or v > 245)
        extreme_bonus = extreme_count * 5
        
        # Base sur les patterns rares dans le hash
        rare_patterns = ['00', 'ff', '777', '888', 'abc', 'def']
        pattern_bonus = sum(3 for p in rare_patterns if p in vault_hash.lower())
        
        # Base sur l'entropie
        entropy_score = (seed_values[13] / 255) * 30
        
        # Score final de base
        base_score = (seed_values[14] / 255) * 40
        total = base_score + extreme_bonus + pattern_bonus + entropy_score
        
        # Appliquer le bonus pionnier
        if self.pioneer_tier and self.pioneer_tier in PIONEER_RARITY_BONUS:
            pioneer_bonus = PIONEER_RARITY_BONUS[self.pioneer_tier]
            total += pioneer_bonus
        
        # S'assurer que le score respecte le minimum garanti du tier
        if self.pioneer_tier and self.pioneer_tier in PIONEER_MIN_RARITY:
            min_rarity = PIONEER_MIN_RARITY[self.pioneer_tier]
            min_score = RARITY_TIERS.get(min_rarity, (0, 0))[0]
            total = max(total, min_score + 1)  # +1 pour etre dans le tier
        
        return min(100, max(0, round(total, 2)))
    
    def _get_rarity_tier(self, score: float) -> str:
        """Determine le tier de rarete"""
        for tier, (min_val, max_val) in RARITY_TIERS.items():
            if min_val <= score < max_val:
                return tier
        return "primordial"
    
    def get_pioneer_info(self) -> Optional[Dict]:
        """Retourne les informations du tier pionnier"""
        if not self.pioneer_tier:
            return None
        
        return {
            'tier': self.pioneer_tier,
            'vault_number': self.vault_number,
            'rarity_bonus': PIONEER_RARITY_BONUS.get(self.pioneer_tier, 0),
            'attribute_multiplier': PIONEER_ATTRIBUTE_MULTIPLIER.get(self.pioneer_tier, 1.0),
            'min_rarity': PIONEER_MIN_RARITY.get(self.pioneer_tier, 'common'),
            'exclusive_types': EXCLUSIVE_GEOMETRIC_TYPES.get(self.pioneer_tier, [])
        }
    
    def generate_stats(self) -> AvatarStats:
        """
        Genere les stats de combat du personnage basees sur:
        - L'ADN du vault (seed_values)
        - La rarete de l'avatar (determine les plages de roll)
        - Le type geometrique (affinites de stats)
        - Le tier pionnier (bonus)
        
        Systeme de roll:
        1. Chaque rarete a une plage de stats (min-max)
        2. Les stats affines au type geometrique recoivent +25% 
        3. Un nombre de stats sont garanties "high roll" selon la rarete
        4. Bonus pioneer applique en dernier
        """
        dna = self.dna
        seed = dna.seed_values
        rarity = dna.rarity_tier.lower()
        geometric_type = dna.geometric_name
        
        # Get stat ranges for this rarity
        ranges = RARITY_STAT_RANGES.get(rarity, RARITY_STAT_RANGES["common"])
        stat_min = ranges["min"]
        stat_max = ranges["max"]
        variance = ranges["variance"]
        guaranteed_high = ranges["guaranteed_high"]
        
        # Get affine stats for this geometric type
        affine_stats = GEOMETRIC_STAT_AFFINITY.get(geometric_type, [])
        
        # Bonus pionnier
        pioneer_bonus = PIONEER_STAT_BONUS.get(self.pioneer_tier, {"base": 0, "multiplier": 1.0})
        base_bonus = pioneer_bonus["base"]
        pioneer_mult = pioneer_bonus["multiplier"]
        
        # Roll a stat using DNA seed
        def roll_stat(seed_idx: int, stat_name: str, force_high: bool = False) -> int:
            raw = seed[seed_idx % len(seed)]
            
            if force_high:
                # High roll: upper 30% of range
                range_size = stat_max - stat_min
                high_min = stat_min + int(range_size * 0.7)
                roll_range = stat_max - high_min
                base_value = high_min + int((raw / 255) * roll_range)
            else:
                # Normal roll within variance
                midpoint = (stat_min + stat_max) // 2
                offset = int((raw / 255 - 0.5) * variance * 2)
                base_value = midpoint + offset
                base_value = max(stat_min, min(stat_max, base_value))
            
            # Apply affinity bonus
            if stat_name in affine_stats:
                base_value = int(base_value * (1 + AFFINITY_BONUS))
            
            # Apply pioneer bonus
            final_value = int((base_value + base_bonus) * pioneer_mult)
            
            return max(1, min(100, final_value))
        
        # Determine which stats get high rolls
        all_stats = ["strength", "agility", "intelligence", "vitality", "luck", "charisma"]
        
        # Prioritize affine stats for high rolls
        high_roll_stats = set()
        for stat in affine_stats:
            if stat in all_stats and len(high_roll_stats) < guaranteed_high:
                high_roll_stats.add(stat)
        
        # Fill remaining high rolls with random stats based on seed
        remaining_stats = [s for s in all_stats if s not in high_roll_stats]
        for i, stat in enumerate(remaining_stats):
            if len(high_roll_stats) >= guaranteed_high:
                break
            # Use seed to determine if this stat gets high roll
            if seed[(i + 10) % len(seed)] > 128:
                high_roll_stats.add(stat)
        
        # Roll each stat
        strength = roll_stat(0, "strength", "strength" in high_roll_stats)
        agility = roll_stat(1, "agility", "agility" in high_roll_stats)
        intelligence = roll_stat(2, "intelligence", "intelligence" in high_roll_stats)
        vitality = roll_stat(3, "vitality", "vitality" in high_roll_stats)
        luck = roll_stat(4, "luck", "luck" in high_roll_stats)
        charisma = roll_stat(5, "charisma", "charisma" in high_roll_stats)
        
        # Stats quantiques basees sur les attributs DNA et rarete
        attrs = dna.attributes
        quantum_mult = RARITY_STAT_MULTIPLIER.get(rarity, 1.0) * pioneer_mult
        
        quantum_power = int(attrs.get('quantum_entropy', 50) * quantum_mult)
        dimensional_sync = round(attrs.get('dimensional_depth', 3.5) / 7 * 100 * quantum_mult, 1)
        entropy_resistance = round(attrs.get('cryptographic_strength', 50) * quantum_mult / 2, 1)
        temporal_flux = round(attrs.get('temporal_stability', 50) * quantum_mult / 3, 1)
        nexus_affinity = round(attrs.get('energy_resonance', 50) * quantum_mult / 2, 1)
        
        # Creer l'objet stats
        stats = AvatarStats(
            level=1,
            xp=0,
            xp_to_next=100,
            strength=strength,
            agility=agility,
            intelligence=intelligence,
            vitality=vitality,
            luck=luck,
            charisma=charisma,
            quantum_power=quantum_power,
            dimensional_sync=min(100, dimensional_sync),
            entropy_resistance=min(100, entropy_resistance),
            temporal_flux=min(100, temporal_flux),
            nexus_affinity=min(100, nexus_affinity),
            stat_points=0
        )
        
        # Store roll info for display
        stats._high_roll_stats = list(high_roll_stats)
        stats._affine_stats = affine_stats
        stats._rarity = rarity
        
        # Calculer les stats secondaires
        stats.recalculate_secondary()
        
        # Bonus special Supreme: stats quantiques maximales
        if self.pioneer_tier == "supreme":
            stats.quantum_power = int(stats.quantum_power * 1.5)
            stats.dimensional_sync = 100.0
            stats.nexus_affinity = 100.0
        
        return stats
    
    def get_available_classes(self) -> List[str]:
        """
        Retourne la liste des classes disponibles pour cet avatar.
        Basee sur le type geometrique et le tier pionnier.
        """
        available = []
        geometric_name = self.dna.geometric_name
        
        # Classes avec affinite naturelle pour ce type geometrique
        affine_classes = GEOMETRIC_CLASS_AFFINITY.get(geometric_name, [])
        
        for class_id, class_data in AVATAR_CLASSES.items():
            # Verifier si c'est une classe Supreme-only
            if class_data.get("supreme_only", False):
                if self.pioneer_tier == "supreme":
                    available.append(class_id)
            else:
                available.append(class_id)
        
        # Trier: classes avec affinite en premier
        def sort_key(c):
            if c in affine_classes:
                return (0, affine_classes.index(c))
            return (1, c)
        
        available.sort(key=sort_key)
        return available
    
    def select_class(self, class_id: str = None) -> Optional[AvatarClass]:
        """
        Selectionne une classe pour l'avatar.
        Si aucune classe n'est specifiee, choisit automatiquement basee sur:
        - L'affinite geometrique
        - Les stats dominantes
        """
        available = self.get_available_classes()
        
        if not available:
            return None
        
        # Si une classe est specifiee et valide
        if class_id:
            if class_id in available:
                return AvatarClass.from_class_id(class_id)
            return None
        
        # Selection automatique basee sur le type geometrique
        geometric_name = self.dna.geometric_name
        affine_classes = GEOMETRIC_CLASS_AFFINITY.get(geometric_name, [])
        
        if affine_classes:
            # Prendre la premiere classe affine disponible
            for class_id in affine_classes:
                if class_id in available:
                    return AvatarClass.from_class_id(class_id)
        
        # Fallback: premiere classe disponible
        return AvatarClass.from_class_id(available[0])
    
    def apply_class_bonuses(self, stats: AvatarStats, avatar_class: AvatarClass) -> AvatarStats:
        """Applique les bonus de classe aux stats"""
        bonuses = avatar_class.stat_bonuses
        
        for stat_name, bonus in bonuses.items():
            if hasattr(stats, stat_name):
                current = getattr(stats, stat_name)
                if isinstance(current, (int, float)):
                    setattr(stats, stat_name, current + bonus)
        
        # Recalculer les stats secondaires apres application des bonus
        stats.recalculate_secondary()
        return stats
    
    def generate_geometry(self) -> Dict:
        """Genere la geometrie 3D de l'avatar"""
        dna = self.dna
        
        # Choisir la methode selon le type
        generators = {
            0: self._create_quantum_sphere,
            1: self._create_spinor_torus,
            2: self._create_bell_polyhedron,
            3: self._create_clifford_lattice,
            4: self._create_entropy_fractal,
            5: self._create_7d_projection,
            6: self._create_hybrid_form,
            7: self._create_nexus_crystal
        }
        
        generator = generators.get(dna.geometric_type, self._create_quantum_sphere)
        vertices, faces = generator()
        
        # Appliquer les transformations
        vertices = self._apply_transformations(vertices)
        
        # Calculer les normales
        normals = self._calculate_normals(vertices, faces)
        
        # Generer les UVs
        uvs = self._generate_uvs(vertices)
        
        return {
            'vertices': vertices,
            'faces': faces,
            'normals': normals,
            'uvs': uvs,
            'type': dna.geometric_name,
            'colors': dna.color_palette
        }
    
    def _create_quantum_sphere(self) -> Tuple[List, List]:
        """Cree une sphere quantique avec perturbations"""
        vertices = []
        faces = []
        
        n_lat = 16
        n_lon = 24
        radius = 1.0
        
        # Perturbation basee sur l'ADN
        perturb = self.dna.seed_values[0] / 500
        
        for i in range(n_lat + 1):
            theta = math.pi * i / n_lat
            for j in range(n_lon):
                phi = 2 * math.pi * j / n_lon
                
                # Perturbation quantique
                noise = perturb * math.sin(theta * 5) * math.cos(phi * 3)
                r = radius + noise
                
                x = r * math.sin(theta) * math.cos(phi)
                y = r * math.sin(theta) * math.sin(phi)
                z = r * math.cos(theta)
                
                vertices.append([x, y, z])
        
        # Generer les faces
        for i in range(n_lat):
            for j in range(n_lon):
                v1 = i * n_lon + j
                v2 = i * n_lon + (j + 1) % n_lon
                v3 = (i + 1) * n_lon + j
                v4 = (i + 1) * n_lon + (j + 1) % n_lon
                
                faces.append([v1, v2, v3])
                faces.append([v2, v4, v3])
        
        return vertices, faces
    
    def _create_spinor_torus(self) -> Tuple[List, List]:
        """Cree un tore spinoriel"""
        vertices = []
        faces = []
        
        R = 1.0 + self.dna.seed_values[1] / 500
        r = 0.4 + self.dna.seed_values[2] / 1000
        
        n_u = 24
        n_v = 16
        
        twist = self.dna.seed_values[3] / 100
        
        for i in range(n_u):
            u = 2 * math.pi * i / n_u
            for j in range(n_v):
                v = 2 * math.pi * j / n_v
                
                x = (R + r * math.cos(v)) * math.cos(u)
                y = (R + r * math.cos(v)) * math.sin(u)
                z = r * math.sin(v)
                
                # Twist spinoriel
                x += twist * math.sin(5 * v)
                y += twist * math.cos(5 * v)
                
                vertices.append([x, y, z])
        
        # Generer les faces
        for i in range(n_u):
            for j in range(n_v):
                v1 = i * n_v + j
                v2 = i * n_v + (j + 1) % n_v
                v3 = ((i + 1) % n_u) * n_v + j
                v4 = ((i + 1) % n_u) * n_v + (j + 1) % n_v
                
                faces.append([v1, v2, v3])
                faces.append([v2, v4, v3])
        
        return vertices, faces
    
    def _create_bell_polyhedron(self) -> Tuple[List, List]:
        """Cree un polyedre de Bell (icosaedre modifie)"""
        # Golden ratio
        phi = (1 + math.sqrt(5)) / 2
        
        # Vertices de l'icosaedre
        base_vertices = [
            [-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
            [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
            [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1]
        ]
        
        # Modifier selon l'ADN
        scale = 0.8 + self.dna.seed_values[4] / 500
        vertices = [[v[0] * scale, v[1] * scale, v[2] * scale] for v in base_vertices]
        
        # Faces de l'icosaedre
        faces = [
            [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
            [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
            [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
            [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]
        ]
        
        return vertices, faces
    
    def _create_clifford_lattice(self) -> Tuple[List, List]:
        """Cree un reseau de Clifford"""
        vertices = []
        faces = []
        
        size = 3
        spacing = 0.5 + self.dna.seed_values[5] / 500
        
        # Creer les points du reseau
        for i in range(-size, size + 1):
            for j in range(-size, size + 1):
                for k in range(-size, size + 1):
                    if (i + j + k) % 2 == 0:  # Pattern alterné
                        x = i * spacing
                        y = j * spacing
                        z = k * spacing
                        
                        # Deformation basee sur l'ADN
                        distort = self.dna.seed_values[6] / 1000
                        x += distort * math.sin(y * 2)
                        y += distort * math.cos(z * 2)
                        z += distort * math.sin(x * 2)
                        
                        vertices.append([x, y, z])
        
        # Connecter les points proches
        for i in range(len(vertices)):
            for j in range(i + 1, min(i + 10, len(vertices))):
                dist = sum((vertices[i][k] - vertices[j][k])**2 for k in range(3))**0.5
                if dist < spacing * 1.5:
                    # Creer un triangle avec le point suivant
                    if j + 1 < len(vertices):
                        faces.append([i, j, (j + 1) % len(vertices)])
        
        return vertices, faces
    
    def _create_entropy_fractal(self) -> Tuple[List, List]:
        """Cree un fractal base sur l'entropie"""
        # Tetraedre de base
        vertices = [
            [1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]
        ]
        faces = [
            [0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]
        ]
        
        # Subdiviser selon l'ADN
        iterations = min(3, self.dna.seed_values[7] // 80)
        
        for _ in range(iterations):
            new_vertices = list(vertices)
            new_faces = []
            
            for face in faces:
                # Points milieux
                mid_points = []
                for i in range(3):
                    p1 = vertices[face[i]]
                    p2 = vertices[face[(i + 1) % 3]]
                    mid = [(p1[k] + p2[k]) / 2 for k in range(3)]
                    
                    # Deplacer vers l'exterieur
                    length = sum(m**2 for m in mid)**0.5
                    if length > 0:
                        scale = 1.1
                        mid = [m * scale / length * length for m in mid]
                    
                    new_vertices.append(mid)
                    mid_points.append(len(new_vertices) - 1)
                
                # Creer 4 nouveaux triangles
                new_faces.append([face[0], mid_points[0], mid_points[2]])
                new_faces.append([face[1], mid_points[1], mid_points[0]])
                new_faces.append([face[2], mid_points[2], mid_points[1]])
                new_faces.append([mid_points[0], mid_points[1], mid_points[2]])
            
            vertices = new_vertices
            faces = new_faces
        
        return vertices, faces
    
    def _create_7d_projection(self) -> Tuple[List, List]:
        """Cree une projection 3D d'un objet 7D"""
        vertices = []
        faces = []
        
        # Creer un hypercube simplifie projete
        n_points = 32
        
        for i in range(n_points):
            t = 2 * math.pi * i / n_points
            
            # Coordonnees 7D projetees en 3D
            d1 = math.sin(t)
            d2 = math.cos(t)
            d3 = math.sin(2 * t)
            d4 = math.cos(2 * t)
            d5 = math.sin(3 * t)
            d6 = math.cos(3 * t)
            d7 = math.sin(4 * t)
            
            # Projection en 3D avec poids de l'ADN
            w = [self.dna.seed_values[k] / 255 for k in range(7)]
            
            x = d1 * w[0] + d4 * w[3] + d7 * w[6]
            y = d2 * w[1] + d5 * w[4]
            z = d3 * w[2] + d6 * w[5]
            
            vertices.append([x, y, z])
        
        # Connecter les points
        for i in range(n_points):
            j = (i + 1) % n_points
            k = (i + 2) % n_points
            faces.append([i, j, k])
        
        return vertices, faces
    
    def _create_hybrid_form(self) -> Tuple[List, List]:
        """Cree une forme hybride combinant plusieurs geometries"""
        # Combiner sphere et tore
        sphere_v, sphere_f = self._create_quantum_sphere()
        torus_v, torus_f = self._create_spinor_torus()
        
        # Reduire le tore
        torus_v = [[v[0] * 0.5, v[1] * 0.5, v[2] * 0.5 + 1.5] for v in torus_v]
        
        # Combiner
        offset = len(sphere_v)
        torus_f = [[f[0] + offset, f[1] + offset, f[2] + offset] for f in torus_f]
        
        vertices = sphere_v + torus_v
        faces = sphere_f + torus_f
        
        return vertices, faces
    
    def _create_nexus_crystal(self) -> Tuple[List, List]:
        """Cree un cristal du Nexus"""
        vertices = []
        
        # Pointe superieure
        vertices.append([0, 0, 1.5])
        
        # Anneau superieur
        n_sides = 6 + (self.dna.seed_values[8] % 4)
        for i in range(n_sides):
            angle = 2 * math.pi * i / n_sides
            r = 0.8
            vertices.append([r * math.cos(angle), r * math.sin(angle), 0.5])
        
        # Anneau central (plus large)
        for i in range(n_sides):
            angle = 2 * math.pi * i / n_sides + math.pi / n_sides
            r = 1.2
            vertices.append([r * math.cos(angle), r * math.sin(angle), 0])
        
        # Anneau inferieur
        for i in range(n_sides):
            angle = 2 * math.pi * i / n_sides
            r = 0.8
            vertices.append([r * math.cos(angle), r * math.sin(angle), -0.5])
        
        # Pointe inferieure
        vertices.append([0, 0, -1.5])
        
        # Faces
        faces = []
        
        # Pointe superieure vers anneau superieur
        for i in range(n_sides):
            faces.append([0, 1 + i, 1 + (i + 1) % n_sides])
        
        # Anneau superieur vers central
        for i in range(n_sides):
            faces.append([1 + i, 1 + n_sides + i, 1 + (i + 1) % n_sides])
            faces.append([1 + (i + 1) % n_sides, 1 + n_sides + i, 1 + n_sides + (i + 1) % n_sides])
        
        # Central vers inferieur
        for i in range(n_sides):
            faces.append([1 + n_sides + i, 1 + 2 * n_sides + i, 1 + n_sides + (i + 1) % n_sides])
            faces.append([1 + n_sides + (i + 1) % n_sides, 1 + 2 * n_sides + i, 1 + 2 * n_sides + (i + 1) % n_sides])
        
        # Anneau inferieur vers pointe
        bottom_idx = 1 + 3 * n_sides
        for i in range(n_sides):
            faces.append([1 + 2 * n_sides + i, bottom_idx, 1 + 2 * n_sides + (i + 1) % n_sides])
        
        return vertices, faces
    
    def _apply_transformations(self, vertices: List) -> List:
        """Applique des transformations basees sur l'ADN"""
        dna = self.dna
        
        # Scaling
        sx = 1.0 + dna.seed_values[9] / 500
        sy = 1.0 + dna.seed_values[10] / 500
        sz = 1.0 + dna.seed_values[11] / 500
        
        # Rotation angles
        ax = dna.seed_values[12] * math.pi / 128
        ay = dna.seed_values[13] * math.pi / 128
        az = dna.seed_values[14] * math.pi / 128
        
        result = []
        for v in vertices:
            x, y, z = v[0] * sx, v[1] * sy, v[2] * sz
            
            # Rotation X
            y2 = y * math.cos(ax) - z * math.sin(ax)
            z2 = y * math.sin(ax) + z * math.cos(ax)
            y, z = y2, z2
            
            # Rotation Y
            x2 = x * math.cos(ay) + z * math.sin(ay)
            z2 = -x * math.sin(ay) + z * math.cos(ay)
            x, z = x2, z2
            
            # Rotation Z
            x2 = x * math.cos(az) - y * math.sin(az)
            y2 = x * math.sin(az) + y * math.cos(az)
            x, y = x2, y2
            
            result.append([round(x, 6), round(y, 6), round(z, 6)])
        
        return result
    
    def _calculate_normals(self, vertices: List, faces: List) -> List:
        """Calcule les normales pour chaque vertex"""
        normals = [[0, 0, 0] for _ in vertices]
        
        for face in faces:
            if len(face) >= 3:
                v0 = vertices[face[0]]
                v1 = vertices[face[1]]
                v2 = vertices[face[2]]
                
                # Vecteurs
                u = [v1[i] - v0[i] for i in range(3)]
                v = [v2[i] - v0[i] for i in range(3)]
                
                # Produit vectoriel
                n = [
                    u[1] * v[2] - u[2] * v[1],
                    u[2] * v[0] - u[0] * v[2],
                    u[0] * v[1] - u[1] * v[0]
                ]
                
                # Ajouter aux vertices de la face
                for idx in face:
                    for i in range(3):
                        normals[idx][i] += n[i]
        
        # Normaliser
        for i, n in enumerate(normals):
            length = sum(x**2 for x in n)**0.5
            if length > 0:
                normals[i] = [round(x / length, 6) for x in n]
            else:
                normals[i] = [0, 0, 1]
        
        return normals
    
    def _generate_uvs(self, vertices: List) -> List:
        """Genere les coordonnees UV"""
        uvs = []
        for v in vertices:
            # Projection spherique simple
            length = (v[0]**2 + v[1]**2 + v[2]**2)**0.5
            if length > 0:
                u = 0.5 + math.atan2(v[1], v[0]) / (2 * math.pi)
                vv = 0.5 - math.asin(max(-1, min(1, v[2] / length))) / math.pi
            else:
                u, vv = 0.5, 0.5
            uvs.append([round(u, 4), round(vv, 4)])
        return uvs
    
    def generate_avatar(self) -> Avatar3D:
        """Genere l'avatar complet"""
        geometry = self.generate_geometry()
        
        avatar_id = hashlib.sha256(
            f"{self.vault_id}{self.dna.vault_hash}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        self.avatar = Avatar3D(
            avatar_id=avatar_id,
            vault_id=self.vault_id,
            dna=self.dna,
            vertices=geometry['vertices'],
            faces=geometry['faces'],
            normals=geometry['normals'],
            uvs=geometry['uvs'],
            created_at=datetime.now().isoformat(),
            version=AVATAR_VERSION
        )
        
        return self.avatar
    
    def export_obj(self, output_path: str) -> str:
        """Exporte l'avatar en format OBJ"""
        if not self.avatar:
            self.generate_avatar()
        
        avatar = self.avatar
        output_path = Path(output_path)
        
        with open(output_path, 'w') as f:
            f.write(f"# Eidolon Avatar\n")
            f.write(f"# Vault: {avatar.vault_id}\n")
            f.write(f"# Avatar ID: {avatar.avatar_id}\n")
            f.write(f"# Type: {avatar.dna.geometric_name}\n")
            f.write(f"# Rarity: {avatar.dna.rarity_tier} ({avatar.dna.rarity_score:.1f})\n")
            f.write(f"# Generated: {avatar.created_at}\n\n")
            
            # Vertices
            for v in avatar.vertices:
                f.write(f"v {v[0]} {v[1]} {v[2]}\n")
            
            f.write("\n")
            
            # UVs
            for uv in avatar.uvs:
                f.write(f"vt {uv[0]} {uv[1]}\n")
            
            f.write("\n")
            
            # Normals
            for n in avatar.normals:
                f.write(f"vn {n[0]} {n[1]} {n[2]}\n")
            
            f.write("\n")
            
            # Faces
            for face in avatar.faces:
                f.write(f"f {face[0]+1}/{face[0]+1}/{face[0]+1} "
                       f"{face[1]+1}/{face[1]+1}/{face[1]+1} "
                       f"{face[2]+1}/{face[2]+1}/{face[2]+1}\n")
        
        avatar.obj_path = str(output_path)
        return str(output_path)
    
    def generate_texture(self, output_path: str, size: int = 512) -> str:
        """Genere une texture unique pour l'avatar"""
        if not PIL_AVAILABLE:
            print("[WARN] PIL not available for texture generation")
            return ""
        
        if not self.avatar:
            self.generate_avatar()
        
        texture = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(texture)
        
        dna = self.dna
        
        # Fond avec gradient
        for y in range(size):
            for x in range(size):
                # Couleur basee sur la position et l'ADN
                idx = ((x + y) // 64) % len(dna.color_palette)
                base_color = dna.color_palette[idx]
                
                r = int(base_color[1:3], 16)
                g = int(base_color[3:5], 16)
                b = int(base_color[5:7], 16)
                
                # Variation
                noise = (dna.seed_values[(x * y) % 16] % 30) - 15
                r = max(0, min(255, r + noise))
                g = max(0, min(255, g + noise))
                b = max(0, min(255, b + noise))
                
                texture.putpixel((x, y), (r, g, b, 200))
        
        # Motifs geometriques
        cell_size = 64
        for i in range(0, size, cell_size):
            for j in range(0, size, cell_size):
                color_idx = ((i + j) // cell_size) % len(dna.color_palette)
                color = dna.color_palette[color_idx]
                rgba = (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16), 150)
                
                pattern = (i * j) % 4
                
                if pattern == 0:
                    draw.ellipse([i + 8, j + 8, i + cell_size - 8, j + cell_size - 8], 
                               fill=rgba, outline=rgba)
                elif pattern == 1:
                    draw.rectangle([i + 8, j + 8, i + cell_size - 8, j + cell_size - 8],
                                 fill=rgba, outline=rgba)
                elif pattern == 2:
                    points = [
                        (i + cell_size // 2, j + 8),
                        (i + cell_size - 8, j + cell_size - 8),
                        (i + 8, j + cell_size - 8)
                    ]
                    draw.polygon(points, fill=rgba, outline=rgba)
                else:
                    draw.line([i + 8, j + 8, i + cell_size - 8, j + cell_size - 8], 
                             fill=rgba, width=3)
                    draw.line([i + cell_size - 8, j + 8, i + 8, j + cell_size - 8],
                             fill=rgba, width=3)
        
        # Appliquer un flou leger
        texture = texture.filter(ImageFilter.GaussianBlur(radius=1))
        
        texture.save(output_path)
        self.avatar.texture_path = str(output_path)
        
        return str(output_path)
    
    def generate_preview(self, output_path: str, size: int = 400) -> str:
        """Genere une image de previsualisation 2D"""
        if not PIL_AVAILABLE:
            print("[WARN] PIL not available for preview generation")
            return ""
        
        if not self.avatar:
            self.generate_avatar()
        
        img = Image.new('RGBA', (size, size), (20, 20, 30, 255))
        draw = ImageDraw.Draw(img)
        
        avatar = self.avatar
        dna = self.dna
        
        # Projection 2D simple
        center_x, center_y = size // 2, size // 2
        scale = size // 4
        
        # Dessiner les edges
        for face in avatar.faces[:100]:  # Limiter pour la performance
            points = []
            for idx in face:
                v = avatar.vertices[idx]
                # Projection orthographique
                x = center_x + int(v[0] * scale)
                y = center_y - int(v[1] * scale)  # Y inverse
                points.append((x, y))
            
            if len(points) >= 3:
                color_idx = face[0] % len(dna.color_palette)
                color = dna.color_palette[color_idx]
                rgba = (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16), 180)
                
                draw.polygon(points, fill=rgba, outline=(255, 255, 255, 100))
        
        # Ajouter le titre
        title = f"{dna.geometric_name.replace('_', ' ').title()}"
        draw.text((10, 10), title, fill=(255, 255, 255, 255))
        draw.text((10, size - 30), f"Rarity: {dna.rarity_tier.upper()}", 
                 fill=(255, 215, 0, 255))
        
        img.save(output_path)
        self.avatar.preview_path = str(output_path)
        
        return str(output_path)
    
    def get_metadata(self) -> Dict:
        """Retourne les metadonnees completes de l'avatar"""
        if not self.avatar:
            self.generate_avatar()
        
        return {
            'avatar_id': self.avatar.avatar_id,
            'vault_id': self.vault_id,
            'version': AVATAR_VERSION,
            'dna': self.dna.to_dict(),
            'geometry': {
                'type': self.dna.geometric_name,
                'vertex_count': len(self.avatar.vertices),
                'face_count': len(self.avatar.faces)
            },
            'files': {
                'obj': self.avatar.obj_path,
                'texture': self.avatar.texture_path,
                'preview': self.avatar.preview_path
            },
            'created_at': self.avatar.created_at
        }


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  QUANTUM AVATAR GENERATOR TEST")
    print("=" * 60)
    
    # Generer un avatar de test
    generator = QuantumAvatarGenerator(
        vault_id="test_vault_001",
        generation=1
    )
    
    print(f"\nDNA Extract:")
    print(f"  Vault Hash: {generator.dna.vault_hash[:16]}...")
    print(f"  Geometric Type: {generator.dna.geometric_name}")
    print(f"  Rarity: {generator.dna.rarity_tier} ({generator.dna.rarity_score:.1f})")
    print(f"  Colors: {generator.dna.color_palette}")
    
    print(f"\nAttributes:")
    for attr, value in generator.dna.attributes.items():
        print(f"  {attr}: {value:.2f}")
    
    # Generer l'avatar
    avatar = generator.generate_avatar()
    print(f"\nAvatar Generated:")
    print(f"  ID: {avatar.avatar_id}")
    print(f"  Vertices: {len(avatar.vertices)}")
    print(f"  Faces: {len(avatar.faces)}")
    
    # Exporter (si dossier existe)
    from pathlib import Path
    output_dir = Path(__file__).parent.parent.parent / "avatars"
    output_dir.mkdir(exist_ok=True)
    
    obj_path = generator.export_obj(output_dir / f"avatar_{avatar.avatar_id}.obj")
    print(f"\nExported OBJ: {obj_path}")
    
    if PIL_AVAILABLE:
        texture_path = generator.generate_texture(output_dir / f"texture_{avatar.avatar_id}.png")
        print(f"Generated Texture: {texture_path}")
        
        preview_path = generator.generate_preview(output_dir / f"preview_{avatar.avatar_id}.png")
        print(f"Generated Preview: {preview_path}")
    
    print("\n" + "=" * 60)
    print("  TEST COMPLETE")
    print("=" * 60)
