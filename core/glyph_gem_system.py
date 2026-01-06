"""
Systeme de Glyphes et Gemmes Spinorielles
==========================================

Chaque artefact possede 7 Glyphes dimensionnels
Chaque Glyphe est enchasse de 3 Gemmes
Total: 21 Gemmes par artefact

Generation optimisee par chiffrement Poly-Spinor 7D
pour une entropie maximale dans le RNG.
"""

import sys
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
# TYPES DE GEMMES
# ============================================================================

class GemType(Enum):
    """Types de gemmes avec proprietes elementaires"""
    # Gemmes primaires (haute puissance)
    VOID_CRYSTAL = "void_crystal"           # Cristal du Vide
    QUANTUM_SHARD = "quantum_shard"         # Eclat Quantique
    TEMPORAL_ESSENCE = "temporal_essence"   # Essence Temporelle
    SPATIAL_PRISM = "spatial_prism"         # Prisme Spatial
    ENTROPIC_CORE = "entropic_core"         # Coeur Entropique
    HARMONIC_GEM = "harmonic_gem"           # Gemme Harmonique
    CELESTIAL_TEAR = "celestial_tear"       # Larme Celeste
    
    # Gemmes secondaires (bonus specifiques)
    SPINOR_FRAGMENT = "spinor_fragment"     # Fragment Spinoriel
    BELL_RESONATOR = "bell_resonator"       # Resonateur de Bell
    DIRAC_PEARL = "dirac_pearl"             # Perle de Dirac
    CLIFFORD_STONE = "clifford_stone"       # Pierre de Clifford
    MERKLE_RUBY = "merkle_ruby"             # Rubis de Merkle
    ENTROPY_SAPPHIRE = "entropy_sapphire"   # Saphir d'Entropie
    NEXUS_EMERALD = "nexus_emerald"         # Emeraude du Nexus


class GemRarity(Enum):
    """Rarete des gemmes"""
    FLAWED = "flawed"           # 30% - Defectueuse
    STANDARD = "standard"       # 35% - Standard
    POLISHED = "polished"       # 20% - Polie
    PRISTINE = "pristine"       # 10% - Pristine
    PERFECT = "perfect"         # 4% - Parfaite
    TRANSCENDENT = "transcendent"  # 1% - Transcendante


GEM_RARITY_WEIGHTS = {
    GemRarity.FLAWED: 3000,
    GemRarity.STANDARD: 3500,
    GemRarity.POLISHED: 2000,
    GemRarity.PRISTINE: 1000,
    GemRarity.PERFECT: 400,
    GemRarity.TRANSCENDENT: 100,
}

GEM_RARITY_MULTIPLIERS = {
    GemRarity.FLAWED: 0.5,
    GemRarity.STANDARD: 1.0,
    GemRarity.POLISHED: 1.5,
    GemRarity.PRISTINE: 2.5,
    GemRarity.PERFECT: 4.0,
    GemRarity.TRANSCENDENT: 8.0,
}

GEM_COLORS = {
    GemType.VOID_CRYSTAL: "#1a0033",
    GemType.QUANTUM_SHARD: "#00ff88",
    GemType.TEMPORAL_ESSENCE: "#ffaa00",
    GemType.SPATIAL_PRISM: "#00aaff",
    GemType.ENTROPIC_CORE: "#ff3366",
    GemType.HARMONIC_GEM: "#aa55ff",
    GemType.CELESTIAL_TEAR: "#ffffaa",
    GemType.SPINOR_FRAGMENT: "#ff00ff",
    GemType.BELL_RESONATOR: "#00ffff",
    GemType.DIRAC_PEARL: "#ffffff",
    GemType.CLIFFORD_STONE: "#8b4513",
    GemType.MERKLE_RUBY: "#dc143c",
    GemType.ENTROPY_SAPPHIRE: "#0000cd",
    GemType.NEXUS_EMERALD: "#00ff00",
}

GEM_SYMBOLS = {
    GemType.VOID_CRYSTAL: "◆",
    GemType.QUANTUM_SHARD: "◇",
    GemType.TEMPORAL_ESSENCE: "◈",
    GemType.SPATIAL_PRISM: "◊",
    GemType.ENTROPIC_CORE: "●",
    GemType.HARMONIC_GEM: "○",
    GemType.CELESTIAL_TEAR: "✧",
    GemType.SPINOR_FRAGMENT: "⬡",
    GemType.BELL_RESONATOR: "⬢",
    GemType.DIRAC_PEARL: "◉",
    GemType.CLIFFORD_STONE: "▣",
    GemType.MERKLE_RUBY: "♦",
    GemType.ENTROPY_SAPPHIRE: "♢",
    GemType.NEXUS_EMERALD: "❖",
}


# ============================================================================
# TYPES DE GLYPHES
# ============================================================================

class GlyphType(Enum):
    """Types de glyphes correspondant aux 7 dimensions"""
    GLYPH_VOID = "glyph_void"           # Dimension 0 - Glyphe du Vide
    GLYPH_QUANTUM = "glyph_quantum"     # Dimension 1 - Glyphe Quantique
    GLYPH_TEMPORAL = "glyph_temporal"   # Dimension 2 - Glyphe Temporel
    GLYPH_SPATIAL = "glyph_spatial"     # Dimension 3 - Glyphe Spatial
    GLYPH_ENTROPIC = "glyph_entropic"   # Dimension 4 - Glyphe Entropique
    GLYPH_HARMONIC = "glyph_harmonic"   # Dimension 5 - Glyphe Harmonique
    GLYPH_CELESTIAL = "glyph_celestial" # Dimension 6 - Glyphe Celeste


GLYPH_SYMBOLS = {
    GlyphType.GLYPH_VOID: "ᛟ",      # Othala - Heritage
    GlyphType.GLYPH_QUANTUM: "ᚠ",   # Fehu - Creation
    GlyphType.GLYPH_TEMPORAL: "ᛞ",  # Dagaz - Jour/Cycle
    GlyphType.GLYPH_SPATIAL: "ᚱ",   # Raidho - Voyage
    GlyphType.GLYPH_ENTROPIC: "ᚺ",  # Hagalaz - Chaos
    GlyphType.GLYPH_HARMONIC: "ᚹ",  # Wunjo - Harmonie
    GlyphType.GLYPH_CELESTIAL: "ᛊ", # Sowilo - Soleil
}

GLYPH_NAMES = {
    GlyphType.GLYPH_VOID: "Othala - Glyphe du Vide",
    GlyphType.GLYPH_QUANTUM: "Fehu - Glyphe Quantique",
    GlyphType.GLYPH_TEMPORAL: "Dagaz - Glyphe Temporel",
    GlyphType.GLYPH_SPATIAL: "Raidho - Glyphe Spatial",
    GlyphType.GLYPH_ENTROPIC: "Hagalaz - Glyphe Entropique",
    GlyphType.GLYPH_HARMONIC: "Wunjo - Glyphe Harmonique",
    GlyphType.GLYPH_CELESTIAL: "Sowilo - Glyphe Celeste",
}

GLYPH_BONUSES = {
    GlyphType.GLYPH_VOID: {"void_power": 1.5, "stability": 10},
    GlyphType.GLYPH_QUANTUM: {"quantum_resonance": 1.5, "entropy": 15},
    GlyphType.GLYPH_TEMPORAL: {"temporal_flux": 1.5, "duration": 20},
    GlyphType.GLYPH_SPATIAL: {"spatial_range": 1.5, "reach": 25},
    GlyphType.GLYPH_ENTROPIC: {"chaos_power": 2.0, "variance": 30},
    GlyphType.GLYPH_HARMONIC: {"harmony_bonus": 1.5, "synergy": 20},
    GlyphType.GLYPH_CELESTIAL: {"celestial_light": 2.0, "purity": 25},
}


# ============================================================================
# STRUCTURES DE DONNEES
# ============================================================================

@dataclass
class SpinorGem:
    """Gemme spinorielle avec proprietes cryptographiques"""
    gem_id: str
    gem_type: GemType
    rarity: GemRarity
    
    # Proprietes de puissance
    base_power: float
    resonance: float
    purity: float
    
    # Signature spinorielle
    spinor_hash: str
    entropy_bits: int
    dimension_affinity: int  # 0-6
    
    # Bonus
    power_multiplier: float = 1.0
    special_effect: Optional[str] = None
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['gem_type'] = self.gem_type.value
        d['rarity'] = self.rarity.value
        return d
    
    @classmethod
    def from_dict(cls, data: dict) -> "SpinorGem":
        data['gem_type'] = GemType(data['gem_type'])
        data['rarity'] = GemRarity(data['rarity'])
        return cls(**data)
    
    @property
    def effective_power(self) -> float:
        return self.base_power * self.power_multiplier * GEM_RARITY_MULTIPLIERS[self.rarity]
    
    @property
    def symbol(self) -> str:
        return GEM_SYMBOLS.get(self.gem_type, "?")
    
    @property
    def color(self) -> str:
        return GEM_COLORS.get(self.gem_type, "#ffffff")


@dataclass
class DimensionalGlyph:
    """Glyphe dimensionnel avec 3 gemmes enchassees"""
    glyph_id: str
    glyph_type: GlyphType
    dimension: int  # 0-6
    
    # Les 3 gemmes enchassees
    gems: List[SpinorGem] = field(default_factory=list)
    
    # Proprietes du glyphe
    activation_level: float = 0.0  # 0-100%
    resonance_frequency: float = 0.0
    dimensional_stability: float = 0.0
    
    # Signature
    glyph_hash: str = ""
    spinor_signature: List[float] = field(default_factory=list)
    
    # Bonus combines
    total_power: float = 0.0
    synergy_bonus: float = 1.0
    
    def to_dict(self) -> dict:
        d = {
            'glyph_id': self.glyph_id,
            'glyph_type': self.glyph_type.value,
            'dimension': self.dimension,
            'gems': [g.to_dict() for g in self.gems],
            'activation_level': self.activation_level,
            'resonance_frequency': self.resonance_frequency,
            'dimensional_stability': self.dimensional_stability,
            'glyph_hash': self.glyph_hash,
            'spinor_signature': self.spinor_signature,
            'total_power': self.total_power,
            'synergy_bonus': self.synergy_bonus,
        }
        return d
    
    @classmethod
    def from_dict(cls, data: dict) -> "DimensionalGlyph":
        data['glyph_type'] = GlyphType(data['glyph_type'])
        data['gems'] = [SpinorGem.from_dict(g) for g in data.get('gems', [])]
        return cls(**data)
    
    @property
    def symbol(self) -> str:
        return GLYPH_SYMBOLS.get(self.glyph_type, "?")
    
    @property
    def name(self) -> str:
        return GLYPH_NAMES.get(self.glyph_type, "Unknown Glyph")
    
    @property
    def gem_symbols(self) -> str:
        return "".join(g.symbol for g in self.gems)
    
    def calculate_total_power(self):
        """Calcule la puissance totale du glyphe"""
        if not self.gems:
            return 0.0
        
        # Somme des puissances des gemmes
        gem_power = sum(g.effective_power for g in self.gems)
        
        # Bonus de synergie si les 3 gemmes sont de meme rarete
        rarities = [g.rarity for g in self.gems]
        if len(set(rarities)) == 1:
            self.synergy_bonus = 1.5
        elif rarities.count(rarities[0]) >= 2:
            self.synergy_bonus = 1.2
        else:
            self.synergy_bonus = 1.0
        
        self.total_power = gem_power * self.synergy_bonus
        return self.total_power


@dataclass
class GlyphArray:
    """Ensemble des 7 glyphes d'un artefact"""
    array_id: str
    glyphs: List[DimensionalGlyph] = field(default_factory=list)
    
    # Stats globales
    total_gems: int = 0
    total_power: float = 0.0
    average_resonance: float = 0.0
    dimensional_balance: float = 0.0  # 0-100%
    
    # Signature poly-spinorielle
    poly_spinor_hash: str = ""
    bell_correlation: float = 0.0
    entanglement_degree: float = 0.0
    
    # Bonus d'ensemble
    set_bonus: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'array_id': self.array_id,
            'glyphs': [g.to_dict() for g in self.glyphs],
            'total_gems': self.total_gems,
            'total_power': self.total_power,
            'average_resonance': self.average_resonance,
            'dimensional_balance': self.dimensional_balance,
            'poly_spinor_hash': self.poly_spinor_hash,
            'bell_correlation': self.bell_correlation,
            'entanglement_degree': self.entanglement_degree,
            'set_bonus': self.set_bonus,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "GlyphArray":
        data['glyphs'] = [DimensionalGlyph.from_dict(g) for g in data.get('glyphs', [])]
        return cls(**data)
    
    def calculate_stats(self):
        """Calcule toutes les statistiques de l'array"""
        if not self.glyphs:
            return
        
        # Total gems
        self.total_gems = sum(len(g.gems) for g in self.glyphs)
        
        # Total power
        for glyph in self.glyphs:
            glyph.calculate_total_power()
        self.total_power = sum(g.total_power for g in self.glyphs)
        
        # Average resonance
        all_gems = [gem for glyph in self.glyphs for gem in glyph.gems]
        if all_gems:
            self.average_resonance = sum(g.resonance for g in all_gems) / len(all_gems)
        
        # Dimensional balance (toutes les dimensions representees = 100%)
        dimensions = set(g.dimension for g in self.glyphs)
        self.dimensional_balance = (len(dimensions) / 7) * 100
        
        # Set bonus
        self._calculate_set_bonus()
    
    def _calculate_set_bonus(self):
        """Calcule les bonus d'ensemble"""
        self.set_bonus = {}
        
        # Bonus si les 7 dimensions sont presentes
        if len(self.glyphs) == 7:
            self.set_bonus["complete_array"] = 2.0
            self.set_bonus["dimensional_mastery"] = 1.5
        
        # Bonus par type de gemme majoritaire
        gem_types = [gem.gem_type for glyph in self.glyphs for gem in glyph.gems]
        if gem_types:
            from collections import Counter
            most_common = Counter(gem_types).most_common(1)[0]
            if most_common[1] >= 5:
                self.set_bonus[f"{most_common[0].value}_affinity"] = 1.3


# ============================================================================
# GENERATEUR POLY-SPINORIAL
# ============================================================================

class PolySpinorGlyphGenerator:
    """
    Generateur de glyphes et gemmes utilisant le chiffrement Poly-Spinor 7D
    pour maximiser l'entropie RNG.
    """
    
    def __init__(self, master_seed: bytes = None):
        """
        Args:
            master_seed: Seed maitre pour le RNG cryptographique
        """
        self.master_seed = master_seed or secrets.token_bytes(64)
        self._initialize_spinor_state()
    
    def _initialize_spinor_state(self):
        """Initialise l'etat spinoriel 7D"""
        # Derive 7 seeds independants pour chaque dimension
        self.dimension_seeds = []
        for i in range(7):
            seed = hashlib.sha512(
                self.master_seed + f"DIM_{i}".encode() + secrets.token_bytes(16)
            ).digest()
            self.dimension_seeds.append(seed)
        
        # Etat RNG principal
        self._rng_state = hashlib.sha512(self.master_seed).digest()
        
        # Matrices de Clifford Cl(0,7) simplifiees
        self._clifford_matrices = self._generate_clifford_basis()
        
        # Compteur d'entropie
        self._entropy_consumed = 0
    
    def _generate_clifford_basis(self) -> List[np.ndarray]:
        """Genere les 7 matrices de base de Clifford"""
        matrices = []
        
        # Matrices de Pauli
        sigma_x = np.array([[0, 1], [1, 0]], dtype=complex)
        sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        sigma_z = np.array([[1, 0], [0, -1]], dtype=complex)
        identity = np.eye(2, dtype=complex)
        
        # Genere les 7 matrices gamma
        paulis = [sigma_x, sigma_y, sigma_z]
        for i in range(7):
            # Produit tensoriel pour construire les gamma
            gamma = np.eye(1, dtype=complex)
            for j in range(3):
                if j < i % 3:
                    gamma = np.kron(gamma, sigma_z)
                elif j == i % 3:
                    gamma = np.kron(gamma, paulis[i % 3])
                else:
                    gamma = np.kron(gamma, identity)
            
            # Redimensionner a 8x8
            if gamma.shape[0] < 8:
                padded = np.zeros((8, 8), dtype=complex)
                padded[:gamma.shape[0], :gamma.shape[1]] = gamma
                gamma = padded
            
            matrices.append(gamma[:8, :8])
        
        return matrices
    
    def _spinor_rng(self, dimension: int = 0) -> Tuple[float, bytes]:
        """
        Genere un nombre aleatoire via transformation spinorielle.
        Retourne (valeur float 0-1, bytes d'entropie)
        """
        # Melange l'etat avec le seed dimensionnel
        mixed = hashlib.sha512(
            self._rng_state + 
            self.dimension_seeds[dimension % 7] +
            secrets.token_bytes(8)
        ).digest()
        
        # Applique la transformation de Clifford
        state_vector = np.frombuffer(mixed[:64], dtype=np.float64)
        state_vector = state_vector / (np.linalg.norm(state_vector) + 1e-10)
        
        # Transforme via la matrice gamma
        gamma = self._clifford_matrices[dimension % 7]
        transformed = np.real(gamma @ state_vector[:8])
        
        # Nouvelle entropie
        new_entropy = hashlib.sha512(transformed.tobytes() + mixed).digest()
        
        # Met a jour l'etat
        self._rng_state = new_entropy
        self._entropy_consumed += 512
        
        # Valeur finale
        value = int.from_bytes(new_entropy[:8], 'big') / (2**64)
        
        return value, new_entropy[:32]
    
    def _spinor_random_int(self, max_val: int, dimension: int = 0) -> int:
        """Genere un entier aleatoire spinoriel"""
        val, _ = self._spinor_rng(dimension)
        return int(val * max_val)
    
    def _roll_gem_rarity(self, dimension: int) -> GemRarity:
        """Tire une rarete de gemme avec RNG spinoriel"""
        total = sum(GEM_RARITY_WEIGHTS.values())
        roll = self._spinor_random_int(total, dimension)
        
        cumulative = 0
        for rarity, weight in GEM_RARITY_WEIGHTS.items():
            cumulative += weight
            if roll < cumulative:
                return rarity
        
        return GemRarity.STANDARD
    
    def _select_gem_type(self, dimension: int, glyph_type: GlyphType) -> GemType:
        """Selectionne un type de gemme avec affinite dimensionnelle"""
        # Types primaires lies aux dimensions
        primary_types = [
            GemType.VOID_CRYSTAL,
            GemType.QUANTUM_SHARD,
            GemType.TEMPORAL_ESSENCE,
            GemType.SPATIAL_PRISM,
            GemType.ENTROPIC_CORE,
            GemType.HARMONIC_GEM,
            GemType.CELESTIAL_TEAR,
        ]
        
        # Types secondaires
        secondary_types = [
            GemType.SPINOR_FRAGMENT,
            GemType.BELL_RESONATOR,
            GemType.DIRAC_PEARL,
            GemType.CLIFFORD_STONE,
            GemType.MERKLE_RUBY,
            GemType.ENTROPY_SAPPHIRE,
            GemType.NEXUS_EMERALD,
        ]
        
        # 70% chance de gemme primaire alignee, 30% secondaire
        roll = self._spinor_random_int(100, dimension)
        
        if roll < 50:
            # Gemme primaire alignee avec la dimension
            return primary_types[dimension % 7]
        elif roll < 70:
            # Gemme primaire aleatoire
            idx = self._spinor_random_int(len(primary_types), dimension)
            return primary_types[idx]
        else:
            # Gemme secondaire
            idx = self._spinor_random_int(len(secondary_types), dimension)
            return secondary_types[idx]
    
    def generate_gem(self, dimension: int, glyph_type: GlyphType) -> SpinorGem:
        """Genere une gemme spinorielle"""
        # Type et rarete
        gem_type = self._select_gem_type(dimension, glyph_type)
        rarity = self._roll_gem_rarity(dimension)
        
        # Puissance de base (10-1000 selon rarete)
        base_ranges = {
            GemRarity.FLAWED: (10, 50),
            GemRarity.STANDARD: (40, 150),
            GemRarity.POLISHED: (100, 400),
            GemRarity.PRISTINE: (300, 800),
            GemRarity.PERFECT: (600, 1500),
            GemRarity.TRANSCENDENT: (1200, 3000),
        }
        min_p, max_p = base_ranges[rarity]
        val, entropy = self._spinor_rng(dimension)
        base_power = min_p + val * (max_p - min_p)
        
        # Resonance (0-100)
        res_val, _ = self._spinor_rng(dimension)
        resonance = res_val * 100
        
        # Purete (0-100)
        pur_val, _ = self._spinor_rng(dimension)
        purity = 30 + pur_val * 70
        
        # Hash spinoriel
        spinor_hash = hashlib.sha256(entropy).hexdigest()[:16]
        
        # Effet special (rare)
        special_effect = None
        if rarity in [GemRarity.PERFECT, GemRarity.TRANSCENDENT]:
            effects = [
                "entropy_amplifier",
                "dimensional_pierce",
                "quantum_echo",
                "temporal_lock",
                "void_absorption",
                "celestial_radiance",
                "harmonic_cascade",
            ]
            effect_roll = self._spinor_random_int(100, dimension)
            if effect_roll < 30:
                special_effect = effects[self._spinor_random_int(len(effects), dimension)]
        
        # ID unique
        gem_id = hashlib.sha256(
            f"{gem_type.value}{rarity.value}{datetime.now().isoformat()}{secrets.token_hex(4)}".encode()
        ).hexdigest()[:12]
        
        return SpinorGem(
            gem_id=gem_id,
            gem_type=gem_type,
            rarity=rarity,
            base_power=round(base_power, 2),
            resonance=round(resonance, 2),
            purity=round(purity, 2),
            spinor_hash=spinor_hash,
            entropy_bits=512,
            dimension_affinity=dimension,
            power_multiplier=1.0 + (resonance / 200),
            special_effect=special_effect
        )
    
    def generate_glyph(self, dimension: int) -> DimensionalGlyph:
        """Genere un glyphe dimensionnel avec 3 gemmes"""
        glyph_types = list(GlyphType)
        glyph_type = glyph_types[dimension % 7]
        
        # Genere les 3 gemmes
        gems = []
        for i in range(3):
            gem = self.generate_gem(dimension, glyph_type)
            gems.append(gem)
        
        # Calcule les proprietes du glyphe
        val1, _ = self._spinor_rng(dimension)
        val2, _ = self._spinor_rng(dimension)
        val3, entropy = self._spinor_rng(dimension)
        
        activation_level = val1 * 100
        resonance_frequency = 100 + val2 * 900  # 100-1000 Hz
        dimensional_stability = 50 + val3 * 50  # 50-100%
        
        # Signature spinorielle (7 composantes)
        spinor_signature = []
        for i in range(7):
            comp, _ = self._spinor_rng(dimension)
            spinor_signature.append(round(comp * 2 - 1, 4))  # -1 to 1
        
        # Hash du glyphe
        glyph_hash = hashlib.sha256(
            entropy + json.dumps([g.to_dict() for g in gems], sort_keys=True).encode()
        ).hexdigest()[:16]
        
        # ID unique
        glyph_id = f"glyph_{dimension}_{secrets.token_hex(6)}"
        
        glyph = DimensionalGlyph(
            glyph_id=glyph_id,
            glyph_type=glyph_type,
            dimension=dimension,
            gems=gems,
            activation_level=round(activation_level, 2),
            resonance_frequency=round(resonance_frequency, 2),
            dimensional_stability=round(dimensional_stability, 2),
            glyph_hash=glyph_hash,
            spinor_signature=spinor_signature
        )
        
        glyph.calculate_total_power()
        
        return glyph
    
    def generate_glyph_array(self) -> GlyphArray:
        """Genere un array complet de 7 glyphes (21 gemmes)"""
        array_id = f"array_{secrets.token_hex(8)}"
        
        # Genere les 7 glyphes
        glyphs = []
        for dimension in range(7):
            glyph = self.generate_glyph(dimension)
            glyphs.append(glyph)
        
        # Calcule le hash poly-spinoriel
        all_hashes = "".join(g.glyph_hash for g in glyphs)
        poly_spinor_hash = hashlib.sha512(all_hashes.encode()).hexdigest()[:32]
        
        # Correlation de Bell (mesure d'intrication)
        bell_val, _ = self._spinor_rng(0)
        bell_correlation = 2.0 + bell_val * 0.83  # 2.0 to 2.83 (max violation)
        
        # Degre d'intrication
        entanglement_val, _ = self._spinor_rng(0)
        entanglement_degree = entanglement_val
        
        array = GlyphArray(
            array_id=array_id,
            glyphs=glyphs,
            poly_spinor_hash=poly_spinor_hash,
            bell_correlation=round(bell_correlation, 4),
            entanglement_degree=round(entanglement_degree, 4)
        )
        
        array.calculate_stats()
        
        return array
    
    def get_entropy_consumed(self) -> int:
        """Retourne le nombre de bits d'entropie consommes"""
        return self._entropy_consumed


# ============================================================================
# AFFICHAGE
# ============================================================================

def format_gem_display(gem: SpinorGem) -> str:
    """Formate l'affichage d'une gemme"""
    return (f"{gem.symbol} [{gem.rarity.value.upper()[:4]}] {gem.gem_type.value.replace('_', ' ').title()} "
            f"| PWR:{gem.effective_power:.0f} | RES:{gem.resonance:.0f}% | PUR:{gem.purity:.0f}%"
            f"{' | ' + gem.special_effect if gem.special_effect else ''}")


def format_glyph_display(glyph: DimensionalGlyph) -> str:
    """Formate l'affichage d'un glyphe"""
    lines = []
    lines.append(f"\n  {glyph.symbol} {glyph.name}")
    lines.append(f"     Dimension: D{glyph.dimension} | Power: {glyph.total_power:.0f} | Synergy: {glyph.synergy_bonus}x")
    lines.append(f"     Activation: {glyph.activation_level:.0f}% | Stability: {glyph.dimensional_stability:.0f}%")
    lines.append(f"     Gems ({glyph.gem_symbols}):")
    
    for gem in glyph.gems:
        lines.append(f"       {format_gem_display(gem)}")
    
    return "\n".join(lines)


def format_array_display(array: GlyphArray) -> str:
    """Formate l'affichage complet d'un array de glyphes"""
    lines = []
    lines.append("\n" + "="*70)
    lines.append("  ⬡ GLYPH ARRAY - POLY-SPINOR 7D")
    lines.append("="*70)
    
    lines.append(f"\n  Array ID: {array.array_id}")
    lines.append(f"  Total Gems: {array.total_gems}")
    lines.append(f"  Total Power: {array.total_power:,.0f}")
    lines.append(f"  Average Resonance: {array.average_resonance:.1f}%")
    lines.append(f"  Dimensional Balance: {array.dimensional_balance:.0f}%")
    lines.append(f"  Bell Correlation: {array.bell_correlation:.4f}")
    lines.append(f"  Entanglement: {array.entanglement_degree:.4f}")
    
    if array.set_bonus:
        lines.append(f"\n  Set Bonuses:")
        for bonus, value in array.set_bonus.items():
            lines.append(f"    + {bonus.replace('_', ' ').title()}: {value}x")
    
    lines.append(f"\n  GLYPHS (7):")
    for glyph in array.glyphs:
        lines.append(format_glyph_display(glyph))
    
    lines.append("\n" + "="*70)
    
    return "\n".join(lines)


# ============================================================================
# CLI / DEMO
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  POLY-SPINOR GLYPH & GEM GENERATOR")
    print("="*70)
    
    # Cree un generateur
    generator = PolySpinorGlyphGenerator()
    
    # Genere un array complet
    print("\n[+] Generating 7 Glyphs with 21 Gems...")
    array = generator.generate_glyph_array()
    
    # Affiche
    print(format_array_display(array))
    
    # Stats d'entropie
    print(f"\n  Entropy consumed: {generator.get_entropy_consumed():,} bits")
    print(f"  (~{generator.get_entropy_consumed() // 8:,} bytes of cryptographic randomness)")
