#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              COMBAT EQUIPMENT SYSTEM - Eidolon                               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Complete combat equipment with original names and Pioneer bonuses:          ║
║  - 50+ unique equipment types with original names                            ║
║  - Combat chests with Pioneer tier bonuses (vaults 1-10000)                  ║
║  - 2 chests per vault (Armory + Arsenal)                                     ║
║  - Rarity scaling based on vault number                                      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import random
import hashlib
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path


# ============================================================================
# EQUIPMENT CATEGORIES WITH ORIGINAL NAMES
# ============================================================================

class WeaponClass(Enum):
    """Weapon classes with unique Eidolon names"""
    # Blades
    VOIDBLADE = ("voidblade", "Voidblade", "main_hand", {"phys_damage": 1.0, "attack_speed": 1.0})
    AETHERCLEAVER = ("aethercleaver", "Aethercleaver", "main_hand", {"phys_damage": 1.25, "attack_speed": 0.8})
    SHADOWFANG = ("shadowfang", "Shadowfang", "main_hand", {"phys_damage": 0.7, "attack_speed": 1.5, "crit_chance": 0.08})
    SPINORBLADE = ("spinorblade", "Spinorblade", "main_hand", {"phys_damage": 1.1, "mag_damage": 0.3})
    
    # Heavy Weapons
    DOOMHAMMER = ("doomhammer", "Doomhammer", "two_hand", {"phys_damage": 2.2, "attack_speed": 0.5, "stun_chance": 0.1})
    NEXUSREAPER = ("nexusreaper", "Nexusreaper", "two_hand", {"phys_damage": 1.8, "life_steal": 0.08})
    QUANTUMMAUL = ("quantummaul", "Quantummaul", "two_hand", {"phys_damage": 2.0, "armor_pen": 0.2})
    ENTROPYSCYTHE = ("entropyscythe", "Entropyscythe", "two_hand", {"phys_damage": 1.5, "mag_damage": 0.8})
    
    # Ranged
    STARPIERCE = ("starpierce", "Starpierce Bow", "two_hand", {"phys_damage": 1.4, "range": 3.0, "crit_damage": 0.3})
    VOIDCASTER = ("voidcaster", "Voidcaster", "two_hand", {"phys_damage": 1.7, "armor_pen": 0.25})
    
    # Magic Weapons
    AETHERSTAFF = ("aetherstaff", "Aetherstaff", "two_hand", {"mag_damage": 1.8, "mana": 80, "cast_speed": 0.1})
    NEXUSWAND = ("nexuswand", "Nexuswand", "main_hand", {"mag_damage": 1.0, "cast_speed": 0.2})
    SPINORSCEPTER = ("spinorscepter", "Spinor Scepter", "main_hand", {"mag_damage": 1.2, "mana_regen": 0.15})
    ENTROPYFOCUS = ("entropyfocus", "Entropy Focus", "main_hand", {"mag_damage": 0.9, "crit_chance": 0.1})
    COSMICORB = ("cosmicorb", "Cosmic Orb", "off_hand", {"mag_damage": 0.5, "mana": 50, "cooldown_reduction": 0.1})
    
    # Off-hand
    VOIDSHIELD = ("voidshield", "Voidshield", "off_hand", {"defense": 1.2, "block_chance": 0.2})
    AETHERBUCKLER = ("aetherbuckler", "Aetherbuckler", "off_hand", {"defense": 0.6, "block_chance": 0.12, "evasion": 0.05})
    SHADOWDAGGER = ("shadowdagger", "Shadowdagger", "off_hand", {"phys_damage": 0.4, "crit_chance": 0.06, "evasion": 0.08})
    GRIMOIRE = ("grimoire", "Ancient Grimoire", "off_hand", {"mag_damage": 0.3, "mana": 40, "cooldown_reduction": 0.15})
    
    def __init__(self, wep_id: str, name: str, slot: str, base_stats: dict):
        self.wep_id = wep_id
        self.display_name = name
        self.slot = slot
        self.base_stats = base_stats


class ArmorClass(Enum):
    """Armor classes with unique Eidolon names"""
    # Heavy Armor
    VOIDPLATE_HELM = ("voidplate_helm", "Voidplate Helm", "head", {"defense": 1.2, "health": 50})
    VOIDPLATE_CHEST = ("voidplate_chest", "Voidplate Cuirass", "chest", {"defense": 1.8, "health": 80})
    VOIDPLATE_GAUNTLETS = ("voidplate_gauntlets", "Voidplate Gauntlets", "hands", {"defense": 1.0, "phys_damage": 0.1})
    VOIDPLATE_GREAVES = ("voidplate_greaves", "Voidplate Greaves", "legs", {"defense": 1.4, "health": 60})
    VOIDPLATE_SABATONS = ("voidplate_sabatons", "Voidplate Sabatons", "feet", {"defense": 0.9, "movement_speed": -0.05})
    
    # Medium Armor
    NEXUSWEAVE_HOOD = ("nexusweave_hood", "Nexusweave Hood", "head", {"defense": 0.8, "health": 30, "evasion": 0.03})
    NEXUSWEAVE_VEST = ("nexusweave_vest", "Nexusweave Vest", "chest", {"defense": 1.2, "health": 50, "evasion": 0.05})
    NEXUSWEAVE_GLOVES = ("nexusweave_gloves", "Nexusweave Gloves", "hands", {"defense": 0.6, "attack_speed": 0.05})
    NEXUSWEAVE_PANTS = ("nexusweave_pants", "Nexusweave Pants", "legs", {"defense": 1.0, "health": 40, "evasion": 0.04})
    NEXUSWEAVE_BOOTS = ("nexusweave_boots", "Nexusweave Boots", "feet", {"defense": 0.5, "movement_speed": 0.08})
    
    # Light Armor
    AETHERSILK_COWL = ("aethersilk_cowl", "Aethersilk Cowl", "head", {"defense": 0.4, "mana": 30, "cast_speed": 0.05})
    AETHERSILK_ROBE = ("aethersilk_robe", "Aethersilk Robe", "chest", {"defense": 0.5, "mana": 80, "cast_speed": 0.08})
    AETHERSILK_WRAPS = ("aethersilk_wraps", "Aethersilk Wraps", "hands", {"defense": 0.25, "cast_speed": 0.08})
    AETHERSILK_LEGGINGS = ("aethersilk_leggings", "Aethersilk Leggings", "legs", {"defense": 0.35, "mana": 50})
    AETHERSILK_SLIPPERS = ("aethersilk_slippers", "Aethersilk Slippers", "feet", {"defense": 0.2, "movement_speed": 0.12})
    
    # Cloaks
    SHADOWMANTLE = ("shadowmantle", "Shadowmantle", "back", {"evasion": 0.1, "crit_chance": 0.05})
    VOIDCLOAK = ("voidcloak", "Voidcloak", "back", {"defense": 0.4, "void_resist": 0.15})
    STARWEAVE_CAPE = ("starweave_cape", "Starweave Cape", "back", {"mana": 60, "cooldown_reduction": 0.08})
    ENTROPYSHROUD = ("entropyshroud", "Entropyshroud", "back", {"evasion": 0.08, "life_steal": 0.03})
    
    def __init__(self, armor_id: str, name: str, slot: str, base_stats: dict):
        self.armor_id = armor_id
        self.display_name = name
        self.slot = slot
        self.base_stats = base_stats


class AccessoryClass(Enum):
    """Accessory classes with unique Eidolon names"""
    # Amulets
    NEXUS_PENDANT = ("nexus_pendant", "Nexus Pendant", "neck", {"health": 40, "mana": 30})
    VOIDHEART_AMULET = ("voidheart_amulet", "Voidheart Amulet", "neck", {"mag_damage": 0.15, "void_resist": 0.1})
    STARCORE_CHAIN = ("starcore_chain", "Starcore Chain", "neck", {"crit_chance": 0.05, "crit_damage": 0.2})
    ENTROPY_LOCKET = ("entropy_locket", "Entropy Locket", "neck", {"life_steal": 0.05, "health_regen": 0.02})
    
    # Rings
    SPINOR_BAND = ("spinor_band", "Spinor Band", "ring", {"phys_damage": 0.08, "mag_damage": 0.08})
    VOIDLOOP = ("voidloop", "Voidloop", "ring", {"evasion": 0.05, "movement_speed": 0.05})
    NEXUS_SIGNET = ("nexus_signet", "Nexus Signet", "ring", {"health": 50, "defense": 0.2})
    ENTROPY_RING = ("entropy_ring", "Entropy Ring", "ring", {"crit_chance": 0.04, "crit_damage": 0.15})
    AETHER_CIRCLE = ("aether_circle", "Aether Circle", "ring", {"mana": 40, "cooldown_reduction": 0.05})
    STELLAR_LOOP = ("stellar_loop", "Stellar Loop", "ring", {"all_resist": 0.05})
    
    # Trinkets
    QUANTUM_RELIC = ("quantum_relic", "Quantum Relic", "trinket", {"random_stat": True})
    PRIMORDIAL_SHARD = ("primordial_shard", "Primordial Shard", "trinket", {"all_stats": 0.05})
    COSMIC_FRAGMENT = ("cosmic_fragment", "Cosmic Fragment", "trinket", {"crit_damage": 0.25, "armor_pen": 0.1})
    VOID_ESSENCE = ("void_essence", "Void Essence", "trinket", {"void_damage": 0.15, "life_steal": 0.05})
    ENTROPY_CORE = ("entropy_core", "Entropy Core", "trinket", {"attack_speed": 0.1, "cast_speed": 0.1})
    
    def __init__(self, acc_id: str, name: str, slot: str, base_stats: dict):
        self.acc_id = acc_id
        self.display_name = name
        self.slot = slot
        self.base_stats = base_stats


# ============================================================================
# EQUIPMENT RARITY
# ============================================================================

class CombatRarity(Enum):
    """Combat equipment rarity tiers"""
    FRACTURED = ("fractured", "Fractured", 0.6, "#666666", 0, 1)
    COMMON = ("common", "Common", 1.0, "#9d9d9d", 0, 2)
    ENHANCED = ("enhanced", "Enhanced", 1.4, "#1eff00", 1, 2)
    SUPERIOR = ("superior", "Superior", 1.8, "#0070dd", 2, 3)
    ELITE = ("elite", "Elite", 2.3, "#a335ee", 2, 4)
    LEGENDARY = ("legendary", "Legendary", 3.0, "#ff8000", 3, 5)
    MYTHIC = ("mythic", "Mythic", 4.0, "#e6cc80", 4, 6)
    ASCENDANT = ("ascendant", "Ascendant", 5.5, "#00ffff", 5, 7)
    PRIMORDIAL = ("primordial", "Primordial", 8.0, "#ff00ff", 6, 8)
    GENESIS = ("genesis", "Genesis", 12.0, "#ffd700", 7, 10)
    
    def __init__(self, rarity_id: str, name: str, stat_mult: float, color: str, 
                 min_mods: int, max_mods: int):
        self.rarity_id = rarity_id
        self.display_name = name
        self.stat_multiplier = stat_mult
        self.color = color
        self.min_mods = min_mods
        self.max_mods = max_mods


# ============================================================================
# PIONEER TIERS
# ============================================================================

class PioneerTier(Enum):
    """Pioneer tiers based on vault number - earlier = better loot"""
    GENESIS = ("genesis", "Genesis Pioneer", 1, 10, 3.0, {"genesis_chance": 0.05})
    PRIMORDIAL = ("primordial", "Primordial Pioneer", 11, 33, 2.5, {"ascendant_chance": 0.08})
    SUPREME = ("supreme", "Supreme Pioneer", 34, 100, 2.0, {"mythic_chance": 0.12})
    ELITE = ("elite", "Elite Pioneer", 101, 333, 1.7, {"legendary_chance": 0.15})
    VETERAN = ("veteran", "Veteran Pioneer", 334, 1000, 1.4, {"elite_chance": 0.18})
    EARLY = ("early", "Early Pioneer", 1001, 3333, 1.2, {"superior_chance": 0.20})
    PIONEER = ("pioneer", "Pioneer", 3334, 10000, 1.1, {"enhanced_chance": 0.22})
    STANDARD = ("standard", "Standard", 10001, float('inf'), 1.0, {})
    
    def __init__(self, tier_id: str, name: str, min_vault: int, max_vault: int, 
                 loot_mult: float, bonuses: dict):
        self.tier_id = tier_id
        self.display_name = name
        self.min_vault = min_vault
        self.max_vault = max_vault
        self.loot_multiplier = loot_mult
        self.bonuses = bonuses
    
    @classmethod
    def get_tier(cls, vault_number: int) -> "PioneerTier":
        """Get pioneer tier for a vault number"""
        for tier in cls:
            if tier.min_vault <= vault_number <= tier.max_vault:
                return tier
        return cls.STANDARD


# ============================================================================
# COMBAT CHEST TYPES
# ============================================================================

class CombatChestType(Enum):
    """Types of combat chests distributed to vaults"""
    ARMORY = ("armory", "Armory Chest", "armor", {
        "head": 0.2, "chest": 0.25, "hands": 0.15, "legs": 0.2, "feet": 0.15, "back": 0.05
    })
    ARSENAL = ("arsenal", "Arsenal Chest", "weapons", {
        "main_hand": 0.45, "two_hand": 0.35, "off_hand": 0.20
    })
    
    def __init__(self, chest_id: str, name: str, category: str, slot_weights: dict):
        self.chest_id = chest_id
        self.display_name = name
        self.category = category
        self.slot_weights = slot_weights


# ============================================================================
# EQUIPMENT MODS
# ============================================================================

COMBAT_MODS = {
    # Offensive
    "brutal_force": {"name": "Brutal Force", "stat": "phys_damage", "range": (5, 60), "pct": False},
    "arcane_power": {"name": "Arcane Power", "stat": "mag_damage", "range": (5, 60), "pct": False},
    "swift_strikes": {"name": "Swift Strikes", "stat": "attack_speed", "range": (3, 18), "pct": True},
    "rapid_casting": {"name": "Rapid Casting", "stat": "cast_speed", "range": (3, 18), "pct": True},
    "deadly_precision": {"name": "Deadly Precision", "stat": "crit_chance", "range": (1, 12), "pct": True},
    "savage_blows": {"name": "Savage Blows", "stat": "crit_damage", "range": (10, 60), "pct": True},
    "armor_crusher": {"name": "Armor Crusher", "stat": "armor_pen", "range": (3, 20), "pct": True},
    
    # Defensive
    "vitality_surge": {"name": "Vitality Surge", "stat": "health", "range": (30, 300), "pct": False},
    "mana_well": {"name": "Mana Well", "stat": "mana", "range": (20, 150), "pct": False},
    "iron_skin": {"name": "Iron Skin", "stat": "defense", "range": (10, 80), "pct": False},
    "arcane_ward": {"name": "Arcane Ward", "stat": "magic_resist", "range": (10, 80), "pct": False},
    "shadow_dance": {"name": "Shadow Dance", "stat": "evasion", "range": (2, 15), "pct": True},
    "stalwart_guard": {"name": "Stalwart Guard", "stat": "block_chance", "range": (3, 20), "pct": True},
    
    # Sustain
    "vampiric_touch": {"name": "Vampiric Touch", "stat": "life_steal", "range": (1, 10), "pct": True},
    "soul_siphon": {"name": "Soul Siphon", "stat": "mana_steal", "range": (1, 6), "pct": True},
    "vital_regeneration": {"name": "Vital Regeneration", "stat": "health_regen", "range": (1, 5), "pct": True},
    
    # Utility
    "chrono_flux": {"name": "Chrono Flux", "stat": "cooldown_reduction", "range": (2, 18), "pct": True},
    "windrunner": {"name": "Windrunner", "stat": "movement_speed", "range": (2, 12), "pct": True},
    
    # Elemental
    "fire_attunement": {"name": "Fire Attunement", "stat": "fire_resist", "range": (5, 35), "pct": True},
    "frost_attunement": {"name": "Frost Attunement", "stat": "ice_resist", "range": (5, 35), "pct": True},
    "storm_attunement": {"name": "Storm Attunement", "stat": "lightning_resist", "range": (5, 35), "pct": True},
    "void_attunement": {"name": "Void Attunement", "stat": "void_resist", "range": (5, 35), "pct": True},
}

MOD_TIERS = {
    "minor": ("Minor", 0.5),
    "lesser": ("Lesser", 0.75),
    "standard": ("", 1.0),
    "greater": ("Greater", 1.5),
    "superior": ("Superior", 2.0),
    "prime": ("Prime", 2.5),
    "divine": ("Divine", 3.5),
}


# ============================================================================
# NAME GENERATION
# ============================================================================

NAME_PREFIXES = {
    "fractured": ["Cracked", "Broken", "Worn", "Damaged"],
    "common": ["Simple", "Basic", "Plain", "Standard"],
    "enhanced": ["Sturdy", "Solid", "Reinforced", "Tempered"],
    "superior": ["Fine", "Quality", "Refined", "Forged"],
    "elite": ["Elite", "Champion's", "Veteran's", "Battle-worn"],
    "legendary": ["Legendary", "Heroic", "Valiant", "Glorious"],
    "mythic": ["Mythic", "Ancient", "Eternal", "Timeless"],
    "ascendant": ["Ascendant", "Celestial", "Divine", "Empyrean"],
    "primordial": ["Primordial", "Origin", "First", "Primal"],
    "genesis": ["Genesis", "Ultimate", "Perfect", "Absolute"],
}

NAME_SUFFIXES = [
    "of the Void", "of the Nexus", "of Entropy", "of the Spinor",
    "of Devastation", "of Protection", "of the Aether", "of Stars",
    "of Shadows", "of Light", "of the Cosmos", "of Infinity",
    "of Power", "of the Guardian", "of the Destroyer", "of Balance",
    "of the Pioneer", "of Genesis", "of the Ancients", "of Eternity",
]


# ============================================================================
# COMBAT EQUIPMENT DATACLASS
# ============================================================================

@dataclass
class CombatEquipment:
    """A piece of combat equipment"""
    item_id: str
    name: str
    equipment_class: str
    slot: str
    rarity: str
    item_level: int = 1
    
    # Stats
    base_stats: Dict[str, float] = field(default_factory=dict)
    mods: List[Dict[str, Any]] = field(default_factory=list)
    
    # Calculated combat stats
    physical_damage: float = 0.0
    magical_damage: float = 0.0
    defense: float = 0.0
    health: float = 0.0
    mana: float = 0.0
    attack_speed: float = 0.0
    cast_speed: float = 0.0
    crit_chance: float = 0.0
    crit_damage: float = 0.0
    evasion: float = 0.0
    block_chance: float = 0.0
    life_steal: float = 0.0
    armor_pen: float = 0.0
    movement_speed: float = 0.0
    cooldown_reduction: float = 0.0
    
    # Resistances
    fire_resist: float = 0.0
    ice_resist: float = 0.0
    lightning_resist: float = 0.0
    void_resist: float = 0.0
    
    # Meta
    origin_vault: int = 0
    current_vault: int = 0
    pioneer_tier: str = ""
    chest_origin: str = ""
    created_at: str = ""
    is_equipped: bool = False
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "CombatEquipment":
        return cls(**data)
    
    def get_power_score(self) -> float:
        """Calculate equipment power score"""
        score = 0.0
        score += self.physical_damage * 2
        score += self.magical_damage * 2
        score += self.defense * 1.5
        score += self.health * 0.5
        score += self.mana * 0.3
        score += self.crit_chance * 100
        score += self.crit_damage * 50
        score += self.attack_speed * 80
        score += self.life_steal * 150
        return score


# ============================================================================
# COMBAT CHEST DATACLASS
# ============================================================================

@dataclass
class CombatChest:
    """A combat equipment chest"""
    chest_id: str
    chest_type: str
    vault_number: int
    pioneer_tier: str
    items: List[str] = field(default_factory=list)
    is_opened: bool = False
    created_at: str = ""
    opened_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================================
# EQUIPMENT GENERATOR
# ============================================================================

class CombatEquipmentGenerator:
    """Generates combat equipment with Pioneer bonuses"""
    
    def __init__(self, seed: bytes = None):
        self.seed = seed or random.randbytes(32)
        self._rng = random.Random(int.from_bytes(self.seed[:8], 'big'))
    
    def _roll_rarity(self, vault_number: int) -> CombatRarity:
        """Roll rarity with Pioneer bonuses"""
        tier = PioneerTier.get_tier(vault_number)
        
        weights = {
            CombatRarity.FRACTURED: 500,
            CombatRarity.COMMON: 3000,
            CombatRarity.ENHANCED: 2500,
            CombatRarity.SUPERIOR: 2000,
            CombatRarity.ELITE: 1200,
            CombatRarity.LEGENDARY: 500,
            CombatRarity.MYTHIC: 200,
            CombatRarity.ASCENDANT: 70,
            CombatRarity.PRIMORDIAL: 25,
            CombatRarity.GENESIS: 5,
        }
        
        # Apply Pioneer bonuses
        mult = tier.loot_multiplier
        for rarity in [CombatRarity.LEGENDARY, CombatRarity.MYTHIC, 
                      CombatRarity.ASCENDANT, CombatRarity.PRIMORDIAL, CombatRarity.GENESIS]:
            weights[rarity] = int(weights[rarity] * mult)
        
        # Apply specific tier bonuses
        if "genesis_chance" in tier.bonuses:
            weights[CombatRarity.GENESIS] = int(weights[CombatRarity.GENESIS] * (1 + tier.bonuses["genesis_chance"] * 10))
        if "ascendant_chance" in tier.bonuses:
            weights[CombatRarity.ASCENDANT] = int(weights[CombatRarity.ASCENDANT] * (1 + tier.bonuses["ascendant_chance"] * 10))
        if "mythic_chance" in tier.bonuses:
            weights[CombatRarity.MYTHIC] = int(weights[CombatRarity.MYTHIC] * (1 + tier.bonuses["mythic_chance"] * 10))
        
        total = sum(weights.values())
        roll = self._rng.randint(0, total - 1)
        
        cumulative = 0
        for rarity, weight in weights.items():
            cumulative += weight
            if roll < cumulative:
                return rarity
        return CombatRarity.COMMON
    
    def _roll_mod_tier(self, rarity: CombatRarity) -> str:
        """Roll mod tier based on equipment rarity"""
        weights = {
            "minor": 2000,
            "lesser": 3000,
            "standard": 3000,
            "greater": 1500,
            "superior": 400,
            "prime": 90,
            "divine": 10,
        }
        
        # Higher rarity = better mods
        bonus = rarity.stat_multiplier - 1.0
        for tier in ["greater", "superior", "prime", "divine"]:
            weights[tier] = int(weights[tier] * (1 + bonus))
        
        total = sum(weights.values())
        roll = self._rng.randint(0, total - 1)
        
        cumulative = 0
        for tier, weight in weights.items():
            cumulative += weight
            if roll < cumulative:
                return tier
        return "standard"
    
    def _generate_name(self, equip_class, rarity: CombatRarity) -> str:
        """Generate equipment name"""
        prefix = self._rng.choice(NAME_PREFIXES.get(rarity.rarity_id, [""]))
        base = equip_class.display_name
        
        if rarity.stat_multiplier >= 2.5:
            suffix = self._rng.choice(NAME_SUFFIXES)
            return f"{prefix} {base} {suffix}"
        elif rarity.stat_multiplier >= 1.5:
            return f"{prefix} {base}"
        return base
    
    def generate_weapon(self, vault_number: int, weapon_class: WeaponClass = None,
                       rarity: CombatRarity = None) -> CombatEquipment:
        """Generate a weapon"""
        if weapon_class is None:
            weapon_class = self._rng.choice(list(WeaponClass))
        if rarity is None:
            rarity = self._roll_rarity(vault_number)
        
        return self._generate_equipment(weapon_class, rarity, vault_number)
    
    def generate_armor(self, vault_number: int, armor_class: ArmorClass = None,
                      rarity: CombatRarity = None) -> CombatEquipment:
        """Generate armor"""
        if armor_class is None:
            armor_class = self._rng.choice(list(ArmorClass))
        if rarity is None:
            rarity = self._roll_rarity(vault_number)
        
        return self._generate_equipment(armor_class, rarity, vault_number)
    
    def generate_accessory(self, vault_number: int, acc_class: AccessoryClass = None,
                          rarity: CombatRarity = None) -> CombatEquipment:
        """Generate accessory"""
        if acc_class is None:
            acc_class = self._rng.choice(list(AccessoryClass))
        if rarity is None:
            rarity = self._roll_rarity(vault_number)
        
        return self._generate_equipment(acc_class, rarity, vault_number)
    
    def _generate_equipment(self, equip_class, rarity: CombatRarity, 
                           vault_number: int) -> CombatEquipment:
        """Generate equipment from class"""
        tier = PioneerTier.get_tier(vault_number)
        
        # Item level scales with pioneer tier
        base_level = max(1, 100 - vault_number // 100)
        item_level = int(base_level * tier.loot_multiplier)
        
        # Generate ID
        item_id = hashlib.sha256(
            f"{equip_class.display_name}_{rarity.rarity_id}_{vault_number}_{datetime.now().isoformat()}_{self._rng.random()}".encode()
        ).hexdigest()[:16]
        
        # Generate name
        name = self._generate_name(equip_class, rarity)
        
        # Determine slot
        if hasattr(equip_class, 'wep_id'):
            class_id = equip_class.wep_id
        elif hasattr(equip_class, 'armor_id'):
            class_id = equip_class.armor_id
        else:
            class_id = equip_class.acc_id
        
        slot = equip_class.slot
        if slot == "two_hand":
            slot = "main_hand"
        elif slot == "ring":
            slot = self._rng.choice(["ring_1", "ring_2"])
        
        # Calculate base stats with rarity multiplier
        base_stats = {}
        stat_mult = rarity.stat_multiplier * (1 + item_level * 0.01)
        for stat, value in equip_class.base_stats.items():
            base_stats[stat] = value * stat_mult
        
        # Generate mods
        num_mods = self._rng.randint(rarity.min_mods, rarity.max_mods)
        mods = []
        used_mods = set()
        
        for _ in range(num_mods):
            available = [m for m in COMBAT_MODS.keys() if m not in used_mods]
            if not available:
                break
            
            mod_key = self._rng.choice(available)
            used_mods.add(mod_key)
            
            mod_info = COMBAT_MODS[mod_key]
            mod_tier = self._roll_mod_tier(rarity)
            tier_name, tier_mult = MOD_TIERS[mod_tier]
            
            min_val, max_val = mod_info["range"]
            value = self._rng.uniform(min_val, max_val) * tier_mult * (1 + item_level * 0.005)
            
            mods.append({
                "mod_id": mod_key,
                "name": f"{tier_name} {mod_info['name']}".strip(),
                "stat": mod_info["stat"],
                "value": round(value, 2),
                "tier": mod_tier,
                "is_percent": mod_info["pct"]
            })
        
        # Create equipment
        equipment = CombatEquipment(
            item_id=item_id,
            name=name,
            equipment_class=class_id,
            slot=slot,
            rarity=rarity.rarity_id,
            item_level=item_level,
            base_stats=base_stats,
            mods=mods,
            origin_vault=vault_number,
            current_vault=vault_number,
            pioneer_tier=tier.tier_id
        )
        
        # Apply base stats to equipment
        equipment.physical_damage = base_stats.get("phys_damage", 0) * 10
        equipment.magical_damage = base_stats.get("mag_damage", 0) * 10
        equipment.defense = base_stats.get("defense", 0) * 10
        equipment.health = base_stats.get("health", 0)
        equipment.mana = base_stats.get("mana", 0)
        equipment.attack_speed = base_stats.get("attack_speed", 0)
        equipment.cast_speed = base_stats.get("cast_speed", 0)
        equipment.crit_chance = base_stats.get("crit_chance", 0)
        equipment.crit_damage = base_stats.get("crit_damage", 0)
        equipment.evasion = base_stats.get("evasion", 0)
        equipment.block_chance = base_stats.get("block_chance", 0)
        equipment.life_steal = base_stats.get("life_steal", 0)
        equipment.armor_pen = base_stats.get("armor_pen", 0)
        equipment.movement_speed = base_stats.get("movement_speed", 0)
        equipment.cooldown_reduction = base_stats.get("cooldown_reduction", 0)
        
        return equipment


# ============================================================================
# COMBAT CHEST SYSTEM
# ============================================================================

class CombatChestSystem:
    """Manages combat chests for vaults"""
    
    def __init__(self, storage_path: str = "./alchemical_vault/combat_chests"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.equipment_path = self.storage_path.parent / "combat_equipment"
        self.equipment_path.mkdir(parents=True, exist_ok=True)
        self.generator = CombatEquipmentGenerator()
    
    def create_vault_chests(self, vault_number: int) -> List[CombatChest]:
        """Create 2 combat chests for a vault (Armory + Arsenal)"""
        chests = []
        
        for chest_type in CombatChestType:
            chest_id = hashlib.sha256(
                f"{chest_type.chest_id}_{vault_number}_{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]
            
            tier = PioneerTier.get_tier(vault_number)
            
            chest = CombatChest(
                chest_id=chest_id,
                chest_type=chest_type.chest_id,
                vault_number=vault_number,
                pioneer_tier=tier.tier_id
            )
            
            # Save chest
            chest_file = self.storage_path / f"combat_chest_{chest_id}.json"
            with open(chest_file, 'w', encoding='utf-8') as f:
                json.dump(chest.to_dict(), f, indent=2, ensure_ascii=False)
            
            chests.append(chest)
        
        return chests
    
    def open_chest(self, chest_id: str) -> List[CombatEquipment]:
        """Open a combat chest and generate equipment"""
        chest_file = self.storage_path / f"combat_chest_{chest_id}.json"
        if not chest_file.exists():
            raise ValueError(f"Chest not found: {chest_id}")
        
        with open(chest_file, 'r', encoding='utf-8') as f:
            chest_data = json.load(f)
        
        if chest_data.get("is_opened"):
            raise ValueError("Chest already opened")
        
        chest_type = CombatChestType[chest_data["chest_type"].upper()]
        vault_number = chest_data["vault_number"]
        tier = PioneerTier.get_tier(vault_number)
        
        # Determine number of items based on Pioneer tier
        base_items = 3
        bonus_items = int(tier.loot_multiplier)
        num_items = base_items + bonus_items
        
        equipment_list = []
        
        for _ in range(num_items):
            # Roll slot based on chest type weights
            slot_roll = random.random()
            cumulative = 0
            selected_slot = None
            
            for slot, weight in chest_type.slot_weights.items():
                cumulative += weight
                if slot_roll < cumulative:
                    selected_slot = slot
                    break
            
            if selected_slot is None:
                selected_slot = list(chest_type.slot_weights.keys())[0]
            
            # Generate equipment based on slot
            if chest_type == CombatChestType.ARSENAL:
                # Weapons
                if selected_slot == "two_hand":
                    two_hand_weapons = [w for w in WeaponClass if w.slot == "two_hand"]
                    weapon_class = random.choice(two_hand_weapons)
                elif selected_slot == "off_hand":
                    off_hand = [w for w in WeaponClass if w.slot == "off_hand"]
                    weapon_class = random.choice(off_hand)
                else:
                    main_hand = [w for w in WeaponClass if w.slot == "main_hand"]
                    weapon_class = random.choice(main_hand)
                
                equip = self.generator.generate_weapon(vault_number, weapon_class)
            else:
                # Armor
                armor_for_slot = [a for a in ArmorClass if a.slot == selected_slot]
                if armor_for_slot:
                    armor_class = random.choice(armor_for_slot)
                    equip = self.generator.generate_armor(vault_number, armor_class)
                else:
                    # Fallback to accessory
                    equip = self.generator.generate_accessory(vault_number)
            
            equip.chest_origin = chest_id
            equipment_list.append(equip)
            
            # Save equipment
            equip_file = self.equipment_path / f"combat_equip_{equip.item_id}.json"
            with open(equip_file, 'w', encoding='utf-8') as f:
                json.dump(equip.to_dict(), f, indent=2, ensure_ascii=False)
        
        # Update chest
        chest_data["is_opened"] = True
        chest_data["opened_at"] = datetime.now().isoformat()
        chest_data["items"] = [e.item_id for e in equipment_list]
        
        with open(chest_file, 'w', encoding='utf-8') as f:
            json.dump(chest_data, f, indent=2, ensure_ascii=False)
        
        return equipment_list
    
    def get_vault_chests(self, vault_number: int) -> List[dict]:
        """Get all chests for a vault"""
        chests = []
        for chest_file in self.storage_path.glob("combat_chest_*.json"):
            with open(chest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get("vault_number") == vault_number:
                    chests.append(data)
        return chests
    
    def get_vault_equipment(self, vault_number: int) -> List[CombatEquipment]:
        """Get all combat equipment for a vault"""
        equipment = []
        for equip_file in self.equipment_path.glob("combat_equip_*.json"):
            with open(equip_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get("current_vault") == vault_number:
                    equipment.append(CombatEquipment.from_dict(data))
        return equipment


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_combat_equipment(equip: CombatEquipment) -> str:
    """Format equipment for display"""
    rarity_colors = {r.rarity_id: r.color for r in CombatRarity}
    
    lines = []
    lines.append(f"\n{'='*55}")
    lines.append(f"  [{equip.rarity.upper()}] {equip.name}")
    lines.append(f"  Type: {equip.equipment_class} | Slot: {equip.slot}")
    lines.append(f"  Item Level: {equip.item_level} | Pioneer: {equip.pioneer_tier}")
    lines.append(f"  Power Score: {equip.get_power_score():,.0f}")
    lines.append(f"{'='*55}")
    
    # Combat stats
    lines.append("\n  COMBAT STATS:")
    if equip.physical_damage > 0:
        lines.append(f"    Physical Damage: {equip.physical_damage:.0f}")
    if equip.magical_damage > 0:
        lines.append(f"    Magical Damage: {equip.magical_damage:.0f}")
    if equip.defense > 0:
        lines.append(f"    Defense: {equip.defense:.0f}")
    if equip.health > 0:
        lines.append(f"    Health: +{equip.health:.0f}")
    if equip.mana > 0:
        lines.append(f"    Mana: +{equip.mana:.0f}")
    
    # Secondary stats
    secondary = []
    if equip.attack_speed != 0:
        secondary.append(f"Attack Speed: {equip.attack_speed:+.0%}")
    if equip.crit_chance > 0:
        secondary.append(f"Crit Chance: {equip.crit_chance:.1%}")
    if equip.crit_damage > 0:
        secondary.append(f"Crit Damage: {equip.crit_damage:.0%}")
    if equip.evasion > 0:
        secondary.append(f"Evasion: {equip.evasion:.1%}")
    if equip.block_chance > 0:
        secondary.append(f"Block: {equip.block_chance:.1%}")
    if equip.life_steal > 0:
        secondary.append(f"Life Steal: {equip.life_steal:.1%}")
    if equip.armor_pen > 0:
        secondary.append(f"Armor Pen: {equip.armor_pen:.1%}")
    
    if secondary:
        lines.append("\n  SECONDARY:")
        for s in secondary:
            lines.append(f"    {s}")
    
    # Mods
    if equip.mods:
        lines.append("\n  MODS:")
        for mod in equip.mods:
            tier_tag = f"[{mod['tier'].upper()}]" if mod['tier'] not in ['standard', 'lesser', 'minor'] else ""
            value_str = f"+{mod['value']:.1f}%" if mod['is_percent'] else f"+{mod['value']:.0f}"
            lines.append(f"    {tier_tag} {mod['name']}: {value_str}")
    
    lines.append(f"\n{'='*55}\n")
    return "\n".join(lines)


# Singleton
_chest_system: Optional[CombatChestSystem] = None

def get_combat_chest_system() -> CombatChestSystem:
    global _chest_system
    if _chest_system is None:
        _chest_system = CombatChestSystem()
    return _chest_system
