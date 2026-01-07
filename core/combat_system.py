#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              COMBAT SYSTEM - Eidolon                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Complete RPG combat system with:                                            ║
║  - Equipment slots (12 slots)                                                ║
║  - Damage types (Physical, Magical, Elemental)                               ║
║  - Combat mechanics (Attack, Defense, Critical, Dodge)                       ║
║  - Status effects (Buffs, Debuffs, DoTs)                                     ║
║  - Combat log and statistics                                                 ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import math
import random
import hashlib
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path


# ============================================================================
# EQUIPMENT SLOTS
# ============================================================================

class EquipmentSlot(Enum):
    """12 equipment slots for characters"""
    # Armor (6 slots)
    HEAD = ("head", "Head", "🎭", "Helmets, Crowns, Hoods")
    CHEST = ("chest", "Chest", "🎽", "Armor, Robes, Tunics")
    HANDS = ("hands", "Hands", "🧤", "Gloves, Gauntlets, Bracers")
    LEGS = ("legs", "Legs", "👖", "Leggings, Greaves, Pants")
    FEET = ("feet", "Feet", "👢", "Boots, Shoes, Sabatons")
    BACK = ("back", "Back", "🧥", "Cloaks, Capes, Wings")
    
    # Weapons (2 slots)
    MAIN_HAND = ("main_hand", "Main Hand", "⚔️", "Swords, Staffs, Wands")
    OFF_HAND = ("off_hand", "Off Hand", "🛡️", "Shields, Orbs, Daggers")
    
    # Accessories (4 slots)
    NECK = ("neck", "Neck", "📿", "Amulets, Necklaces, Chains")
    RING_1 = ("ring_1", "Ring 1", "💍", "Rings of Power")
    RING_2 = ("ring_2", "Ring 2", "💍", "Rings of Power")
    TRINKET = ("trinket", "Trinket", "🔮", "Artifacts, Relics, Talismans")
    
    def __init__(self, slot_id: str, name: str, icon: str, description: str):
        self.slot_id = slot_id
        self.display_name = name
        self.icon = icon
        self.description = description


# ============================================================================
# EQUIPMENT TYPES
# ============================================================================

class EquipmentType(Enum):
    """Equipment types with base stats"""
    # === WEAPONS ===
    # One-handed
    SWORD = ("sword", "Sword", "main_hand", {"phys_damage": 1.0, "attack_speed": 1.0})
    AXE = ("axe", "Axe", "main_hand", {"phys_damage": 1.2, "attack_speed": 0.85})
    MACE = ("mace", "Mace", "main_hand", {"phys_damage": 1.1, "attack_speed": 0.9, "armor_pen": 0.1})
    DAGGER = ("dagger", "Dagger", "main_hand", {"phys_damage": 0.7, "attack_speed": 1.4, "crit_chance": 0.05})
    WAND = ("wand", "Wand", "main_hand", {"mag_damage": 0.8, "cast_speed": 1.1})
    SCEPTER = ("scepter", "Scepter", "main_hand", {"mag_damage": 1.0, "cast_speed": 1.0, "mana_regen": 0.1})
    
    # Two-handed
    GREATSWORD = ("greatsword", "Greatsword", "two_hand", {"phys_damage": 1.8, "attack_speed": 0.7})
    GREATAXE = ("greataxe", "Greataxe", "two_hand", {"phys_damage": 2.0, "attack_speed": 0.6, "crit_damage": 0.2})
    STAFF = ("staff", "Staff", "two_hand", {"mag_damage": 1.5, "cast_speed": 0.9, "mana": 50})
    BOW = ("bow", "Bow", "two_hand", {"phys_damage": 1.3, "attack_speed": 1.1, "range": 2.0})
    CROSSBOW = ("crossbow", "Crossbow", "two_hand", {"phys_damage": 1.6, "attack_speed": 0.7, "armor_pen": 0.15})
    SCYTHE = ("scythe", "Scythe", "two_hand", {"phys_damage": 1.4, "mag_damage": 0.6, "life_steal": 0.05})
    
    # Off-hand
    SHIELD = ("shield", "Shield", "off_hand", {"defense": 1.0, "block_chance": 0.15})
    BUCKLER = ("buckler", "Buckler", "off_hand", {"defense": 0.5, "block_chance": 0.1, "attack_speed": 0.05})
    ORB = ("orb", "Orb", "off_hand", {"mag_damage": 0.3, "mana": 30, "cast_speed": 0.1})
    TOME = ("tome", "Tome", "off_hand", {"mag_damage": 0.2, "cooldown_reduction": 0.1})
    FOCUS = ("focus", "Focus", "off_hand", {"mag_damage": 0.4, "crit_chance": 0.03})
    PARRY_DAGGER = ("parry_dagger", "Parry Dagger", "off_hand", {"phys_damage": 0.3, "evasion": 0.05})
    
    # === ARMOR ===
    # Heavy
    PLATE_HELM = ("plate_helm", "Plate Helm", "head", {"defense": 1.0, "health": 30})
    PLATE_CHEST = ("plate_chest", "Plate Chest", "chest", {"defense": 1.5, "health": 50})
    PLATE_GAUNTLETS = ("plate_gauntlets", "Plate Gauntlets", "hands", {"defense": 0.8, "phys_damage": 0.05})
    PLATE_GREAVES = ("plate_greaves", "Plate Greaves", "legs", {"defense": 1.2, "health": 40})
    PLATE_BOOTS = ("plate_boots", "Plate Boots", "feet", {"defense": 0.7, "movement_speed": -0.05})
    
    # Medium
    MAIL_HELM = ("mail_helm", "Mail Helm", "head", {"defense": 0.7, "health": 20})
    MAIL_CHEST = ("mail_chest", "Mail Chest", "chest", {"defense": 1.0, "health": 30})
    MAIL_GLOVES = ("mail_gloves", "Mail Gloves", "hands", {"defense": 0.5, "attack_speed": 0.03})
    MAIL_LEGGINGS = ("mail_leggings", "Mail Leggings", "legs", {"defense": 0.8, "health": 25})
    MAIL_BOOTS = ("mail_boots", "Mail Boots", "feet", {"defense": 0.5, "movement_speed": 0.0})
    
    # Light
    LEATHER_HOOD = ("leather_hood", "Leather Hood", "head", {"defense": 0.4, "evasion": 0.03})
    LEATHER_VEST = ("leather_vest", "Leather Vest", "chest", {"defense": 0.6, "evasion": 0.05})
    LEATHER_GLOVES = ("leather_gloves", "Leather Gloves", "hands", {"defense": 0.3, "attack_speed": 0.05})
    LEATHER_PANTS = ("leather_pants", "Leather Pants", "legs", {"defense": 0.5, "evasion": 0.04})
    LEATHER_BOOTS = ("leather_boots", "Leather Boots", "feet", {"defense": 0.3, "movement_speed": 0.05})
    
    # Cloth
    CLOTH_HAT = ("cloth_hat", "Cloth Hat", "head", {"defense": 0.2, "mana": 20, "cast_speed": 0.03})
    CLOTH_ROBE = ("cloth_robe", "Cloth Robe", "chest", {"defense": 0.3, "mana": 50, "cast_speed": 0.05})
    CLOTH_WRAPS = ("cloth_wraps", "Cloth Wraps", "hands", {"defense": 0.15, "cast_speed": 0.05})
    CLOTH_PANTS = ("cloth_pants", "Cloth Pants", "legs", {"defense": 0.25, "mana": 30})
    CLOTH_SHOES = ("cloth_shoes", "Cloth Shoes", "feet", {"defense": 0.1, "movement_speed": 0.08})
    
    # === CLOAKS ===
    WARRIOR_CLOAK = ("warrior_cloak", "Warrior Cloak", "back", {"defense": 0.3, "health": 20})
    RANGER_CLOAK = ("ranger_cloak", "Ranger Cloak", "back", {"evasion": 0.05, "movement_speed": 0.05})
    MAGE_CLOAK = ("mage_cloak", "Mage Cloak", "back", {"mana": 40, "cooldown_reduction": 0.05})
    SHADOW_CLOAK = ("shadow_cloak", "Shadow Cloak", "back", {"evasion": 0.08, "crit_chance": 0.03})
    
    # === ACCESSORIES ===
    AMULET = ("amulet", "Amulet", "neck", {"health": 30, "mana": 20})
    PENDANT = ("pendant", "Pendant", "neck", {"mag_damage": 0.1, "mag_resist": 0.1})
    CHAIN = ("chain", "Chain", "neck", {"defense": 0.2, "health": 15})
    RING = ("ring", "Ring", "ring", {"variable": True})
    ARTIFACT_TRINKET = ("artifact_trinket", "Artifact", "trinket", {"special": True})
    
    def __init__(self, type_id: str, name: str, slot: str, base_stats: Dict[str, float]):
        self.type_id = type_id
        self.display_name = name
        self.slot = slot
        self.base_stats = base_stats


# ============================================================================
# DAMAGE TYPES
# ============================================================================

class DamageType(Enum):
    """Types of damage in combat"""
    PHYSICAL = ("physical", "Physical", "#ff6644", "Reduced by Defense")
    MAGICAL = ("magical", "Magical", "#6644ff", "Reduced by Magic Resist")
    TRUE = ("true", "True", "#ffffff", "Ignores all resistances")
    
    # Elemental
    FIRE = ("fire", "Fire", "#ff4400", "Burns over time")
    ICE = ("ice", "Ice", "#88ccff", "Slows target")
    LIGHTNING = ("lightning", "Lightning", "#ffff00", "Chain damage")
    EARTH = ("earth", "Earth", "#8b4513", "Armor break")
    VOID = ("void", "Void", "#aa00ff", "Ignores shields")
    LIGHT = ("light", "Light", "#ffffaa", "Bonus vs undead")
    SHADOW = ("shadow", "Shadow", "#333366", "Life steal")
    QUANTUM = ("quantum", "Quantum", "#00ffff", "Random effects")
    
    def __init__(self, dmg_id: str, name: str, color: str, description: str):
        self.dmg_id = dmg_id
        self.display_name = name
        self.color = color
        self.description = description


# ============================================================================
# STATUS EFFECTS
# ============================================================================

class StatusEffect(Enum):
    """Combat status effects"""
    # Buffs
    EMPOWERED = ("empowered", "Empowered", "buff", "+25% damage", 10)
    HASTE = ("haste", "Haste", "buff", "+30% attack speed", 8)
    FORTIFIED = ("fortified", "Fortified", "buff", "+30% defense", 10)
    REGENERATING = ("regenerating", "Regenerating", "buff", "Heal 2%/sec", 10)
    SHIELDED = ("shielded", "Shielded", "buff", "Absorbs damage", 8)
    FOCUSED = ("focused", "Focused", "buff", "+20% crit chance", 6)
    
    # Debuffs
    WEAKENED = ("weakened", "Weakened", "debuff", "-25% damage", 8)
    SLOWED = ("slowed", "Slowed", "debuff", "-30% speed", 6)
    VULNERABLE = ("vulnerable", "Vulnerable", "debuff", "+25% damage taken", 8)
    SILENCED = ("silenced", "Silenced", "debuff", "Cannot cast", 4)
    STUNNED = ("stunned", "Stunned", "debuff", "Cannot act", 2)
    BLINDED = ("blinded", "Blinded", "debuff", "-50% accuracy", 5)
    
    # DoTs
    BURNING = ("burning", "Burning", "dot", "Fire damage/sec", 6)
    POISONED = ("poisoned", "Poisoned", "dot", "Poison damage/sec", 10)
    BLEEDING = ("bleeding", "Bleeding", "dot", "Physical damage/sec", 8)
    CORRUPTED = ("corrupted", "Corrupted", "dot", "Void damage/sec", 6)
    FROZEN = ("frozen", "Frozen", "dot", "Ice damage + slow", 4)
    ELECTRIFIED = ("electrified", "Electrified", "dot", "Lightning damage", 5)
    
    def __init__(self, effect_id: str, name: str, category: str, description: str, base_duration: int):
        self.effect_id = effect_id
        self.display_name = name
        self.category = category
        self.description = description
        self.base_duration = base_duration


# ============================================================================
# EQUIPMENT RARITY
# ============================================================================

class EquipmentRarity(Enum):
    """Equipment rarity tiers"""
    COMMON = ("common", "Common", 1.0, "#9d9d9d", 0, 1)
    UNCOMMON = ("uncommon", "Uncommon", 1.3, "#1eff00", 1, 2)
    RARE = ("rare", "Rare", 1.7, "#0070dd", 2, 3)
    EPIC = ("epic", "Epic", 2.2, "#a335ee", 3, 4)
    LEGENDARY = ("legendary", "Legendary", 3.0, "#ff8000", 4, 5)
    MYTHIC = ("mythic", "Mythic", 4.0, "#e6cc80", 5, 6)
    TRANSCENDENT = ("transcendent", "Transcendent", 5.5, "#00ffff", 6, 7)
    PRIMORDIAL = ("primordial", "Primordial", 8.0, "#ff00ff", 7, 8)
    
    def __init__(self, rarity_id: str, name: str, stat_mult: float, color: str, 
                 min_mods: int, max_mods: int):
        self.rarity_id = rarity_id
        self.display_name = name
        self.stat_multiplier = stat_mult
        self.color = color
        self.min_mods = min_mods
        self.max_mods = max_mods


# ============================================================================
# EQUIPMENT DATA
# ============================================================================

@dataclass
class EquipmentMod:
    """A modifier on equipment"""
    mod_type: str
    value: float
    tier: str
    is_percent: bool = False
    
    def get_display(self) -> str:
        if self.is_percent:
            return f"+{self.value:.1f}%"
        return f"+{self.value:.0f}"


@dataclass
class Equipment:
    """A piece of equipment"""
    item_id: str
    name: str
    equipment_type: str
    slot: str
    rarity: str
    item_level: int = 1
    
    # Base stats
    base_stats: Dict[str, float] = field(default_factory=dict)
    
    # Mods
    mods: List[EquipmentMod] = field(default_factory=list)
    
    # Combat stats (calculated)
    physical_damage: float = 0.0
    magical_damage: float = 0.0
    defense: float = 0.0
    health: float = 0.0
    mana: float = 0.0
    
    # Secondary stats
    attack_speed: float = 0.0
    cast_speed: float = 0.0
    crit_chance: float = 0.0
    crit_damage: float = 0.0
    evasion: float = 0.0
    block_chance: float = 0.0
    movement_speed: float = 0.0
    life_steal: float = 0.0
    mana_steal: float = 0.0
    cooldown_reduction: float = 0.0
    
    # Resistances
    fire_resist: float = 0.0
    ice_resist: float = 0.0
    lightning_resist: float = 0.0
    void_resist: float = 0.0
    
    # Meta
    created_at: str = ""
    origin_vault: Optional[int] = None
    current_vault: Optional[int] = None
    is_equipped: bool = False
    equipped_by: Optional[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['mods'] = [asdict(m) for m in self.mods]
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "Equipment":
        mods_data = data.pop('mods', [])
        equip = cls(**data)
        equip.mods = [EquipmentMod(**m) for m in mods_data]
        return equip
    
    def get_total_stat(self, stat_name: str) -> float:
        """Get total value of a stat including mods"""
        base = getattr(self, stat_name, 0) or self.base_stats.get(stat_name, 0)
        mod_flat = sum(m.value for m in self.mods 
                      if m.mod_type == stat_name and not m.is_percent)
        mod_pct = sum(m.value for m in self.mods 
                     if m.mod_type == stat_name and m.is_percent)
        return base * (1 + mod_pct / 100) + mod_flat


# ============================================================================
# COMBAT STATS
# ============================================================================

@dataclass
class CombatStats:
    """Complete combat statistics for a character"""
    # Core
    level: int = 1
    health: float = 100.0
    max_health: float = 100.0
    mana: float = 50.0
    max_mana: float = 50.0
    
    # Offense
    physical_damage: float = 10.0
    magical_damage: float = 10.0
    attack_speed: float = 1.0
    cast_speed: float = 1.0
    
    # Defense
    defense: float = 10.0
    magic_resist: float = 10.0
    evasion: float = 0.0
    block_chance: float = 0.0
    
    # Critical
    crit_chance: float = 0.05
    crit_damage: float = 1.5
    
    # Utility
    movement_speed: float = 1.0
    cooldown_reduction: float = 0.0
    life_steal: float = 0.0
    mana_steal: float = 0.0
    
    # Resistances
    fire_resist: float = 0.0
    ice_resist: float = 0.0
    lightning_resist: float = 0.0
    void_resist: float = 0.0
    
    def apply_equipment(self, equipment: Equipment):
        """Apply equipment stats"""
        self.max_health += equipment.get_total_stat('health')
        self.max_mana += equipment.get_total_stat('mana')
        self.physical_damage += equipment.get_total_stat('physical_damage')
        self.magical_damage += equipment.get_total_stat('magical_damage')
        self.defense += equipment.get_total_stat('defense')
        self.attack_speed += equipment.get_total_stat('attack_speed')
        self.cast_speed += equipment.get_total_stat('cast_speed')
        self.crit_chance += equipment.get_total_stat('crit_chance')
        self.crit_damage += equipment.get_total_stat('crit_damage')
        self.evasion += equipment.get_total_stat('evasion')
        self.block_chance += equipment.get_total_stat('block_chance')
        self.life_steal += equipment.get_total_stat('life_steal')
        self.cooldown_reduction += equipment.get_total_stat('cooldown_reduction')
        self.fire_resist += equipment.get_total_stat('fire_resist')
        self.ice_resist += equipment.get_total_stat('ice_resist')
        self.lightning_resist += equipment.get_total_stat('lightning_resist')
        self.void_resist += equipment.get_total_stat('void_resist')


# ============================================================================
# EQUIPMENT GENERATOR
# ============================================================================

class EquipmentGenerator:
    """Generates random equipment with stats and mods"""
    
    # Available mods for equipment
    EQUIPMENT_MODS = {
        # Offensive
        "physical_damage": {"name": "Physical Power", "range": (5, 50), "is_pct": False},
        "magical_damage": {"name": "Magical Power", "range": (5, 50), "is_pct": False},
        "attack_speed": {"name": "Attack Speed", "range": (3, 15), "is_pct": True},
        "cast_speed": {"name": "Cast Speed", "range": (3, 15), "is_pct": True},
        "crit_chance": {"name": "Critical Chance", "range": (1, 10), "is_pct": True},
        "crit_damage": {"name": "Critical Damage", "range": (10, 50), "is_pct": True},
        "armor_penetration": {"name": "Armor Pen", "range": (3, 15), "is_pct": True},
        
        # Defensive
        "health": {"name": "Health", "range": (20, 200), "is_pct": False},
        "mana": {"name": "Mana", "range": (10, 100), "is_pct": False},
        "defense": {"name": "Defense", "range": (5, 50), "is_pct": False},
        "magic_resist": {"name": "Magic Resist", "range": (5, 50), "is_pct": False},
        "evasion": {"name": "Evasion", "range": (2, 12), "is_pct": True},
        "block_chance": {"name": "Block Chance", "range": (2, 15), "is_pct": True},
        
        # Utility
        "life_steal": {"name": "Life Steal", "range": (1, 8), "is_pct": True},
        "mana_steal": {"name": "Mana Steal", "range": (1, 5), "is_pct": True},
        "cooldown_reduction": {"name": "Cooldown Reduction", "range": (2, 15), "is_pct": True},
        "movement_speed": {"name": "Movement Speed", "range": (2, 10), "is_pct": True},
        
        # Resistances
        "fire_resist": {"name": "Fire Resistance", "range": (5, 30), "is_pct": True},
        "ice_resist": {"name": "Ice Resistance", "range": (5, 30), "is_pct": True},
        "lightning_resist": {"name": "Lightning Resistance", "range": (5, 30), "is_pct": True},
        "void_resist": {"name": "Void Resistance", "range": (5, 30), "is_pct": True},
    }
    
    # Mod tiers with multipliers
    MOD_TIERS = {
        "minor": 0.5,
        "standard": 1.0,
        "greater": 1.5,
        "superior": 2.0,
        "prime": 2.5,
        "divine": 3.0,
    }
    
    # Name prefixes by rarity
    NAME_PREFIXES = {
        "common": ["Simple", "Basic", "Plain", "Worn"],
        "uncommon": ["Sturdy", "Solid", "Reinforced", "Quality"],
        "rare": ["Fine", "Superior", "Mastercraft", "Enchanted"],
        "epic": ["Heroic", "Valiant", "Champion's", "Noble"],
        "legendary": ["Legendary", "Mythical", "Ancient", "Eternal"],
        "mythic": ["Divine", "Celestial", "Godly", "Sacred"],
        "transcendent": ["Transcendent", "Cosmic", "Infinite", "Void-touched"],
        "primordial": ["Primordial", "Origin", "Genesis", "Ultimate"],
    }
    
    # Name suffixes
    NAME_SUFFIXES = [
        "of Power", "of Might", "of the Titan", "of Destruction",
        "of Protection", "of the Guardian", "of Fortitude", "of the Mountain",
        "of Swiftness", "of the Wind", "of Agility", "of Lightning",
        "of Wisdom", "of the Sage", "of Knowledge", "of Arcana",
        "of Fortune", "of the Stars", "of Destiny", "of Fate",
        "of the Void", "of Shadows", "of Fire", "of Ice",
    ]
    
    def __init__(self, seed: bytes = None):
        self.seed = seed or random.randbytes(32)
        self._rng = random.Random(int.from_bytes(self.seed[:8], 'big'))
    
    def _roll_rarity(self, luck_bonus: float = 0.0) -> EquipmentRarity:
        """Roll for equipment rarity"""
        weights = {
            EquipmentRarity.COMMON: 4000,
            EquipmentRarity.UNCOMMON: 3000,
            EquipmentRarity.RARE: 2000,
            EquipmentRarity.EPIC: 700,
            EquipmentRarity.LEGENDARY: 200,
            EquipmentRarity.MYTHIC: 70,
            EquipmentRarity.TRANSCENDENT: 25,
            EquipmentRarity.PRIMORDIAL: 5,
        }
        
        # Luck bonus increases rare drops
        if luck_bonus > 0:
            for rarity in [EquipmentRarity.LEGENDARY, EquipmentRarity.MYTHIC, 
                          EquipmentRarity.TRANSCENDENT, EquipmentRarity.PRIMORDIAL]:
                weights[rarity] = int(weights[rarity] * (1 + luck_bonus))
        
        total = sum(weights.values())
        roll = self._rng.randint(0, total - 1)
        
        cumulative = 0
        for rarity, weight in weights.items():
            cumulative += weight
            if roll < cumulative:
                return rarity
        return EquipmentRarity.COMMON
    
    def _roll_mod_tier(self, rarity: EquipmentRarity) -> str:
        """Roll for mod tier based on equipment rarity"""
        weights = {
            "minor": 3000,
            "standard": 4000,
            "greater": 2000,
            "superior": 800,
            "prime": 180,
            "divine": 20,
        }
        
        # Higher rarity = better mod tiers
        rarity_bonus = rarity.stat_multiplier - 1.0
        for tier in ["greater", "superior", "prime", "divine"]:
            weights[tier] = int(weights[tier] * (1 + rarity_bonus * 0.5))
        
        total = sum(weights.values())
        roll = self._rng.randint(0, total - 1)
        
        cumulative = 0
        for tier, weight in weights.items():
            cumulative += weight
            if roll < cumulative:
                return tier
        return "standard"
    
    def _generate_name(self, equip_type: EquipmentType, rarity: EquipmentRarity) -> str:
        """Generate equipment name"""
        prefix = self._rng.choice(self.NAME_PREFIXES.get(rarity.rarity_id, [""])) 
        base = equip_type.display_name
        
        if rarity.stat_multiplier >= 2.0:
            suffix = self._rng.choice(self.NAME_SUFFIXES)
            return f"{prefix} {base} {suffix}"
        return f"{prefix} {base}"
    
    def generate(self, equip_type: EquipmentType = None, 
                 rarity: EquipmentRarity = None,
                 item_level: int = 1,
                 vault_number: int = None) -> Equipment:
        """Generate a random piece of equipment"""
        
        # Random type if not specified
        if equip_type is None:
            equip_type = self._rng.choice(list(EquipmentType))
        
        # Roll rarity if not specified
        if rarity is None:
            rarity = self._roll_rarity()
        
        # Generate ID
        item_id = hashlib.sha256(
            f"{equip_type.type_id}_{rarity.rarity_id}_{datetime.now().isoformat()}_{self._rng.random()}".encode()
        ).hexdigest()[:16]
        
        # Generate name
        name = self._generate_name(equip_type, rarity)
        
        # Calculate base stats with rarity multiplier
        base_stats = {}
        for stat, value in equip_type.base_stats.items():
            base_stats[stat] = value * rarity.stat_multiplier * (1 + item_level * 0.05)
        
        # Determine slot
        slot = equip_type.slot
        if slot == "two_hand":
            slot = "main_hand"  # Two-handers use main hand slot
        elif slot == "ring":
            slot = self._rng.choice(["ring_1", "ring_2"])
        
        # Generate mods
        num_mods = self._rng.randint(rarity.min_mods, rarity.max_mods)
        mods = []
        used_mods = set()
        
        for _ in range(num_mods):
            available = [m for m in self.EQUIPMENT_MODS.keys() if m not in used_mods]
            if not available:
                break
            
            mod_type = self._rng.choice(available)
            used_mods.add(mod_type)
            
            mod_info = self.EQUIPMENT_MODS[mod_type]
            tier = self._roll_mod_tier(rarity)
            tier_mult = self.MOD_TIERS[tier]
            
            min_val, max_val = mod_info["range"]
            value = self._rng.uniform(min_val, max_val) * tier_mult * (1 + item_level * 0.02)
            
            mods.append(EquipmentMod(
                mod_type=mod_type,
                value=round(value, 1),
                tier=tier,
                is_percent=mod_info["is_pct"]
            ))
        
        # Create equipment
        equipment = Equipment(
            item_id=item_id,
            name=name,
            equipment_type=equip_type.type_id,
            slot=slot,
            rarity=rarity.rarity_id,
            item_level=item_level,
            base_stats=base_stats,
            mods=mods,
            origin_vault=vault_number,
            current_vault=vault_number
        )
        
        # Calculate derived stats
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
        equipment.movement_speed = base_stats.get("movement_speed", 0)
        equipment.cooldown_reduction = base_stats.get("cooldown_reduction", 0)
        
        return equipment


# ============================================================================
# COMBAT ENGINE
# ============================================================================

@dataclass
class CombatAction:
    """A single combat action"""
    action_type: str  # "attack", "skill", "defend", "flee"
    source: str
    target: str
    damage_type: str = "physical"
    damage: float = 0.0
    is_critical: bool = False
    is_blocked: bool = False
    is_evaded: bool = False
    status_applied: Optional[str] = None
    timestamp: str = ""


class CombatEngine:
    """Handles combat calculations"""
    
    def __init__(self):
        self.combat_log: List[CombatAction] = []
    
    def calculate_damage(self, attacker: CombatStats, defender: CombatStats,
                        damage_type: DamageType = DamageType.PHYSICAL,
                        skill_multiplier: float = 1.0) -> Tuple[float, bool, bool, bool]:
        """
        Calculate damage from attacker to defender
        Returns: (damage, is_critical, is_blocked, is_evaded)
        """
        # Base damage
        if damage_type == DamageType.PHYSICAL:
            base_damage = attacker.physical_damage * skill_multiplier
            reduction = defender.defense
        elif damage_type == DamageType.MAGICAL:
            base_damage = attacker.magical_damage * skill_multiplier
            reduction = defender.magic_resist
        elif damage_type == DamageType.TRUE:
            base_damage = (attacker.physical_damage + attacker.magical_damage) / 2 * skill_multiplier
            reduction = 0
        else:
            # Elemental
            base_damage = attacker.magical_damage * skill_multiplier
            resist = getattr(defender, f"{damage_type.dmg_id}_resist", 0)
            reduction = defender.magic_resist * (1 + resist / 100)
        
        # Check evasion
        is_evaded = random.random() < defender.evasion
        if is_evaded:
            return 0, False, False, True
        
        # Check block
        is_blocked = random.random() < defender.block_chance
        if is_blocked:
            base_damage *= 0.3  # Blocked attacks deal 30% damage
        
        # Check critical
        is_critical = random.random() < attacker.crit_chance
        if is_critical:
            base_damage *= attacker.crit_damage
        
        # Apply defense reduction (diminishing returns formula)
        damage_multiplier = 100 / (100 + reduction)
        final_damage = base_damage * damage_multiplier
        
        # Minimum damage
        final_damage = max(1, final_damage)
        
        return final_damage, is_critical, is_blocked, is_evaded
    
    def apply_damage(self, target: CombatStats, damage: float) -> bool:
        """Apply damage to target, returns True if target dies"""
        target.health -= damage
        return target.health <= 0
    
    def apply_healing(self, target: CombatStats, amount: float) -> float:
        """Apply healing to target, returns actual healed amount"""
        old_health = target.health
        target.health = min(target.max_health, target.health + amount)
        return target.health - old_health
    
    def process_life_steal(self, attacker: CombatStats, damage: float) -> float:
        """Process life steal from damage dealt"""
        if attacker.life_steal > 0:
            heal_amount = damage * attacker.life_steal
            return self.apply_healing(attacker, heal_amount)
        return 0


# ============================================================================
# EQUIPMENT MANAGER
# ============================================================================

class EquipmentManager:
    """Manages equipment storage and operations"""
    
    def __init__(self, storage_path: str = "./alchemical_vault/equipment"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._equipment: Dict[str, Equipment] = {}
        self._load_equipment()
    
    def _load_equipment(self):
        """Load all equipment from storage"""
        for file in self.storage_path.glob("equip_*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    equip = Equipment.from_dict(data)
                    self._equipment[equip.item_id] = equip
            except Exception as e:
                print(f"Error loading {file}: {e}")
    
    def save_equipment(self, equipment: Equipment):
        """Save equipment to storage"""
        file_path = self.storage_path / f"equip_{equipment.item_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(equipment.to_dict(), f, indent=2, ensure_ascii=False)
        self._equipment[equipment.item_id] = equipment
    
    def get_equipment(self, item_id: str) -> Optional[Equipment]:
        """Get equipment by ID"""
        return self._equipment.get(item_id)
    
    def get_vault_equipment(self, vault_number: int) -> List[Equipment]:
        """Get all equipment for a vault"""
        return [e for e in self._equipment.values() if e.current_vault == vault_number]
    
    def generate_equipment(self, vault_number: int, count: int = 1, 
                          min_level: int = 1, max_level: int = 10) -> List[Equipment]:
        """Generate random equipment for a vault"""
        generator = EquipmentGenerator()
        equipment_list = []
        
        for _ in range(count):
            level = random.randint(min_level, max_level)
            equip = generator.generate(item_level=level, vault_number=vault_number)
            self.save_equipment(equip)
            equipment_list.append(equip)
        
        return equipment_list


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_equipment_display(equipment: Equipment) -> str:
    """Format equipment for display"""
    rarity_colors = {
        "common": "white", "uncommon": "green", "rare": "blue",
        "epic": "purple", "legendary": "orange", "mythic": "gold",
        "transcendent": "cyan", "primordial": "magenta"
    }
    
    lines = []
    lines.append(f"\n{'='*50}")
    lines.append(f"  [{equipment.rarity.upper()}] {equipment.name}")
    lines.append(f"  Type: {equipment.equipment_type} | Slot: {equipment.slot}")
    lines.append(f"  Item Level: {equipment.item_level}")
    lines.append(f"{'='*50}")
    
    # Base stats
    lines.append("\n  BASE STATS:")
    if equipment.physical_damage > 0:
        lines.append(f"    Physical Damage: {equipment.physical_damage:.0f}")
    if equipment.magical_damage > 0:
        lines.append(f"    Magical Damage: {equipment.magical_damage:.0f}")
    if equipment.defense > 0:
        lines.append(f"    Defense: {equipment.defense:.0f}")
    if equipment.health > 0:
        lines.append(f"    Health: +{equipment.health:.0f}")
    if equipment.mana > 0:
        lines.append(f"    Mana: +{equipment.mana:.0f}")
    
    # Secondary stats
    secondary = []
    if equipment.attack_speed != 0:
        secondary.append(f"Attack Speed: {equipment.attack_speed:+.1%}")
    if equipment.crit_chance > 0:
        secondary.append(f"Crit Chance: {equipment.crit_chance:.1%}")
    if equipment.evasion > 0:
        secondary.append(f"Evasion: {equipment.evasion:.1%}")
    if equipment.life_steal > 0:
        secondary.append(f"Life Steal: {equipment.life_steal:.1%}")
    
    if secondary:
        lines.append("\n  SECONDARY:")
        for s in secondary:
            lines.append(f"    {s}")
    
    # Mods
    if equipment.mods:
        lines.append("\n  MODS:")
        for mod in equipment.mods:
            tier_display = f"[{mod.tier.upper()}]" if mod.tier != "standard" else ""
            lines.append(f"    {tier_display} {mod.mod_type}: {mod.get_display()}")
    
    lines.append(f"\n{'='*50}\n")
    return "\n".join(lines)


# Singleton
_equipment_manager: Optional[EquipmentManager] = None

def get_equipment_manager() -> EquipmentManager:
    global _equipment_manager
    if _equipment_manager is None:
        _equipment_manager = EquipmentManager()
    return _equipment_manager
