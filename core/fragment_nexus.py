"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     FRAGMENT NEXUS - ALCHEMICAL ECONOMY                      ║
║══════════════════════════════════════════════════════════════════════════════║
║                                                                              ║
║  "Les fragments ne sont pas des debris... ce sont des graines d'univers."   ║
║                                                                              ║
║  Un systeme economique decentralise gouverne par:                            ║
║  - L'Alchimie des Fragments (transmutation et fusion)                        ║
║  - Le Reseau de Resonance (intrication inter-vaults)                         ║
║  - Les Constellations (patterns de pouvoir)                                  ║
║  - La Gouvernance DAO (votes et propositions)                                ║
║  - Les Propheties (fragments oraculaires)                                    ║
║  - Les Cycles Cosmiques (marches temporels)                                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import json
import hashlib
import secrets
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ============================================================================
# ESSENCES FRAGMENTAIRES - Les 7 Essences Primordiales
# ============================================================================

class FragmentEssence(Enum):
    """Les 7 essences dimensionnelles des fragments"""
    VOID = ("void", "ᛟ", "#0a0020", "Essence du Vide", 0, 
            "Absorbe l'energie environnante")
    QUANTUM = ("quantum", "ᚠ", "#00ff88", "Essence Quantique", 1,
               "Existe dans plusieurs etats simultanement")
    TEMPORAL = ("temporal", "ᛞ", "#ffaa00", "Essence Temporelle", 2,
                "Transcende le flux du temps")
    SPATIAL = ("spatial", "ᚱ", "#00aaff", "Essence Spatiale", 3,
               "Plie les dimensions de l'espace")
    ENTROPIC = ("entropic", "ᚺ", "#ff3366", "Essence Entropique", 4,
                "Canalise le chaos primordial")
    HARMONIC = ("harmonic", "ᚹ", "#aa55ff", "Essence Harmonique", 5,
                "Resonne avec les frequences universelles")
    CELESTIAL = ("celestial", "ᛊ", "#ffffaa", "Essence Celeste", 6,
                 "Connecte aux forces cosmiques")
    
    def __init__(self, essence_id: str, symbol: str, color: str, 
                 name: str, dimension: int, description: str):
        self.essence_id = essence_id
        self.symbol = symbol
        self.color = color
        self.display_name = name
        self.dimension = dimension
        self.description = description


# ============================================================================
# TYPES DE FRAGMENTS SPECIAUX
# ============================================================================

class FragmentType(Enum):
    """Types de fragments avec proprietes uniques"""
    
    # Fragments de base (issus de gemmes brisees)
    SHARD = ("shard", "◇", "Eclat", "Fragment basique d'une gemme brisee")
    SPLINTER = ("splinter", "◆", "Echarde", "Fragment tranchant a haute energie")
    DUST = ("dust", "·", "Poussiere", "Particules fines d'essence")
    
    # Fragments alchimiques (crees par transmutation)
    CATALYST = ("catalyst", "⚗", "Catalyseur", "Accelere les reactions alchimiques")
    REAGENT = ("reagent", "⚛", "Reactif", "Ingredient pour transmutations")
    PHILOSOPHER = ("philosopher", "☿", "Pierre Philosophale", "Fragment ultime de transmutation")
    
    # Fragments de gouvernance (votent dans la DAO)
    VOICE = ("voice", "📜", "Voix", "Droit de vote dans la DAO")
    DECREE = ("decree", "⚖", "Decret", "Pouvoir de proposition")
    CROWN = ("crown", "👑", "Couronne", "Droit de veto et gouvernance supreme")
    
    # Fragments prophetiques (predisent et influencent)
    OMEN = ("omen", "🔮", "Presage", "Predit des evenements mineurs")
    PROPHECY = ("prophecy", "📖", "Prophetie", "Revele des destins majeurs")
    ORACLE = ("oracle", "👁", "Oracle", "Voit a travers tous les temps")
    
    # Fragments de resonance (connectent les vaults)
    ECHO = ("echo", "〰", "Echo", "Resonne avec les fragments proches")
    BOND = ("bond", "∞", "Lien", "Cree des connexions permanentes")
    NEXUS = ("nexus", "✦", "Nexus", "Point central du reseau de resonance")
    
    # Fragments cosmiques (cycles et constellations)
    STAR = ("star", "⭐", "Etoile", "Element de constellation")
    MOON = ("moon", "🌙", "Lune", "Affecte par les cycles lunaires")
    SUN = ("sun", "☀", "Soleil", "Source d'energie cosmique")
    COMET = ("comet", "☄", "Comete", "Fragment voyageur entre les vaults")
    
    def __init__(self, type_id: str, symbol: str, name: str, description: str):
        self.type_id = type_id
        self.symbol = symbol
        self.display_name = name
        self.description = description


# ============================================================================
# FRAGMENT SOUL - L'Ame du Fragment
# ============================================================================

@dataclass
class FragmentSoul:
    """
    L'ame d'un fragment - contient les memoires et pouvoirs residuels
    de la gemme originale dont il provient.
    """
    # Memoire de l'origine
    origin_gem_type: str
    origin_gem_rarity: str
    origin_gem_power: float
    
    # Memoires stockees (experiences du fragment)
    memories: List[Dict] = field(default_factory=list)
    
    # Puissance residuelle
    residual_power: float = 0.0
    
    # Affinites (heritees de la gemme)
    affinities: Dict[str, float] = field(default_factory=dict)
    
    # Corruption (degradation avec le temps)
    corruption_level: float = 0.0
    
    def add_memory(self, event: str, data: Dict = None):
        """Ajoute une memoire a l'ame"""
        self.memories.append({
            "event": event,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
            "power_at_time": self.residual_power
        })
    
    def decay(self, amount: float = 0.01):
        """Degradation naturelle"""
        self.corruption_level = min(1.0, self.corruption_level + amount)
        self.residual_power *= (1 - amount)


# ============================================================================
# FRAGMENT PRINCIPAL
# ============================================================================

@dataclass 
class Fragment:
    """Fragment avec ame, essence et proprietes economiques"""
    
    # Identite
    fragment_id: str
    fragment_type: str  # FragmentType
    essence: str  # FragmentEssence
    
    # Stats de base
    mass: float  # Masse en unites d'essence
    purity: float  # 0-100%
    stability: float  # 0-100%
    
    # Ame (si provient d'une gemme)
    soul: Optional[Dict] = None
    
    # Resonance
    resonance_frequency: float = 0.0  # Frequence de resonance
    entangled_fragments: List[str] = field(default_factory=list)  # IDs des fragments lies
    
    # Gouvernance
    voting_power: float = 0.0
    governance_tier: int = 0  # 0=aucun, 1=Voice, 2=Decree, 3=Crown
    votes_cast: List[Dict] = field(default_factory=list)
    
    # Prophetie
    prophecy_text: Optional[str] = None
    prophecy_fulfilled: bool = False
    prophecy_target_date: Optional[str] = None
    
    # Constellation
    constellation_id: Optional[str] = None
    constellation_position: Optional[int] = None
    
    # Cycles cosmiques
    birth_cycle: int = 0  # Cycle lunaire de creation
    optimal_cycles: List[int] = field(default_factory=list)  # Cycles ou le fragment est puissant
    
    # Marche
    market_value: float = 0.0
    price_history: List[Dict] = field(default_factory=list)
    
    # Origine
    origin_vault: int = 0
    created_at: str = ""
    
    # Position actuelle
    current_vault: Optional[int] = None
    status: str = "active"  # active, forging, locked, consumed, traveling
    
    # Historique
    transfer_history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Fragment":
        return cls(**data)
    
    @property
    def effective_power(self) -> float:
        """Puissance effective du fragment"""
        base = self.mass * (self.purity / 100) * (self.stability / 100)
        
        # Bonus d'ame
        if self.soul:
            base += self.soul.get('residual_power', 0) * 0.5
        
        # Bonus de resonance
        base *= (1 + len(self.entangled_fragments) * 0.1)
        
        # Bonus de constellation
        if self.constellation_id:
            base *= 1.25
        
        return base
    
    @property
    def display_symbol(self) -> str:
        ftype = next((f for f in FragmentType if f.type_id == self.fragment_type), None)
        essence = next((e for e in FragmentEssence if e.essence_id == self.essence), None)
        return f"{essence.symbol if essence else '?'}{ftype.symbol if ftype else '?'}"


# ============================================================================
# RECETTES ALCHIMIQUES
# ============================================================================

@dataclass
class AlchemicalRecipe:
    """Recette de transmutation alchimique"""
    recipe_id: str
    name: str
    description: str
    
    # Ingredients requis (essence -> quantite)
    required_essences: Dict[str, int]
    required_types: Dict[str, int]
    
    # Catalyseur optionnel
    catalyst_type: Optional[str] = None
    catalyst_boost: float = 1.0
    
    # Resultat
    output_type: str = "shard"
    output_essence: Optional[str] = None  # None = melange
    output_count: int = 1
    output_quality_range: Tuple[float, float] = (0.5, 1.0)
    
    # Conditions
    min_purity: float = 0.0
    required_cycle: Optional[int] = None  # Cycle lunaire requis
    required_constellation: Optional[str] = None
    
    # Difficulte
    success_rate: float = 0.8
    discovery_difficulty: int = 1  # 1-10


# Recettes de base (d'autres peuvent etre decouvertes)
ALCHEMICAL_RECIPES = {
    "basic_fusion": AlchemicalRecipe(
        recipe_id="basic_fusion",
        name="Fusion Basique",
        description="Combine 3 eclats de meme essence en un eclat plus pur",
        required_essences={},  # Any essence
        required_types={"shard": 3},
        output_type="shard",
        output_count=1,
        output_quality_range=(1.2, 1.8),
        success_rate=0.9
    ),
    "essence_purification": AlchemicalRecipe(
        recipe_id="essence_purification",
        name="Purification d'Essence",
        description="Transforme la poussiere en eclat pur",
        required_essences={},
        required_types={"dust": 7},
        catalyst_type="catalyst",
        catalyst_boost=1.5,
        output_type="shard",
        output_quality_range=(0.8, 1.2),
        success_rate=0.75
    ),
    "catalyst_creation": AlchemicalRecipe(
        recipe_id="catalyst_creation",
        name="Creation de Catalyseur",
        description="Cree un catalyseur a partir d'essences variees",
        required_essences={"void": 1, "quantum": 1, "entropic": 1},
        required_types={"shard": 3},
        output_type="catalyst",
        output_count=1,
        success_rate=0.6,
        discovery_difficulty=3
    ),
    "voice_forging": AlchemicalRecipe(
        recipe_id="voice_forging",
        name="Forge de la Voix",
        description="Cree un fragment de gouvernance",
        required_essences={"harmonic": 2, "celestial": 1},
        required_types={"shard": 5, "catalyst": 1},
        output_type="voice",
        min_purity=70.0,
        success_rate=0.4,
        discovery_difficulty=5
    ),
    "decree_ascension": AlchemicalRecipe(
        recipe_id="decree_ascension",
        name="Ascension du Decret",
        description="Eleve une Voix en Decret",
        required_essences={},
        required_types={"voice": 3, "catalyst": 2},
        catalyst_type="philosopher",
        catalyst_boost=2.0,
        output_type="decree",
        success_rate=0.25,
        discovery_difficulty=7
    ),
    "omen_divination": AlchemicalRecipe(
        recipe_id="omen_divination",
        name="Divination des Presages",
        description="Cree un fragment prophetique",
        required_essences={"temporal": 2, "void": 1},
        required_types={"shard": 3},
        required_cycle=0,  # Nouvelle lune
        output_type="omen",
        success_rate=0.5,
        discovery_difficulty=4
    ),
    "star_birth": AlchemicalRecipe(
        recipe_id="star_birth",
        name="Naissance Stellaire",
        description="Cree une etoile pour les constellations",
        required_essences={"celestial": 3},
        required_types={"shard": 5, "dust": 10},
        output_type="star",
        success_rate=0.6,
        discovery_difficulty=4
    ),
    "resonance_bond": AlchemicalRecipe(
        recipe_id="resonance_bond",
        name="Lien de Resonance",
        description="Cree un lien inter-vault",
        required_essences={"quantum": 2, "harmonic": 2},
        required_types={"echo": 2},
        output_type="bond",
        success_rate=0.5,
        discovery_difficulty=5
    ),
    "philosopher_stone": AlchemicalRecipe(
        recipe_id="philosopher_stone",
        name="Pierre Philosophale",
        description="Le fragment ultime de l'alchimie",
        required_essences={"void": 3, "quantum": 3, "temporal": 3, 
                          "spatial": 3, "entropic": 3, "harmonic": 3, "celestial": 3},
        required_types={"catalyst": 7, "reagent": 7},
        output_type="philosopher",
        output_count=1,
        success_rate=0.1,
        discovery_difficulty=10
    ),
}


# ============================================================================
# CONSTELLATIONS
# ============================================================================

@dataclass
class Constellation:
    """Pattern de fragments formant une constellation"""
    constellation_id: str
    name: str
    description: str
    
    # Pattern requis (positions -> essence requise)
    pattern: Dict[int, str]  # position -> essence_id
    
    # Fragments actuellement places
    placed_fragments: Dict[int, str] = field(default_factory=dict)  # position -> fragment_id
    
    # Bonus quand complete
    power_multiplier: float = 1.5
    special_ability: str = ""
    governance_boost: float = 0.0
    
    # Statut
    is_complete: bool = False
    completed_at: Optional[str] = None
    owner_vault: Optional[int] = None
    
    def check_completion(self) -> bool:
        """Verifie si la constellation est complete"""
        self.is_complete = set(self.pattern.keys()) == set(self.placed_fragments.keys())
        if self.is_complete and not self.completed_at:
            self.completed_at = datetime.now().isoformat()
        return self.is_complete


# Constellations disponibles
CONSTELLATIONS = {
    "the_forge": Constellation(
        constellation_id="the_forge",
        name="La Forge",
        description="Augmente le taux de succes des transmutations",
        pattern={0: "entropic", 1: "void", 2: "entropic", 
                3: "temporal", 4: "spatial"},
        power_multiplier=1.3,
        special_ability="forge_mastery",
        governance_boost=0.0
    ),
    "the_council": Constellation(
        constellation_id="the_council",
        name="Le Conseil",
        description="Multiplie le pouvoir de vote",
        pattern={0: "harmonic", 1: "harmonic", 2: "celestial",
                3: "harmonic", 4: "harmonic"},
        power_multiplier=1.2,
        special_ability="council_voice",
        governance_boost=2.0
    ),
    "the_oracle": Constellation(
        constellation_id="the_oracle",
        name="L'Oracle",
        description="Revele les propheties cachees",
        pattern={0: "temporal", 1: "void", 2: "temporal",
                3: "quantum", 4: "void", 5: "quantum", 6: "celestial"},
        power_multiplier=1.5,
        special_ability="true_sight",
        governance_boost=0.5
    ),
    "the_nexus": Constellation(
        constellation_id="the_nexus",
        name="Le Nexus",
        description="Point central de toute resonance",
        pattern={0: "quantum", 1: "spatial", 2: "quantum",
                3: "harmonic", 4: "void", 5: "harmonic",
                6: "quantum", 7: "spatial", 8: "quantum"},
        power_multiplier=2.0,
        special_ability="nexus_control",
        governance_boost=1.0
    ),
    "the_crown": Constellation(
        constellation_id="the_crown",
        name="La Couronne",
        description="Confere le pouvoir supreme de gouvernance",
        pattern={0: "celestial", 1: "celestial", 2: "celestial",
                3: "harmonic", 4: "void", 5: "harmonic",
                6: "celestial"},
        power_multiplier=1.8,
        special_ability="crown_authority",
        governance_boost=5.0
    ),
}


# ============================================================================
# PROPOSITIONS DAO
# ============================================================================

class ProposalType(Enum):
    """Types de propositions pour la DAO"""
    NEW_RECIPE = "new_recipe"
    RECIPE_MODIFICATION = "recipe_modification"
    ECONOMIC_ADJUSTMENT = "economic_adjustment"
    NEW_CONSTELLATION = "new_constellation"
    FRAGMENT_CREATION = "fragment_creation"
    EMERGENCY_ACTION = "emergency_action"
    TREASURY_ALLOCATION = "treasury_allocation"


@dataclass
class DAOProposal:
    """Proposition soumise a la DAO"""
    proposal_id: str
    title: str
    description: str
    proposal_type: str  # ProposalType
    
    # Proposeur
    proposer_vault: int
    proposer_fragment_id: str  # Fragment de gouvernance utilise
    
    # Contenu de la proposition
    payload: Dict = field(default_factory=dict)
    
    # Votes
    votes_for: Dict[str, float] = field(default_factory=dict)  # fragment_id -> power
    votes_against: Dict[str, float] = field(default_factory=dict)
    votes_abstain: Dict[str, float] = field(default_factory=dict)
    
    # Timing
    created_at: str = ""
    voting_ends_at: str = ""
    executed_at: Optional[str] = None
    
    # Statut
    status: str = "pending"  # pending, active, passed, rejected, executed, vetoed
    
    # Quorum requis
    quorum_percentage: float = 10.0  # % du pouvoir de vote total
    pass_threshold: float = 60.0  # % des votes pour passer
    
    @property
    def total_votes(self) -> float:
        return (sum(self.votes_for.values()) + 
                sum(self.votes_against.values()) + 
                sum(self.votes_abstain.values()))
    
    @property
    def approval_percentage(self) -> float:
        total_decisive = sum(self.votes_for.values()) + sum(self.votes_against.values())
        if total_decisive == 0:
            return 0
        return (sum(self.votes_for.values()) / total_decisive) * 100


# ============================================================================
# CYCLES COSMIQUES
# ============================================================================

class CosmicCycle:
    """Gere les cycles cosmiques qui affectent l'economie"""
    
    LUNAR_PHASES = [
        ("new_moon", "🌑", "Nouvelle Lune", {"prophecy": 1.5, "void": 1.3}),
        ("waxing_crescent", "🌒", "Premier Croissant", {"creation": 1.2}),
        ("first_quarter", "🌓", "Premier Quartier", {"forging": 1.2}),
        ("waxing_gibbous", "🌔", "Gibbeuse Croissante", {"growth": 1.3}),
        ("full_moon", "🌕", "Pleine Lune", {"power": 1.5, "celestial": 1.5}),
        ("waning_gibbous", "🌖", "Gibbeuse Decroissante", {"harvest": 1.3}),
        ("last_quarter", "🌗", "Dernier Quartier", {"destruction": 1.2}),
        ("waning_crescent", "🌘", "Dernier Croissant", {"rest": 1.1, "decay": 0.8}),
    ]
    
    @classmethod
    def get_current_phase(cls) -> Tuple[int, str, str, str, Dict]:
        """Retourne la phase lunaire actuelle (simulee)"""
        # Simulation basee sur le timestamp
        days_since_epoch = (datetime.now() - datetime(2024, 1, 1)).days
        phase_index = days_since_epoch % 8
        phase_id, symbol, name, modifiers = cls.LUNAR_PHASES[phase_index]
        return phase_index, phase_id, symbol, name, modifiers
    
    @classmethod
    def get_market_modifier(cls) -> float:
        """Modificateur de marche base sur le cycle"""
        _, _, _, _, modifiers = cls.get_current_phase()
        return modifiers.get('power', 1.0)


# ============================================================================
# FRAGMENT NEXUS - Gestionnaire Principal
# ============================================================================

class FragmentNexus:
    """
    Gestionnaire central du systeme de fragments.
    Gere l'economie, la gouvernance, les transmutations et les propheties.
    """
    
    def __init__(self, data_dir: str = None):
        base_path = Path(__file__).parent.parent
        self.data_dir = Path(data_dir) if data_dir else base_path / "fragment_nexus"
        
        self.fragments_dir = self.data_dir / "fragments"
        self.proposals_dir = self.data_dir / "proposals"
        self.constellations_dir = self.data_dir / "constellations"
        self.recipes_dir = self.data_dir / "recipes"
        self.treasury_dir = self.data_dir / "treasury"
        
        for d in [self.fragments_dir, self.proposals_dir, 
                  self.constellations_dir, self.recipes_dir, self.treasury_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        self._fragments: Dict[str, Fragment] = {}
        self._proposals: Dict[str, DAOProposal] = {}
        self._constellations: Dict[str, Constellation] = {}
        self._discovered_recipes: Set[str] = set()
        
        self._load_all()
    
    def _load_all(self):
        """Charge toutes les donnees"""
        # Fragments
        for f in self.fragments_dir.glob("fragment_*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                self._fragments[data['fragment_id']] = Fragment.from_dict(data)
            except Exception as e:
                print(f"[WARN] Error loading {f}: {e}")
        
        # Recettes decouvertes
        recipes_file = self.recipes_dir / "discovered.json"
        if recipes_file.exists():
            with open(recipes_file, 'r', encoding='utf-8') as f:
                self._discovered_recipes = set(json.load(f))
        else:
            # Recettes de base disponibles par defaut
            self._discovered_recipes = {"basic_fusion", "essence_purification"}
    
    def _save_fragment(self, fragment: Fragment):
        """Sauvegarde un fragment"""
        filepath = self.fragments_dir / f"fragment_{fragment.fragment_id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(fragment.to_dict(), f, indent=2, ensure_ascii=False)
        self._fragments[fragment.fragment_id] = fragment
    
    def _save_discovered_recipes(self):
        """Sauvegarde les recettes decouvertes"""
        filepath = self.recipes_dir / "discovered.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(list(self._discovered_recipes), f)
    
    # ========================================================================
    # CREATION DE FRAGMENTS
    # ========================================================================
    
    def create_fragment_from_shatter(self, gem_data: Dict, vault_number: int) -> List[Fragment]:
        """
        Cree des fragments a partir d'une gemme brisee.
        La gemme laisse son ame dans les fragments.
        """
        fragments = []
        
        # Determiner combien de fragments
        gem_power = gem_data.get('effective_power', gem_data.get('base_power', 100))
        base_count = max(1, int(math.log10(gem_power + 1)))
        count = base_count + secrets.randbelow(3)
        
        # Creer l'ame
        soul = FragmentSoul(
            origin_gem_type=gem_data.get('gem_type', 'unknown'),
            origin_gem_rarity=gem_data.get('rarity', 'common'),
            origin_gem_power=gem_power,
            residual_power=gem_power * 0.3,
            affinities={}
        )
        soul.add_memory("gem_shattered", {"original_power": gem_power})
        
        # Distribuer l'essence selon le type de gemme
        essence = self._gem_to_essence(gem_data.get('gem_type', ''))
        
        # Creer les fragments
        remaining_mass = gem_power * 0.5  # 50% de la puissance devient masse
        
        for i in range(count):
            # Repartir la masse
            if i == count - 1:
                mass = remaining_mass
            else:
                mass = remaining_mass * (0.3 + secrets.randbelow(40) / 100)
                remaining_mass -= mass
            
            # Type de fragment
            roll = secrets.randbelow(100)
            if roll < 60:
                ftype = FragmentType.SHARD
            elif roll < 85:
                ftype = FragmentType.SPLINTER
            else:
                ftype = FragmentType.DUST
            
            fragment = self._create_fragment(
                vault_number=vault_number,
                fragment_type=ftype,
                essence=essence,
                mass=mass,
                soul=soul.to_dict() if i == 0 else None  # Ame dans le premier fragment
            )
            
            fragments.append(fragment)
        
        return fragments
    
    def _create_fragment(self, vault_number: int, 
                        fragment_type: FragmentType,
                        essence: FragmentEssence,
                        mass: float,
                        soul: Dict = None) -> Fragment:
        """Cree un nouveau fragment"""
        
        # ID unique
        fragment_id = hashlib.sha256(
            f"{fragment_type.type_id}{essence.essence_id}{mass}"
            f"{datetime.now().isoformat()}{secrets.token_hex(8)}".encode()
        ).hexdigest()[:16]
        
        # Stats
        purity = 30 + secrets.randbelow(50)
        stability = 40 + secrets.randbelow(40)
        
        # Frequence de resonance basee sur l'essence
        resonance = essence.dimension * 1000 + secrets.randbelow(1000)
        
        # Cycle cosmique actuel
        cycle_index, _, _, _, _ = CosmicCycle.get_current_phase()
        
        # Cycles optimaux (l'essence determine les affinites)
        optimal = [(essence.dimension + i) % 8 for i in range(3)]
        
        # Valeur de marche initiale
        market_value = mass * (purity / 100) * CosmicCycle.get_market_modifier()
        
        fragment = Fragment(
            fragment_id=fragment_id,
            fragment_type=fragment_type.type_id,
            essence=essence.essence_id,
            mass=mass,
            purity=purity,
            stability=stability,
            soul=soul,
            resonance_frequency=resonance,
            birth_cycle=cycle_index,
            optimal_cycles=optimal,
            market_value=market_value,
            origin_vault=vault_number,
            current_vault=vault_number,
            created_at=datetime.now().isoformat()
        )
        
        self._save_fragment(fragment)
        return fragment
    
    def _gem_to_essence(self, gem_type: str) -> FragmentEssence:
        """Convertit un type de gemme en essence"""
        mapping = {
            'void': FragmentEssence.VOID,
            'quantum': FragmentEssence.QUANTUM,
            'temporal': FragmentEssence.TEMPORAL,
            'spatial': FragmentEssence.SPATIAL,
            'entropic': FragmentEssence.ENTROPIC,
            'harmonic': FragmentEssence.HARMONIC,
            'celestial': FragmentEssence.CELESTIAL,
        }
        
        for key, essence in mapping.items():
            if key in gem_type.lower():
                return essence
        
        # Defaut aleatoire
        return list(FragmentEssence)[secrets.randbelow(7)]
    
    # ========================================================================
    # TRANSMUTATION ALCHIMIQUE
    # ========================================================================
    
    def transmute(self, recipe_id: str, fragment_ids: List[str], 
                  catalyst_id: str = None, vault_number: int = None) -> Tuple[bool, List[Fragment], str]:
        """
        Execute une transmutation alchimique.
        Retourne (success, output_fragments, message)
        """
        # Verifier la recette
        if recipe_id not in self._discovered_recipes:
            return False, [], f"Recette '{recipe_id}' non decouverte"
        
        recipe = ALCHEMICAL_RECIPES.get(recipe_id)
        if not recipe:
            return False, [], f"Recette '{recipe_id}' inexistante"
        
        # Recuperer les fragments
        fragments = [self._fragments.get(fid) for fid in fragment_ids]
        if None in fragments:
            return False, [], "Certains fragments n'existent pas"
        
        # Verifier les types requis
        type_counts = {}
        essence_counts = {}
        total_purity = 0
        total_mass = 0
        
        for f in fragments:
            type_counts[f.fragment_type] = type_counts.get(f.fragment_type, 0) + 1
            essence_counts[f.essence] = essence_counts.get(f.essence, 0) + 1
            total_purity += f.purity
            total_mass += f.mass
        
        avg_purity = total_purity / len(fragments) if fragments else 0
        
        # Verifier les requirements
        for req_type, req_count in recipe.required_types.items():
            if type_counts.get(req_type, 0) < req_count:
                return False, [], f"Manque {req_count - type_counts.get(req_type, 0)} {req_type}"
        
        for req_ess, req_count in recipe.required_essences.items():
            if essence_counts.get(req_ess, 0) < req_count:
                return False, [], f"Manque essence {req_ess}"
        
        # Verifier purete minimale
        if avg_purity < recipe.min_purity:
            return False, [], f"Purete insuffisante ({avg_purity:.1f}% < {recipe.min_purity}%)"
        
        # Verifier cycle si requis
        if recipe.required_cycle is not None:
            current_cycle, _, _, _, _ = CosmicCycle.get_current_phase()
            if current_cycle != recipe.required_cycle:
                return False, [], f"Mauvais cycle lunaire (actuel: {current_cycle}, requis: {recipe.required_cycle})"
        
        # Catalyseur
        catalyst_boost = 1.0
        if catalyst_id:
            catalyst = self._fragments.get(catalyst_id)
            if catalyst and catalyst.fragment_type == recipe.catalyst_type:
                catalyst_boost = recipe.catalyst_boost
                # Consommer le catalyseur
                catalyst.status = "consumed"
                self._save_fragment(catalyst)
        
        # Calculer le succes
        success_chance = recipe.success_rate * (avg_purity / 100) * catalyst_boost
        
        # Bonus de constellation
        for f in fragments:
            if f.constellation_id == "the_forge":
                success_chance *= 1.2
                break
        
        success = secrets.randbelow(100) < success_chance * 100
        
        if not success:
            # Echec - perte partielle
            for f in fragments:
                f.mass *= 0.7
                f.stability -= 10
                self._save_fragment(f)
            return False, [], "Transmutation echouee! Fragments endommages."
        
        # Succes - consommer les fragments
        vault = vault_number or fragments[0].current_vault
        
        for f in fragments:
            f.status = "consumed"
            self._save_fragment(f)
        
        # Creer les outputs
        output_essence = next(
            (e for e in FragmentEssence if e.essence_id == recipe.output_essence),
            list(FragmentEssence)[secrets.randbelow(7)]  # Random si non specifie
        )
        
        output_type = next(
            (t for t in FragmentType if t.type_id == recipe.output_type),
            FragmentType.SHARD
        )
        
        # Qualite du resultat
        min_q, max_q = recipe.output_quality_range
        quality = min_q + (max_q - min_q) * (avg_purity / 100)
        
        outputs = []
        for _ in range(recipe.output_count):
            output = self._create_fragment(
                vault_number=vault,
                fragment_type=output_type,
                essence=output_essence,
                mass=total_mass * quality / recipe.output_count
            )
            output.purity = min(100, avg_purity * quality)
            output.stability = min(100, 50 + avg_purity * 0.4)
            
            # Heritage des ames
            souls_inherited = [f.soul for f in fragments if f.soul]
            if souls_inherited:
                # Fusionner les memoires
                merged_soul = souls_inherited[0].copy()
                merged_soul['memories'] = []
                for s in souls_inherited:
                    if isinstance(s, dict) and 'memories' in s:
                        merged_soul['memories'].extend(s.get('memories', []))
                merged_soul['residual_power'] = sum(
                    s.get('residual_power', 0) for s in souls_inherited if isinstance(s, dict)
                ) * 0.8
                output.soul = merged_soul
            
            self._save_fragment(output)
            outputs.append(output)
        
        return True, outputs, f"Transmutation reussie! {len(outputs)} fragment(s) cree(s)."
    
    def discover_recipe(self, vault_number: int, fragment_ids: List[str]) -> Tuple[bool, str]:
        """
        Tente de decouvrir une nouvelle recette par experimentation.
        Necessite des fragments specifiques et de la chance.
        """
        fragments = [self._fragments.get(fid) for fid in fragment_ids if self._fragments.get(fid)]
        
        if len(fragments) < 3:
            return False, "Il faut au moins 3 fragments pour experimenter"
        
        # Verifier quelles recettes non decouvertes correspondent
        for recipe_id, recipe in ALCHEMICAL_RECIPES.items():
            if recipe_id in self._discovered_recipes:
                continue
            
            # Calculer la correspondance
            type_match = sum(1 for f in fragments 
                           if f.fragment_type in recipe.required_types)
            essence_match = sum(1 for f in fragments
                              if f.essence in recipe.required_essences)
            
            total_match = type_match + essence_match
            
            # Chance de decouverte
            discovery_chance = (total_match / (len(fragments) * 2)) * (10 / recipe.discovery_difficulty)
            
            if secrets.randbelow(100) < discovery_chance * 100:
                self._discovered_recipes.add(recipe_id)
                self._save_discovered_recipes()
                
                # Consommer un fragment comme cout
                fragments[0].mass *= 0.5
                self._save_fragment(fragments[0])
                
                return True, f"DECOUVERTE! Nouvelle recette: {recipe.name}"
        
        # Echec
        for f in fragments[:2]:
            f.stability -= 5
            self._save_fragment(f)
        
        return False, "Experimentation echouee. Les fragments sont affaiblis."
    
    # ========================================================================
    # GOUVERNANCE DAO
    # ========================================================================
    
    def create_proposal(self, title: str, description: str, 
                       proposal_type: ProposalType, payload: Dict,
                       proposer_vault: int, proposer_fragment_id: str,
                       voting_days: int = 7) -> Tuple[bool, str]:
        """Cree une nouvelle proposition DAO"""
        
        fragment = self._fragments.get(proposer_fragment_id)
        if not fragment:
            return False, "Fragment non trouve"
        
        if fragment.governance_tier < 2:  # Besoin d'un Decree ou plus
            return False, "Fragment de gouvernance insuffisant (Decree requis)"
        
        proposal_id = hashlib.sha256(
            f"{title}{datetime.now().isoformat()}{secrets.token_hex(8)}".encode()
        ).hexdigest()[:16]
        
        proposal = DAOProposal(
            proposal_id=proposal_id,
            title=title,
            description=description,
            proposal_type=proposal_type.value,
            proposer_vault=proposer_vault,
            proposer_fragment_id=proposer_fragment_id,
            payload=payload,
            created_at=datetime.now().isoformat(),
            voting_ends_at=(datetime.now() + timedelta(days=voting_days)).isoformat(),
            status="active"
        )
        
        # Sauvegarder
        filepath = self.proposals_dir / f"proposal_{proposal_id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(proposal), f, indent=2, ensure_ascii=False)
        
        self._proposals[proposal_id] = proposal
        
        return True, f"Proposition '{title}' creee avec ID: {proposal_id}"
    
    def vote(self, proposal_id: str, voter_fragment_id: str, 
             vote_type: str) -> Tuple[bool, str]:
        """Vote sur une proposition"""
        
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return False, "Proposition non trouvee"
        
        if proposal.status != "active":
            return False, f"Proposition non active (status: {proposal.status})"
        
        fragment = self._fragments.get(voter_fragment_id)
        if not fragment:
            return False, "Fragment non trouve"
        
        if fragment.governance_tier < 1:
            return False, "Fragment sans pouvoir de vote"
        
        # Calculer le pouvoir de vote
        voting_power = fragment.voting_power
        if fragment.constellation_id:
            const = CONSTELLATIONS.get(fragment.constellation_id)
            if const:
                voting_power *= (1 + const.governance_boost)
        
        # Enregistrer le vote
        if vote_type == "for":
            proposal.votes_for[voter_fragment_id] = voting_power
        elif vote_type == "against":
            proposal.votes_against[voter_fragment_id] = voting_power
        else:
            proposal.votes_abstain[voter_fragment_id] = voting_power
        
        # Enregistrer dans l'historique du fragment
        fragment.votes_cast.append({
            "proposal_id": proposal_id,
            "vote": vote_type,
            "power": voting_power,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_fragment(fragment)
        
        # Sauvegarder la proposition
        filepath = self.proposals_dir / f"proposal_{proposal_id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(proposal), f, indent=2, ensure_ascii=False)
        
        return True, f"Vote enregistre: {vote_type} ({voting_power:.1f} pouvoir)"
    
    def veto_proposal(self, proposal_id: str, crown_fragment_id: str) -> Tuple[bool, str]:
        """Veto d'une proposition par un detenteur de Crown"""
        
        proposal = self._proposals.get(proposal_id)
        fragment = self._fragments.get(crown_fragment_id)
        
        if not proposal or not fragment:
            return False, "Proposition ou fragment non trouve"
        
        if fragment.governance_tier < 3:  # Crown requis
            return False, "Seul un fragment Crown peut exercer un veto"
        
        proposal.status = "vetoed"
        
        filepath = self.proposals_dir / f"proposal_{proposal_id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(proposal), f, indent=2, ensure_ascii=False)
        
        return True, f"Proposition vetoed par Crown {crown_fragment_id[:8]}"
    
    # ========================================================================
    # RESONANCE & ENTANGLEMENT
    # ========================================================================
    
    def create_entanglement(self, fragment_id_1: str, fragment_id_2: str) -> Tuple[bool, str]:
        """Cree une intrication quantique entre deux fragments"""
        
        f1 = self._fragments.get(fragment_id_1)
        f2 = self._fragments.get(fragment_id_2)
        
        if not f1 or not f2:
            return False, "Fragments non trouves"
        
        if f1.current_vault == f2.current_vault:
            return False, "Les fragments doivent etre dans des vaults differents"
        
        # Verifier la compatibilite de resonance
        freq_diff = abs(f1.resonance_frequency - f2.resonance_frequency)
        if freq_diff > 2000:
            return False, f"Frequences trop differentes ({freq_diff:.0f}Hz)"
        
        # Creer l'intrication
        f1.entangled_fragments.append(fragment_id_2)
        f2.entangled_fragments.append(fragment_id_1)
        
        # Synchroniser les frequences
        avg_freq = (f1.resonance_frequency + f2.resonance_frequency) / 2
        f1.resonance_frequency = avg_freq
        f2.resonance_frequency = avg_freq
        
        self._save_fragment(f1)
        self._save_fragment(f2)
        
        return True, f"Intrication creee! Frequence synchronisee: {avg_freq:.0f}Hz"
    
    def propagate_resonance(self, source_fragment_id: str, effect: str, value: float):
        """Propage un effet a travers le reseau d'intrication"""
        
        visited = set()
        to_visit = [source_fragment_id]
        
        while to_visit:
            current_id = to_visit.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)
            
            fragment = self._fragments.get(current_id)
            if not fragment:
                continue
            
            # Appliquer l'effet (attenue avec la distance)
            distance = len(visited) - 1
            attenuated_value = value * (0.8 ** distance)
            
            if effect == "power_boost":
                fragment.mass *= (1 + attenuated_value)
            elif effect == "purify":
                fragment.purity = min(100, fragment.purity + attenuated_value)
            elif effect == "corrupt":
                if fragment.soul:
                    fragment.soul['corruption_level'] = min(1.0, 
                        fragment.soul.get('corruption_level', 0) + attenuated_value)
            
            self._save_fragment(fragment)
            
            # Ajouter les fragments intriques
            for entangled_id in fragment.entangled_fragments:
                if entangled_id not in visited:
                    to_visit.append(entangled_id)
        
        return len(visited)
    
    # ========================================================================
    # PROPHETIES
    # ========================================================================
    
    def generate_prophecy(self, omen_fragment_id: str) -> Tuple[bool, str]:
        """Genere une prophetie a partir d'un fragment Omen"""
        
        fragment = self._fragments.get(omen_fragment_id)
        if not fragment or fragment.fragment_type not in ['omen', 'prophecy', 'oracle']:
            return False, "Fragment prophetique requis"
        
        # Types de propheties
        prophecies = [
            "Quand {n} fragments de {essence} se reuniront, un grand pouvoir emergera.",
            "Le vault #{vault} connitra une transformation majeure lors du cycle {cycle}.",
            "Une constellation sera completee avant la fin du {n}eme cycle.",
            "Un fragment Divine apparaitra quand la Pleine Lune brillera trois fois.",
            "L'intrication de 7 fragments ouvrira le chemin vers la Pierre Philosophale.",
            "Celui qui forge {n} Voix en un seul Decret gouvernera le Nexus.",
            "Le prochain Oracle revelera l'emplacement d'une recette perdue.",
            "Quand l'entropie atteindra {n}%, un reset cosmique surviendra.",
            "Le fragment primordial attend dans le vault le plus ancien.",
            "Sept essences unies forgeront la Couronne ultime.",
        ]
        
        # Generer la prophetie
        prophecy_template = secrets.choice(prophecies)
        prophecy_text = prophecy_template.format(
            n=secrets.randbelow(10) + 3,
            essence=secrets.choice(list(FragmentEssence)).display_name,
            vault=secrets.randbelow(100) + 1,
            cycle=secrets.choice(CosmicCycle.LUNAR_PHASES)[2]
        )
        
        # Date cible
        days_until = secrets.randbelow(60) + 7
        target_date = (datetime.now() + timedelta(days=days_until)).isoformat()
        
        fragment.prophecy_text = prophecy_text
        fragment.prophecy_target_date = target_date
        self._save_fragment(fragment)
        
        return True, prophecy_text
    
    # ========================================================================
    # STATISTIQUES
    # ========================================================================
    
    def get_statistics(self) -> Dict:
        """Retourne les statistiques globales du nexus"""
        
        active_fragments = [f for f in self._fragments.values() if f.status == "active"]
        
        essence_counts = {}
        type_counts = {}
        total_mass = 0
        total_voting_power = 0
        entanglement_count = 0
        
        for f in active_fragments:
            essence_counts[f.essence] = essence_counts.get(f.essence, 0) + 1
            type_counts[f.fragment_type] = type_counts.get(f.fragment_type, 0) + 1
            total_mass += f.mass
            total_voting_power += f.voting_power
            entanglement_count += len(f.entangled_fragments)
        
        return {
            "total_fragments": len(active_fragments),
            "total_mass": total_mass,
            "total_voting_power": total_voting_power,
            "entanglement_pairs": entanglement_count // 2,
            "by_essence": essence_counts,
            "by_type": type_counts,
            "discovered_recipes": len(self._discovered_recipes),
            "total_recipes": len(ALCHEMICAL_RECIPES),
            "active_proposals": len([p for p in self._proposals.values() if p.status == "active"]),
            "current_cycle": CosmicCycle.get_current_phase()[2],
            "market_modifier": CosmicCycle.get_market_modifier(),
        }
    
    def get_vault_fragments(self, vault_number: int) -> List[Fragment]:
        """Retourne les fragments d'un vault"""
        return [f for f in self._fragments.values() 
                if f.current_vault == vault_number and f.status == "active"]
    
    def get_all_fragments(self) -> List[Fragment]:
        """Retourne tous les fragments actifs"""
        return [f for f in self._fragments.values() if f.status == "active"]


# ============================================================================
# AFFICHAGE
# ============================================================================

def format_fragment_display(fragment: Fragment) -> str:
    """Format d'affichage d'un fragment"""
    essence = next((e for e in FragmentEssence if e.essence_id == fragment.essence), None)
    ftype = next((t for t in FragmentType if t.type_id == fragment.fragment_type), None)
    
    essence_sym = essence.symbol if essence else "?"
    type_sym = ftype.symbol if ftype else "?"
    type_name = ftype.display_name if ftype else "?"
    
    soul_indicator = "☼" if fragment.soul else " "
    entangled = f"⚡{len(fragment.entangled_fragments)}" if fragment.entangled_fragments else ""
    
    return (f"{essence_sym}{type_sym} {soul_indicator} [{type_name:12}] "
            f"M:{fragment.mass:>8.1f} P:{fragment.purity:>5.1f}% "
            f"S:{fragment.stability:>5.1f}% {entangled}")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  FRAGMENT NEXUS - Alchemical Economy System")
    print("="*70)
    
    nexus = FragmentNexus()
    stats = nexus.get_statistics()
    
    print(f"\n  Total Fragments: {stats['total_fragments']}")
    print(f"  Total Mass: {stats['total_mass']:,.1f}")
    print(f"  Voting Power: {stats['total_voting_power']:,.1f}")
    print(f"  Entanglement Pairs: {stats['entanglement_pairs']}")
    print(f"  Discovered Recipes: {stats['discovered_recipes']}/{stats['total_recipes']}")
    
    # Cycle actuel
    phase_idx, phase_id, phase_sym, phase_name, modifiers = CosmicCycle.get_current_phase()
    print(f"\n  Current Cosmic Cycle: {phase_sym} {phase_name}")
    print(f"  Market Modifier: x{stats['market_modifier']:.2f}")
    
    # Afficher les essences
    print("\n  BY ESSENCE:")
    for essence in FragmentEssence:
        count = stats['by_essence'].get(essence.essence_id, 0)
        if count > 0:
            print(f"    {essence.symbol} {essence.display_name:20}: {count}")
    
    # Afficher les types
    print("\n  BY TYPE:")
    for ftype in FragmentType:
        count = stats['by_type'].get(ftype.type_id, 0)
        if count > 0:
            print(f"    {ftype.symbol} {ftype.display_name:20}: {count}")
    
    # Recettes decouvertes
    print(f"\n  DISCOVERED RECIPES ({len(nexus._discovered_recipes)}):")
    for recipe_id in sorted(nexus._discovered_recipes):
        recipe = ALCHEMICAL_RECIPES.get(recipe_id)
        if recipe:
            print(f"    ⚗ {recipe.name}: {recipe.description[:50]}...")
    
    # Constellations
    print(f"\n  CONSTELLATIONS AVAILABLE ({len(CONSTELLATIONS)}):")
    for const_id, const in CONSTELLATIONS.items():
        print(f"    ✦ {const.name}: {const.description}")
    
    print("\n" + "="*70)
