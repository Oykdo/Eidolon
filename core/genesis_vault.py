"""
Systeme Genesis Vault Evolutif pour Poly-Spinor Nexus 7D
=========================================================

Chaque nouveau vault herite de la force collective de tous les vaults precedents,
creant une chaine cryptographique de plus en plus puissante.

Architecture:
- Genesis Block: Bloc fondateur avec heritage evolutif
- Collective Strength: Force cumulative du reseau
- Founder Rewards: Recompenses en runes Bitcoin
- Runic Inscriptions: Inscriptions permanentes sur Bitcoin
- Genealogy Tree: Arbre des relations entre vaults

Tiers Fondateurs:
- Quantum Pioneer (1-100): 1 milliard runes + multiplicateur 10x
- Spinor Visionary (101-1,000): 100M runes + multiplicateur 5x
- Bell Verifier (1,001-10,000): 10M runes + multiplicateur 2x
- Post-Quantum Guardian (10,001-100,000): 1M runes + multiplicateur 1.5x
"""

import os
import json
import hashlib
import secrets
import math
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
import struct


# ============================================================================
# CONSTANTES RUNIQUES
# ============================================================================

RUNIC_SYMBOLS = {
    "FEHU": "ᚠ",      # Richesse, creation
    "URUZ": "ᚢ",      # Force, potentiel
    "THURISAZ": "ᚦ",  # Protection, defense
    "ANSUZ": "ᚨ",     # Sagesse, communication
    "RAIDHO": "ᚱ",    # Voyage, evolution
    "KENAZ": "ᚲ",     # Connaissance, illumination
    "GEBO": "ᚷ",      # Don, partenariat
    "WUNJO": "ᚹ",     # Joie, harmonie
    "HAGALAZ": "ᚺ",   # Transformation, changement
    "NAUTHIZ": "ᚾ",   # Necessite, resistance
    "ISA": "ᛁ",       # Glace, concentration
    "JERA": "ᛃ",      # Cycle, recolte
    "EIHWAZ": "ᛇ",    # Stabilite, endurance
    "PERTHRO": "ᛈ",   # Mystere, destin
    "ALGIZ": "ᛉ",     # Protection, eveil
    "SOWILO": "ᛊ",    # Soleil, victoire
    "TIWAZ": "ᛏ",     # Justice, honneur
    "BERKANO": "ᛒ",   # Renaissance, croissance
    "EHWAZ": "ᛖ",     # Mouvement, progres
    "MANNAZ": "ᛗ",    # Humanite, conscience
    "LAGUZ": "ᛚ",     # Eau, intuition
    "INGWAZ": "ᛝ",    # Fertilite, accomplissement
    "DAGAZ": "ᛞ",     # Jour, percee
    "OTHALA": "ᛟ",    # Heritage, ancestral
}

TIER_RUNES = {
    "quantum_pioneer": ["FEHU", "SOWILO", "DAGAZ", "OTHALA"],      # Creation + Victoire + Percee + Heritage
    "spinor_visionary": ["ANSUZ", "KENAZ", "PERTHRO", "MANNAZ"],   # Sagesse + Connaissance + Mystere + Conscience
    "bell_verifier": ["THURISAZ", "ALGIZ", "TIWAZ", "EIHWAZ"],     # Protection + Eveil + Justice + Stabilite
    "post_quantum_guardian": ["URUZ", "HAGALAZ", "NAUTHIZ", "ISA"] # Force + Transformation + Resistance + Concentration
}


# ============================================================================
# ENUMERATIONS
# ============================================================================

class FounderTier(Enum):
    """Tiers des fondateurs"""
    QUANTUM_PIONEER = "quantum_pioneer"           # 1-100
    SPINOR_VISIONARY = "spinor_visionary"         # 101-1,000
    BELL_VERIFIER = "bell_verifier"               # 1,001-10,000
    POST_QUANTUM_GUARDIAN = "post_quantum_guardian"  # 10,001-100,000
    STANDARD = "standard"                          # > 100,000


class GenesisType(Enum):
    """Types de blocs Genesis"""
    PRIMORDIAL = "primordial"    # Bloc 0, le tout premier
    FOUNDER = "founder"          # Blocs fondateurs (1-100,000)
    STANDARD = "standard"        # Blocs standards
    MERGED = "merged"            # Bloc issu d'une fusion


class InscriptionStatus(Enum):
    """Statut d'inscription Bitcoin"""
    PENDING = "pending"
    INSCRIBED = "inscribed"
    CONFIRMED = "confirmed"
    FAILED = "failed"


# ============================================================================
# CONFIGURATION DES TIERS
# ============================================================================

@dataclass
class TierConfig:
    """Configuration d'un tier fondateur"""
    tier: FounderTier
    name: str
    rarity: str
    min_number: int
    max_number: int
    rune_reward: int
    strength_multiplier: float
    runes: List[str]
    color: str
    special_abilities: List[str]

    def to_dict(self) -> dict:
        d = asdict(self)
        d['tier'] = self.tier.value
        return d


TIER_CONFIGS = {
    FounderTier.QUANTUM_PIONEER: TierConfig(
        tier=FounderTier.QUANTUM_PIONEER,
        name="Quantum Pioneer",
        rarity="Mythic",
        min_number=1,
        max_number=100,
        rune_reward=1_000_000_000,  # 1 milliard
        strength_multiplier=10.0,
        runes=TIER_RUNES["quantum_pioneer"],
        color="#FFD700",  # Or
        special_abilities=[
            "quantum_resonance",      # Bonus de force quantique
            "primordial_link",        # Lien direct au bloc primordial
            "infinite_inheritance",   # Heritage illimite
            "rune_mastery"           # Maitrise des runes
        ]
    ),
    FounderTier.SPINOR_VISIONARY: TierConfig(
        tier=FounderTier.SPINOR_VISIONARY,
        name="Spinor Visionary",
        rarity="Legendary",
        min_number=101,
        max_number=1000,
        rune_reward=100_000_000,  # 100 millions
        strength_multiplier=5.0,
        runes=TIER_RUNES["spinor_visionary"],
        color="#9400D3",  # Violet
        special_abilities=[
            "spinor_mastery",         # Maitrise spinorielle
            "vision_7d",              # Vision en 7D
            "enhanced_inheritance"    # Heritage ameliore
        ]
    ),
    FounderTier.BELL_VERIFIER: TierConfig(
        tier=FounderTier.BELL_VERIFIER,
        name="Bell Verifier",
        rarity="Epic",
        min_number=1001,
        max_number=10000,
        rune_reward=10_000_000,  # 10 millions
        strength_multiplier=2.0,
        runes=TIER_RUNES["bell_verifier"],
        color="#00CED1",  # Turquoise
        special_abilities=[
            "bell_verification",      # Verification de Bell
            "entanglement_boost"      # Boost d'intrication
        ]
    ),
    FounderTier.POST_QUANTUM_GUARDIAN: TierConfig(
        tier=FounderTier.POST_QUANTUM_GUARDIAN,
        name="Post-Quantum Guardian",
        rarity="Rare",
        min_number=10001,
        max_number=100000,
        rune_reward=1_000_000,  # 1 million
        strength_multiplier=1.5,
        runes=TIER_RUNES["post_quantum_guardian"],
        color="#32CD32",  # Vert
        special_abilities=[
            "quantum_resistance"      # Resistance quantique
        ]
    )
}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class CollectiveStrength:
    """Force collective du reseau"""
    total_vaults: int = 0
    cumulative_entropy: int = 0           # Bits d'entropie cumules
    network_hash_power: float = 0.0       # Puissance de hash relative
    founder_multiplier: float = 1.0       # Multiplicateur des fondateurs
    
    # Statistiques par tier
    tier_counts: Dict[str, int] = field(default_factory=dict)
    
    # Force calculee
    base_strength: float = 0.0
    boosted_strength: float = 0.0
    
    def calculate(self):
        """Calcule la force collective"""
        # Force de base: log2 du nombre de vaults * entropie moyenne
        if self.total_vaults > 0:
            avg_entropy = self.cumulative_entropy / self.total_vaults
            self.base_strength = math.log2(self.total_vaults + 1) * avg_entropy
        
        # Force boostee par les fondateurs
        self.boosted_strength = self.base_strength * self.founder_multiplier
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RunicInscription:
    """Inscription runique pour Bitcoin"""
    inscription_id: str
    vault_number: int
    tier: FounderTier
    runes: List[str]
    rune_symbols: str
    
    # Contenu de l'inscription
    content: Dict[str, Any] = field(default_factory=dict)
    
    # Bitcoin
    txid: Optional[str] = None
    block_height: Optional[int] = None
    sat_number: Optional[int] = None
    
    # Status
    status: InscriptionStatus = InscriptionStatus.PENDING
    created_at: str = ""
    inscribed_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['tier'] = self.tier.value
        d['status'] = self.status.value
        return d
    
    def generate_ordinal_content(self) -> Dict[str, Any]:
        """Genere le contenu pour inscription Ordinal"""
        return {
            "p": "psnx",
            "op": "genesis",
            "vault": self.vault_number,
            "tier": self.tier.value,
            "runes": self.rune_symbols,
            "content": self.content,
            "ts": int(time.time())
        }


@dataclass
class GenesisBlock:
    """Bloc Genesis evolutif"""
    # Identifiants
    block_id: str
    vault_number: int
    vault_name: str
    genesis_type: GenesisType
    
    # Timestamps
    created_at: str
    
    # Heritage
    parent_hash: Optional[str] = None       # Hash du bloc parent
    parent_number: Optional[int] = None     # Numero du vault parent
    ancestry_depth: int = 0                  # Profondeur dans l'arbre
    ancestor_hashes: List[str] = field(default_factory=list)  # Tous les ancetres
    
    # Force
    inherited_strength: float = 0.0          # Force heritee des ancetres
    own_entropy: int = 0                     # Entropie propre (bits)
    total_strength: float = 0.0              # Force totale
    
    # Fondateur
    tier: Optional[FounderTier] = None
    tier_config: Optional[Dict] = None
    is_founder: bool = False
    
    # Runes
    runic_inscription: Optional[RunicInscription] = None
    rune_balance: int = 0
    
    # Hash et signature
    block_hash: str = ""
    signature: str = ""
    signer_public_key: str = ""              # Cle publique du signataire
    signed_at: Optional[str] = None          # Date de signature
    
    # Donnees cryptographiques
    spinor_seed: str = ""                    # Seed spinoriel
    bell_proof: str = ""                     # Preuve de Bell
    merkle_root: str = ""                    # Racine Merkle
    
    def __post_init__(self):
        if not self.block_hash:
            self.block_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Calcule le hash du bloc"""
        data = {
            "block_id": self.block_id,
            "vault_number": self.vault_number,
            "parent_hash": self.parent_hash,
            "created_at": self.created_at,
            "own_entropy": self.own_entropy,
            "spinor_seed": self.spinor_seed
        }
        
        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['genesis_type'] = self.genesis_type.value
        d['tier'] = self.tier.value if self.tier else None
        
        if self.runic_inscription:
            d['runic_inscription'] = self.runic_inscription.to_dict()
        
        return d
    
    @classmethod
    def from_dict(cls, data: dict) -> "GenesisBlock":
        """Reconstruit depuis un dictionnaire"""
        data['genesis_type'] = GenesisType(data['genesis_type'])
        
        if data.get('tier'):
            data['tier'] = FounderTier(data['tier'])
        
        if data.get('runic_inscription'):
            ri = data['runic_inscription']
            ri['tier'] = FounderTier(ri['tier'])
            ri['status'] = InscriptionStatus(ri['status'])
            data['runic_inscription'] = RunicInscription(**ri)
        
        return cls(**data)


@dataclass  
class VaultLineage:
    """Lignee d'un vault"""
    vault_number: int
    ancestors: List[int]           # Numeros des ancetres
    descendants: List[int]         # Numeros des descendants
    siblings: List[int]            # Vaults du meme parent
    depth: int                     # Profondeur dans l'arbre
    
    # Force de lignee
    lineage_strength: float = 0.0
    
    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================================
# GESTIONNAIRE DE GENESIS EVOLUTIF
# ============================================================================

class EvolutiveGenesisManager:
    """Gestionnaire du systeme Genesis evolutif"""
    
    def __init__(self, data_dir: str = "./genesis_data"):
        self.data_dir = Path(data_dir)
        self.blocks_dir = self.data_dir / "blocks"
        self.inscriptions_dir = self.data_dir / "inscriptions"
        
        for d in [self.blocks_dir, self.inscriptions_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Cache
        self._blocks: Dict[int, GenesisBlock] = {}
        self._collective_strength = CollectiveStrength()
        
        # Charger l'etat
        self._load_state()
    
    def _load_state(self):
        """Charge l'etat depuis le disque"""
        state_file = self.data_dir / "state.json"
        
        if state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                self._collective_strength = CollectiveStrength(**state.get('collective_strength', {}))
        
        # Charger les blocs
        for block_file in self.blocks_dir.glob("*.json"):
            with open(block_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                block = GenesisBlock.from_dict(data)
                self._blocks[block.vault_number] = block
    
    def _save_state(self):
        """Sauvegarde l'etat sur le disque"""
        state = {
            "collective_strength": self._collective_strength.to_dict(),
            "total_blocks": len(self._blocks),
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.data_dir / "state.json", 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    
    def _save_block(self, block: GenesisBlock):
        """Sauvegarde un bloc"""
        self._blocks[block.vault_number] = block
        
        with open(self.blocks_dir / f"block_{block.vault_number:08d}.json", 'w', encoding='utf-8') as f:
            json.dump(block.to_dict(), f, indent=2, ensure_ascii=False)
    
    def get_next_vault_number(self) -> int:
        """Obtient le prochain numero de vault"""
        if not self._blocks:
            return 1
        return max(self._blocks.keys()) + 1
    
    def get_tier_for_number(self, vault_number: int) -> Optional[FounderTier]:
        """Determine le tier pour un numero de vault"""
        for tier, config in TIER_CONFIGS.items():
            if config.min_number <= vault_number <= config.max_number:
                return tier
        return None
    
    def get_parent_block(self) -> Optional[GenesisBlock]:
        """Obtient le bloc parent (le plus recent)"""
        if not self._blocks:
            return None
        
        latest_number = max(self._blocks.keys())
        return self._blocks[latest_number]
    
    def calculate_inherited_strength(self, parent: Optional[GenesisBlock]) -> Tuple[float, List[str]]:
        """Calcule la force heritee et les ancetres"""
        if not parent:
            return 0.0, []
        
        # Collecter tous les ancetres
        ancestors = parent.ancestor_hashes.copy()
        ancestors.append(parent.block_hash)
        
        # Calculer la force heritee
        # Formule: sum(strength_i * decay^(depth - depth_i))
        inherited = 0.0
        decay = 0.95  # Facteur de decroissance par generation
        
        for i, ancestor_hash in enumerate(ancestors):
            # Trouver le bloc ancetre
            for block in self._blocks.values():
                if block.block_hash == ancestor_hash:
                    depth_diff = len(ancestors) - i
                    contribution = block.total_strength * (decay ** depth_diff)
                    inherited += contribution
                    break
        
        # Ajouter la force du parent direct (sans decay)
        inherited += parent.total_strength * 0.5
        
        return inherited, ancestors
    
    def generate_runic_inscription(self, vault_number: int, tier: FounderTier) -> RunicInscription:
        """Genere une inscription runique"""
        config = TIER_CONFIGS[tier]
        
        # Obtenir les symboles runiques
        rune_symbols = "".join(RUNIC_SYMBOLS[r] for r in config.runes)
        
        inscription = RunicInscription(
            inscription_id=f"psnx_{vault_number:08d}_{secrets.token_hex(8)}",
            vault_number=vault_number,
            tier=tier,
            runes=config.runes,
            rune_symbols=rune_symbols,
            content={
                "tier_name": config.name,
                "rarity": config.rarity,
                "reward": config.rune_reward,
                "multiplier": config.strength_multiplier,
                "abilities": config.special_abilities
            },
            created_at=datetime.now().isoformat()
        )
        
        return inscription
    
    def create_genesis_block(self, vault_name: str, 
                            spinor_data: Dict[str, Any] = None) -> GenesisBlock:
        """Cree un nouveau bloc Genesis evolutif"""
        vault_number = self.get_next_vault_number()
        parent = self.get_parent_block()
        
        # Determiner le type et le tier
        if vault_number == 1:
            genesis_type = GenesisType.PRIMORDIAL
        elif vault_number <= 100000:
            genesis_type = GenesisType.FOUNDER
        else:
            genesis_type = GenesisType.STANDARD
        
        tier = self.get_tier_for_number(vault_number)
        tier_config = TIER_CONFIGS.get(tier).to_dict() if tier else None
        
        # Calculer l'heritage
        inherited_strength, ancestor_hashes = self.calculate_inherited_strength(parent)
        
        # Entropie propre (simulee si pas de donnees spinor)
        if spinor_data:
            own_entropy = spinor_data.get('total_entropy', 8192)
            spinor_seed = spinor_data.get('spinor_hash', secrets.token_hex(32))
            bell_proof = spinor_data.get('bell_proof', secrets.token_hex(64))
            merkle_root = spinor_data.get('merkle_root', secrets.token_hex(32))
        else:
            own_entropy = 8192
            spinor_seed = secrets.token_hex(32)
            bell_proof = secrets.token_hex(64)
            merkle_root = secrets.token_hex(32)
        
        # Calculer la force totale
        multiplier = tier_config['strength_multiplier'] if tier_config else 1.0
        total_strength = (inherited_strength + own_entropy) * multiplier
        
        # Creer le bloc
        block = GenesisBlock(
            block_id=f"genesis_{vault_number:08d}_{secrets.token_hex(8)}",
            vault_number=vault_number,
            vault_name=vault_name,
            genesis_type=genesis_type,
            created_at=datetime.now().isoformat(),
            parent_hash=parent.block_hash if parent else None,
            parent_number=parent.vault_number if parent else None,
            ancestry_depth=len(ancestor_hashes),
            ancestor_hashes=ancestor_hashes,
            inherited_strength=inherited_strength,
            own_entropy=own_entropy,
            total_strength=total_strength,
            tier=tier,
            tier_config=tier_config,
            is_founder=tier is not None,
            spinor_seed=spinor_seed,
            bell_proof=bell_proof,
            merkle_root=merkle_root
        )
        
        # Generer l'inscription runique si fondateur
        if tier:
            block.runic_inscription = self.generate_runic_inscription(vault_number, tier)
            block.rune_balance = TIER_CONFIGS[tier].rune_reward
        
        # Calculer le hash final
        block.block_hash = block._compute_hash()
        
        # Mettre a jour la force collective
        self._update_collective_strength(block)
        
        # Sauvegarder
        self._save_block(block)
        self._save_state()
        
        return block
    
    def _update_collective_strength(self, new_block: GenesisBlock):
        """Met a jour la force collective"""
        cs = self._collective_strength
        
        cs.total_vaults += 1
        cs.cumulative_entropy += new_block.own_entropy
        
        # Compter par tier
        if new_block.tier:
            tier_key = new_block.tier.value
            cs.tier_counts[tier_key] = cs.tier_counts.get(tier_key, 0) + 1
        
        # Recalculer le multiplicateur fondateur
        total_multiplier = 1.0
        for tier, config in TIER_CONFIGS.items():
            count = cs.tier_counts.get(tier.value, 0)
            if count > 0:
                # Contribution decroissante avec le nombre
                contribution = config.strength_multiplier * math.log2(count + 1) / count
                total_multiplier += contribution
        
        cs.founder_multiplier = total_multiplier
        cs.calculate()
    
    def get_vault_lineage(self, vault_number: int) -> Optional[VaultLineage]:
        """Obtient la lignee d'un vault"""
        block = self._blocks.get(vault_number)
        
        if not block:
            return None
        
        # Trouver les ancetres
        ancestors = []
        for b in self._blocks.values():
            if b.block_hash in block.ancestor_hashes:
                ancestors.append(b.vault_number)
        
        # Trouver les descendants
        descendants = []
        for b in self._blocks.values():
            if block.block_hash in b.ancestor_hashes:
                descendants.append(b.vault_number)
        
        # Trouver les siblings (meme parent)
        siblings = []
        if block.parent_hash:
            for b in self._blocks.values():
                if b.parent_hash == block.parent_hash and b.vault_number != vault_number:
                    siblings.append(b.vault_number)
        
        return VaultLineage(
            vault_number=vault_number,
            ancestors=sorted(ancestors),
            descendants=sorted(descendants),
            siblings=sorted(siblings),
            depth=block.ancestry_depth,
            lineage_strength=block.inherited_strength + block.total_strength
        )
    
    def get_block(self, vault_number: int) -> Optional[GenesisBlock]:
        """Recupere un bloc par numero"""
        return self._blocks.get(vault_number)
    
    def get_collective_strength(self) -> CollectiveStrength:
        """Obtient la force collective actuelle"""
        return self._collective_strength
    
    def get_all_founders(self) -> List[GenesisBlock]:
        """Liste tous les blocs fondateurs"""
        return [b for b in self._blocks.values() if b.is_founder]
    
    def get_tier_stats(self) -> Dict[str, Dict]:
        """Statistiques par tier"""
        stats = {}
        
        for tier, config in TIER_CONFIGS.items():
            founders = [b for b in self._blocks.values() if b.tier == tier]
            
            remaining = config.max_number - config.min_number + 1 - len(founders)
            
            stats[tier.value] = {
                "name": config.name,
                "rarity": config.rarity,
                "count": len(founders),
                "max": config.max_number - config.min_number + 1,
                "remaining": max(0, remaining),
                "rune_reward": config.rune_reward,
                "multiplier": config.strength_multiplier,
                "color": config.color,
                "runes": "".join(RUNIC_SYMBOLS[r] for r in config.runes)
            }
        
        return stats


# ============================================================================
# VISUALISATION DE L'ARBRE GENEALOGIQUE
# ============================================================================

class GenealogyVisualizer:
    """Visualisation de l'arbre genealogique des vaults"""
    
    def __init__(self, manager: EvolutiveGenesisManager):
        self.manager = manager
    
    def generate_ascii_tree(self, max_depth: int = 10) -> str:
        """Genere un arbre ASCII"""
        lines = []
        lines.append("=" * 60)
        lines.append("  ARBRE GENEALOGIQUE DES VAULTS GENESIS")
        lines.append("=" * 60)
        
        blocks = sorted(self.manager._blocks.values(), key=lambda b: b.vault_number)
        
        if not blocks:
            lines.append("  (Aucun vault cree)")
            return "\n".join(lines)
        
        for block in blocks[:max_depth]:
            indent = "  " * min(block.ancestry_depth, 5)
            
            # Symbole selon le type
            if block.genesis_type == GenesisType.PRIMORDIAL:
                symbol = "◆"
            elif block.tier == FounderTier.QUANTUM_PIONEER:
                symbol = "★"
            elif block.tier == FounderTier.SPINOR_VISIONARY:
                symbol = "◇"
            elif block.tier == FounderTier.BELL_VERIFIER:
                symbol = "○"
            elif block.tier == FounderTier.POST_QUANTUM_GUARDIAN:
                symbol = "□"
            else:
                symbol = "·"
            
            # Runes
            runes = ""
            if block.runic_inscription:
                runes = f" {block.runic_inscription.rune_symbols}"
            
            # Ligne
            tier_name = block.tier_config['name'] if block.tier_config else "Standard"
            line = f"{indent}{symbol} #{block.vault_number:05d} [{tier_name}]{runes}"
            line += f" | Force: {block.total_strength:.0f}"
            
            lines.append(line)
        
        if len(blocks) > max_depth:
            lines.append(f"  ... et {len(blocks) - max_depth} autres vaults")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def generate_mermaid_diagram(self, max_nodes: int = 20) -> str:
        """Genere un diagramme Mermaid"""
        lines = ["graph TD"]
        
        blocks = sorted(self.manager._blocks.values(), key=lambda b: b.vault_number)[:max_nodes]
        
        for block in blocks:
            # Style selon tier
            if block.tier == FounderTier.QUANTUM_PIONEER:
                style = ":::gold"
            elif block.tier == FounderTier.SPINOR_VISIONARY:
                style = ":::purple"
            elif block.tier == FounderTier.BELL_VERIFIER:
                style = ":::cyan"
            elif block.tier == FounderTier.POST_QUANTUM_GUARDIAN:
                style = ":::green"
            else:
                style = ""
            
            node_id = f"V{block.vault_number}"
            label = f"#{block.vault_number}"
            
            if block.runic_inscription:
                label += f"<br/>{block.runic_inscription.rune_symbols}"
            
            lines.append(f"    {node_id}[\"{label}\"]{style}")
            
            # Lien vers parent
            if block.parent_number:
                lines.append(f"    V{block.parent_number} --> {node_id}")
        
        # Styles
        lines.append("")
        lines.append("    classDef gold fill:#FFD700,stroke:#B8860B")
        lines.append("    classDef purple fill:#9400D3,stroke:#4B0082")
        lines.append("    classDef cyan fill:#00CED1,stroke:#008B8B")
        lines.append("    classDef green fill:#32CD32,stroke:#228B22")
        
        return "\n".join(lines)
    
    def generate_stats_display(self) -> str:
        """Genere l'affichage des statistiques"""
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("  STATISTIQUES DU RESEAU GENESIS EVOLUTIF")
        lines.append("=" * 70)
        
        cs = self.manager.get_collective_strength()
        
        lines.append(f"\n  Total Vaults: {cs.total_vaults}")
        lines.append(f"  Entropie Cumulative: {cs.cumulative_entropy:,} bits")
        lines.append(f"  Force de Base: {cs.base_strength:,.2f}")
        lines.append(f"  Force Boostee: {cs.boosted_strength:,.2f}")
        lines.append(f"  Multiplicateur Fondateurs: {cs.founder_multiplier:.2f}x")
        
        lines.append("\n  TIERS FONDATEURS:")
        lines.append("  " + "-" * 66)
        
        stats = self.manager.get_tier_stats()
        
        for tier_key, tier_stats in stats.items():
            runes = tier_stats['runes']
            name = tier_stats['name']
            count = tier_stats['count']
            remaining = tier_stats['remaining']
            reward = tier_stats['rune_reward']
            
            lines.append(f"  {runes} {name}")
            lines.append(f"      Crees: {count} | Restants: {remaining}")
            lines.append(f"      Recompense: {reward:,} runes | Multiplicateur: {tier_stats['multiplier']}x")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


# ============================================================================
# INSCRIPTION BITCOIN RUNE PROTOCOL
# ============================================================================

class BitcoinRuneInscriber:
    """Inscripteur Bitcoin Rune Protocol"""
    
    def __init__(self, network: str = "testnet"):
        self.network = network
        self.api_url = "https://mempool.space/testnet/api" if network == "testnet" else "https://mempool.space/api"
    
    def prepare_inscription(self, block: GenesisBlock) -> Dict[str, Any]:
        """Prepare une inscription pour un bloc Genesis"""
        if not block.runic_inscription:
            raise ValueError("Block has no runic inscription")
        
        inscription = block.runic_inscription
        
        # Contenu de l'inscription
        content = {
            "p": "psnx-genesis",
            "op": "mint",
            "tick": "PSNX",
            "vault": block.vault_number,
            "tier": block.tier.value if block.tier else "standard",
            "runes": inscription.rune_symbols,
            "strength": int(block.total_strength),
            "ancestry": block.ancestry_depth,
            "reward": inscription.content.get('reward', 0),
            "ts": int(time.time()),
            "hash": block.block_hash[:16]
        }
        
        # Encoder en JSON compact
        json_content = json.dumps(content, separators=(',', ':'))
        
        return {
            "content_type": "application/json",
            "content": json_content,
            "content_bytes": json_content.encode(),
            "metadata": {
                "vault_number": block.vault_number,
                "tier": block.tier.value if block.tier else None,
                "runes": inscription.rune_symbols
            }
        }
    
    def generate_commit_tx(self, inscription_data: Dict, 
                          funding_utxo: Dict) -> Dict[str, Any]:
        """Genere la transaction commit (simplifie)"""
        # En production, utiliserait une vraie librairie Bitcoin
        
        commit_tx = {
            "type": "commit",
            "inputs": [funding_utxo],
            "outputs": [
                {
                    "type": "taproot_commit",
                    "value": 10000,  # sats
                    "script": hashlib.sha256(
                        inscription_data['content_bytes']
                    ).hexdigest()
                }
            ],
            "inscription": inscription_data['content']
        }
        
        return commit_tx
    
    def generate_reveal_tx(self, commit_txid: str, 
                          inscription_data: Dict) -> Dict[str, Any]:
        """Genere la transaction reveal (simplifie)"""
        reveal_tx = {
            "type": "reveal",
            "inputs": [{"txid": commit_txid, "vout": 0}],
            "outputs": [
                {
                    "type": "inscription",
                    "value": 546,  # dust limit
                    "inscription": inscription_data['content']
                }
            ],
            "witness": {
                "content_type": inscription_data['content_type'],
                "content": inscription_data['content']
            }
        }
        
        return reveal_tx
    
    def estimate_fees(self, inscription_data: Dict) -> Dict[str, int]:
        """Estime les frais d'inscription"""
        content_size = len(inscription_data['content_bytes'])
        
        # Estimation basee sur la taille
        commit_vbytes = 150
        reveal_vbytes = 100 + content_size
        
        # Frais estimes (sats/vbyte)
        fee_rate = 10  # Ajuster selon le mempool
        
        return {
            "commit_fee": commit_vbytes * fee_rate,
            "reveal_fee": reveal_vbytes * fee_rate,
            "total_fee": (commit_vbytes + reveal_vbytes) * fee_rate,
            "content_size": content_size
        }


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_evolutive_genesis_manager(data_dir: str = "./genesis_data") -> EvolutiveGenesisManager:
    """Cree un gestionnaire Genesis evolutif"""
    return EvolutiveGenesisManager(data_dir)


def create_genealogy_visualizer(manager: EvolutiveGenesisManager) -> GenealogyVisualizer:
    """Cree un visualiseur de genealogie"""
    return GenealogyVisualizer(manager)


def create_rune_inscriber(network: str = "testnet") -> BitcoinRuneInscriber:
    """Cree un inscripteur Bitcoin Rune"""
    return BitcoinRuneInscriber(network)
