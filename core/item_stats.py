#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              SYSTEME DE STATS - Eidolon                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Stats primaires et secondaires pour les items et personnages.              ║
║                                                                              ║
║  STATS PRIMAIRES (6):                                                        ║
║  - FORCE: Degats physiques, capacite de port                                ║
║  - AGILITE: Vitesse, esquive, precision                                     ║
║  - INTELLIGENCE: Puissance magique, mana                                    ║
║  - VITALITE: Points de vie, regeneration                                    ║
║  - SAGESSE: Resistance magique, cooldowns                                   ║
║  - CHANCE: Drops, critiques, rolls                                          ║
║                                                                              ║
║  STATS SECONDAIRES (derivees):                                              ║
║  - PV Max, Mana Max, Degats, Defense, Critique, etc.                        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import random
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any


# ============================================================================
# STATS PRIMAIRES
# ============================================================================

class PrimaryStat(Enum):
    """Les 6 stats primaires"""
    STRENGTH = ("strength", "Force", "STR", "Degats physiques et capacite de port")
    AGILITY = ("agility", "Agilite", "AGI", "Vitesse, esquive et precision")
    INTELLIGENCE = ("intelligence", "Intelligence", "INT", "Puissance magique et mana")
    VITALITY = ("vitality", "Vitalite", "VIT", "Points de vie et regeneration")
    WISDOM = ("wisdom", "Sagesse", "SAG", "Resistance magique et cooldowns")
    LUCK = ("luck", "Chance", "LCK", "Drops, critiques et rolls")
    
    def __init__(self, stat_id: str, name: str, abbrev: str, description: str):
        self.stat_id = stat_id
        self.display_name = name
        self.abbrev = abbrev
        self.description = description


# ============================================================================
# STATS SECONDAIRES
# ============================================================================

class SecondaryStat(Enum):
    """Stats secondaires derivees des primaires"""
    # === Combat ===
    HEALTH = ("health", "Points de Vie", "PV", "VIT")
    MANA = ("mana", "Mana", "MP", "INT")
    PHYSICAL_DAMAGE = ("phys_dmg", "Degats Physiques", "DPhy", "STR")
    MAGICAL_DAMAGE = ("mag_dmg", "Degats Magiques", "DMag", "INT")
    DEFENSE = ("defense", "Defense", "DEF", "VIT+STR")
    MAGIC_RESIST = ("mag_res", "Resistance Magique", "RMag", "SAG")
    
    # === Vitesse ===
    ATTACK_SPEED = ("atk_spd", "Vitesse d'Attaque", "VAtk", "AGI")
    CAST_SPEED = ("cast_spd", "Vitesse d'Incantation", "VInc", "INT+AGI")
    MOVEMENT_SPEED = ("mov_spd", "Vitesse de Deplacement", "VMov", "AGI")
    
    # === Precision ===
    ACCURACY = ("accuracy", "Precision", "PRC", "AGI")
    EVASION = ("evasion", "Esquive", "ESQ", "AGI")
    BLOCK_CHANCE = ("block", "Blocage", "BLK", "STR")
    
    # === Critique ===
    CRIT_CHANCE = ("crit_chance", "Chance Critique", "CCrit", "LCK+AGI")
    CRIT_DAMAGE = ("crit_dmg", "Degats Critiques", "DCrit", "STR+LCK")
    
    # === Regeneration ===
    HEALTH_REGEN = ("hp_regen", "Regen PV", "RPV", "VIT")
    MANA_REGEN = ("mp_regen", "Regen Mana", "RMP", "SAG")
    
    # === Utilitaire ===
    COOLDOWN_REDUCTION = ("cdr", "Reduction Cooldown", "CDR", "SAG")
    RESOURCE_GAIN = ("res_gain", "Gain de Ressources", "GRes", "LCK")
    EXPERIENCE_BONUS = ("exp_bonus", "Bonus Experience", "BExp", "SAG+LCK")
    DROP_BONUS = ("drop_bonus", "Bonus Drop", "BDrp", "LCK")
    
    def __init__(self, stat_id: str, name: str, abbrev: str, derived_from: str):
        self.stat_id = stat_id
        self.display_name = name
        self.abbrev = abbrev
        self.derived_from = derived_from


# ============================================================================
# STATS ELEMENTAIRES
# ============================================================================

class Element(Enum):
    """Elements pour degats et resistances"""
    FIRE = ("fire", "Feu", "#ff4400", "STR")
    ICE = ("ice", "Glace", "#88ccff", "INT")
    LIGHTNING = ("lightning", "Foudre", "#ffff00", "AGI")
    EARTH = ("earth", "Terre", "#8b4513", "VIT")
    WIND = ("wind", "Vent", "#aaffaa", "AGI")
    VOID = ("void", "Vide", "#aa00ff", "INT")
    LIGHT = ("light", "Lumiere", "#ffffff", "SAG")
    SHADOW = ("shadow", "Ombre", "#333333", "LCK")
    QUANTUM = ("quantum", "Quantique", "#00ffff", "INT+SAG")
    TEMPORAL = ("temporal", "Temporel", "#ffd700", "SAG+LCK")
    
    def __init__(self, elem_id: str, name: str, color: str, scaling: str):
        self.elem_id = elem_id
        self.display_name = name
        self.color = color
        self.scaling_stat = scaling


# ============================================================================
# BLOC DE STATS
# ============================================================================

@dataclass
class StatBlock:
    """Bloc de statistiques complet pour un item ou personnage"""
    
    # Stats primaires (base 0-100 pour items)
    strength: int = 0
    agility: int = 0
    intelligence: int = 0
    vitality: int = 0
    wisdom: int = 0
    luck: int = 0
    
    # Stats secondaires (bonus flat)
    health_bonus: int = 0
    mana_bonus: int = 0
    phys_damage_bonus: int = 0
    mag_damage_bonus: int = 0
    defense_bonus: int = 0
    mag_resist_bonus: int = 0
    
    # Stats en pourcentage
    attack_speed_pct: float = 0.0
    cast_speed_pct: float = 0.0
    movement_speed_pct: float = 0.0
    crit_chance_pct: float = 0.0
    crit_damage_pct: float = 0.0
    evasion_pct: float = 0.0
    block_pct: float = 0.0
    cooldown_reduction_pct: float = 0.0
    
    # Regeneration
    health_regen: float = 0.0
    mana_regen: float = 0.0
    
    # Bonus utilitaires
    experience_bonus_pct: float = 0.0
    drop_bonus_pct: float = 0.0
    resource_gain_pct: float = 0.0
    
    # Degats elementaires
    fire_damage: int = 0
    ice_damage: int = 0
    lightning_damage: int = 0
    void_damage: int = 0
    
    # Resistances elementaires (%)
    fire_resist_pct: float = 0.0
    ice_resist_pct: float = 0.0
    lightning_resist_pct: float = 0.0
    void_resist_pct: float = 0.0
    all_resist_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StatBlock':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def get_primary_total(self) -> int:
        """Total des stats primaires"""
        return self.strength + self.agility + self.intelligence + \
               self.vitality + self.wisdom + self.luck
    
    def get_dominant_stat(self) -> PrimaryStat:
        """Retourne la stat primaire dominante"""
        stats = {
            PrimaryStat.STRENGTH: self.strength,
            PrimaryStat.AGILITY: self.agility,
            PrimaryStat.INTELLIGENCE: self.intelligence,
            PrimaryStat.VITALITY: self.vitality,
            PrimaryStat.WISDOM: self.wisdom,
            PrimaryStat.LUCK: self.luck,
        }
        return max(stats, key=stats.get)
    
    def __add__(self, other: 'StatBlock') -> 'StatBlock':
        """Additionne deux blocs de stats"""
        return StatBlock(
            strength=self.strength + other.strength,
            agility=self.agility + other.agility,
            intelligence=self.intelligence + other.intelligence,
            vitality=self.vitality + other.vitality,
            wisdom=self.wisdom + other.wisdom,
            luck=self.luck + other.luck,
            health_bonus=self.health_bonus + other.health_bonus,
            mana_bonus=self.mana_bonus + other.mana_bonus,
            phys_damage_bonus=self.phys_damage_bonus + other.phys_damage_bonus,
            mag_damage_bonus=self.mag_damage_bonus + other.mag_damage_bonus,
            defense_bonus=self.defense_bonus + other.defense_bonus,
            mag_resist_bonus=self.mag_resist_bonus + other.mag_resist_bonus,
            attack_speed_pct=self.attack_speed_pct + other.attack_speed_pct,
            cast_speed_pct=self.cast_speed_pct + other.cast_speed_pct,
            movement_speed_pct=self.movement_speed_pct + other.movement_speed_pct,
            crit_chance_pct=self.crit_chance_pct + other.crit_chance_pct,
            crit_damage_pct=self.crit_damage_pct + other.crit_damage_pct,
            evasion_pct=self.evasion_pct + other.evasion_pct,
            block_pct=self.block_pct + other.block_pct,
            cooldown_reduction_pct=self.cooldown_reduction_pct + other.cooldown_reduction_pct,
            health_regen=self.health_regen + other.health_regen,
            mana_regen=self.mana_regen + other.mana_regen,
            experience_bonus_pct=self.experience_bonus_pct + other.experience_bonus_pct,
            drop_bonus_pct=self.drop_bonus_pct + other.drop_bonus_pct,
            resource_gain_pct=self.resource_gain_pct + other.resource_gain_pct,
            fire_damage=self.fire_damage + other.fire_damage,
            ice_damage=self.ice_damage + other.ice_damage,
            lightning_damage=self.lightning_damage + other.lightning_damage,
            void_damage=self.void_damage + other.void_damage,
            fire_resist_pct=self.fire_resist_pct + other.fire_resist_pct,
            ice_resist_pct=self.ice_resist_pct + other.ice_resist_pct,
            lightning_resist_pct=self.lightning_resist_pct + other.lightning_resist_pct,
            void_resist_pct=self.void_resist_pct + other.void_resist_pct,
            all_resist_pct=self.all_resist_pct + other.all_resist_pct,
        )


# ============================================================================
# GENERATION DE STATS POUR ITEMS
# ============================================================================

# Configuration des stats par categorie d'item
CATEGORY_STAT_WEIGHTS = {
    "potion": {"vitality": 40, "strength": 20, "intelligence": 20, "luck": 10, "agility": 5, "wisdom": 5},
    "elixir": {"wisdom": 30, "vitality": 25, "intelligence": 25, "luck": 10, "strength": 5, "agility": 5},
    "rune": {"intelligence": 35, "wisdom": 30, "luck": 20, "agility": 10, "strength": 3, "vitality": 2},
    "scroll": {"intelligence": 40, "wisdom": 35, "luck": 15, "agility": 5, "strength": 3, "vitality": 2},
    "essence": {"luck": 30, "intelligence": 25, "wisdom": 25, "vitality": 10, "agility": 5, "strength": 5},
    "talisman": {"wisdom": 35, "vitality": 30, "luck": 20, "intelligence": 10, "strength": 3, "agility": 2},
    "orb": {"intelligence": 40, "wisdom": 30, "luck": 15, "vitality": 10, "agility": 3, "strength": 2},
    "seal": {"wisdom": 40, "intelligence": 30, "luck": 15, "vitality": 10, "strength": 3, "agility": 2},
    "sigil": {"luck": 35, "agility": 25, "intelligence": 20, "wisdom": 15, "strength": 3, "vitality": 2},
    "crystal": {"intelligence": 35, "luck": 30, "wisdom": 20, "agility": 10, "vitality": 3, "strength": 2},
}

# Bonus de stats par rarete
RARITY_STAT_MULTIPLIER = {
    "crude": 0.3,
    "common": 1.0,
    "refined": 1.5,
    "superior": 2.0,
    "exquisite": 2.8,
    "masterwork": 4.0,
    "legendary": 6.0,
    "mythical": 9.0,
    "primordial": 15.0,
}

# Stats secondaires par categorie
CATEGORY_SECONDARY_STATS = {
    "potion": ["health_bonus", "health_regen", "phys_damage_bonus", "attack_speed_pct"],
    "elixir": ["mana_bonus", "mana_regen", "experience_bonus_pct", "cooldown_reduction_pct"],
    "rune": ["mag_damage_bonus", "crit_chance_pct", "crit_damage_pct"],
    "scroll": ["mag_damage_bonus", "cast_speed_pct", "cooldown_reduction_pct"],
    "essence": ["drop_bonus_pct", "resource_gain_pct", "luck"],
    "talisman": ["defense_bonus", "mag_resist_bonus", "block_pct", "all_resist_pct"],
    "orb": ["mana_bonus", "mag_damage_bonus", "cast_speed_pct"],
    "seal": ["defense_bonus", "mag_resist_bonus", "cooldown_reduction_pct"],
    "sigil": ["evasion_pct", "movement_speed_pct", "crit_chance_pct"],
    "crystal": ["mag_damage_bonus", "fire_damage", "ice_damage", "lightning_damage", "void_damage"],
}


def generate_item_stats(category: str, rarity: str, item_value: float = 100, 
                        luck_bonus: float = 0) -> StatBlock:
    """
    Genere un bloc de stats pour un item.
    
    Args:
        category: Categorie de l'item (potion, rune, etc.)
        rarity: Rarete de l'item
        item_value: Valeur de base de l'item
        luck_bonus: Bonus de chance au roll
    
    Returns:
        StatBlock avec les stats generees
    """
    stats = StatBlock()
    
    # Obtenir les poids de stats pour cette categorie
    weights = CATEGORY_STAT_WEIGHTS.get(category.lower(), {
        "strength": 15, "agility": 15, "intelligence": 20,
        "vitality": 20, "wisdom": 15, "luck": 15
    })
    
    # Multiplicateur de rarete
    rarity_mult = RARITY_STAT_MULTIPLIER.get(rarity.lower(), 1.0)
    
    # Base de stats selon valeur et rarete
    base_stat_budget = int(item_value * rarity_mult * 0.5)
    
    # Distribuer le budget selon les poids
    total_weight = sum(weights.values())
    
    for stat_name, weight in weights.items():
        # Calculer la part de ce stat
        base_value = int(base_stat_budget * weight / total_weight)
        
        # Ajouter de la variance (-20% a +30%)
        variance = random.uniform(-0.2, 0.3 + luck_bonus / 100)
        final_value = max(0, int(base_value * (1 + variance)))
        
        # Assigner au bloc
        setattr(stats, stat_name, final_value)
    
    # === Stats secondaires ===
    secondary_stats = CATEGORY_SECONDARY_STATS.get(category.lower(), [])
    secondary_budget = int(item_value * rarity_mult * 0.3)
    
    for sec_stat in secondary_stats:
        if hasattr(stats, sec_stat):
            # Valeur selon si c'est un pourcentage ou flat
            if sec_stat.endswith('_pct'):
                # Pourcentage: 1-30% selon rarete
                base_pct = random.uniform(1, 5) * rarity_mult
                variance = random.uniform(0.8, 1.3 + luck_bonus / 200)
                setattr(stats, sec_stat, round(base_pct * variance, 1))
            elif sec_stat.endswith('_bonus') or sec_stat.endswith('_damage'):
                # Flat: selon budget
                base_val = random.randint(5, 20) * int(rarity_mult)
                variance = random.uniform(0.7, 1.4)
                setattr(stats, sec_stat, int(base_val * variance))
            elif sec_stat.endswith('_regen'):
                # Regen: 0.5-10 selon rarete
                base_regen = random.uniform(0.5, 2) * rarity_mult
                setattr(stats, sec_stat, round(base_regen, 1))
    
    # === Bonus elementaire pour certaines categories ===
    if category.lower() == "crystal":
        # Choisir un element dominant
        elements = ['fire_damage', 'ice_damage', 'lightning_damage', 'void_damage']
        main_element = random.choice(elements)
        elem_value = int(item_value * rarity_mult * 0.4)
        setattr(stats, main_element, elem_value)
    
    return stats


def calculate_stat_power(stats: StatBlock) -> float:
    """
    Calcule la puissance totale d'un bloc de stats.
    
    Returns:
        Score de puissance (0-10000+)
    """
    power = 0.0
    
    # Stats primaires (x10)
    power += stats.strength * 10
    power += stats.agility * 10
    power += stats.intelligence * 10
    power += stats.vitality * 10
    power += stats.wisdom * 10
    power += stats.luck * 15  # Luck vaut plus
    
    # Stats secondaires flat
    power += stats.health_bonus * 0.5
    power += stats.mana_bonus * 0.5
    power += stats.phys_damage_bonus * 2
    power += stats.mag_damage_bonus * 2
    power += stats.defense_bonus * 1.5
    power += stats.mag_resist_bonus * 1.5
    
    # Stats en pourcentage (x20)
    power += stats.attack_speed_pct * 20
    power += stats.cast_speed_pct * 20
    power += stats.movement_speed_pct * 15
    power += stats.crit_chance_pct * 30
    power += stats.crit_damage_pct * 20
    power += stats.evasion_pct * 25
    power += stats.block_pct * 25
    power += stats.cooldown_reduction_pct * 25
    
    # Regen
    power += stats.health_regen * 10
    power += stats.mana_regen * 10
    
    # Bonus utilitaires
    power += stats.experience_bonus_pct * 15
    power += stats.drop_bonus_pct * 20
    power += stats.resource_gain_pct * 10
    
    # Degats elementaires
    power += stats.fire_damage * 1.5
    power += stats.ice_damage * 1.5
    power += stats.lightning_damage * 1.5
    power += stats.void_damage * 2.0
    
    # Resistances
    power += stats.fire_resist_pct * 10
    power += stats.ice_resist_pct * 10
    power += stats.lightning_resist_pct * 10
    power += stats.void_resist_pct * 12
    power += stats.all_resist_pct * 50
    
    return power


def format_stats_display(stats: StatBlock, compact: bool = False) -> str:
    """
    Formate un bloc de stats pour affichage.
    
    Args:
        stats: Bloc de stats
        compact: Mode compact (une ligne)
    
    Returns:
        Texte formate
    """
    lines = []
    
    # Stats primaires
    primary = [
        ("STR", stats.strength),
        ("AGI", stats.agility),
        ("INT", stats.intelligence),
        ("VIT", stats.vitality),
        ("SAG", stats.wisdom),
        ("LCK", stats.luck),
    ]
    
    if compact:
        primary_str = " ".join(f"{abbr}:{val}" for abbr, val in primary if val > 0)
        return primary_str
    
    # Mode complet
    lines.append("=== STATS PRIMAIRES ===")
    for abbr, val in primary:
        if val > 0:
            bar_len = min(20, val // 5)
            bar = "#" * bar_len
            lines.append(f"  {abbr}: {val:3d} {bar}")
    
    # Stats secondaires significatives
    secondary = []
    if stats.health_bonus > 0:
        secondary.append(f"+{stats.health_bonus} PV")
    if stats.mana_bonus > 0:
        secondary.append(f"+{stats.mana_bonus} Mana")
    if stats.phys_damage_bonus > 0:
        secondary.append(f"+{stats.phys_damage_bonus} Degats Phys")
    if stats.mag_damage_bonus > 0:
        secondary.append(f"+{stats.mag_damage_bonus} Degats Mag")
    if stats.defense_bonus > 0:
        secondary.append(f"+{stats.defense_bonus} Defense")
    if stats.crit_chance_pct > 0:
        secondary.append(f"+{stats.crit_chance_pct:.1f}% Crit")
    if stats.attack_speed_pct > 0:
        secondary.append(f"+{stats.attack_speed_pct:.1f}% Vit.Atk")
    if stats.cooldown_reduction_pct > 0:
        secondary.append(f"-{stats.cooldown_reduction_pct:.1f}% CD")
    if stats.drop_bonus_pct > 0:
        secondary.append(f"+{stats.drop_bonus_pct:.1f}% Drop")
    
    if secondary:
        lines.append("\n=== STATS SECONDAIRES ===")
        for stat in secondary:
            lines.append(f"  {stat}")
    
    # Degats elementaires
    elemental = []
    if stats.fire_damage > 0:
        elemental.append(f"+{stats.fire_damage} Feu")
    if stats.ice_damage > 0:
        elemental.append(f"+{stats.ice_damage} Glace")
    if stats.lightning_damage > 0:
        elemental.append(f"+{stats.lightning_damage} Foudre")
    if stats.void_damage > 0:
        elemental.append(f"+{stats.void_damage} Vide")
    
    if elemental:
        lines.append("\n=== DEGATS ELEMENTAIRES ===")
        for elem in elemental:
            lines.append(f"  {elem}")
    
    # Puissance totale
    power = calculate_stat_power(stats)
    lines.append(f"\n[PUISSANCE: {power:.0f}]")
    
    return "\n".join(lines)


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  TEST SYSTEME DE STATS")
    print("=" * 60)
    
    categories = ["potion", "rune", "crystal", "talisman", "essence"]
    rarities = ["common", "legendary", "primordial"]
    
    for cat in categories:
        print(f"\n{'='*60}")
        print(f"  CATEGORIE: {cat.upper()}")
        print("=" * 60)
        
        for rarity in rarities:
            print(f"\n  [{rarity.upper()}]")
            stats = generate_item_stats(cat, rarity, item_value=100)
            
            # Affichage compact
            compact = format_stats_display(stats, compact=True)
            print(f"  Stats: {compact}")
            
            power = calculate_stat_power(stats)
            print(f"  Puissance: {power:.0f}")
    
    # Test d'addition de stats
    print("\n" + "=" * 60)
    print("  TEST ADDITION DE STATS")
    print("=" * 60)
    
    stats1 = generate_item_stats("potion", "legendary")
    stats2 = generate_item_stats("rune", "legendary")
    combined = stats1 + stats2
    
    print("\n  Stats Potion:")
    print(format_stats_display(stats1, compact=True))
    
    print("\n  Stats Rune:")
    print(format_stats_display(stats2, compact=True))
    
    print("\n  Stats Combinees:")
    print(format_stats_display(combined, compact=True))
    print(f"  Puissance combinee: {calculate_stat_power(combined):.0f}")
