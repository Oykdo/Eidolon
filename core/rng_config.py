#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              CONFIGURATION RNG - Eidolon                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Systeme centralise de configuration des probabilites et rolls.             ║
║  Permet d'ajuster finement le RNG pour equilibrer l'economie du jeu.        ║
║                                                                              ║
║  TRANCHES DE ROLLS:                                                          ║
║  - ABYSMAL (0-5%): Rolls catastrophiques                                    ║
║  - TERRIBLE (5-15%): Rolls tres mauvais                                     ║
║  - POOR (15-30%): Rolls mauvais                                             ║
║  - BELOW_AVERAGE (30-45%): Sous la moyenne                                  ║
║  - AVERAGE (45-55%): Dans la moyenne                                        ║
║  - ABOVE_AVERAGE (55-70%): Au dessus de la moyenne                          ║
║  - GOOD (70-85%): Bons rolls                                                ║
║  - EXCELLENT (85-95%): Excellents rolls                                     ║
║  - PERFECT (95-100%): Rolls parfaits                                        ║
║  - DIVINE (100%+): Rolls divins (bonus luck)                                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import random
import hashlib
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any


# ============================================================================
# TRANCHES DE QUALITE DES ROLLS
# ============================================================================

class RollQuality(Enum):
    """Qualite d'un roll basee sur le pourcentage"""
    ABYSMAL = ("abysmal", "Abyssal", 0, 5, "X", "#330000")
    TERRIBLE = ("terrible", "Terrible", 5, 15, "-", "#660000")
    POOR = ("poor", "Mauvais", 15, 30, "o", "#888888")
    BELOW_AVERAGE = ("below_avg", "Mediocre", 30, 45, ".", "#aaaaaa")
    AVERAGE = ("average", "Moyen", 45, 55, "*", "#ffffff")
    ABOVE_AVERAGE = ("above_avg", "Bon", 55, 70, "+", "#88ff88")
    GOOD = ("good", "Tres bon", 70, 85, "#", "#00ff00")
    EXCELLENT = ("excellent", "Excellent", 85, 95, "@", "#00ffff")
    PERFECT = ("perfect", "Parfait", 95, 100, "$", "#ffd700")
    DIVINE = ("divine", "Divin", 100, 110, "!", "#ff00ff")
    
    def __init__(self, quality_id: str, name: str, min_pct: int, max_pct: int, 
                 symbol: str, color: str):
        self.quality_id = quality_id
        self.display_name = name
        self.min_percent = min_pct
        self.max_percent = max_pct
        self.symbol = symbol
        self.color = color
    
    @classmethod
    def from_percent(cls, percent: float) -> 'RollQuality':
        """Retourne la qualite correspondant a un pourcentage."""
        for quality in cls:
            if quality.min_percent <= percent < quality.max_percent:
                return quality
        return cls.DIVINE if percent >= 100 else cls.ABYSMAL


# ============================================================================
# CONFIGURATION DES PROBABILITES DE RARETE
# ============================================================================

@dataclass
class RarityConfig:
    """Configuration pour une rarete"""
    name: str
    weight: int           # Poids relatif (plus eleve = plus commun)
    value_multiplier: float
    mod_count_min: int
    mod_count_max: int
    quality_bonus: float  # Bonus au roll de qualite (0-20)
    
# Configuration par defaut des raretes d'items
ITEM_RARITY_CONFIG: Dict[str, RarityConfig] = {
    "crude": RarityConfig("Brut", 1500, 0.3, 0, 1, -10),
    "common": RarityConfig("Commun", 3000, 1.0, 1, 2, 0),
    "refined": RarityConfig("Raffine", 2500, 1.8, 1, 3, 5),
    "superior": RarityConfig("Superieur", 1500, 3.0, 2, 3, 10),
    "exquisite": RarityConfig("Exquis", 800, 5.0, 2, 4, 15),
    "masterwork": RarityConfig("Chef-d'oeuvre", 400, 8.0, 3, 5, 20),
    "legendary": RarityConfig("Legendaire", 200, 15.0, 4, 6, 25),
    "mythical": RarityConfig("Mythique", 80, 25.0, 5, 7, 30),
    "primordial": RarityConfig("Primordial", 20, 50.0, 5, 7, 40),
}

# Configuration des raretes de gems
GEM_RARITY_CONFIG: Dict[str, RarityConfig] = {
    "flawed": RarityConfig("Defectueux", 2000, 0.5, 0, 0, -15),
    "rough": RarityConfig("Brut", 2500, 1.0, 0, 1, -5),
    "cut": RarityConfig("Taille", 2000, 2.0, 1, 1, 0),
    "polished": RarityConfig("Poli", 1500, 3.5, 1, 2, 10),
    "pristine": RarityConfig("Immacule", 1000, 6.0, 2, 2, 20),
    "radiant": RarityConfig("Radiant", 500, 10.0, 2, 3, 30),
    "ethereal": RarityConfig("Etheree", 300, 18.0, 3, 3, 40),
    "transcendent": RarityConfig("Transcendant", 150, 30.0, 3, 4, 50),
    "divine": RarityConfig("Divin", 50, 50.0, 4, 4, 60),
}


# ============================================================================
# CONFIGURATION DES TIERS DE MODS
# ============================================================================

@dataclass
class ModTierConfig:
    """Configuration pour un tier de mod"""
    name: str
    weight: int           # Poids relatif
    power_multiplier: float
    roll_bonus: float     # Bonus au roll (0-100)

MOD_TIER_CONFIG: Dict[str, ModTierConfig] = {
    "minor": ModTierConfig("Mineur", 3000, 1.0, -10),
    "standard": ModTierConfig("Standard", 4000, 1.5, 0),
    "greater": ModTierConfig("Majeur", 2000, 2.5, 5),
    "superior": ModTierConfig("Superieur", 700, 4.0, 10),
    "prime": ModTierConfig("Prime", 250, 6.0, 20),
    "divine": ModTierConfig("Divin", 50, 10.0, 35),
}


# ============================================================================
# CONFIGURATION DES TRANCHES DE ROLLS
# ============================================================================

@dataclass
class RollBracket:
    """Tranche de roll avec ses probabilites"""
    name: str
    min_roll: float       # Roll minimum (0-100)
    max_roll: float       # Roll maximum (0-100)
    weight: int           # Poids relatif pour cette tranche
    description: str

# Tranches de rolls par defaut (distribution normale centree sur 50%)
DEFAULT_ROLL_BRACKETS: List[RollBracket] = [
    RollBracket("abysmal", 0, 5, 50, "Rolls catastrophiques"),
    RollBracket("terrible", 5, 15, 150, "Rolls tres mauvais"),
    RollBracket("poor", 15, 30, 500, "Rolls mauvais"),
    RollBracket("below_avg", 30, 45, 1500, "Sous la moyenne"),
    RollBracket("average", 45, 55, 3000, "Dans la moyenne"),
    RollBracket("above_avg", 55, 70, 2500, "Au dessus de la moyenne"),
    RollBracket("good", 70, 85, 1500, "Bons rolls"),
    RollBracket("excellent", 85, 95, 600, "Excellents rolls"),
    RollBracket("perfect", 95, 100, 180, "Rolls parfaits"),
    RollBracket("divine", 100, 110, 20, "Rolls divins (overflow)"),
]

# Tranches alternatives pour differents contextes
GENEROUS_ROLL_BRACKETS: List[RollBracket] = [
    RollBracket("abysmal", 0, 5, 20, "Rolls catastrophiques"),
    RollBracket("terrible", 5, 15, 80, "Rolls tres mauvais"),
    RollBracket("poor", 15, 30, 300, "Rolls mauvais"),
    RollBracket("below_avg", 30, 45, 1000, "Sous la moyenne"),
    RollBracket("average", 45, 55, 2500, "Dans la moyenne"),
    RollBracket("above_avg", 55, 70, 2800, "Au dessus de la moyenne"),
    RollBracket("good", 70, 85, 2000, "Bons rolls"),
    RollBracket("excellent", 85, 95, 1000, "Excellents rolls"),
    RollBracket("perfect", 95, 100, 250, "Rolls parfaits"),
    RollBracket("divine", 100, 110, 50, "Rolls divins"),
]

HARSH_ROLL_BRACKETS: List[RollBracket] = [
    RollBracket("abysmal", 0, 5, 200, "Rolls catastrophiques"),
    RollBracket("terrible", 5, 15, 500, "Rolls tres mauvais"),
    RollBracket("poor", 15, 30, 1500, "Rolls mauvais"),
    RollBracket("below_avg", 30, 45, 2500, "Sous la moyenne"),
    RollBracket("average", 45, 55, 3000, "Dans la moyenne"),
    RollBracket("above_avg", 55, 70, 1500, "Au dessus de la moyenne"),
    RollBracket("good", 70, 85, 600, "Bons rolls"),
    RollBracket("excellent", 85, 95, 150, "Excellents rolls"),
    RollBracket("perfect", 95, 100, 40, "Rolls parfaits"),
    RollBracket("divine", 100, 110, 5, "Rolls divins"),
]


# ============================================================================
# GENERATEUR RNG CONFIGURABLE
# ============================================================================

class ConfigurableRNG:
    """
    Generateur de nombres aleatoires configurable avec tranches de rolls.
    
    Permet de controler precisement la distribution des rolls.
    """
    
    def __init__(self, 
                 roll_brackets: List[RollBracket] = None,
                 seed: Any = None,
                 luck_modifier: float = 0.0):
        """
        Initialise le RNG.
        
        Args:
            roll_brackets: Tranches de rolls a utiliser
            seed: Seed pour reproductibilite
            luck_modifier: Modificateur de chance (-50 a +50)
        """
        self.roll_brackets = roll_brackets or DEFAULT_ROLL_BRACKETS
        self.luck_modifier = max(-50, min(50, luck_modifier))
        
        if seed is not None:
            if isinstance(seed, str):
                seed = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16)
            random.seed(seed)
        
        self._precompute_weights()
    
    def _precompute_weights(self):
        """Precalcule les poids cumules pour selection rapide."""
        self.total_weight = sum(b.weight for b in self.roll_brackets)
        self.cumulative_weights = []
        cumsum = 0
        for bracket in self.roll_brackets:
            cumsum += bracket.weight
            self.cumulative_weights.append(cumsum)
    
    def roll_percent(self, bonus: float = 0.0) -> float:
        """
        Genere un roll en pourcentage (0-100+).
        
        Args:
            bonus: Bonus au roll (-100 a +100)
        
        Returns:
            Roll en pourcentage (peut depasser 100 avec luck/bonus)
        """
        # Selectionner une tranche selon les poids
        rand_val = random.randint(1, self.total_weight)
        selected_bracket = None
        
        for i, cumweight in enumerate(self.cumulative_weights):
            if rand_val <= cumweight:
                selected_bracket = self.roll_brackets[i]
                break
        
        if selected_bracket is None:
            selected_bracket = self.roll_brackets[-1]
        
        # Roll dans la tranche selectionnee
        base_roll = random.uniform(selected_bracket.min_roll, selected_bracket.max_roll)
        
        # Appliquer les modificateurs
        final_roll = base_roll + self.luck_modifier + bonus
        
        # Clamp entre 0 et 110 (permet le overflow pour divine)
        return max(0.0, min(110.0, final_roll))
    
    def roll_value(self, min_val: float, max_val: float, bonus: float = 0.0) -> Tuple[float, float]:
        """
        Genere un roll de valeur entre min et max.
        
        Args:
            min_val: Valeur minimum
            max_val: Valeur maximum
            bonus: Bonus au roll
        
        Returns:
            (valeur, pourcentage)
        """
        percent = self.roll_percent(bonus)
        
        # Calculer la valeur
        range_val = max_val - min_val
        value = min_val + (range_val * percent / 100.0)
        
        # Si divine roll (100%+), bonus supplementaire
        if percent > 100:
            overflow = percent - 100
            value += range_val * overflow / 100.0
        
        return (value, percent)
    
    def roll_rarity(self, config: Dict[str, RarityConfig] = None, 
                    luck_bonus: float = 0.0) -> str:
        """
        Roll une rarete selon la configuration.
        
        Args:
            config: Configuration des raretes
            luck_bonus: Bonus de chance (augmente chance de rarete elevee)
        
        Returns:
            ID de la rarete
        """
        config = config or ITEM_RARITY_CONFIG
        
        # Ajuster les poids selon le luck_bonus
        adjusted_weights = {}
        rarities = list(config.keys())
        
        for i, (rarity_id, rarity_cfg) in enumerate(config.items()):
            weight = rarity_cfg.weight
            
            # luck_bonus augmente les raretes elevees (fin de liste)
            position_factor = i / len(rarities)  # 0 pour common, ~1 pour rare
            luck_effect = luck_bonus * position_factor * 0.5
            
            adjusted_weights[rarity_id] = max(1, int(weight * (1 + luck_effect / 100)))
        
        # Selection ponderee
        total = sum(adjusted_weights.values())
        rand_val = random.randint(1, total)
        
        cumsum = 0
        for rarity_id, weight in adjusted_weights.items():
            cumsum += weight
            if rand_val <= cumsum:
                return rarity_id
        
        return rarities[0]
    
    def roll_mod_tier(self, config: Dict[str, ModTierConfig] = None,
                      rarity_bonus: float = 0.0) -> str:
        """
        Roll un tier de mod.
        
        Args:
            config: Configuration des tiers
            rarity_bonus: Bonus base sur la rarete de l'item
        
        Returns:
            ID du tier
        """
        config = config or MOD_TIER_CONFIG
        
        adjusted_weights = {}
        tiers = list(config.keys())
        
        for i, (tier_id, tier_cfg) in enumerate(config.items()):
            weight = tier_cfg.weight
            position_factor = i / len(tiers)
            bonus_effect = rarity_bonus * position_factor * 0.3
            adjusted_weights[tier_id] = max(1, int(weight * (1 + bonus_effect / 100)))
        
        total = sum(adjusted_weights.values())
        rand_val = random.randint(1, total)
        
        cumsum = 0
        for tier_id, weight in adjusted_weights.items():
            cumsum += weight
            if rand_val <= cumsum:
                return tier_id
        
        return tiers[0]
    
    def get_quality(self, percent: float) -> RollQuality:
        """Retourne la qualite d'un roll."""
        return RollQuality.from_percent(percent)


# ============================================================================
# INSTANCE GLOBALE ET FONCTIONS UTILITAIRES
# ============================================================================

# RNG global par defaut
_global_rng: Optional[ConfigurableRNG] = None

def get_rng(luck_modifier: float = 0.0) -> ConfigurableRNG:
    """Obtient le RNG global ou en cree un nouveau."""
    global _global_rng
    if _global_rng is None or luck_modifier != 0.0:
        _global_rng = ConfigurableRNG(luck_modifier=luck_modifier)
    return _global_rng

def set_rng_brackets(brackets: List[RollBracket]):
    """Change les tranches de roll du RNG global."""
    global _global_rng
    _global_rng = ConfigurableRNG(roll_brackets=brackets)

def set_generous_mode():
    """Active le mode genereux (meilleurs rolls)."""
    set_rng_brackets(GENEROUS_ROLL_BRACKETS)

def set_harsh_mode():
    """Active le mode difficile (rolls plus durs)."""
    set_rng_brackets(HARSH_ROLL_BRACKETS)

def set_default_mode():
    """Remet le mode par defaut."""
    set_rng_brackets(DEFAULT_ROLL_BRACKETS)


# ============================================================================
# STATISTIQUES ET ANALYSE
# ============================================================================

def analyze_roll_distribution(rng: ConfigurableRNG = None, 
                              samples: int = 10000) -> Dict[str, Any]:
    """
    Analyse la distribution des rolls d'un RNG.
    
    Args:
        rng: RNG a analyser (defaut: global)
        samples: Nombre d'echantillons
    
    Returns:
        Statistiques de distribution
    """
    rng = rng or get_rng()
    
    quality_counts = {q.name: 0 for q in RollQuality}
    rolls = []
    
    for _ in range(samples):
        roll = rng.roll_percent()
        rolls.append(roll)
        quality = rng.get_quality(roll)
        quality_counts[quality.name] += 1
    
    return {
        "samples": samples,
        "min_roll": min(rolls),
        "max_roll": max(rolls),
        "avg_roll": sum(rolls) / len(rolls),
        "median_roll": sorted(rolls)[len(rolls) // 2],
        "quality_distribution": {
            name: {"count": count, "percent": count / samples * 100}
            for name, count in quality_counts.items()
        },
        "perfect_rate": quality_counts["PERFECT"] / samples * 100,
        "divine_rate": quality_counts["DIVINE"] / samples * 100,
    }


def print_distribution_report(stats: Dict[str, Any]):
    """Affiche un rapport de distribution."""
    print("\n" + "=" * 60)
    print("  RAPPORT DE DISTRIBUTION RNG")
    print("=" * 60)
    print(f"\n  Echantillons: {stats['samples']:,}")
    print(f"  Roll min: {stats['min_roll']:.2f}%")
    print(f"  Roll max: {stats['max_roll']:.2f}%")
    print(f"  Roll moyen: {stats['avg_roll']:.2f}%")
    print(f"  Roll median: {stats['median_roll']:.2f}%")
    print(f"\n  Taux Perfect (95%+): {stats['perfect_rate']:.2f}%")
    print(f"  Taux Divine (100%+): {stats['divine_rate']:.2f}%")
    print("\n  Distribution par qualite:")
    print("  " + "-" * 50)
    
    for quality in RollQuality:
        data = stats["quality_distribution"].get(quality.name, {"percent": 0})
        bar_len = int(data["percent"] / 2)
        bar = "#" * bar_len
        print(f"  {quality.symbol} {quality.display_name:12} {data['percent']:5.1f}% {bar}")


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  TEST RNG CONFIGURABLE")
    print("=" * 60)
    
    # Test mode par defaut
    print("\n[MODE PAR DEFAUT]")
    rng = ConfigurableRNG()
    stats = analyze_roll_distribution(rng, 10000)
    print_distribution_report(stats)
    
    # Test mode genereux
    print("\n[MODE GENEREUX]")
    rng_generous = ConfigurableRNG(roll_brackets=GENEROUS_ROLL_BRACKETS)
    stats = analyze_roll_distribution(rng_generous, 10000)
    print_distribution_report(stats)
    
    # Test mode difficile
    print("\n[MODE DIFFICILE]")
    rng_harsh = ConfigurableRNG(roll_brackets=HARSH_ROLL_BRACKETS)
    stats = analyze_roll_distribution(rng_harsh, 10000)
    print_distribution_report(stats)
    
    # Test avec luck
    print("\n[MODE PAR DEFAUT + LUCK +20]")
    rng_lucky = ConfigurableRNG(luck_modifier=20)
    stats = analyze_roll_distribution(rng_lucky, 10000)
    print_distribution_report(stats)
    
    # Exemples de rolls
    print("\n" + "=" * 60)
    print("  EXEMPLES DE ROLLS")
    print("=" * 60)
    
    rng = ConfigurableRNG()
    for i in range(10):
        value, percent = rng.roll_value(10, 100)
        quality = rng.get_quality(percent)
        print(f"  Roll {i+1}: {percent:5.1f}% -> {value:6.1f} [{quality.symbol} {quality.display_name}]")
    
    print("\n  Raretes (10 rolls):")
    for i in range(10):
        rarity = rng.roll_rarity()
        print(f"    {i+1}. {rarity}")
