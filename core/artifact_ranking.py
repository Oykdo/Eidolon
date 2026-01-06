"""
Systeme de Ranking et Classement des Artefacts
===============================================

Fonctionnalites:
- Calcul de puissance globale par vault
- Leaderboard mondial
- Tiers de puissance dynamiques
- Statistiques et analytics
- Achievements et badges
"""

import os
import sys
import json
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Import du systeme d'artefacts
try:
    from core.artifact_vault import ArtifactVault, DetachableArtifact, ArtifactStatus
    from core.artifact_system import ArtifactRarity, RARITY_MULTIPLIERS
except ImportError:
    from artifact_vault import ArtifactVault, DetachableArtifact, ArtifactStatus
    from artifact_system import ArtifactRarity, RARITY_MULTIPLIERS


# ============================================================================
# TIERS DE PUISSANCE
# ============================================================================

class PowerTier(Enum):
    """Tiers de puissance base sur la puissance totale des artefacts"""
    PRIMORDIAL = "primordial"
    TRANSCENDENT = "transcendent"
    MYTHIC = "mythic"
    LEGENDARY = "legendary"
    EPIC = "epic"
    RARE = "rare"
    UNCOMMON = "uncommon"
    COMMON = "common"


POWER_TIER_CONFIG = {
    PowerTier.PRIMORDIAL: {
        "min_power": 1_000_000,
        "color": "#FF00FF",
        "emoji": "⚡",
        "title": "Primordial Nexus Lord",
        "description": "Maitrise absolue du Nexus Spinoriel"
    },
    PowerTier.TRANSCENDENT: {
        "min_power": 500_000,
        "color": "#00FFFF",
        "emoji": "✧",
        "title": "Transcendent Archon",
        "description": "A transcende les limites dimensionnelles"
    },
    PowerTier.MYTHIC: {
        "min_power": 200_000,
        "color": "#E6CC80",
        "emoji": "🔥",
        "title": "Mythic Sovereign",
        "description": "Legende vivante du Poly-Spinor"
    },
    PowerTier.LEGENDARY: {
        "min_power": 50_000,
        "color": "#FF8000",
        "emoji": "🌟",
        "title": "Legendary Champion",
        "description": "Champion des 7 dimensions"
    },
    PowerTier.EPIC: {
        "min_power": 10_000,
        "color": "#A335EE",
        "emoji": "💎",
        "title": "Epic Warden",
        "description": "Gardien des secrets spinoriels"
    },
    PowerTier.RARE: {
        "min_power": 1_000,
        "color": "#0070DD",
        "emoji": "🔮",
        "title": "Rare Adept",
        "description": "Adepte des arts quantiques"
    },
    PowerTier.UNCOMMON: {
        "min_power": 100,
        "color": "#1EFF00",
        "emoji": "🌿",
        "title": "Uncommon Seeker",
        "description": "Chercheur du Nexus"
    },
    PowerTier.COMMON: {
        "min_power": 0,
        "color": "#9D9D9D",
        "emoji": "📦",
        "title": "Initiate",
        "description": "Debut du voyage dimensionnel"
    }
}


# ============================================================================
# ACHIEVEMENTS
# ============================================================================

@dataclass
class Achievement:
    """Achievement deblocable"""
    id: str
    name: str
    description: str
    icon: str
    condition_type: str  # power, count, rarity, special
    condition_value: Any
    reward_power_bonus: float = 0.0
    unlocked: bool = False
    unlocked_at: Optional[str] = None


ACHIEVEMENTS = [
    # Power achievements
    Achievement("first_artifact", "First Steps", "Posseder votre premier artefact", "🎯", "count", 1),
    Achievement("power_1k", "Rising Power", "Atteindre 1,000 de puissance", "⚡", "power", 1000),
    Achievement("power_10k", "Power Surge", "Atteindre 10,000 de puissance", "💪", "power", 10000),
    Achievement("power_100k", "Overwhelming Force", "Atteindre 100,000 de puissance", "🔥", "power", 100000),
    Achievement("power_1m", "Primordial Might", "Atteindre 1,000,000 de puissance", "⚡", "power", 1000000),
    
    # Rarity achievements
    Achievement("first_rare", "Rare Find", "Obtenir un artefact RARE", "🔵", "rarity", "rare"),
    Achievement("first_epic", "Epic Discovery", "Obtenir un artefact EPIC", "💜", "rarity", "epic"),
    Achievement("first_legendary", "Legendary Collector", "Obtenir un artefact LEGENDARY", "🟠", "rarity", "legendary"),
    Achievement("first_mythic", "Mythic Seeker", "Obtenir un artefact MYTHIC", "🟡", "rarity", "mythic"),
    Achievement("first_transcendent", "Transcendence", "Obtenir un artefact TRANSCENDENT", "🔷", "rarity", "transcendent"),
    Achievement("first_primordial", "Primordial Origin", "Obtenir un artefact PRIMORDIAL", "🟣", "rarity", "primordial"),
    
    # Collection achievements
    Achievement("collector_5", "Artifact Collector", "Posseder 5 artefacts", "📦", "count", 5),
    Achievement("collector_10", "Artifact Hoarder", "Posseder 10 artefacts", "📦", "count", 10),
    Achievement("collector_25", "Artifact Master", "Posseder 25 artefacts", "📦", "count", 25),
    
    # Special achievements
    Achievement("founder_artifact", "Founder's Legacy", "Posseder un artefact fondateur", "⭐", "special", "founder"),
    Achievement("full_set", "Element Master", "Posseder un artefact de chaque element", "🌈", "special", "all_elements"),
    Achievement("quantum_pioneer", "Quantum Pioneer", "Etre un Quantum Pioneer", "🏆", "special", "quantum_pioneer"),
]


# ============================================================================
# VAULT STATS
# ============================================================================

@dataclass
class VaultStats:
    """Statistiques completes d'un vault"""
    vault_number: int
    total_power: float
    power_tier: PowerTier
    tier_config: Dict[str, Any]
    artifact_count: int
    founder_artifact_count: int
    
    # Repartition par rarete
    rarity_breakdown: Dict[str, int] = field(default_factory=dict)
    
    # Repartition par element
    element_breakdown: Dict[str, int] = field(default_factory=dict)
    
    # Achievements
    unlocked_achievements: List[str] = field(default_factory=list)
    achievement_progress: Dict[str, float] = field(default_factory=dict)
    
    # Ranking
    global_rank: int = 0
    percentile: float = 0.0
    
    # Bonus
    power_multiplier: float = 1.0
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['power_tier'] = self.power_tier.value
        return d


@dataclass 
class LeaderboardEntry:
    """Entree du leaderboard"""
    rank: int
    vault_number: int
    vault_name: str
    total_power: float
    power_tier: PowerTier
    artifact_count: int
    top_artifact_name: str
    top_artifact_rarity: str
    is_founder: bool
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['power_tier'] = self.power_tier.value
        return d


# ============================================================================
# SYSTEME DE RANKING
# ============================================================================

class ArtifactPowerSystem:
    """Systeme de ranking et classement des artefacts"""
    
    def __init__(self, artifact_vault: ArtifactVault = None):
        self.artifact_vault = artifact_vault or ArtifactVault()
        self._stats_cache: Dict[int, VaultStats] = {}
        self._leaderboard_cache: List[LeaderboardEntry] = []
        self._last_update: Optional[datetime] = None
    
    def get_power_tier(self, total_power: float) -> PowerTier:
        """Obtient le tier de puissance"""
        for tier in PowerTier:
            config = POWER_TIER_CONFIG[tier]
            if total_power >= config["min_power"]:
                return tier
        return PowerTier.COMMON
    
    def calculate_vault_stats(self, vault_number: int) -> VaultStats:
        """Calcule les statistiques completes d'un vault"""
        artifacts = self.artifact_vault.get_artifacts_by_owner(vault_number)
        
        # Puissance totale
        total_power = sum(a.power for a in artifacts)
        
        # Tier de puissance
        power_tier = self.get_power_tier(total_power)
        tier_config = POWER_TIER_CONFIG[power_tier]
        
        # Repartition par rarete
        rarity_breakdown = {}
        for a in artifacts:
            rarity_breakdown[a.rarity] = rarity_breakdown.get(a.rarity, 0) + 1
        
        # Repartition par element
        element_breakdown = {}
        for a in artifacts:
            element = a.artifact_data.get('element', 'unknown')
            element_breakdown[element] = element_breakdown.get(element, 0) + 1
        
        # Artefacts fondateurs
        founder_count = len([a for a in artifacts if a.is_founder_artifact])
        
        # Achievements
        unlocked, progress = self._check_achievements(artifacts, total_power)
        
        # Calculer les bonus
        power_mult = self._calculate_power_multiplier(artifacts, unlocked)
        
        stats = VaultStats(
            vault_number=vault_number,
            total_power=total_power * power_mult,
            power_tier=power_tier,
            tier_config=tier_config,
            artifact_count=len(artifacts),
            founder_artifact_count=founder_count,
            rarity_breakdown=rarity_breakdown,
            element_breakdown=element_breakdown,
            unlocked_achievements=unlocked,
            achievement_progress=progress,
            power_multiplier=power_mult
        )
        
        self._stats_cache[vault_number] = stats
        return stats
    
    def _check_achievements(self, artifacts: List[DetachableArtifact], 
                           total_power: float) -> Tuple[List[str], Dict[str, float]]:
        """Verifie les achievements debloques"""
        unlocked = []
        progress = {}
        
        for achievement in ACHIEVEMENTS:
            achieved = False
            prog = 0.0
            
            if achievement.condition_type == "power":
                target = achievement.condition_value
                prog = min(1.0, total_power / target)
                achieved = total_power >= target
                
            elif achievement.condition_type == "count":
                target = achievement.condition_value
                prog = min(1.0, len(artifacts) / target)
                achieved = len(artifacts) >= target
                
            elif achievement.condition_type == "rarity":
                target_rarity = achievement.condition_value
                has_rarity = any(a.rarity == target_rarity for a in artifacts)
                prog = 1.0 if has_rarity else 0.0
                achieved = has_rarity
                
            elif achievement.condition_type == "special":
                if achievement.condition_value == "founder":
                    has_founder = any(a.is_founder_artifact for a in artifacts)
                    prog = 1.0 if has_founder else 0.0
                    achieved = has_founder
                    
                elif achievement.condition_value == "all_elements":
                    elements = set(a.artifact_data.get('element', '') for a in artifacts)
                    all_elements = ['void', 'quantum', 'temporal', 'spatial', 
                                   'entropic', 'harmonic', 'celestial', 'primordial']
                    prog = len(elements) / len(all_elements)
                    achieved = len(elements) >= len(all_elements)
            
            if achieved:
                unlocked.append(achievement.id)
            progress[achievement.id] = prog
        
        return unlocked, progress
    
    def _calculate_power_multiplier(self, artifacts: List[DetachableArtifact],
                                    unlocked_achievements: List[str]) -> float:
        """Calcule le multiplicateur de puissance total"""
        mult = 1.0
        
        # Bonus par nombre d'artefacts
        if len(artifacts) >= 5:
            mult += 0.1
        if len(artifacts) >= 10:
            mult += 0.15
        if len(artifacts) >= 25:
            mult += 0.25
        
        # Bonus par achievements
        for ach in ACHIEVEMENTS:
            if ach.id in unlocked_achievements and ach.reward_power_bonus > 0:
                mult += ach.reward_power_bonus
        
        # Bonus si possede un artefact primordial
        if any(a.rarity == 'primordial' for a in artifacts):
            mult += 0.5
        
        return mult
    
    def calculate_global_leaderboard(self, force_refresh: bool = False) -> List[LeaderboardEntry]:
        """Calcule le classement mondial"""
        # Cache de 60 secondes
        if not force_refresh and self._leaderboard_cache and self._last_update:
            delta = (datetime.now() - self._last_update).total_seconds()
            if delta < 60:
                return self._leaderboard_cache
        
        # Collecter tous les vaults avec artefacts
        all_artifacts = self.artifact_vault.get_all_artifacts()
        vault_numbers = set(a.current_owner_vault for a in all_artifacts if a.current_owner_vault)
        
        # Calculer les stats de chaque vault
        entries = []
        for vault_num in vault_numbers:
            stats = self.calculate_vault_stats(vault_num)
            
            # Trouver l'artefact principal
            vault_artifacts = self.artifact_vault.get_artifacts_by_owner(vault_num)
            if vault_artifacts:
                top_artifact = max(vault_artifacts, key=lambda x: x.power)
                top_name = top_artifact.name
                top_rarity = top_artifact.rarity
            else:
                top_name = "None"
                top_rarity = "none"
            
            # Verifier si fondateur
            is_founder = any(a.is_founder_artifact for a in vault_artifacts)
            
            entry = LeaderboardEntry(
                rank=0,  # Sera mis a jour apres le tri
                vault_number=vault_num,
                vault_name=f"Vault #{vault_num:05d}",
                total_power=stats.total_power,
                power_tier=stats.power_tier,
                artifact_count=stats.artifact_count,
                top_artifact_name=top_name,
                top_artifact_rarity=top_rarity,
                is_founder=is_founder
            )
            entries.append(entry)
        
        # Trier par puissance decroissante
        entries.sort(key=lambda x: x.total_power, reverse=True)
        
        # Assigner les rangs
        for i, entry in enumerate(entries, 1):
            entry.rank = i
        
        # Mettre a jour les percentiles dans les stats
        total_vaults = len(entries)
        for entry in entries:
            if entry.vault_number in self._stats_cache:
                stats = self._stats_cache[entry.vault_number]
                stats.global_rank = entry.rank
                stats.percentile = (1 - (entry.rank - 1) / max(1, total_vaults)) * 100
        
        self._leaderboard_cache = entries
        self._last_update = datetime.now()
        
        return entries
    
    def get_vault_rank(self, vault_number: int) -> Optional[int]:
        """Obtient le rang d'un vault"""
        leaderboard = self.calculate_global_leaderboard()
        for entry in leaderboard:
            if entry.vault_number == vault_number:
                return entry.rank
        return None
    
    def format_leaderboard_display(self, limit: int = 10) -> str:
        """Formate l'affichage du leaderboard"""
        leaderboard = self.calculate_global_leaderboard()
        
        lines = []
        lines.append("\n" + "="*70)
        lines.append("  🏆 GLOBAL ARTIFACT LEADERBOARD")
        lines.append("="*70 + "\n")
        
        for entry in leaderboard[:limit]:
            tier_config = POWER_TIER_CONFIG[entry.power_tier]
            emoji = tier_config["emoji"]
            founder_mark = "⭐" if entry.is_founder else " "
            
            rank_str = f"#{entry.rank:2d}"
            power_str = f"{entry.total_power:,.0f}"
            
            lines.append(
                f"  {rank_str} {founder_mark} {entry.vault_name:15} "
                f"| {emoji} {entry.power_tier.value.upper():12} "
                f"| PWR: {power_str:>12} "
                f"| 📦 {entry.artifact_count}"
            )
            lines.append(
                f"       └─ Top: [{entry.top_artifact_rarity.upper()[:4]}] {entry.top_artifact_name}"
            )
        
        lines.append("\n" + "="*70)
        return "\n".join(lines)
    
    def format_vault_stats_display(self, vault_number: int) -> str:
        """Formate l'affichage des stats d'un vault"""
        stats = self.calculate_vault_stats(vault_number)
        tier_config = stats.tier_config
        
        lines = []
        lines.append("\n" + "="*60)
        lines.append(f"  {tier_config['emoji']} VAULT #{vault_number:05d} STATS")
        lines.append("="*60 + "\n")
        
        lines.append(f"  POWER TIER: {stats.power_tier.value.upper()}")
        lines.append(f"  Title: {tier_config['title']}")
        lines.append(f"  \"{tier_config['description']}\"")
        
        lines.append(f"\n  STATISTICS:")
        lines.append(f"    Total Power: {stats.total_power:,.0f}")
        lines.append(f"    Artifacts: {stats.artifact_count}")
        lines.append(f"    Founder Artifacts: {stats.founder_artifact_count}")
        lines.append(f"    Power Multiplier: {stats.power_multiplier:.2f}x")
        lines.append(f"    Global Rank: #{stats.global_rank}")
        lines.append(f"    Percentile: Top {100 - stats.percentile:.1f}%")
        
        lines.append(f"\n  RARITY BREAKDOWN:")
        for rarity, count in sorted(stats.rarity_breakdown.items()):
            lines.append(f"    {rarity.upper():12}: {count}")
        
        lines.append(f"\n  ELEMENT BREAKDOWN:")
        for element, count in sorted(stats.element_breakdown.items()):
            lines.append(f"    {element.upper():12}: {count}")
        
        lines.append(f"\n  ACHIEVEMENTS ({len(stats.unlocked_achievements)}/{len(ACHIEVEMENTS)}):")
        for ach in ACHIEVEMENTS:
            if ach.id in stats.unlocked_achievements:
                lines.append(f"    ✓ {ach.icon} {ach.name}: {ach.description}")
            else:
                prog = stats.achievement_progress.get(ach.id, 0)
                if prog > 0:
                    lines.append(f"    ○ {ach.icon} {ach.name}: {prog*100:.0f}%")
        
        lines.append("\n" + "="*60)
        return "\n".join(lines)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Artifact Ranking System")
    parser.add_argument("--leaderboard", "-l", action="store_true", help="Afficher le leaderboard")
    parser.add_argument("--stats", "-s", type=int, help="Afficher les stats d'un vault")
    parser.add_argument("--top", type=int, default=10, help="Nombre d'entrees du leaderboard")
    
    args = parser.parse_args()
    
    system = ArtifactPowerSystem()
    
    if args.leaderboard:
        print(system.format_leaderboard_display(args.top))
    
    elif args.stats:
        print(system.format_vault_stats_display(args.stats))
    
    else:
        # Par defaut, afficher le leaderboard
        print(system.format_leaderboard_display(args.top))
