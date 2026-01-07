"""
Systeme d'Artefacts Spinoriels pour Eidolon
========================================================

Genere des artefacts uniques avec:
- Classes de rarete RNG cryptographique
- Puissance calculee via le moteur Poly-Spinor 7D
- Caracteristiques et particularites uniques
- Affinites elementaires et capacites speciales
"""

import os
import sys
import json
import hashlib
import secrets
import math
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
# CLASSES DE RARETE
# ============================================================================

class ArtifactRarity(Enum):
    """Classes de rarete avec probabilites RNG"""
    COMMON = "common"           # 40%
    UNCOMMON = "uncommon"       # 25%
    RARE = "rare"              # 18%
    EPIC = "epic"              # 10%
    LEGENDARY = "legendary"     # 5%
    MYTHIC = "mythic"          # 1.5%
    TRANSCENDENT = "transcendent"  # 0.4%
    PRIMORDIAL = "primordial"  # 0.1%


RARITY_WEIGHTS = {
    ArtifactRarity.COMMON: 4000,
    ArtifactRarity.UNCOMMON: 2500,
    ArtifactRarity.RARE: 1800,
    ArtifactRarity.EPIC: 1000,
    ArtifactRarity.LEGENDARY: 500,
    ArtifactRarity.MYTHIC: 150,
    ArtifactRarity.TRANSCENDENT: 40,
    ArtifactRarity.PRIMORDIAL: 10,
}

RARITY_COLORS = {
    ArtifactRarity.COMMON: "#9d9d9d",
    ArtifactRarity.UNCOMMON: "#1eff00",
    ArtifactRarity.RARE: "#0070dd",
    ArtifactRarity.EPIC: "#a335ee",
    ArtifactRarity.LEGENDARY: "#ff8000",
    ArtifactRarity.MYTHIC: "#e6cc80",
    ArtifactRarity.TRANSCENDENT: "#00ffff",
    ArtifactRarity.PRIMORDIAL: "#ff00ff",
}

RARITY_MULTIPLIERS = {
    ArtifactRarity.COMMON: 1.0,
    ArtifactRarity.UNCOMMON: 1.5,
    ArtifactRarity.RARE: 2.5,
    ArtifactRarity.EPIC: 4.0,
    ArtifactRarity.LEGENDARY: 7.0,
    ArtifactRarity.MYTHIC: 12.0,
    ArtifactRarity.TRANSCENDENT: 20.0,
    ArtifactRarity.PRIMORDIAL: 50.0,
}


# ============================================================================
# AFFINITES ELEMENTAIRES
# ============================================================================

class ElementalAffinity(Enum):
    """Affinites elementaires basees sur les 7 dimensions spinoriales"""
    VOID = "void"           # Dimension 0 - Neant primordial
    QUANTUM = "quantum"     # Dimension 1 - Superposition quantique
    TEMPORAL = "temporal"   # Dimension 2 - Flux temporel
    SPATIAL = "spatial"     # Dimension 3 - Distorsion spatiale
    ENTROPIC = "entropic"   # Dimension 4 - Chaos entropique
    HARMONIC = "harmonic"   # Dimension 5 - Resonance harmonique
    CELESTIAL = "celestial" # Dimension 6 - Energie celeste
    PRIMORDIAL = "primordial"  # Dimension 7 - Essence primordiale


ELEMENT_SYMBOLS = {
    ElementalAffinity.VOID: "◯",
    ElementalAffinity.QUANTUM: "⚛",
    ElementalAffinity.TEMPORAL: "⧖",
    ElementalAffinity.SPATIAL: "◈",
    ElementalAffinity.ENTROPIC: "☢",
    ElementalAffinity.HARMONIC: "♒",
    ElementalAffinity.CELESTIAL: "✧",
    ElementalAffinity.PRIMORDIAL: "⬡",
}

ELEMENT_COLORS = {
    ElementalAffinity.VOID: "#1a1a2e",
    ElementalAffinity.QUANTUM: "#00ff88",
    ElementalAffinity.TEMPORAL: "#ffaa00",
    ElementalAffinity.SPATIAL: "#00aaff",
    ElementalAffinity.ENTROPIC: "#ff3366",
    ElementalAffinity.HARMONIC: "#aa55ff",
    ElementalAffinity.CELESTIAL: "#ffff66",
    ElementalAffinity.PRIMORDIAL: "#ffffff",
}


# ============================================================================
# TYPES D'ARTEFACTS
# ============================================================================

class ArtifactType(Enum):
    """Types d'artefacts avec caracteristiques uniques"""
    CRYSTAL = "crystal"        # Cristal de puissance
    RUNE_STONE = "rune_stone"  # Pierre runique
    SPINOR_ORB = "spinor_orb"  # Orbe spinoriel
    QUANTUM_KEY = "quantum_key"  # Cle quantique
    VOID_SHARD = "void_shard"  # Eclat du vide
    NEXUS_CORE = "nexus_core"  # Coeur de nexus
    TEMPORAL_ANCHOR = "temporal_anchor"  # Ancre temporelle
    ENTROPY_SEED = "entropy_seed"  # Graine d'entropie


ARTIFACT_EMOJIS = {
    ArtifactType.CRYSTAL: "💎",
    ArtifactType.RUNE_STONE: "🗿",
    ArtifactType.SPINOR_ORB: "🔮",
    ArtifactType.QUANTUM_KEY: "🔑",
    ArtifactType.VOID_SHARD: "🌑",
    ArtifactType.NEXUS_CORE: "⚙",
    ArtifactType.TEMPORAL_ANCHOR: "⏳",
    ArtifactType.ENTROPY_SEED: "🌀",
}


# ============================================================================
# CAPACITES SPECIALES
# ============================================================================

SPECIAL_ABILITIES = {
    # Capacites communes
    "entropy_boost": {
        "name": "Entropy Boost",
        "description": "Augmente l'entropie generee de {value}%",
        "min_rarity": ArtifactRarity.COMMON,
        "value_range": (5, 50),
    },
    "strength_amplifier": {
        "name": "Strength Amplifier", 
        "description": "Multiplie la force de base par {value}",
        "min_rarity": ArtifactRarity.UNCOMMON,
        "value_range": (1.1, 2.0),
    },
    "rune_resonance": {
        "name": "Rune Resonance",
        "description": "Les runes gagnent {value}% de puissance",
        "min_rarity": ArtifactRarity.RARE,
        "value_range": (10, 100),
    },
    # Capacites rares
    "quantum_entanglement": {
        "name": "Quantum Entanglement",
        "description": "Lie {value} vaults pour partager la force",
        "min_rarity": ArtifactRarity.EPIC,
        "value_range": (2, 7),
    },
    "temporal_echo": {
        "name": "Temporal Echo",
        "description": "Duplique les gains d'entropie {value} fois",
        "min_rarity": ArtifactRarity.EPIC,
        "value_range": (2, 5),
    },
    # Capacites legendaires
    "void_channel": {
        "name": "Void Channel",
        "description": "Puise {value}% d'energie du vide primordial",
        "min_rarity": ArtifactRarity.LEGENDARY,
        "value_range": (15, 75),
    },
    "spinor_mastery": {
        "name": "Spinor Mastery",
        "description": "Controle parfait des {value} dimensions spinoriales",
        "min_rarity": ArtifactRarity.LEGENDARY,
        "value_range": (3, 7),
    },
    # Capacites mythiques
    "primordial_link": {
        "name": "Primordial Link",
        "description": "Connexion directe au bloc Genesis #{value}",
        "min_rarity": ArtifactRarity.MYTHIC,
        "value_range": (1, 100),
    },
    "dimension_shift": {
        "name": "Dimension Shift",
        "description": "Peut traverser {value} dimensions simultanement",
        "min_rarity": ArtifactRarity.MYTHIC,
        "value_range": (2, 7),
    },
    # Capacites transcendantes
    "infinity_resonance": {
        "name": "Infinity Resonance",
        "description": "Force infinie pendant {value} cycles",
        "min_rarity": ArtifactRarity.TRANSCENDENT,
        "value_range": (1, 10),
    },
    "reality_anchor": {
        "name": "Reality Anchor",
        "description": "Ancre la realite dans {value} dimensions",
        "min_rarity": ArtifactRarity.TRANSCENDENT,
        "value_range": (3, 7),
    },
    # Capacites primordiales
    "genesis_authority": {
        "name": "Genesis Authority",
        "description": "Autorite absolue sur la creation de {value} vaults",
        "min_rarity": ArtifactRarity.PRIMORDIAL,
        "value_range": (10, 1000),
    },
    "omega_protocol": {
        "name": "Omega Protocol",
        "description": "Active le protocole Omega niveau {value}",
        "min_rarity": ArtifactRarity.PRIMORDIAL,
        "value_range": (1, 7),
    },
}


# ============================================================================
# STATISTIQUES D'ARTEFACT
# ============================================================================

@dataclass
class ArtifactStats:
    """Statistiques completes d'un artefact"""
    # Stats primaires
    base_power: float           # Puissance de base (1-1000)
    spinor_resonance: float     # Resonance spinoriale (0-100%)
    entropy_coefficient: float  # Coefficient d'entropie (0.1-10.0)
    dimensional_affinity: float # Affinite dimensionnelle (0-7)
    
    # Stats secondaires
    stability: float           # Stabilite (0-100%)
    purity: float             # Purete (0-100%)
    coherence: float          # Coherence quantique (0-100%)
    
    # Stats derivees
    effective_power: float = 0.0
    total_multiplier: float = 1.0
    
    def calculate_effective_power(self, rarity_mult: float) -> float:
        """Calcule la puissance effective"""
        self.total_multiplier = rarity_mult * (1 + self.spinor_resonance / 100)
        self.effective_power = self.base_power * self.total_multiplier * self.entropy_coefficient
        return self.effective_power
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SpinorSignature:
    """Signature spinoriale unique de l'artefact"""
    seed_7d: List[float]           # Seed dans les 7 dimensions
    dirac_components: List[float]  # Composantes de Dirac (8)
    bell_violation: float          # Violation des inegalites de Bell
    entanglement_degree: float     # Degre d'intrication
    quantum_state: str             # Etat quantique encode
    
    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================================
# ARTEFACT PRINCIPAL
# ============================================================================

@dataclass
class SpinorArtifact:
    """Artefact spinoriel complet avec toutes ses caracteristiques"""
    # Identite
    artifact_id: str
    name: str
    artifact_type: ArtifactType
    rarity: ArtifactRarity
    
    # Creation
    created_at: str
    genesis_block_id: Optional[str] = None
    vault_number: Optional[int] = None
    
    # Caracteristiques
    element: ElementalAffinity = ElementalAffinity.VOID
    stats: Optional[ArtifactStats] = None
    signature: Optional[SpinorSignature] = None
    
    # Capacites
    abilities: List[Dict[str, Any]] = field(default_factory=list)
    
    # Glyphes et Gemmes (7 glyphes x 3 gemmes = 21 gemmes)
    glyph_array: Optional[Dict[str, Any]] = None
    
    # Visuel
    description: str = ""
    lore: str = ""
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['artifact_type'] = self.artifact_type.value
        d['rarity'] = self.rarity.value
        d['element'] = self.element.value
        return d
    
    @classmethod
    def from_dict(cls, data: dict) -> "SpinorArtifact":
        data['artifact_type'] = ArtifactType(data['artifact_type'])
        data['rarity'] = ArtifactRarity(data['rarity'])
        data['element'] = ElementalAffinity(data['element'])
        if data.get('stats'):
            data['stats'] = ArtifactStats(**data['stats'])
        if data.get('signature'):
            data['signature'] = SpinorSignature(**data['signature'])
        return cls(**data)
    
    @property
    def color(self) -> str:
        return RARITY_COLORS.get(self.rarity, "#ffffff")
    
    @property
    def emoji(self) -> str:
        return ARTIFACT_EMOJIS.get(self.artifact_type, "?")
    
    @property
    def element_symbol(self) -> str:
        return ELEMENT_SYMBOLS.get(self.element, "?")
    
    def get_display_name(self) -> str:
        return f"{self.emoji} {self.name} {self.element_symbol}"
    
    def get_power_rating(self) -> str:
        """Note de puissance sur 5 etoiles"""
        if not self.stats:
            return "?"
        power = self.stats.effective_power
        if power < 100:
            return "★☆☆☆☆"
        elif power < 500:
            return "★★☆☆☆"
        elif power < 2000:
            return "★★★☆☆"
        elif power < 10000:
            return "★★★★☆"
        else:
            return "★★★★★"


# ============================================================================
# GENERATEUR D'ARTEFACTS SPINORIELS
# ============================================================================

class SpinorArtifactGenerator:
    """Generateur d'artefacts utilisant le moteur Poly-Spinor 7D"""
    
    # Noms proceduraux
    PREFIXES = [
        "Ancient", "Ethereal", "Void", "Quantum", "Primordial",
        "Nexus", "Infinite", "Omega", "Alpha", "Cosmic",
        "Resonant", "Harmonic", "Entropic", "Temporal", "Spatial",
        "Celestial", "Dark", "Radiant", "Eternal", "Unstable"
    ]
    
    SUFFIXES = [
        "of the Void", "of Infinity", "of Resonance", "of Power",
        "of the Ancients", "of Eternity", "of Chaos", "of Order",
        "of the Nexus", "of Genesis", "of Entropy", "of Harmony",
        "of the Seven", "of Dimensions", "of the Spinor"
    ]
    
    CORE_NAMES = {
        ArtifactType.CRYSTAL: ["Shard", "Prism", "Gem", "Fragment", "Core"],
        ArtifactType.RUNE_STONE: ["Tablet", "Monolith", "Obelisk", "Sigil", "Glyph"],
        ArtifactType.SPINOR_ORB: ["Sphere", "Orb", "Eye", "Node", "Singularity"],
        ArtifactType.QUANTUM_KEY: ["Key", "Cipher", "Lock", "Gate", "Passage"],
        ArtifactType.VOID_SHARD: ["Void", "Abyss", "Shadow", "Eclipse", "Null"],
        ArtifactType.NEXUS_CORE: ["Heart", "Core", "Engine", "Matrix", "Nexus"],
        ArtifactType.TEMPORAL_ANCHOR: ["Anchor", "Hourglass", "Pendulum", "Clock", "Loop"],
        ArtifactType.ENTROPY_SEED: ["Seed", "Spark", "Source", "Well", "Font"],
    }
    
    LORE_TEMPLATES = [
        "Forge dans les profondeurs du {element}, cet artefact resonne avec {ability}.",
        "Les anciens ont cree cet objet pour canaliser {element}. Sa puissance est {rating}.",
        "Ne dans le chaos de {element}, il confere {ability} a son porteur.",
        "Temoin de la creation du Nexus, il vibre avec l'energie de {element}.",
        "Les {dimension} dimensions convergent en cet artefact de {element}.",
    ]
    
    def __init__(self, vault_seed: Optional[bytes] = None):
        """
        Args:
            vault_seed: Seed derivee de la cle du vault pour le RNG
        """
        self.vault_seed = vault_seed or secrets.token_bytes(32)
        self._rng_state = hashlib.sha512(self.vault_seed).digest()
        
    def _next_random(self, max_val: int = 10000) -> int:
        """Genere un nombre aleatoire cryptographique"""
        self._rng_state = hashlib.sha512(self._rng_state).digest()
        value = int.from_bytes(self._rng_state[:8], 'big')
        return value % max_val
    
    def _next_random_float(self) -> float:
        """Genere un float entre 0 et 1"""
        return self._next_random(1000000) / 1000000.0
    
    def _roll_rarity(self) -> ArtifactRarity:
        """Tire une rarete avec les poids definis"""
        total = sum(RARITY_WEIGHTS.values())
        roll = self._next_random(total)
        
        cumulative = 0
        for rarity, weight in RARITY_WEIGHTS.items():
            cumulative += weight
            if roll < cumulative:
                return rarity
        
        return ArtifactRarity.COMMON
    
    def _generate_spinor_seed(self) -> np.ndarray:
        """Genere un seed 7D pour les calculs spinoriels"""
        seed = np.zeros(7)
        for i in range(7):
            # Utilise le RNG cryptographique
            raw = self._next_random(1000000) / 500000.0 - 1.0  # [-1, 1]
            seed[i] = raw
        
        # Normalise pour avoir une norme unitaire
        norm = np.linalg.norm(seed)
        if norm > 0:
            seed = seed / norm
        
        return seed
    
    def _compute_dirac_spinor(self, seed_7d: np.ndarray) -> np.ndarray:
        """Calcule le spineur de Dirac 8D"""
        dirac = np.zeros(8, dtype=complex)
        dirac[:7] = seed_7d
        dirac[7] = np.sqrt(max(0, 1 - np.sum(seed_7d ** 2)))
        
        # Applique une rotation dans l'espace spinoriel
        theta = self._next_random_float() * 2 * np.pi
        phi = self._next_random_float() * np.pi
        
        rotation = np.exp(1j * theta) * np.cos(phi)
        dirac = dirac * rotation
        
        return dirac
    
    def _compute_bell_violation(self, dirac: np.ndarray) -> float:
        """Calcule la violation des inegalites de Bell"""
        # Mesure de l'intrication via les correlations
        correlations = []
        for i in range(4):
            for j in range(i + 1, 8):
                corr = abs(dirac[i] * np.conj(dirac[j]))
                correlations.append(corr)
        
        # La violation maximale de Bell est 2*sqrt(2) ≈ 2.83
        avg_corr = np.mean(correlations) if correlations else 0
        violation = 2.0 + avg_corr * 0.83
        
        return min(violation, 2.83)
    
    def _calculate_base_power(self, seed_7d: np.ndarray, rarity: ArtifactRarity) -> float:
        """Calcule la puissance de base via le poly-spinor"""
        # Produit tensoriel des composantes
        tensor_product = 1.0
        for i in range(7):
            for j in range(i + 1, 7):
                tensor_product += abs(seed_7d[i] * seed_7d[j])
        
        # Puissance de base selon la rarete
        base_ranges = {
            ArtifactRarity.COMMON: (10, 50),
            ArtifactRarity.UNCOMMON: (40, 120),
            ArtifactRarity.RARE: (100, 300),
            ArtifactRarity.EPIC: (250, 600),
            ArtifactRarity.LEGENDARY: (500, 1200),
            ArtifactRarity.MYTHIC: (1000, 3000),
            ArtifactRarity.TRANSCENDENT: (2500, 7000),
            ArtifactRarity.PRIMORDIAL: (5000, 15000),
        }
        
        min_p, max_p = base_ranges.get(rarity, (10, 50))
        power = min_p + (max_p - min_p) * tensor_product
        
        # Bonus d'entropie
        entropy_bonus = self._next_random_float() * 0.5 + 0.75
        
        return power * entropy_bonus
    
    def _generate_stats(self, seed_7d: np.ndarray, rarity: ArtifactRarity) -> ArtifactStats:
        """Genere les statistiques completes"""
        base_power = self._calculate_base_power(seed_7d, rarity)
        
        # Resonance spinoriale basee sur la coherence du seed
        coherence = np.std(seed_7d) * 100
        resonance = min(100, coherence + self._next_random(30))
        
        # Coefficient d'entropie
        entropy_coef = 0.5 + self._next_random_float() * 2.0
        
        # Affinite dimensionnelle (0-7)
        dim_affinity = np.argmax(np.abs(seed_7d)) + self._next_random_float()
        
        # Stats secondaires
        stability = 50 + self._next_random(50)
        purity = 30 + self._next_random(70)
        quantum_coherence = 20 + self._next_random(80)
        
        stats = ArtifactStats(
            base_power=round(base_power, 2),
            spinor_resonance=round(resonance, 2),
            entropy_coefficient=round(entropy_coef, 3),
            dimensional_affinity=round(dim_affinity, 2),
            stability=stability,
            purity=purity,
            coherence=quantum_coherence
        )
        
        # Calcule la puissance effective
        rarity_mult = RARITY_MULTIPLIERS.get(rarity, 1.0)
        stats.calculate_effective_power(rarity_mult)
        
        return stats
    
    def _select_element(self, seed_7d: np.ndarray) -> ElementalAffinity:
        """Selectionne l'element basé sur la dimension dominante"""
        dominant_dim = np.argmax(np.abs(seed_7d))
        elements = list(ElementalAffinity)
        
        # La dimension dominante determine l'element principal
        # avec une chance de variation
        if self._next_random(100) < 75:
            return elements[dominant_dim]
        else:
            return elements[self._next_random(len(elements))]
    
    def _select_artifact_type(self, rarity: ArtifactRarity) -> ArtifactType:
        """Selectionne le type d'artefact"""
        types = list(ArtifactType)
        
        # Certains types sont plus rares
        rare_types = [ArtifactType.NEXUS_CORE, ArtifactType.VOID_SHARD]
        
        if rarity in [ArtifactRarity.PRIMORDIAL, ArtifactRarity.TRANSCENDENT]:
            if self._next_random(100) < 40:
                return rare_types[self._next_random(len(rare_types))]
        
        return types[self._next_random(len(types))]
    
    def _generate_abilities(self, rarity: ArtifactRarity) -> List[Dict[str, Any]]:
        """Genere les capacites speciales selon la rarete"""
        abilities = []
        
        # Nombre de capacites selon la rarete
        ability_counts = {
            ArtifactRarity.COMMON: 1,
            ArtifactRarity.UNCOMMON: 1,
            ArtifactRarity.RARE: 2,
            ArtifactRarity.EPIC: 2,
            ArtifactRarity.LEGENDARY: 3,
            ArtifactRarity.MYTHIC: 3,
            ArtifactRarity.TRANSCENDENT: 4,
            ArtifactRarity.PRIMORDIAL: 5,
        }
        
        num_abilities = ability_counts.get(rarity, 1)
        
        # Filtre les capacites disponibles pour cette rarete
        rarity_order = list(ArtifactRarity)
        rarity_index = rarity_order.index(rarity)
        
        available = []
        for key, ability in SPECIAL_ABILITIES.items():
            min_rarity_index = rarity_order.index(ability["min_rarity"])
            if min_rarity_index <= rarity_index:
                available.append((key, ability))
        
        # Selectionne les capacites
        selected_keys = set()
        for _ in range(min(num_abilities, len(available))):
            attempts = 0
            while attempts < 10:
                idx = self._next_random(len(available))
                key, ability = available[idx]
                if key not in selected_keys:
                    selected_keys.add(key)
                    
                    # Genere la valeur
                    min_val, max_val = ability["value_range"]
                    if isinstance(min_val, float):
                        value = min_val + self._next_random_float() * (max_val - min_val)
                        value = round(value, 2)
                    else:
                        value = min_val + self._next_random(max_val - min_val + 1)
                    
                    abilities.append({
                        "id": key,
                        "name": ability["name"],
                        "description": ability["description"].format(value=value),
                        "value": value
                    })
                    break
                attempts += 1
        
        return abilities
    
    def _generate_name(self, artifact_type: ArtifactType, rarity: ArtifactRarity, 
                       element: ElementalAffinity) -> str:
        """Genere un nom procedural"""
        prefix = self.PREFIXES[self._next_random(len(self.PREFIXES))]
        core = self.CORE_NAMES[artifact_type][self._next_random(5)]
        
        # Les raretes hautes ont des suffixes
        if rarity in [ArtifactRarity.LEGENDARY, ArtifactRarity.MYTHIC, 
                      ArtifactRarity.TRANSCENDENT, ArtifactRarity.PRIMORDIAL]:
            suffix = self.SUFFIXES[self._next_random(len(self.SUFFIXES))]
            return f"{prefix} {core} {suffix}"
        else:
            return f"{prefix} {core}"
    
    def _generate_lore(self, element: ElementalAffinity, abilities: List[Dict], 
                       stats: ArtifactStats) -> str:
        """Genere le lore de l'artefact"""
        template = self.LORE_TEMPLATES[self._next_random(len(self.LORE_TEMPLATES))]
        
        ability_name = abilities[0]["name"] if abilities else "puissance inconnue"
        rating = "incommensurable" if stats.effective_power > 5000 else "considerable"
        dimension = int(stats.dimensional_affinity) + 1
        
        lore = template.format(
            element=element.value.capitalize(),
            ability=ability_name,
            rating=rating,
            dimension=dimension
        )
        
        return lore
    
    def generate(self, genesis_block_id: Optional[str] = None, 
                 vault_number: Optional[int] = None,
                 force_rarity: Optional[ArtifactRarity] = None) -> SpinorArtifact:
        """
        Genere un artefact spinoriel complet.
        
        Args:
            genesis_block_id: ID du bloc genesis associe
            vault_number: Numero du vault
            force_rarity: Force une rarete specifique (pour tests)
        
        Returns:
            SpinorArtifact complet avec toutes ses caracteristiques
        """
        # Tire la rarete
        rarity = force_rarity or self._roll_rarity()
        
        # Genere le seed spinoriel 7D
        seed_7d = self._generate_spinor_seed()
        
        # Calcule le spineur de Dirac
        dirac = self._compute_dirac_spinor(seed_7d)
        
        # Determine l'element et le type
        element = self._select_element(seed_7d)
        artifact_type = self._select_artifact_type(rarity)
        
        # Genere les stats
        stats = self._generate_stats(seed_7d, rarity)
        
        # Genere les capacites
        abilities = self._generate_abilities(rarity)
        
        # Genere le nom
        name = self._generate_name(artifact_type, rarity, element)
        
        # Signature spinorielle
        signature = SpinorSignature(
            seed_7d=seed_7d.tolist(),
            dirac_components=[float(x.real) for x in dirac],
            bell_violation=self._compute_bell_violation(dirac),
            entanglement_degree=float(np.mean(np.abs(dirac))),
            quantum_state=hashlib.sha256(dirac.tobytes()).hexdigest()[:16]
        )
        
        # Genere les 7 glyphes avec 21 gemmes (poly-spinor optimise)
        glyph_array = None
        try:
            from core.glyph_gem_system import PolySpinorGlyphGenerator
            glyph_generator = PolySpinorGlyphGenerator(self.vault_seed)
            array = glyph_generator.generate_glyph_array()
            glyph_array = array.to_dict()
            
            # Ajoute la puissance des glyphes aux stats
            stats.base_power += array.total_power * 0.1
            stats.calculate_effective_power(RARITY_MULTIPLIERS.get(rarity, 1.0))
        except ImportError:
            try:
                from glyph_gem_system import PolySpinorGlyphGenerator
                glyph_generator = PolySpinorGlyphGenerator(self.vault_seed)
                array = glyph_generator.generate_glyph_array()
                glyph_array = array.to_dict()
                stats.base_power += array.total_power * 0.1
                stats.calculate_effective_power(RARITY_MULTIPLIERS.get(rarity, 1.0))
            except ImportError:
                pass  # Glyph system not available
        
        # Genere le lore
        lore = self._generate_lore(element, abilities, stats)
        
        # Cree l'artefact
        artifact_id = hashlib.sha256(
            f"{name}{datetime.now().isoformat()}{secrets.token_hex(8)}".encode()
        ).hexdigest()[:16]
        
        artifact = SpinorArtifact(
            artifact_id=artifact_id,
            name=name,
            artifact_type=artifact_type,
            rarity=rarity,
            created_at=datetime.now().isoformat(),
            genesis_block_id=genesis_block_id,
            vault_number=vault_number,
            element=element,
            stats=stats,
            signature=signature,
            abilities=abilities,
            glyph_array=glyph_array,
            description=f"{rarity.value.upper()} {artifact_type.value.replace('_', ' ').title()}",
            lore=lore
        )
        
        return artifact
    
    def generate_batch(self, count: int, **kwargs) -> List[SpinorArtifact]:
        """Genere plusieurs artefacts"""
        return [self.generate(**kwargs) for _ in range(count)]


# ============================================================================
# UTILITAIRES D'AFFICHAGE
# ============================================================================

def format_artifact_display(artifact: SpinorArtifact) -> str:
    """Formate l'affichage d'un artefact"""
    lines = []
    
    # Header
    rarity_color = RARITY_COLORS[artifact.rarity]
    lines.append(f"\n{'='*60}")
    lines.append(f"  {artifact.get_display_name()}")
    lines.append(f"  [{artifact.rarity.value.upper()}] {artifact.description}")
    lines.append(f"{'='*60}")
    
    # Stats
    if artifact.stats:
        lines.append(f"\n  STATISTIQUES:")
        lines.append(f"    Puissance: {artifact.stats.effective_power:.0f} {artifact.get_power_rating()}")
        lines.append(f"    Resonance Spinoriale: {artifact.stats.spinor_resonance:.1f}%")
        lines.append(f"    Coefficient Entropie: {artifact.stats.entropy_coefficient:.2f}x")
        lines.append(f"    Affinite Dim.: D{int(artifact.stats.dimensional_affinity)+1}")
        lines.append(f"    Stabilite: {artifact.stats.stability}%")
        lines.append(f"    Purete: {artifact.stats.purity}%")
        lines.append(f"    Coherence: {artifact.stats.coherence}%")
    
    # Element
    lines.append(f"\n  ELEMENT: {artifact.element_symbol} {artifact.element.value.upper()}")
    
    # Signature spinorielle
    if artifact.signature:
        lines.append(f"\n  SIGNATURE SPINORIELLE:")
        lines.append(f"    Violation Bell: {artifact.signature.bell_violation:.3f}")
        lines.append(f"    Intrication: {artifact.signature.entanglement_degree:.3f}")
        lines.append(f"    Etat Quantique: {artifact.signature.quantum_state}")
    
    # Capacites
    if artifact.abilities:
        lines.append(f"\n  CAPACITES SPECIALES:")
        for ability in artifact.abilities:
            lines.append(f"    * {ability['name']}: {ability['description']}")
    
    # Lore
    if artifact.lore:
        lines.append(f"\n  LORE:")
        lines.append(f"    \"{artifact.lore}\"")
    
    lines.append(f"\n{'='*60}\n")
    
    return "\n".join(lines)


def format_artifact_compact(artifact: SpinorArtifact) -> str:
    """Format compact pour les listes"""
    power = artifact.stats.effective_power if artifact.stats else 0
    return (f"{artifact.emoji} [{artifact.rarity.value[:4].upper()}] "
            f"{artifact.name} | {artifact.element_symbol} | "
            f"PWR:{power:.0f} {artifact.get_power_rating()}")


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  SPINOR ARTIFACT GENERATOR - Eidolon")
    print("="*70)
    
    # Cree un generateur avec un seed aleatoire
    generator = SpinorArtifactGenerator()
    
    # Genere des artefacts de test
    print("\n[+] Generation de 10 artefacts aleatoires...\n")
    
    artifacts = generator.generate_batch(10)
    
    # Affiche les stats de distribution
    rarity_count = {}
    for art in artifacts:
        rarity_count[art.rarity.value] = rarity_count.get(art.rarity.value, 0) + 1
    
    print("  Distribution des raretes:")
    for rarity in ArtifactRarity:
        count = rarity_count.get(rarity.value, 0)
        bar = "#" * count
        print(f"    {rarity.value:15} : {bar} ({count})")
    
    # Affiche quelques artefacts
    print("\n[+] Exemples d'artefacts generes:\n")
    
    for art in sorted(artifacts, key=lambda x: RARITY_MULTIPLIERS[x.rarity], reverse=True)[:3]:
        print(format_artifact_display(art))
    
    # Genere un artefact legendaire force
    print("\n[+] Artefact LEGENDARY force:\n")
    legendary = generator.generate(force_rarity=ArtifactRarity.LEGENDARY)
    print(format_artifact_display(legendary))
    
    # Genere un artefact primordial
    print("\n[+] Artefact PRIMORDIAL force:\n")
    primordial = generator.generate(force_rarity=ArtifactRarity.PRIMORDIAL)
    print(format_artifact_display(primordial))
