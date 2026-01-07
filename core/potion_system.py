#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      POTION SYSTEM - Eidolon                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Complete potion system with:                                                ║
║  - 8 potion types (Health, Mana, Power, Defense, Speed, Crit, etc.)         ║
║  - 6 quality tiers (Minor to Supreme)                                        ║
║  - Pioneer-based RNG for chest distribution                                  ║
║  - 16 potions per vault chest                                                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import random
import hashlib
import secrets
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path


# ============================================================================
# POTION TYPES
# ============================================================================

class PotionType(Enum):
    """Types of potions available"""
    # Restoration
    HEALTH = ("health", "Health Potion", "restoration", {
        "restore_health": 1.0, "heal_over_time": 0.0
    })
    MANA = ("mana", "Mana Potion", "restoration", {
        "restore_mana": 1.0, "mana_regen": 0.0
    })
    REJUVENATION = ("rejuvenation", "Rejuvenation Elixir", "restoration", {
        "restore_health": 0.5, "restore_mana": 0.5
    })
    
    # Offensive
    POWER = ("power", "Power Elixir", "offensive", {
        "phys_damage_boost": 1.0, "duration": 60
    })
    ARCANE = ("arcane", "Arcane Draught", "offensive", {
        "mag_damage_boost": 1.0, "duration": 60
    })
    FURY = ("fury", "Fury Tonic", "offensive", {
        "attack_speed_boost": 0.5, "crit_chance_boost": 0.5, "duration": 45
    })
    
    # Defensive
    FORTITUDE = ("fortitude", "Fortitude Brew", "defensive", {
        "defense_boost": 1.0, "duration": 60
    })
    IRONHIDE = ("ironhide", "Ironhide Potion", "defensive", {
        "damage_reduction": 0.7, "health_boost": 0.3, "duration": 45
    })
    
    # Utility
    SWIFTNESS = ("swiftness", "Swiftness Serum", "utility", {
        "movement_speed": 1.0, "duration": 90
    })
    INVISIBILITY = ("invisibility", "Invisibility Vial", "utility", {
        "stealth": 1.0, "duration": 30
    })
    INSIGHT = ("insight", "Insight Philter", "utility", {
        "exp_boost": 0.6, "loot_boost": 0.4, "duration": 120
    })
    
    # Special
    PHOENIX = ("phoenix", "Phoenix Tears", "special", {
        "auto_revive": 1.0, "revive_health": 0.5
    })
    TRANSMUTATION = ("transmutation", "Transmutation Oil", "special", {
        "convert_damage": 1.0, "duration": 60
    })
    VOID_ESSENCE = ("void_essence", "Void Essence", "special", {
        "void_damage": 0.5, "life_steal": 0.5, "duration": 45
    })
    QUANTUM_FLUX = ("quantum_flux", "Quantum Flux", "special", {
        "cooldown_reduction": 0.6, "cast_speed": 0.4, "duration": 60
    })
    NEXUS_CATALYST = ("nexus_catalyst", "Nexus Catalyst", "special", {
        "all_stats_boost": 1.0, "duration": 30
    })
    
    def __init__(self, potion_id: str, name: str, category: str, effects: dict):
        self.potion_id = potion_id
        self.display_name = name
        self.category = category
        self.base_effects = effects


class PotionQuality(Enum):
    """Quality tiers for potions"""
    MINOR = ("minor", "Minor", 0.5, "#808080", 0.35)
    LESSER = ("lesser", "Lesser", 0.75, "#1eff00", 0.25)
    STANDARD = ("standard", "", 1.0, "#0070dd", 0.20)
    GREATER = ("greater", "Greater", 1.5, "#a335ee", 0.12)
    SUPERIOR = ("superior", "Superior", 2.0, "#ff8000", 0.06)
    SUPREME = ("supreme", "Supreme", 3.0, "#e6cc80", 0.02)
    
    def __init__(self, quality_id: str, prefix: str, multiplier: float, 
                 color: str, base_drop_rate: float):
        self.quality_id = quality_id
        self.prefix = prefix
        self.multiplier = multiplier
        self.color = color
        self.base_drop_rate = base_drop_rate


# ============================================================================
# PIONEER TIERS (for RNG)
# ============================================================================

class PotionPioneerTier(Enum):
    """
    Pioneer tiers affect potion quality chances.
    
    Balanced RNG with progressive scaling:
    - Genesis gets best odds but not overwhelming
    - Each tier drops ~20-30% from previous
    - Standard tier uses base rates only
    
    Expected Supreme rates:
    - Genesis: ~5-6%
    - Primordial: ~4%
    - Supreme: ~3%
    - Elite: ~2.5%
    - Veteran: ~2%
    - Early: ~1.5%
    - Pioneer: ~1.2%
    - Standard: ~1%
    """
    GENESIS = ("genesis", 1, 10, 1.8, {
        "supreme_boost": 0.03, "superior_boost": 0.06, "greater_boost": 0.08
    })
    PRIMORDIAL = ("primordial", 11, 33, 1.6, {
        "supreme_boost": 0.02, "superior_boost": 0.04, "greater_boost": 0.06
    })
    SUPREME = ("supreme", 34, 100, 1.4, {
        "supreme_boost": 0.01, "superior_boost": 0.03, "greater_boost": 0.05
    })
    ELITE = ("elite", 101, 333, 1.25, {
        "supreme_boost": 0.006, "superior_boost": 0.02, "greater_boost": 0.04
    })
    VETERAN = ("veteran", 334, 1000, 1.15, {
        "supreme_boost": 0.003, "superior_boost": 0.012, "greater_boost": 0.025
    })
    EARLY = ("early", 1001, 3333, 1.08, {
        "supreme_boost": 0.001, "superior_boost": 0.006, "greater_boost": 0.015
    })
    PIONEER = ("pioneer", 3334, 10000, 1.03, {
        "supreme_boost": 0.0, "superior_boost": 0.003, "greater_boost": 0.008
    })
    STANDARD = ("standard", 10001, float('inf'), 1.0, {
        "supreme_boost": 0.0, "superior_boost": 0.0, "greater_boost": 0.0
    })
    
    def __init__(self, tier_id: str, min_vault: int, max_vault: int,
                 quality_mult: float, bonuses: dict):
        self.tier_id = tier_id
        self.min_vault = min_vault
        self.max_vault = max_vault
        self.quality_multiplier = quality_mult
        self.bonuses = bonuses
    
    @classmethod
    def get_tier(cls, vault_number: int) -> 'PotionPioneerTier':
        for tier in cls:
            if tier.min_vault <= vault_number <= tier.max_vault:
                return tier
        return cls.STANDARD


# ============================================================================
# POTION DATA STRUCTURE
# ============================================================================

@dataclass
class Potion:
    """A single potion instance"""
    potion_id: str
    potion_type: str
    quality: str
    name: str
    
    # Effects
    effects: Dict[str, float] = field(default_factory=dict)
    duration: int = 0  # seconds, 0 = instant
    
    # Stats
    power: float = 0.0
    stack_size: int = 1
    max_stack: int = 20
    
    # Metadata
    category: str = "restoration"
    color: str = "#ffffff"
    description: str = ""
    
    # Origin
    origin_vault: int = 0
    origin_chest: Optional[str] = None
    pioneer_tier: str = "standard"
    
    # Timestamps
    created_at: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Potion':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def get_effect_value(self, effect_name: str) -> float:
        return self.effects.get(effect_name, 0.0)
    
    def format_effects(self) -> str:
        lines = []
        for effect, value in self.effects.items():
            if effect == "duration":
                continue
            formatted = effect.replace("_", " ").title()
            if value < 1:
                lines.append(f"+{value*100:.0f}% {formatted}")
            else:
                lines.append(f"+{value:.0f} {formatted}")
        if self.duration > 0:
            lines.append(f"Duration: {self.duration}s")
        return "\n".join(lines)


@dataclass 
class PotionChest:
    """A chest containing 16 potions"""
    chest_id: str
    vault_number: int
    pioneer_tier: str
    
    potions: List[str] = field(default_factory=list)  # potion_ids
    
    is_opened: bool = False
    created_at: str = ""
    opened_at: Optional[str] = None
    
    # Stats
    total_potions: int = 16
    quality_distribution: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# POTION GENERATOR
# ============================================================================

class PotionGenerator:
    """Generates potions with pioneer-based RNG"""
    
    def __init__(self, seed: bytes = None):
        if seed:
            self._rng = random.Random(int.from_bytes(seed[:8], 'big'))
        else:
            self._rng = random.Random()
    
    def set_seed(self, seed: bytes):
        """Set RNG seed for reproducibility"""
        self._rng = random.Random(int.from_bytes(seed[:8], 'big'))
    
    def _roll_quality(self, vault_number: int) -> PotionQuality:
        """Roll potion quality based on pioneer tier"""
        tier = PotionPioneerTier.get_tier(vault_number)
        
        # Calculate adjusted drop rates
        rates = {}
        for quality in PotionQuality:
            base_rate = quality.base_drop_rate
            
            # Apply pioneer bonuses
            if quality == PotionQuality.SUPREME:
                base_rate += tier.bonuses.get("supreme_boost", 0)
            elif quality == PotionQuality.SUPERIOR:
                base_rate += tier.bonuses.get("superior_boost", 0)
            elif quality == PotionQuality.GREATER:
                base_rate += tier.bonuses.get("greater_boost", 0)
            
            # Apply tier multiplier
            rates[quality] = base_rate * tier.quality_multiplier
        
        # Normalize rates
        total = sum(rates.values())
        normalized = {q: r/total for q, r in rates.items()}
        
        # Roll
        roll = self._rng.random()
        cumulative = 0
        for quality, rate in normalized.items():
            cumulative += rate
            if roll < cumulative:
                return quality
        
        return PotionQuality.MINOR
    
    def _roll_potion_type(self, category_weights: Dict[str, float] = None) -> PotionType:
        """Roll potion type with optional category weighting"""
        if category_weights is None:
            category_weights = {
                "restoration": 0.35,
                "offensive": 0.20,
                "defensive": 0.20,
                "utility": 0.15,
                "special": 0.10
            }
        
        # Group potions by category
        by_category = {}
        for pt in PotionType:
            cat = pt.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(pt)
        
        # Roll category
        roll = self._rng.random()
        cumulative = 0
        selected_category = "restoration"
        for cat, weight in category_weights.items():
            cumulative += weight
            if roll < cumulative:
                selected_category = cat
                break
        
        # Roll type within category
        potions_in_cat = by_category.get(selected_category, list(PotionType))
        return self._rng.choice(potions_in_cat)
    
    def generate_potion(self, vault_number: int, 
                        potion_type: PotionType = None,
                        quality: PotionQuality = None) -> Potion:
        """Generate a single potion"""
        tier = PotionPioneerTier.get_tier(vault_number)
        
        # Roll type and quality if not specified
        if potion_type is None:
            potion_type = self._roll_potion_type()
        if quality is None:
            quality = self._roll_quality(vault_number)
        
        # Generate ID
        potion_id = hashlib.sha256(
            f"{potion_type.potion_id}_{quality.quality_id}_{vault_number}_{datetime.now().isoformat()}_{self._rng.random()}".encode()
        ).hexdigest()[:16]
        
        # Generate name
        if quality.prefix:
            name = f"{quality.prefix} {potion_type.display_name}"
        else:
            name = potion_type.display_name
        
        # Calculate effects with quality multiplier
        effects = {}
        duration = 0
        for effect, base_value in potion_type.base_effects.items():
            if effect == "duration":
                duration = int(base_value * quality.multiplier)
            else:
                effects[effect] = base_value * quality.multiplier
        
        # Calculate power score
        power = sum(effects.values()) * 100 * quality.multiplier
        
        # Generate description
        description = self._generate_description(potion_type, quality)
        
        return Potion(
            potion_id=potion_id,
            potion_type=potion_type.potion_id,
            quality=quality.quality_id,
            name=name,
            effects=effects,
            duration=duration,
            power=power,
            category=potion_type.category,
            color=quality.color,
            description=description,
            origin_vault=vault_number,
            pioneer_tier=tier.tier_id,
            created_at=datetime.now().isoformat()
        )
    
    def _generate_description(self, potion_type: PotionType, 
                              quality: PotionQuality) -> str:
        """Generate potion description"""
        descriptions = {
            "health": "Restores health when consumed.",
            "mana": "Restores magical energy.",
            "rejuvenation": "Restores both health and mana.",
            "power": "Increases physical damage temporarily.",
            "arcane": "Enhances magical abilities.",
            "fury": "Increases attack speed and critical chance.",
            "fortitude": "Enhances defensive capabilities.",
            "ironhide": "Reduces incoming damage.",
            "swiftness": "Increases movement speed.",
            "invisibility": "Grants temporary invisibility.",
            "insight": "Increases experience and loot gains.",
            "phoenix": "Automatically revives upon death.",
            "transmutation": "Converts damage types.",
            "void_essence": "Infuses attacks with void energy.",
            "quantum_flux": "Reduces ability cooldowns.",
            "nexus_catalyst": "Boosts all stats temporarily."
        }
        
        base_desc = descriptions.get(potion_type.potion_id, "A mysterious potion.")
        
        quality_prefix = {
            "minor": "A weak",
            "lesser": "A modest",
            "standard": "A standard",
            "greater": "A potent",
            "superior": "A powerful",
            "supreme": "An extraordinary"
        }
        
        prefix = quality_prefix.get(quality.quality_id, "A")
        return f"{prefix} concoction. {base_desc}"


# ============================================================================
# POTION CHEST SYSTEM
# ============================================================================

class PotionChestSystem:
    """Manages potion chest creation and opening"""
    
    POTIONS_PER_CHEST = 16
    
    def __init__(self, data_dir: str = None):
        base_path = Path(__file__).parent.parent
        self.data_dir = Path(data_dir) if data_dir else base_path / "alchemical_vault"
        
        self.chests_path = self.data_dir / "potion_chests"
        self.potions_path = self.data_dir / "potions"
        
        self.chests_path.mkdir(parents=True, exist_ok=True)
        self.potions_path.mkdir(parents=True, exist_ok=True)
        
        self.generator = PotionGenerator()
    
    def _get_vault_seed(self, vault_number: int) -> bytes:
        """Generate deterministic seed for vault"""
        seed_data = f"eidolon_potion_chest_{vault_number}_v1"
        return hashlib.sha256(seed_data.encode()).digest()
    
    def create_chest(self, vault_number: int) -> PotionChest:
        """Create a potion chest for a vault"""
        tier = PotionPioneerTier.get_tier(vault_number)
        
        # Generate chest ID
        chest_id = hashlib.sha256(
            f"potion_chest_{vault_number}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        chest = PotionChest(
            chest_id=chest_id,
            vault_number=vault_number,
            pioneer_tier=tier.tier_id,
            potions=[],
            is_opened=False,
            created_at=datetime.now().isoformat(),
            total_potions=self.POTIONS_PER_CHEST,
            quality_distribution={}
        )
        
        # Save chest
        chest_file = self.chests_path / f"potion_chest_{chest_id}.json"
        with open(chest_file, 'w', encoding='utf-8') as f:
            json.dump(chest.to_dict(), f, indent=2, ensure_ascii=False)
        
        return chest
    
    def open_chest(self, chest_id: str) -> List[Potion]:
        """Open a potion chest and generate potions"""
        # Load chest
        chest_file = self.chests_path / f"potion_chest_{chest_id}.json"
        if not chest_file.exists():
            # Try to find by pattern
            for f in self.chests_path.glob(f"*{chest_id}*.json"):
                chest_file = f
                break
        
        if not chest_file.exists():
            raise ValueError(f"Chest not found: {chest_id}")
        
        with open(chest_file, 'r', encoding='utf-8') as f:
            chest_data = json.load(f)
        
        if chest_data.get("is_opened"):
            raise ValueError("Chest already opened")
        
        vault_number = chest_data["vault_number"]
        
        # Set deterministic seed based on vault and chest
        seed = hashlib.sha256(
            f"{chest_id}_{vault_number}_potions".encode()
        ).digest()
        self.generator.set_seed(seed)
        
        # Generate potions
        potions = []
        quality_dist = {}
        
        for i in range(self.POTIONS_PER_CHEST):
            potion = self.generator.generate_potion(vault_number)
            potion.origin_chest = chest_id
            potions.append(potion)
            
            # Track quality distribution
            q = potion.quality
            quality_dist[q] = quality_dist.get(q, 0) + 1
            
            # Save potion
            potion_file = self.potions_path / f"potion_{potion.potion_id}.json"
            with open(potion_file, 'w', encoding='utf-8') as f:
                json.dump(potion.to_dict(), f, indent=2, ensure_ascii=False)
        
        # Update chest
        chest_data["is_opened"] = True
        chest_data["opened_at"] = datetime.now().isoformat()
        chest_data["potions"] = [p.potion_id for p in potions]
        chest_data["quality_distribution"] = quality_dist
        
        with open(chest_file, 'w', encoding='utf-8') as f:
            json.dump(chest_data, f, indent=2, ensure_ascii=False)
        
        return potions
    
    def get_vault_chest(self, vault_number: int) -> Optional[Dict]:
        """Get chest for a vault"""
        for chest_file in self.chests_path.glob("potion_chest_*.json"):
            with open(chest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get("vault_number") == vault_number:
                return data
        return None
    
    def get_vault_potions(self, vault_number: int) -> List[Potion]:
        """Get all potions from a vault"""
        potions = []
        for potion_file in self.potions_path.glob("potion_*.json"):
            with open(potion_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get("origin_vault") == vault_number:
                potions.append(Potion.from_dict(data))
        return potions


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_potion(potion: Potion) -> str:
    """Format potion for display"""
    lines = [
        f"{'='*50}",
        f"  [{potion.quality.upper()}] {potion.name}",
        f"  Type: {potion.potion_type} | Category: {potion.category}",
        f"  Power: {potion.power:.0f}",
        f"{'='*50}",
        "",
        "  EFFECTS:"
    ]
    
    for effect, value in potion.effects.items():
        if value < 1:
            lines.append(f"    +{value*100:.0f}% {effect.replace('_', ' ').title()}")
        else:
            lines.append(f"    +{value:.0f} {effect.replace('_', ' ').title()}")
    
    if potion.duration > 0:
        lines.append(f"    Duration: {potion.duration}s")
    
    lines.append("")
    lines.append(f"  {potion.description}")
    
    return "\n".join(lines)
