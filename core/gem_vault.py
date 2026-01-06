"""
Systeme de Gemmes Mobiles pour Poly-Spinor Nexus 7D
===================================================

Gemmes detachables et transferables entre vaults et glyphes.
Grande variete de types avec pouvoirs uniques.
"""

import sys
import os
import json
import hashlib
import secrets
import numpy as np
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ============================================================================
# CATEGORIES DE GEMMES (7 categories, 49+ types)
# ============================================================================

class GemCategory(Enum):
    """Categories principales de gemmes"""
    PRIMORDIAL = "primordial"       # Gemmes des origines
    DIMENSIONAL = "dimensional"     # Gemmes des 7 dimensions
    QUANTUM = "quantum"             # Gemmes quantiques
    ELEMENTAL = "elemental"         # Gemmes elementaires
    COSMIC = "cosmic"               # Gemmes cosmiques
    RUNIC = "runic"                 # Gemmes runiques
    LEGENDARY = "legendary"         # Gemmes legendaires uniques


# ============================================================================
# 49 TYPES DE GEMMES AVEC POUVOIRS UNIQUES
# ============================================================================

class GemType(Enum):
    """Types de gemmes avec symboles et couleurs"""
    
    # === PRIMORDIAL (7) - Gemmes des origines ===
    VOID_CRYSTAL = ("void_crystal", "◆", "#1a0033", "Cristal du Vide", GemCategory.PRIMORDIAL)
    GENESIS_STONE = ("genesis_stone", "◈", "#ffd700", "Pierre de Genese", GemCategory.PRIMORDIAL)
    ORIGIN_PEARL = ("origin_pearl", "◉", "#ffffff", "Perle des Origines", GemCategory.PRIMORDIAL)
    PRIMEVAL_SHARD = ("primeval_shard", "◇", "#330066", "Eclat Primeval", GemCategory.PRIMORDIAL)
    CREATION_EMBER = ("creation_ember", "●", "#ff4500", "Braise de Creation", GemCategory.PRIMORDIAL)
    OMEGA_FRAGMENT = ("omega_fragment", "◐", "#000033", "Fragment Omega", GemCategory.PRIMORDIAL)
    ALPHA_CORE = ("alpha_core", "◑", "#ffffcc", "Coeur Alpha", GemCategory.PRIMORDIAL)
    
    # === DIMENSIONAL (7) - Une pour chaque dimension ===
    VOID_ESSENCE = ("void_essence", "⬡", "#0a0020", "Essence du Vide", GemCategory.DIMENSIONAL)
    QUANTUM_SHARD = ("quantum_shard", "⬢", "#00ff88", "Eclat Quantique", GemCategory.DIMENSIONAL)
    TEMPORAL_GEM = ("temporal_gem", "⧖", "#ffaa00", "Gemme Temporelle", GemCategory.DIMENSIONAL)
    SPATIAL_PRISM = ("spatial_prism", "◊", "#00aaff", "Prisme Spatial", GemCategory.DIMENSIONAL)
    ENTROPIC_CORE = ("entropic_core", "☢", "#ff3366", "Coeur Entropique", GemCategory.DIMENSIONAL)
    HARMONIC_CRYSTAL = ("harmonic_crystal", "♒", "#aa55ff", "Cristal Harmonique", GemCategory.DIMENSIONAL)
    CELESTIAL_TEAR = ("celestial_tear", "✧", "#ffffaa", "Larme Celeste", GemCategory.DIMENSIONAL)
    
    # === QUANTUM (7) - Gemmes a effets quantiques ===
    SCHRODINGER_GEM = ("schrodinger_gem", "Ψ", "#00ffff", "Gemme de Schrodinger", GemCategory.QUANTUM)
    HEISENBERG_SHARD = ("heisenberg_shard", "Δ", "#ff00ff", "Eclat d'Heisenberg", GemCategory.QUANTUM)
    PLANCK_PEARL = ("planck_pearl", "ℏ", "#ffff00", "Perle de Planck", GemCategory.QUANTUM)
    DIRAC_STONE = ("dirac_stone", "∂", "#00ff00", "Pierre de Dirac", GemCategory.QUANTUM)
    BELL_RESONATOR = ("bell_resonator", "⊗", "#ff8800", "Resonateur de Bell", GemCategory.QUANTUM)
    ENTANGLEMENT_CORE = ("entanglement_core", "∞", "#8800ff", "Coeur d'Intrication", GemCategory.QUANTUM)
    SUPERPOSITION_GEM = ("superposition_gem", "⊕", "#00ffaa", "Gemme de Superposition", GemCategory.QUANTUM)
    
    # === ELEMENTAL (7) - Forces naturelles ===
    INFERNO_RUBY = ("inferno_ruby", "🔥", "#ff2200", "Rubis Infernal", GemCategory.ELEMENTAL)
    GLACIER_SAPPHIRE = ("glacier_sapphire", "❄", "#0066ff", "Saphir Glaciaire", GemCategory.ELEMENTAL)
    STORM_TOPAZ = ("storm_topaz", "⚡", "#ffff00", "Topaze de Tempete", GemCategory.ELEMENTAL)
    EARTH_EMERALD = ("earth_emerald", "🌿", "#00aa00", "Emeraude Tellurique", GemCategory.ELEMENTAL)
    SHADOW_ONYX = ("shadow_onyx", "🌑", "#1a1a1a", "Onyx des Ombres", GemCategory.ELEMENTAL)
    LIGHT_DIAMOND = ("light_diamond", "💎", "#ffffff", "Diamant de Lumiere", GemCategory.ELEMENTAL)
    AETHER_OPAL = ("aether_opal", "✨", "#aaddff", "Opale d'Ether", GemCategory.ELEMENTAL)
    
    # === COSMIC (7) - Puissances stellaires ===
    NEBULA_HEART = ("nebula_heart", "🌌", "#663399", "Coeur de Nebuleuse", GemCategory.COSMIC)
    PULSAR_CORE = ("pulsar_core", "💫", "#00ffff", "Coeur de Pulsar", GemCategory.COSMIC)
    QUASAR_SHARD = ("quasar_shard", "🌟", "#ff6600", "Eclat de Quasar", GemCategory.COSMIC)
    BLACKHOLE_FRAGMENT = ("blackhole_fragment", "⚫", "#000000", "Fragment de Trou Noir", GemCategory.COSMIC)
    SUPERNOVA_EMBER = ("supernova_ember", "💥", "#ff3300", "Braise de Supernova", GemCategory.COSMIC)
    DARK_MATTER_GEM = ("dark_matter_gem", "◼", "#1a0a2e", "Gemme de Matiere Noire", GemCategory.COSMIC)
    STELLAR_DUST = ("stellar_dust", "⋆", "#ffeecc", "Poussiere Stellaire", GemCategory.COSMIC)
    
    # === RUNIC (7) - Pouvoirs runiques ===
    FEHU_STONE = ("fehu_stone", "ᚠ", "#ffd700", "Pierre de Fehu", GemCategory.RUNIC)
    URUZ_CRYSTAL = ("uruz_crystal", "ᚢ", "#8b4513", "Cristal d'Uruz", GemCategory.RUNIC)
    THURISAZ_SHARD = ("thurisaz_shard", "ᚦ", "#cc0000", "Eclat de Thurisaz", GemCategory.RUNIC)
    ANSUZ_GEM = ("ansuz_gem", "ᚨ", "#4169e1", "Gemme d'Ansuz", GemCategory.RUNIC)
    RAIDHO_PEARL = ("raidho_pearl", "ᚱ", "#228b22", "Perle de Raidho", GemCategory.RUNIC)
    SOWILO_CORE = ("sowilo_core", "ᛊ", "#ffcc00", "Coeur de Sowilo", GemCategory.RUNIC)
    OTHALA_HEART = ("othala_heart", "ᛟ", "#800080", "Coeur d'Othala", GemCategory.RUNIC)
    
    # === LEGENDARY (7) - Gemmes uniques extremement rares ===
    NEXUS_KEYSTONE = ("nexus_keystone", "⬟", "#ff00ff", "Cle de Voute du Nexus", GemCategory.LEGENDARY)
    SPINOR_MATRIX = ("spinor_matrix", "⎔", "#00ffff", "Matrice Spinorielle", GemCategory.LEGENDARY)
    CLIFFORD_JEWEL = ("clifford_jewel", "⟐", "#ffaa00", "Joyau de Clifford", GemCategory.LEGENDARY)
    MERKLE_ROOT = ("merkle_root", "⌬", "#00ff00", "Racine de Merkle", GemCategory.LEGENDARY)
    ENTROPY_SINGULARITY = ("entropy_singularity", "⊛", "#ff0066", "Singularite Entropique", GemCategory.LEGENDARY)
    POLY_DIMENSIONAL_GEM = ("poly_dimensional_gem", "⧫", "#ffffff", "Gemme Poly-Dimensionnelle", GemCategory.LEGENDARY)
    FOUNDERS_HEART = ("founders_heart", "♥", "#ffd700", "Coeur du Fondateur", GemCategory.LEGENDARY)
    
    def __init__(self, gem_id: str, symbol: str, color: str, display_name: str, category: GemCategory):
        self.gem_id = gem_id
        self.symbol = symbol
        self.color = color
        self.display_name = display_name
        self.category = category


# ============================================================================
# POUVOIRS SPECIAUX DES GEMMES
# ============================================================================

GEM_POWERS = {
    # Primordial Powers
    "void_crystal": {
        "power": "Void Absorption",
        "description": "Absorbe {value}% des degats et les convertit en energie",
        "effect_type": "defensive",
        "value_range": (10, 50)
    },
    "genesis_stone": {
        "power": "Creation Burst",
        "description": "Genere {value} points d'entropie supplementaires",
        "effect_type": "entropy",
        "value_range": (100, 1000)
    },
    "origin_pearl": {
        "power": "Primordial Link",
        "description": "Connexion directe au bloc Genesis #{value}",
        "effect_type": "link",
        "value_range": (1, 100)
    },
    "primeval_shard": {
        "power": "Ancient Resonance",
        "description": "Augmente la resonance de {value}% pour tous les glyphes",
        "effect_type": "buff",
        "value_range": (5, 30)
    },
    "creation_ember": {
        "power": "Spark of Life",
        "description": "Regenere {value} puissance par cycle",
        "effect_type": "regen",
        "value_range": (10, 100)
    },
    "omega_fragment": {
        "power": "End of Cycle",
        "description": "Multiplie la puissance finale par {value}x",
        "effect_type": "multiplier",
        "value_range": (1.1, 2.0)
    },
    "alpha_core": {
        "power": "First Light",
        "description": "Bonus de {value}% au premier artefact cree",
        "effect_type": "bonus",
        "value_range": (20, 100)
    },
    
    # Dimensional Powers
    "void_essence": {
        "power": "Dimensional Void",
        "description": "Ouvre un portail vers la dimension {value}",
        "effect_type": "portal",
        "value_range": (0, 6)
    },
    "quantum_shard": {
        "power": "Quantum Leap",
        "description": "Teleporte {value}% de puissance instantanement",
        "effect_type": "transfer",
        "value_range": (10, 50)
    },
    "temporal_gem": {
        "power": "Time Dilation",
        "description": "Ralentit le temps de {value}% dans le vault",
        "effect_type": "time",
        "value_range": (10, 75)
    },
    "spatial_prism": {
        "power": "Space Fold",
        "description": "Replie l'espace pour {value} dimensions",
        "effect_type": "space",
        "value_range": (2, 7)
    },
    "entropic_core": {
        "power": "Chaos Engine",
        "description": "Genere {value} bits d'entropie aleatoire",
        "effect_type": "entropy",
        "value_range": (256, 2048)
    },
    "harmonic_crystal": {
        "power": "Resonance Wave",
        "description": "Synchronise {value} artefacts ensemble",
        "effect_type": "sync",
        "value_range": (2, 10)
    },
    "celestial_tear": {
        "power": "Heavenly Light",
        "description": "Purifie {value}% des corruptions",
        "effect_type": "purify",
        "value_range": (25, 100)
    },
    
    # Quantum Powers
    "schrodinger_gem": {
        "power": "Superposition State",
        "description": "Existe dans {value} etats simultanement",
        "effect_type": "quantum",
        "value_range": (2, 8)
    },
    "heisenberg_shard": {
        "power": "Uncertainty Field",
        "description": "Incertitude de {value}% sur les mesures ennemies",
        "effect_type": "stealth",
        "value_range": (20, 80)
    },
    "planck_pearl": {
        "power": "Quantum Minimum",
        "description": "Puissance minimale garantie de {value}",
        "effect_type": "floor",
        "value_range": (100, 1000)
    },
    "dirac_stone": {
        "power": "Spinor Transform",
        "description": "Transforme {value}% de masse en energie",
        "effect_type": "convert",
        "value_range": (10, 50)
    },
    "bell_resonator": {
        "power": "Entanglement Boost",
        "description": "Violation de Bell augmentee de {value}",
        "effect_type": "bell",
        "value_range": (0.1, 0.83)
    },
    "entanglement_core": {
        "power": "Quantum Link",
        "description": "Lie {value} vaults par intrication quantique",
        "effect_type": "link",
        "value_range": (2, 7)
    },
    "superposition_gem": {
        "power": "Wave Collapse",
        "description": "Collapse favorable avec {value}% de chance",
        "effect_type": "luck",
        "value_range": (60, 95)
    },
    
    # Elemental Powers
    "inferno_ruby": {
        "power": "Flame Burst",
        "description": "Inflige {value} degats de feu",
        "effect_type": "damage",
        "value_range": (100, 1000)
    },
    "glacier_sapphire": {
        "power": "Frost Shield",
        "description": "Bouclier de glace absorbant {value} degats",
        "effect_type": "shield",
        "value_range": (200, 2000)
    },
    "storm_topaz": {
        "power": "Lightning Strike",
        "description": "Frappe {value} cibles simultanement",
        "effect_type": "aoe",
        "value_range": (2, 10)
    },
    "earth_emerald": {
        "power": "Gaia's Blessing",
        "description": "Regeneration de {value}% par heure",
        "effect_type": "regen",
        "value_range": (1, 10)
    },
    "shadow_onyx": {
        "power": "Void Cloak",
        "description": "Invisibilite pendant {value} cycles",
        "effect_type": "stealth",
        "value_range": (1, 10)
    },
    "light_diamond": {
        "power": "Radiant Aura",
        "description": "Augmente la purete de {value}%",
        "effect_type": "purity",
        "value_range": (10, 50)
    },
    "aether_opal": {
        "power": "Ethereal Phase",
        "description": "Traverse {value} barrieres dimensionnelles",
        "effect_type": "phase",
        "value_range": (1, 7)
    },
    
    # Cosmic Powers
    "nebula_heart": {
        "power": "Star Birth",
        "description": "Cree {value} nouvelles gemmes mineures",
        "effect_type": "spawn",
        "value_range": (1, 5)
    },
    "pulsar_core": {
        "power": "Pulse Wave",
        "description": "Emet {value} pulses d'energie par cycle",
        "effect_type": "pulse",
        "value_range": (3, 12)
    },
    "quasar_shard": {
        "power": "Energy Beam",
        "description": "Rayon d'energie de {value} puissance",
        "effect_type": "beam",
        "value_range": (500, 5000)
    },
    "blackhole_fragment": {
        "power": "Gravity Well",
        "description": "Attire {value}% des ressources proches",
        "effect_type": "attract",
        "value_range": (10, 50)
    },
    "supernova_ember": {
        "power": "Stellar Explosion",
        "description": "Explosion de {value}x la puissance (usage unique)",
        "effect_type": "nuke",
        "value_range": (5, 20)
    },
    "dark_matter_gem": {
        "power": "Hidden Mass",
        "description": "Puissance cachee de {value} non detectable",
        "effect_type": "hidden",
        "value_range": (1000, 10000)
    },
    "stellar_dust": {
        "power": "Cosmic Scatter",
        "description": "Distribue {value}% de puissance aux allies",
        "effect_type": "share",
        "value_range": (5, 25)
    },
    
    # Runic Powers
    "fehu_stone": {
        "power": "Wealth Accumulation",
        "description": "Genere {value} PSNX par jour",
        "effect_type": "income",
        "value_range": (10, 1000)
    },
    "uruz_crystal": {
        "power": "Primal Strength",
        "description": "Force brute augmentee de {value}%",
        "effect_type": "strength",
        "value_range": (10, 100)
    },
    "thurisaz_shard": {
        "power": "Thorn Shield",
        "description": "Renvoie {value}% des degats",
        "effect_type": "reflect",
        "value_range": (10, 50)
    },
    "ansuz_gem": {
        "power": "Divine Wisdom",
        "description": "Revele {value} secrets caches",
        "effect_type": "reveal",
        "value_range": (1, 7)
    },
    "raidho_pearl": {
        "power": "Journey's End",
        "description": "Reduit les couts de transfert de {value}%",
        "effect_type": "discount",
        "value_range": (10, 75)
    },
    "sowilo_core": {
        "power": "Solar Flare",
        "description": "Illumine {value} dimensions",
        "effect_type": "illuminate",
        "value_range": (1, 7)
    },
    "othala_heart": {
        "power": "Ancestral Bond",
        "description": "Heritage de {value}% des ancetres",
        "effect_type": "inherit",
        "value_range": (10, 50)
    },
    
    # Legendary Powers (tres puissants)
    "nexus_keystone": {
        "power": "Nexus Control",
        "description": "Controle total du Nexus niveau {value}",
        "effect_type": "control",
        "value_range": (1, 7)
    },
    "spinor_matrix": {
        "power": "Matrix Override",
        "description": "Modifie {value} parametres spinoriels",
        "effect_type": "override",
        "value_range": (1, 7)
    },
    "clifford_jewel": {
        "power": "Algebraic Mastery",
        "description": "Maitrise Cl(0,{value}) complete",
        "effect_type": "mastery",
        "value_range": (3, 7)
    },
    "merkle_root": {
        "power": "Hash Authority",
        "description": "Verifie {value} branches simultanement",
        "effect_type": "verify",
        "value_range": (8, 256)
    },
    "entropy_singularity": {
        "power": "Infinite Randomness",
        "description": "Genere {value} bits d'entropie pure",
        "effect_type": "entropy",
        "value_range": (4096, 65536)
    },
    "poly_dimensional_gem": {
        "power": "Dimension Weaver",
        "description": "Tisse {value} dimensions ensemble",
        "effect_type": "weave",
        "value_range": (3, 7)
    },
    "founders_heart": {
        "power": "Founder's Blessing",
        "description": "Bonus fondateur permanent de {value}%",
        "effect_type": "founder",
        "value_range": (50, 200)
    },
}


# ============================================================================
# RARETES DE GEMMES
# ============================================================================

class GemRarity(Enum):
    """Raretes des gemmes avec probabilites"""
    CRACKED = ("cracked", 0.3, "#666666", "Fissuree")
    FLAWED = ("flawed", 0.5, "#999999", "Defectueuse")
    COMMON = ("common", 1.0, "#ffffff", "Commune")
    POLISHED = ("polished", 1.5, "#00ff00", "Polie")
    REFINED = ("refined", 2.0, "#00aaff", "Raffinee")
    PRISTINE = ("pristine", 3.0, "#aa55ff", "Pristine")
    PERFECT = ("perfect", 5.0, "#ff8800", "Parfaite")
    FLAWLESS = ("flawless", 8.0, "#ff00ff", "Sans Defaut")
    TRANSCENDENT = ("transcendent", 15.0, "#00ffff", "Transcendante")
    DIVINE = ("divine", 25.0, "#ffd700", "Divine")
    
    def __init__(self, rarity_id: str, multiplier: float, color: str, display_name: str):
        self.rarity_id = rarity_id
        self.multiplier = multiplier
        self.color = color
        self.display_name = display_name


GEM_RARITY_WEIGHTS = {
    GemRarity.CRACKED: 1500,
    GemRarity.FLAWED: 2500,
    GemRarity.COMMON: 3000,
    GemRarity.POLISHED: 1500,
    GemRarity.REFINED: 800,
    GemRarity.PRISTINE: 400,
    GemRarity.PERFECT: 200,
    GemRarity.FLAWLESS: 70,
    GemRarity.TRANSCENDENT: 25,
    GemRarity.DIVINE: 5,
}


# ============================================================================
# GEMME MOBILE
# ============================================================================

class GemStatus(Enum):
    """Statut d'une gemme"""
    SOCKETED = "socketed"       # Enchassee dans un glyphe
    INVENTORY = "inventory"     # Dans l'inventaire
    TRANSFERRED = "transferred" # En cours de transfert
    LOCKED = "locked"           # Verrouillee
    SHATTERED = "shattered"     # Brisee


@dataclass
class MobileGem:
    """Gemme mobile detachable et transferable"""
    # Identite
    gem_id: str
    gem_type: str  # GemType value
    rarity: str    # GemRarity value
    
    # Stats
    base_power: float
    resonance: float
    purity: float
    stability: float
    
    # Pouvoir special
    power_name: str
    power_description: str
    power_value: float
    power_effect_type: str
    
    # Origine
    origin_vault: int
    origin_glyph: Optional[str] = None
    created_at: str = ""
    
    # Position actuelle
    current_vault: Optional[int] = None
    current_glyph: Optional[str] = None
    socket_position: Optional[int] = None  # 0, 1, ou 2
    status: str = "inventory"
    
    # Historique
    transfer_history: List[Dict] = field(default_factory=list)
    
    # Metadonnees
    times_transferred: int = 0
    times_socketed: int = 0
    total_power_generated: float = 0.0
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "MobileGem":
        return cls(**data)
    
    @property
    def effective_power(self) -> float:
        """Puissance effective avec multiplicateur de rarete"""
        rarity_enum = next((r for r in GemRarity if r.rarity_id == self.rarity), GemRarity.COMMON)
        return self.base_power * rarity_enum.multiplier * (1 + self.resonance / 100)
    
    @property
    def display_name(self) -> str:
        gem_enum = next((g for g in GemType if g.gem_id == self.gem_type), None)
        if gem_enum:
            return gem_enum.display_name
        return self.gem_type.replace('_', ' ').title()
    
    @property
    def symbol(self) -> str:
        gem_enum = next((g for g in GemType if g.gem_id == self.gem_type), None)
        return gem_enum.symbol if gem_enum else "?"
    
    @property
    def color(self) -> str:
        gem_enum = next((g for g in GemType if g.gem_id == self.gem_type), None)
        return gem_enum.color if gem_enum else "#ffffff"


# ============================================================================
# GESTIONNAIRE DE GEMMES
# ============================================================================

class GemVault:
    """Gestionnaire de gemmes mobiles"""
    
    def __init__(self, data_dir: str = None):
        base_path = Path(__file__).parent.parent
        self.data_dir = Path(data_dir) if data_dir else base_path / "gem_vault"
        self.gems_dir = self.data_dir / "gems"
        self.inventory_dir = self.data_dir / "inventory"
        
        self.gems_dir.mkdir(parents=True, exist_ok=True)
        self.inventory_dir.mkdir(parents=True, exist_ok=True)
        
        self._gems: Dict[str, MobileGem] = {}
        self._load_gems()
    
    def _load_gems(self):
        """Charge toutes les gemmes"""
        for gem_file in self.gems_dir.glob("gem_*.json"):
            try:
                with open(gem_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                gem = MobileGem.from_dict(data)
                self._gems[gem.gem_id] = gem
            except Exception as e:
                print(f"[WARN] Error loading {gem_file}: {e}")
    
    def _save_gem(self, gem: MobileGem):
        """Sauvegarde une gemme"""
        filepath = self.gems_dir / f"gem_{gem.gem_id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(gem.to_dict(), f, indent=2, ensure_ascii=False)
        self._gems[gem.gem_id] = gem
    
    def generate_gem(self, vault_number: int, 
                    force_type: Optional[GemType] = None,
                    force_rarity: Optional[GemRarity] = None,
                    seed: bytes = None) -> MobileGem:
        """Genere une nouvelle gemme"""
        # RNG
        if seed:
            rng_state = hashlib.sha512(seed).digest()
        else:
            rng_state = secrets.token_bytes(64)
        
        def next_random(max_val: int) -> int:
            nonlocal rng_state
            rng_state = hashlib.sha512(rng_state).digest()
            return int.from_bytes(rng_state[:8], 'big') % max_val
        
        def next_float() -> float:
            return next_random(1000000) / 1000000
        
        # Type
        if force_type:
            gem_type = force_type
        else:
            all_types = list(GemType)
            gem_type = all_types[next_random(len(all_types))]
        
        # Rarete
        if force_rarity:
            rarity = force_rarity
        else:
            total = sum(GEM_RARITY_WEIGHTS.values())
            roll = next_random(total)
            cumulative = 0
            rarity = GemRarity.COMMON
            for r, weight in GEM_RARITY_WEIGHTS.items():
                cumulative += weight
                if roll < cumulative:
                    rarity = r
                    break
        
        # Stats de base selon rarete (ranges NON-chevauchants, Divine > Transcendent)
        base_ranges = {
            GemRarity.CRACKED: (5, 25),
            GemRarity.FLAWED: (30, 80),
            GemRarity.COMMON: (100, 250),
            GemRarity.POLISHED: (300, 600),
            GemRarity.REFINED: (700, 1200),
            GemRarity.PRISTINE: (1500, 2500),
            GemRarity.PERFECT: (3000, 5000),
            GemRarity.FLAWLESS: (6000, 10000),
            GemRarity.TRANSCENDENT: (12000, 20000),
            GemRarity.DIVINE: (25000, 50000),  # Divine TOUJOURS > Transcendent
        }
        
        min_p, max_p = base_ranges.get(rarity, (50, 200))
        base_power = min_p + next_float() * (max_p - min_p)
        
        # Autres stats
        resonance = next_float() * 100
        purity = 30 + next_float() * 70
        stability = 50 + next_float() * 50
        
        # Pouvoir special
        power_info = GEM_POWERS.get(gem_type.gem_id, {
            "power": "Unknown Power",
            "description": "Effet inconnu",
            "effect_type": "unknown",
            "value_range": (1, 10)
        })
        
        min_val, max_val = power_info["value_range"]
        if isinstance(min_val, float):
            power_value = min_val + next_float() * (max_val - min_val)
        else:
            power_value = min_val + next_random(max_val - min_val + 1)
        
        # ID unique
        gem_id = hashlib.sha256(
            f"{gem_type.gem_id}{rarity.rarity_id}{datetime.now().isoformat()}{secrets.token_hex(8)}".encode()
        ).hexdigest()[:16]
        
        gem = MobileGem(
            gem_id=gem_id,
            gem_type=gem_type.gem_id,
            rarity=rarity.rarity_id,
            base_power=round(base_power, 2),
            resonance=round(resonance, 2),
            purity=round(purity, 2),
            stability=round(stability, 2),
            power_name=power_info["power"],
            power_description=power_info["description"].format(value=round(power_value, 2) if isinstance(power_value, float) else power_value),
            power_value=power_value,
            power_effect_type=power_info["effect_type"],
            origin_vault=vault_number,
            created_at=datetime.now().isoformat(),
            current_vault=vault_number,
            status="inventory"
        )
        
        self._save_gem(gem)
        return gem
    
    def socket_gem(self, gem_id: str, glyph_id: str, position: int) -> bool:
        """Enchasse une gemme dans un glyphe"""
        gem = self._gems.get(gem_id)
        if not gem:
            return False
        
        if gem.status not in ["inventory", "socketed"]:
            return False
        
        if position not in [0, 1, 2]:
            return False
        
        # Detacher de l'ancien emplacement si necessaire
        if gem.status == "socketed":
            gem.transfer_history.append({
                "action": "unsocket",
                "from_glyph": gem.current_glyph,
                "timestamp": datetime.now().isoformat()
            })
        
        # Enchasser
        gem.current_glyph = glyph_id
        gem.socket_position = position
        gem.status = "socketed"
        gem.times_socketed += 1
        gem.transfer_history.append({
            "action": "socket",
            "to_glyph": glyph_id,
            "position": position,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_gem(gem)
        return True
    
    def unsocket_gem(self, gem_id: str) -> bool:
        """Retire une gemme de son glyphe"""
        gem = self._gems.get(gem_id)
        if not gem or gem.status != "socketed":
            return False
        
        gem.transfer_history.append({
            "action": "unsocket",
            "from_glyph": gem.current_glyph,
            "timestamp": datetime.now().isoformat()
        })
        
        gem.current_glyph = None
        gem.socket_position = None
        gem.status = "inventory"
        
        self._save_gem(gem)
        return True
    
    def transfer_gem(self, gem_id: str, to_vault: int) -> bool:
        """Transfere une gemme vers un autre vault"""
        gem = self._gems.get(gem_id)
        if not gem:
            return False
        
        if gem.status == "locked":
            return False
        
        # Si enchassee, d'abord retirer
        if gem.status == "socketed":
            self.unsocket_gem(gem_id)
        
        from_vault = gem.current_vault
        gem.current_vault = to_vault
        gem.status = "inventory"
        gem.times_transferred += 1
        gem.transfer_history.append({
            "action": "transfer",
            "from_vault": from_vault,
            "to_vault": to_vault,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_gem(gem)
        return True
    
    def lock_gem(self, gem_id: str) -> bool:
        """Verrouille une gemme"""
        gem = self._gems.get(gem_id)
        if not gem:
            return False
        
        gem.status = "locked"
        gem.transfer_history.append({
            "action": "lock",
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_gem(gem)
        return True
    
    def shatter_gem(self, gem_id: str) -> Optional[List[MobileGem]]:
        """Brise une gemme (peut donner des fragments)"""
        gem = self._gems.get(gem_id)
        if not gem or gem.status == "locked":
            return None
        
        gem.status = "shattered"
        gem.transfer_history.append({
            "action": "shatter",
            "timestamp": datetime.now().isoformat()
        })
        self._save_gem(gem)
        
        # Chance de generer des fragments
        fragments = []
        if secrets.randbelow(100) < 30:  # 30% chance
            for _ in range(secrets.randbelow(3) + 1):
                frag = self.generate_gem(
                    gem.current_vault or gem.origin_vault,
                    force_rarity=GemRarity.CRACKED
                )
                fragments.append(frag)
        
        return fragments
    
    def get_gem(self, gem_id: str) -> Optional[MobileGem]:
        return self._gems.get(gem_id)
    
    def get_vault_gems(self, vault_number: int) -> List[MobileGem]:
        """Obtient toutes les gemmes d'un vault"""
        return [g for g in self._gems.values() 
                if g.current_vault == vault_number and g.status != "shattered"]
    
    def get_inventory(self, vault_number: int) -> List[MobileGem]:
        """Obtient les gemmes dans l'inventaire d'un vault"""
        return [g for g in self._gems.values()
                if g.current_vault == vault_number and g.status == "inventory"]
    
    def get_socketed_gems(self, vault_number: int) -> List[MobileGem]:
        """Obtient les gemmes enchassees d'un vault"""
        return [g for g in self._gems.values()
                if g.current_vault == vault_number and g.status == "socketed"]
    
    def get_all_gems(self) -> List[MobileGem]:
        return [g for g in self._gems.values() if g.status != "shattered"]
    
    def get_gem_stats(self) -> Dict:
        """Statistiques globales des gemmes"""
        all_gems = self.get_all_gems()
        
        rarity_counts = {}
        type_counts = {}
        category_counts = {}
        total_power = 0
        
        for gem in all_gems:
            rarity_counts[gem.rarity] = rarity_counts.get(gem.rarity, 0) + 1
            type_counts[gem.gem_type] = type_counts.get(gem.gem_type, 0) + 1
            
            gem_enum = next((g for g in GemType if g.gem_id == gem.gem_type), None)
            if gem_enum:
                cat = gem_enum.category.value
                category_counts[cat] = category_counts.get(cat, 0) + 1
            
            total_power += gem.effective_power
        
        return {
            "total_gems": len(all_gems),
            "total_power": total_power,
            "rarity_breakdown": rarity_counts,
            "type_breakdown": type_counts,
            "category_breakdown": category_counts,
        }


# ============================================================================
# AFFICHAGE
# ============================================================================

def format_gem_display(gem: MobileGem) -> str:
    """Format d'affichage d'une gemme"""
    status_icons = {
        "socketed": "⚙",
        "inventory": "📦",
        "transferred": "↗",
        "locked": "🔒",
        "shattered": "💔"
    }
    
    icon = status_icons.get(gem.status, "?")
    rarity_enum = next((r for r in GemRarity if r.rarity_id == gem.rarity), GemRarity.COMMON)
    
    return (f"{gem.symbol} {icon} [{rarity_enum.display_name[:4].upper()}] {gem.display_name} "
            f"| PWR:{gem.effective_power:,.0f} | {gem.power_name}")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  GEM VAULT - Mobile Gems System")
    print("="*70 + "\n")
    
    vault = GemVault()
    
    # Stats
    stats = vault.get_gem_stats()
    print(f"Total Gems: {stats['total_gems']}")
    print(f"Total Power: {stats['total_power']:,.0f}")
    
    if stats['total_gems'] == 0:
        print("\n[*] Generating sample gems...\n")
        for i in range(10):
            gem = vault.generate_gem(vault_number=1)
            print(f"  {format_gem_display(gem)}")
    else:
        print("\n[*] Existing gems:\n")
        for gem in sorted(vault.get_all_gems(), key=lambda x: x.effective_power, reverse=True)[:10]:
            print(f"  {format_gem_display(gem)}")
    
    print("\n" + "="*70)
    print("  49 GEM TYPES AVAILABLE:")
    print("="*70)
    
    for category in GemCategory:
        gems_in_cat = [g for g in GemType if g.category == category]
        print(f"\n  {category.value.upper()} ({len(gems_in_cat)}):")
        for gem in gems_in_cat:
            print(f"    {gem.symbol} {gem.display_name}")
