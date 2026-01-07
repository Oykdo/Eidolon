#!/usr/bin/env python3
"""
Eidolon - Lair System (RPG Genesis Blocks)
==========================================

Transforms Genesis Blocks into explorable Lairs - dungeons tied to vaults.
Each vault can own and explore multiple Lairs.

LAIR TYPES:
- Cryptic Sanctum: Hidden knowledge, puzzle-based
- Quantum Void: Reality-bending, high risk/reward
- Spinor Nexus: Dimensional rifts, rare materials
- Temporal Crypt: Time-locked treasures
- Primordial Abyss: Ancient power, legendary drops
- Ethereal Citadel: Celestial rewards, unique artifacts

MECHANICS:
- Lairs have depth levels (1-100)
- Each level has encounters, traps, and loot
- Boss at every 10th level
- Lair affinity affects drop rates
- Vault pioneer tier affects lair quality
- Lairs can be raided, defended, or traded
"""

import hashlib
import json
import secrets
import math
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ============================================================================
# CONSTANTS
# ============================================================================

MAX_LAIR_DEPTH = 100
BOSS_INTERVAL = 10
MAX_LAIRS_PER_VAULT = 18
LAIRS_PER_VAULT = 3  # Fixed number of lairs per vault


# ============================================================================
# ENUMERATIONS
# ============================================================================

class LairType(Enum):
    """Types of Lairs"""
    CRYPTIC_SANCTUM = ("cryptic_sanctum", "Cryptic Sanctum", "#9400D3", "puzzle")
    QUANTUM_VOID = ("quantum_void", "Quantum Void", "#00FFFF", "chaos")
    SPINOR_NEXUS = ("spinor_nexus", "Spinor Nexus", "#FF00FF", "dimensional")
    TEMPORAL_CRYPT = ("temporal_crypt", "Temporal Crypt", "#FFD700", "time")
    PRIMORDIAL_ABYSS = ("primordial_abyss", "Primordial Abyss", "#FF4500", "ancient")
    ETHEREAL_CITADEL = ("ethereal_citadel", "Ethereal Citadel", "#00FF7F", "celestial")
    
    def __init__(self, type_id: str, display_name: str, color: str, affinity: str):
        self.type_id = type_id
        self.display_name = display_name
        self.color = color
        self.affinity = affinity


class LairRarity(Enum):
    """Lair rarity tiers"""
    COMMON = ("common", "Common", 1.0, "#808080")
    UNCOMMON = ("uncommon", "Uncommon", 1.25, "#1EFF00")
    RARE = ("rare", "Rare", 1.5, "#0070DD")
    EPIC = ("epic", "Epic", 2.0, "#A335EE")
    LEGENDARY = ("legendary", "Legendary", 3.0, "#FF8000")
    MYTHIC = ("mythic", "Mythic", 5.0, "#E6CC80")
    PRIMORDIAL = ("primordial", "Primordial", 10.0, "#FF00FF")
    
    def __init__(self, rarity_id: str, display_name: str, multiplier: float, color: str):
        self.rarity_id = rarity_id
        self.display_name = display_name
        self.multiplier = multiplier
        self.color = color


class EncounterType(Enum):
    """Types of encounters in lairs"""
    EMPTY = "empty"
    GUARDIAN = "guardian"
    TRAP = "trap"
    PUZZLE = "puzzle"
    TREASURE = "treasure"
    SHRINE = "shrine"
    BOSS = "boss"
    SECRET = "secret"
    MERCHANT = "merchant"
    PORTAL = "portal"


class LairStatus(Enum):
    """Lair exploration status"""
    UNDISCOVERED = "undiscovered"
    DISCOVERED = "discovered"
    EXPLORING = "exploring"
    CLEARED = "cleared"
    CORRUPTED = "corrupted"
    SEALED = "sealed"


# ============================================================================
# LAIR COMPONENTS
# ============================================================================

@dataclass
class LairGuardian:
    """A guardian/monster in a lair"""
    guardian_id: str
    name: str
    level: int
    health: int
    attack: int
    defense: int
    abilities: List[str]
    loot_table: List[str]
    is_boss: bool = False
    element: str = "neutral"
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class LairTrap:
    """A trap in a lair"""
    trap_id: str
    name: str
    damage: int
    trap_type: str  # spike, poison, magic, temporal
    disarm_difficulty: int  # 1-100
    triggered: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class LairTreasure:
    """Treasure found in a lair"""
    treasure_id: str
    name: str
    treasure_type: str  # gold, item, artifact, fragment, essence
    value: int
    rarity: str
    claimed: bool = False
    contents: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class LairLevel:
    """A single level/floor of a lair"""
    level_number: int
    encounters: List[Dict]
    treasures: List[LairTreasure]
    traps: List[LairTrap]
    guardian: Optional[LairGuardian]
    is_boss_level: bool
    explored: bool = False
    cleared: bool = False
    discovery_bonus: float = 1.0
    
    def to_dict(self) -> Dict:
        return {
            "level_number": self.level_number,
            "encounters": self.encounters,
            "treasures": [t.to_dict() for t in self.treasures],
            "traps": [t.to_dict() for t in self.traps],
            "guardian": self.guardian.to_dict() if self.guardian else None,
            "is_boss_level": self.is_boss_level,
            "explored": self.explored,
            "cleared": self.cleared,
            "discovery_bonus": self.discovery_bonus,
        }


# ============================================================================
# LAIR DATA STRUCTURE
# ============================================================================

@dataclass
class Lair:
    """A Lair (evolved Genesis Block)"""
    # Identity
    lair_id: str
    name: str
    lair_type: str
    rarity: str
    
    # Ownership
    vault_id: str
    vault_number: int
    origin_genesis_block: str  # Original genesis block hash
    
    # Stats
    depth: int  # Max depth (1-100)
    current_depth: int  # Deepest explored
    power_level: int
    discovery_rate: float  # Affects loot
    corruption_level: float  # 0-100, affects difficulty
    
    # Affinity bonuses
    affinity: str
    affinity_bonus: Dict[str, float] = field(default_factory=dict)
    
    # Status
    status: str = "discovered"
    sealed_until: Optional[str] = None
    
    # Exploration
    levels: Dict[int, Dict] = field(default_factory=dict)  # level_num -> LairLevel dict
    cleared_levels: int = 0
    total_runs: int = 0
    best_run_depth: int = 0
    
    # Loot history
    total_loot_value: int = 0
    legendary_drops: int = 0
    boss_kills: int = 0
    
    # Timestamps
    created_at: str = ""
    last_explored: Optional[str] = None
    
    # Special properties
    special_modifiers: List[str] = field(default_factory=list)
    boss_guardian: Optional[Dict] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Lair':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def get_color(self) -> str:
        """Get lair type color"""
        for lt in LairType:
            if lt.type_id == self.lair_type:
                return lt.color
        return "#FFFFFF"
    
    def get_rarity_color(self) -> str:
        """Get rarity color"""
        for lr in LairRarity:
            if lr.rarity_id == self.rarity:
                return lr.color
        return "#808080"
    
    def get_rarity_multiplier(self) -> float:
        """Get rarity loot multiplier"""
        for lr in LairRarity:
            if lr.rarity_id == self.rarity:
                return lr.multiplier
        return 1.0


# ============================================================================
# LAIR GENERATOR
# ============================================================================

class LairGenerator:
    """Generates lairs from genesis blocks or vault data"""
    
    # Guardian names by lair type
    GUARDIAN_NAMES = {
        "cryptic_sanctum": [
            "Cipher Wraith", "Enigma Keeper", "Riddle Shade", "Knowledge Sentinel",
            "Glyph Guardian", "Secret Warden", "Puzzle Master", "Lore Specter"
        ],
        "quantum_void": [
            "Void Walker", "Probability Phantom", "Quantum Beast", "Entropy Spawn",
            "Paradox Entity", "Superposition Horror", "Wave Collapser", "Schrodinger's Guardian"
        ],
        "spinor_nexus": [
            "Dimensional Rift", "Spinor Sentinel", "Nexus Watcher", "Reality Weaver",
            "Plane Shifter", "Manifold Guardian", "Tensor Beast", "Geometric Horror"
        ],
        "temporal_crypt": [
            "Time Wraith", "Chrono Guardian", "Epoch Sentinel", "Moment Keeper",
            "Past Echo", "Future Shadow", "Temporal Loop", "Age Specter"
        ],
        "primordial_abyss": [
            "Ancient One", "Primordial Beast", "Origin Spawn", "First Born",
            "Abyss Dweller", "Proto Entity", "Genesis Horror", "Creation's Shadow"
        ],
        "ethereal_citadel": [
            "Celestial Warden", "Light Keeper", "Ethereal Knight", "Heaven's Guard",
            "Star Sentinel", "Luminous Entity", "Divine Protector", "Astral Guardian"
        ],
    }
    
    # Boss names (more powerful)
    BOSS_NAMES = {
        "cryptic_sanctum": "The Omniscient Cipher",
        "quantum_void": "Harbinger of Entropy",
        "spinor_nexus": "The Dimensional Apex",
        "temporal_crypt": "Chrono Tyrant",
        "primordial_abyss": "The First Darkness",
        "ethereal_citadel": "Celestial Archon",
    }
    
    # Special modifiers
    SPECIAL_MODIFIERS = [
        "Unstable Reality",      # Random buffs/debuffs
        "Time Dilation",         # Slower but more loot
        "Dimensional Bleed",     # Extra portals
        "Ancient Blessing",      # +50% rare drops
        "Corrupted Core",        # Higher difficulty, better rewards
        "Resonant Frequency",    # Bonus to matching affinity
        "Void Touched",          # Chaos effects
        "Primordial Essence",    # Ancient artifacts possible
        "Temporal Lock",         # Time-gated sections
        "Ethereal Veil",         # Hidden treasures
    ]
    
    def __init__(self, seed: bytes = None):
        self.seed = seed or secrets.token_bytes(32)
        self.rng_state = int.from_bytes(hashlib.sha256(self.seed).digest()[:8], 'big')
    
    def _next_random(self) -> float:
        """Deterministic random number generator"""
        self.rng_state = (self.rng_state * 1103515245 + 12345) & 0x7FFFFFFF
        return self.rng_state / 0x7FFFFFFF
    
    def _random_choice(self, items: list):
        """Random choice from list"""
        idx = int(self._next_random() * len(items))
        return items[idx % len(items)]
    
    def generate_from_genesis(self, genesis_block: Dict, vault_id: str, 
                               vault_number: int) -> Lair:
        """Generate a lair from a genesis block"""
        
        # Use genesis block hash as seed for determinism
        block_hash = genesis_block.get("block_hash", secrets.token_hex(32))
        self.seed = bytes.fromhex(block_hash[:64].ljust(64, '0'))
        self.rng_state = int.from_bytes(hashlib.sha256(self.seed).digest()[:8], 'big')
        
        # Determine lair type based on hash
        lair_types = list(LairType)
        lair_type = self._random_choice(lair_types)
        
        # Determine rarity based on vault number (degressive system)
        genesis_tier = genesis_block.get("tier", "standard")
        rarity = self._determine_rarity(genesis_tier, vault_number)
        
        # Generate name
        name = self._generate_lair_name(lair_type)
        
        # Calculate depth based on rarity
        base_depth = 20
        rarity_bonus = {
            "common": 0, "uncommon": 10, "rare": 20,
            "epic": 30, "legendary": 50, "mythic": 70, "primordial": 80
        }
        depth = min(MAX_LAIR_DEPTH, base_depth + rarity_bonus.get(rarity.rarity_id, 0))
        
        # Calculate power level
        power_level = self._calculate_power_level(depth, rarity)
        
        # Generate affinity bonuses
        affinity_bonus = self._generate_affinity_bonus(lair_type)
        
        # Generate special modifiers
        num_modifiers = 1 if rarity.rarity_id in ["common", "uncommon"] else \
                        2 if rarity.rarity_id in ["rare", "epic"] else 3
        special_modifiers = []
        for _ in range(num_modifiers):
            mod = self._random_choice(self.SPECIAL_MODIFIERS)
            if mod not in special_modifiers:
                special_modifiers.append(mod)
        
        # Generate boss guardian
        boss_guardian = self._generate_boss(lair_type.type_id, depth, rarity)
        
        # Create lair
        lair = Lair(
            lair_id=hashlib.sha256(f"{vault_id}:{block_hash}".encode()).hexdigest()[:16],
            name=name,
            lair_type=lair_type.type_id,
            rarity=rarity.rarity_id,
            vault_id=vault_id,
            vault_number=vault_number,
            origin_genesis_block=block_hash,
            depth=depth,
            current_depth=0,
            power_level=power_level,
            discovery_rate=1.0 + (self._next_random() * 0.5),
            corruption_level=self._next_random() * 20,
            affinity=lair_type.affinity,
            affinity_bonus=affinity_bonus,
            special_modifiers=special_modifiers,
            boss_guardian=boss_guardian,
        )
        
        return lair
    
    def _determine_rarity(self, genesis_tier: str, vault_number: int = 1) -> LairRarity:
        """
        Determine lair rarity based on genesis tier and vault number.
        
        Progressive system:
        - Early vaults get better odds but not overwhelming
        - Each tier has ~20-30% drop from previous
        - Standard tier uses base rates
        
        Vault number affects the roll:
        - Vault 1-10: +15% to high rarities
        - Vault 11-33: +10%
        - Vault 34-100: +5%
        - Vault 101-333: +2%
        - Vault 334+: base rates
        """
        # Base weights: [common, uncommon, rare, epic, legendary, mythic, primordial]
        base_weights = [0.35, 0.25, 0.20, 0.12, 0.05, 0.025, 0.005]
        
        # Calculate vault bonus (degressive)
        if vault_number <= 10:
            # Genesis: Good bonus but not crazy
            bonus_mult = 1.8
            high_rarity_boost = 0.08  # +8% to legendary+
        elif vault_number <= 33:
            bonus_mult = 1.5
            high_rarity_boost = 0.05
        elif vault_number <= 100:
            bonus_mult = 1.3
            high_rarity_boost = 0.03
        elif vault_number <= 333:
            bonus_mult = 1.15
            high_rarity_boost = 0.015
        elif vault_number <= 1000:
            bonus_mult = 1.08
            high_rarity_boost = 0.008
        elif vault_number <= 3333:
            bonus_mult = 1.03
            high_rarity_boost = 0.003
        else:
            bonus_mult = 1.0
            high_rarity_boost = 0.0
        
        # Apply bonuses to weights
        weights = base_weights.copy()
        
        # Boost high rarities (legendary, mythic, primordial)
        weights[4] += high_rarity_boost * 2      # legendary
        weights[5] += high_rarity_boost * 1.5    # mythic
        weights[6] += high_rarity_boost          # primordial
        
        # Reduce common/uncommon to compensate
        total_boost = high_rarity_boost * 4.5
        weights[0] -= total_boost * 0.6
        weights[1] -= total_boost * 0.4
        
        # Ensure no negative weights
        weights = [max(0.01, w) for w in weights]
        
        # Normalize
        total = sum(weights)
        weights = [w / total for w in weights]
        
        # Roll
        roll = self._next_random()
        
        cumulative = 0
        rarities = list(LairRarity)
        for i, weight in enumerate(weights):
            cumulative += weight
            if roll < cumulative:
                return rarities[i]
        
        return LairRarity.COMMON
    
    def _generate_lair_name(self, lair_type: LairType) -> str:
        """Generate a unique lair name"""
        prefixes = [
            "Ancient", "Forgotten", "Hidden", "Lost", "Cursed", "Blessed",
            "Eternal", "Shadowed", "Radiant", "Twisted", "Sacred", "Profane"
        ]
        
        type_names = {
            "cryptic_sanctum": ["Library", "Archive", "Repository", "Vault"],
            "quantum_void": ["Rift", "Tear", "Anomaly", "Singularity"],
            "spinor_nexus": ["Gateway", "Convergence", "Manifold", "Vertex"],
            "temporal_crypt": ["Tomb", "Mausoleum", "Catacombs", "Ossuary"],
            "primordial_abyss": ["Depths", "Chasm", "Pit", "Core"],
            "ethereal_citadel": ["Spire", "Bastion", "Sanctum", "Throne"],
        }
        
        prefix = self._random_choice(prefixes)
        suffix = self._random_choice(type_names.get(lair_type.type_id, ["Lair"]))
        
        return f"{prefix} {suffix}"
    
    def _calculate_power_level(self, depth: int, rarity: LairRarity) -> int:
        """Calculate lair power level"""
        base_power = depth * 100
        rarity_mult = rarity.multiplier
        return int(base_power * rarity_mult)
    
    def _generate_affinity_bonus(self, lair_type: LairType) -> Dict[str, float]:
        """Generate affinity bonuses for the lair"""
        bonuses = {
            "puzzle": 0.0,
            "chaos": 0.0,
            "dimensional": 0.0,
            "time": 0.0,
            "ancient": 0.0,
            "celestial": 0.0,
        }
        
        # Primary affinity gets big bonus
        bonuses[lair_type.affinity] = 0.5 + self._next_random() * 0.3
        
        # Random secondary bonuses
        for key in bonuses:
            if key != lair_type.affinity:
                bonuses[key] = self._next_random() * 0.2
        
        return bonuses
    
    def _generate_boss(self, lair_type: str, depth: int, rarity: LairRarity) -> Dict:
        """Generate the final boss for this lair"""
        boss_name = self.BOSS_NAMES.get(lair_type, "Unknown Entity")
        
        # Scale with depth and rarity
        base_health = 10000
        base_attack = 500
        base_defense = 200
        
        depth_mult = 1 + (depth / 100)
        rarity_mult = rarity.multiplier
        
        abilities = [
            "Ultimate Attack",
            "Phase Shift",
            "Summon Minions",
            "Enrage",
        ]
        
        if rarity.rarity_id in ["legendary", "mythic", "primordial"]:
            abilities.extend(["Reality Warp", "Time Stop", "Soul Drain"])
        
        return {
            "guardian_id": f"boss_{lair_type}_{depth}",
            "name": boss_name,
            "level": depth,
            "health": int(base_health * depth_mult * rarity_mult),
            "attack": int(base_attack * depth_mult * rarity_mult),
            "defense": int(base_defense * depth_mult * rarity_mult),
            "abilities": abilities,
            "is_boss": True,
            "element": lair_type.split("_")[0],
            "loot_table": ["legendary_artifact", "mythic_essence", "boss_trophy"],
        }
    
    def generate_level(self, lair: Lair, level_num: int) -> LairLevel:
        """Generate a specific level of a lair"""
        self.seed = bytes.fromhex(lair.lair_id.ljust(32, '0'))
        self.rng_state = int.from_bytes(
            hashlib.sha256(self.seed + level_num.to_bytes(4, 'big')).digest()[:8], 
            'big'
        )
        
        is_boss_level = level_num % BOSS_INTERVAL == 0
        
        # Generate encounters
        num_encounters = 3 + int(self._next_random() * 3)
        encounters = []
        for _ in range(num_encounters):
            enc_type = self._random_choice(list(EncounterType))
            encounters.append({
                "type": enc_type.value,
                "completed": False,
                "rewards": self._generate_encounter_rewards(enc_type, level_num, lair.rarity),
            })
        
        # Generate treasures
        num_treasures = 1 + int(self._next_random() * 2)
        if is_boss_level:
            num_treasures += 2
        treasures = [self._generate_treasure(level_num, lair.rarity) for _ in range(num_treasures)]
        
        # Generate traps
        num_traps = int(self._next_random() * 3)
        traps = [self._generate_trap(level_num) for _ in range(num_traps)]
        
        # Generate guardian for this level
        guardian = None
        if is_boss_level:
            guardian = LairGuardian(**lair.boss_guardian) if lair.boss_guardian else None
        elif self._next_random() > 0.5:
            guardian = self._generate_guardian(lair.lair_type, level_num, is_boss=False)
        
        # Discovery bonus based on depth and rarity
        discovery_bonus = 1.0 + (level_num / MAX_LAIR_DEPTH) + (lair.get_rarity_multiplier() - 1) * 0.5
        
        return LairLevel(
            level_number=level_num,
            encounters=encounters,
            treasures=treasures,
            traps=traps,
            guardian=guardian,
            is_boss_level=is_boss_level,
            discovery_bonus=discovery_bonus,
        )
    
    def _generate_encounter_rewards(self, enc_type: EncounterType, 
                                     level: int, rarity: str) -> Dict:
        """Generate rewards for an encounter"""
        base_gold = level * 10
        base_xp = level * 5
        
        rarity_mult = 1.0
        for lr in LairRarity:
            if lr.rarity_id == rarity:
                rarity_mult = lr.multiplier
                break
        
        return {
            "gold": int(base_gold * rarity_mult * (0.8 + self._next_random() * 0.4)),
            "xp": int(base_xp * rarity_mult),
            "item_chance": min(0.5, 0.1 + level / 200),
        }
    
    def _generate_treasure(self, level: int, rarity: str) -> LairTreasure:
        """Generate a treasure"""
        treasure_types = ["gold", "item", "fragment", "essence", "artifact"]
        weights = [0.4, 0.3, 0.15, 0.1, 0.05]
        
        # Higher levels = better treasure types
        if level > 50:
            weights = [0.2, 0.3, 0.2, 0.2, 0.1]
        if level > 80:
            weights = [0.1, 0.2, 0.25, 0.25, 0.2]
        
        roll = self._next_random()
        cumulative = 0
        treasure_type = "gold"
        for i, w in enumerate(weights):
            cumulative += w
            if roll < cumulative:
                treasure_type = treasure_types[i]
                break
        
        # Value based on level and type
        base_values = {
            "gold": 100, "item": 500, "fragment": 1000,
            "essence": 2000, "artifact": 5000
        }
        value = int(base_values[treasure_type] * level / 10)
        
        return LairTreasure(
            treasure_id=secrets.token_hex(8),
            name=f"{treasure_type.title()} Cache Lv.{level}",
            treasure_type=treasure_type,
            value=value,
            rarity=rarity,
        )
    
    def _generate_trap(self, level: int) -> LairTrap:
        """Generate a trap"""
        trap_types = ["spike", "poison", "magic", "temporal", "void"]
        trap_type = self._random_choice(trap_types)
        
        trap_names = {
            "spike": "Spike Trap",
            "poison": "Venomous Cloud",
            "magic": "Arcane Ward",
            "temporal": "Time Snare",
            "void": "Void Pit",
        }
        
        return LairTrap(
            trap_id=secrets.token_hex(8),
            name=trap_names[trap_type],
            damage=level * 5 + int(self._next_random() * level * 3),
            trap_type=trap_type,
            disarm_difficulty=min(100, 20 + level + int(self._next_random() * 30)),
        )
    
    def _generate_guardian(self, lair_type: str, level: int, is_boss: bool) -> LairGuardian:
        """Generate a guardian for a level"""
        names = self.GUARDIAN_NAMES.get(lair_type, ["Guardian"])
        name = self._random_choice(names)
        
        if is_boss:
            name = self.BOSS_NAMES.get(lair_type, "Boss")
        
        base_mult = 1.0 if not is_boss else 5.0
        
        return LairGuardian(
            guardian_id=secrets.token_hex(8),
            name=name,
            level=level,
            health=int(level * 100 * base_mult),
            attack=int(level * 10 * base_mult),
            defense=int(level * 5 * base_mult),
            abilities=["Attack", "Defend"] + (["Special"] if is_boss else []),
            loot_table=["common_drop", "rare_drop"] if not is_boss else ["epic_drop", "legendary_drop"],
            is_boss=is_boss,
        )


# ============================================================================
# LAIR COLLECTION MANAGER
# ============================================================================

class LairCollection:
    """Manages a vault's collection of lairs"""
    
    def __init__(self, vault_id: str, vault_number: int, storage_dir: str = None):
        self.vault_id = vault_id
        self.vault_number = vault_number
        
        if storage_dir is None:
            base_path = Path(__file__).parent.parent
            storage_dir = base_path / "alchemical_vault" / "lairs"
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.collection_file = self.storage_dir / f"lairs_{vault_id[:16]}.json"
        self._load_collection()
    
    def _load_collection(self):
        """Load lairs from disk"""
        if self.collection_file.exists():
            with open(self.collection_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.lairs: Dict[str, Lair] = {
                k: Lair.from_dict(v) for k, v in data.get("lairs", {}).items()
            }
            self.active_lair_id = data.get("active_lair_id")
            self.total_runs = data.get("total_runs", 0)
            self.best_depth_ever = data.get("best_depth_ever", 0)
        else:
            self.lairs = {}
            self.active_lair_id = None
            self.total_runs = 0
            self.best_depth_ever = 0
    
    def _save_collection(self):
        """Save lairs to disk"""
        data = {
            "vault_id": self.vault_id,
            "vault_number": self.vault_number,
            "lairs": {k: v.to_dict() for k, v in self.lairs.items()},
            "active_lair_id": self.active_lair_id,
            "total_runs": self.total_runs,
            "best_depth_ever": self.best_depth_ever,
            "updated_at": datetime.utcnow().isoformat(),
        }
        with open(self.collection_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def add_lair(self, lair: Lair) -> bool:
        """Add a lair to the collection"""
        if len(self.lairs) >= MAX_LAIRS_PER_VAULT:
            return False
        
        self.lairs[lair.lair_id] = lair
        if not self.active_lair_id:
            self.active_lair_id = lair.lair_id
        
        self._save_collection()
        return True
    
    def get_lair(self, lair_id: str) -> Optional[Lair]:
        """Get a lair by ID"""
        return self.lairs.get(lair_id)
    
    def list_lairs(self) -> List[Lair]:
        """List all lairs"""
        return list(self.lairs.values())
    
    def get_active_lair(self) -> Optional[Lair]:
        """Get the currently active lair"""
        if self.active_lair_id:
            return self.lairs.get(self.active_lair_id)
        return None
    
    def set_active_lair(self, lair_id: str) -> bool:
        """Set the active lair"""
        if lair_id in self.lairs:
            self.active_lair_id = lair_id
            self._save_collection()
            return True
        return False
    
    def get_statistics(self) -> Dict:
        """Get collection statistics"""
        total_depth = sum(l.current_depth for l in self.lairs.values())
        total_power = sum(l.power_level for l in self.lairs.values())
        
        rarity_counts = {}
        type_counts = {}
        for lair in self.lairs.values():
            rarity_counts[lair.rarity] = rarity_counts.get(lair.rarity, 0) + 1
            type_counts[lair.lair_type] = type_counts.get(lair.lair_type, 0) + 1
        
        return {
            "total_lairs": len(self.lairs),
            "total_depth_explored": total_depth,
            "total_power": total_power,
            "best_depth_ever": self.best_depth_ever,
            "total_runs": self.total_runs,
            "by_rarity": rarity_counts,
            "by_type": type_counts,
        }


# ============================================================================
# GENESIS TO LAIR CONVERTER
# ============================================================================

def convert_genesis_to_lairs(genesis_blocks: List[Dict], vault_id: str, 
                              vault_number: int) -> List[Lair]:
    """Convert genesis blocks to lairs"""
    generator = LairGenerator()
    lairs = []
    
    for block in genesis_blocks:
        lair = generator.generate_from_genesis(block, vault_id, vault_number)
        lairs.append(lair)
    
    return lairs


def create_lairs_for_vault(vault_id: str, vault_number: int, 
                           num_lairs: int = None) -> LairCollection:
    """
    Create a lair collection for a vault with generated lairs.
    
    All vaults get exactly 3 lairs (LAIRS_PER_VAULT).
    Rarity is determined by vault number (degressive system).
    """
    if num_lairs is None:
        num_lairs = LAIRS_PER_VAULT  # Default: 3 lairs per vault
    
    collection = LairCollection(vault_id, vault_number)
    generator = LairGenerator(seed=vault_id.encode())
    
    for i in range(num_lairs):
        # Create a pseudo-genesis block for each lair
        genesis_block = {
            "block_hash": hashlib.sha256(f"{vault_id}:genesis:{i}".encode()).hexdigest(),
            "tier": "standard",  # Tier is now determined by vault_number in _determine_rarity
            "inscription_number": i + 1,
        }
        
        lair = generator.generate_from_genesis(genesis_block, vault_id, vault_number)
        collection.add_lair(lair)
    
    return collection


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  LAIR SYSTEM - Test (Degressive RNG)")
    print("=" * 60)
    
    # Test degressive RNG for different vault numbers
    print("\n  RNG Distribution Test (100 samples per tier):")
    print("  " + "-" * 55)
    
    generator = LairGenerator()
    test_vaults = [1, 10, 33, 100, 333, 1000, 5000]
    
    for vault_num in test_vaults:
        rarities = {}
        for i in range(100):
            generator.rng_state = i * 12345 + vault_num
            rarity = generator._determine_rarity("standard", vault_num)
            rarities[rarity.rarity_id] = rarities.get(rarity.rarity_id, 0) + 1
        
        leg_plus = rarities.get("legendary", 0) + rarities.get("mythic", 0) + rarities.get("primordial", 0)
        print(f"  Vault #{vault_num:5}: Leg+: {leg_plus:2}% | Epic: {rarities.get('epic', 0):2}% | Rare: {rarities.get('rare', 0):2}%")
    
    print()
    
    # Create lairs for a test vault (3 lairs)
    vault_id = "test_vault_001"
    vault_number = 1  # Genesis tier
    
    collection = create_lairs_for_vault(vault_id, vault_number)  # Uses LAIRS_PER_VAULT (3)
    
    print(f"  Created {len(collection.lairs)} lairs for vault #{vault_number}")
    print()
    
    for lair in collection.list_lairs():
        print(f"  [{lair.rarity.upper()}] {lair.name}")
        print(f"      Type: {lair.lair_type}")
        print(f"      Depth: {lair.depth} levels")
        print(f"      Power: {lair.power_level}")
        print(f"      Modifiers: {', '.join(lair.special_modifiers)}")
        print()
    
    # Generate a level
    generator = LairGenerator()
    first_lair = list(collection.lairs.values())[0]
    level_1 = generator.generate_level(first_lair, 1)
    
    print(f"  Level 1 of {first_lair.name}:")
    print(f"      Encounters: {len(level_1.encounters)}")
    print(f"      Treasures: {len(level_1.treasures)}")
    print(f"      Traps: {len(level_1.traps)}")
    print(f"      Guardian: {level_1.guardian.name if level_1.guardian else 'None'}")
    
    # Stats
    stats = collection.get_statistics()
    print(f"\n  Collection Stats:")
    print(f"      Total Lairs: {stats['total_lairs']}")
    print(f"      Total Power: {stats['total_power']}")
    print(f"      By Rarity: {stats['by_rarity']}")
