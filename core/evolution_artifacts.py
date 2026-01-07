#!/usr/bin/env python3
"""
Artefacts d'Evolution - Poly-Spinor Nexus 7D
Systeme de creation et distribution des artefacts pour l'evolution des avatars
"""

import json
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum


class EvolutionArtifactType(Enum):
    """Types d'artefacts d'evolution"""
    GENESIS_GLYPH = "genesis_glyph"
    COSMIC_LENS = "cosmic_lens"
    INFINITY_FRAGMENT = "infinity_fragment"
    SOUL_ANCHOR = "soul_anchor"
    DIVINE_SEAL = "divine_seal"
    ORIGIN_KEY = "origin_key"


class EvolutionArtifactRarity(Enum):
    """Rarete des artefacts d'evolution"""
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHICAL = "mythical"
    TRANSCENDENT = "transcendent"
    PRIMORDIAL = "primordial"


@dataclass
class EvolutionArtifact:
    """Artefact utilise pour l'evolution des avatars"""
    artifact_id: str
    artifact_type: str
    name: str
    description: str
    rarity: str
    evolution_stage: str  # Stade d'evolution debloques
    
    # Stats
    power_bonus: float = 1.0
    stat_bonuses: Dict[str, float] = field(default_factory=dict)
    
    # Visuels
    visual_effects: List[str] = field(default_factory=list)
    color_primary: str = "#ffffff"
    color_secondary: str = "#888888"
    glow_intensity: float = 1.0
    
    # Capacites
    abilities: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadonnees
    created_at: str = ""
    vault_id: Optional[str] = None
    origin_vault: Optional[int] = None  # Numero du vault (pour compatibilite)
    current_vault: Optional[int] = None  # Proprietaire actuel
    bound_to_avatar: Optional[str] = None
    is_bound: bool = False
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "EvolutionArtifact":
        return cls(**data)


# Definitions des 6 artefacts d'evolution
EVOLUTION_ARTIFACT_DEFINITIONS = {
    "genesis_glyph": {
        "name": "Glyphe de Genese",
        "description": "Symbole primordial grave dans l'ether, il eveille le potentiel latent de l'avatar.",
        "rarity": EvolutionArtifactRarity.RARE.value,
        "evolution_stage": "awakened",
        "power_bonus": 1.15,
        "stat_bonuses": {"power": 1.1, "vitality": 1.05},
        "visual_effects": ["genesis_glow", "symbol_pulse"],
        "color_primary": "#00ff88",
        "color_secondary": "#00aa55",
        "glow_intensity": 1.2,
        "abilities": [
            {"id": "awakening_pulse", "name": "Pulse d'Eveil", "description": "Accelere le gain d'XP de 10%", "value": 10},
            {"id": "genesis_mark", "name": "Marque de Genese", "description": "Revele le potentiel cache", "value": 1}
        ],
        "lore": "Forge a l'aube de la creation du Nexus, ce glyphe porte l'empreinte du premier bloc."
    },
    "cosmic_lens": {
        "name": "Lentille Cosmique",
        "description": "Cristal taille dans une etoile morte, il permet de voir au-dela des dimensions.",
        "rarity": EvolutionArtifactRarity.EPIC.value,
        "evolution_stage": "evolved",
        "power_bonus": 1.25,
        "stat_bonuses": {"power": 1.15, "perception": 25, "wisdom": 1.1},
        "visual_effects": ["cosmic_eye", "star_particles", "dimension_sight"],
        "color_primary": "#00ffff",
        "color_secondary": "#0088aa",
        "glow_intensity": 1.5,
        "abilities": [
            {"id": "cosmic_vision", "name": "Vision Cosmique", "description": "Revele les objets caches dans un rayon de {value}m", "value": 100},
            {"id": "star_focus", "name": "Focus Stellaire", "description": "Augmente la precision de {value}%", "value": 15},
            {"id": "dimension_peek", "name": "Apercu Dimensionnel", "description": "Voit a travers {value} dimensions", "value": 2}
        ],
        "lore": "Extraite du coeur de la nebuleuse d'Andromede, cette lentille fut polie par des eons de radiation cosmique."
    },
    "infinity_fragment": {
        "name": "Fragment d'Infini",
        "description": "Eclat de l'infini cristallise, il transcende les limites du possible.",
        "rarity": EvolutionArtifactRarity.LEGENDARY.value,
        "evolution_stage": "ascended",
        "power_bonus": 1.4,
        "stat_bonuses": {"all_stats": 1.2, "power": 1.25, "luck": 1.15},
        "visual_effects": ["infinity_loop", "endless_particles", "fractal_aura"],
        "color_primary": "#bf00ff",
        "color_secondary": "#8800aa",
        "glow_intensity": 1.8,
        "abilities": [
            {"id": "infinite_potential", "name": "Potentiel Infini", "description": "Multiplie tous les bonus par {value}", "value": 1.2},
            {"id": "fractal_shield", "name": "Bouclier Fractal", "description": "Absorbe {value}% des degats", "value": 20},
            {"id": "endless_energy", "name": "Energie Sans Fin", "description": "Regenere {value} energie/sec", "value": 5}
        ],
        "lore": "Ce fragment provient de la frontiere entre l'existant et le non-existant, ou le temps et l'espace perdent leur sens."
    },
    "soul_anchor": {
        "name": "Ancre d'Ame",
        "description": "Chaine etheree qui lie l'essence immortelle, protege contre la dissolution.",
        "rarity": EvolutionArtifactRarity.MYTHICAL.value,
        "evolution_stage": "transcendent",
        "power_bonus": 1.6,
        "stat_bonuses": {"power": 1.35, "vitality": 1.4, "immortality": 0.05, "divine": 1.15},
        "visual_effects": ["soul_chains", "ethereal_anchor", "spirit_glow", "immortal_aura"],
        "color_primary": "#ffaa00",
        "color_secondary": "#cc7700",
        "glow_intensity": 2.0,
        "abilities": [
            {"id": "soul_binding", "name": "Lien d'Ame", "description": "Lie l'essence a jamais", "value": 1},
            {"id": "immortal_spark", "name": "Etincelle Immortelle", "description": "{value}% chance de survivre a la mort", "value": 5},
            {"id": "spirit_shield", "name": "Bouclier Spirituel", "description": "Ignore {value}% des degats d'ame", "value": 50},
            {"id": "transcend_death", "name": "Transcender la Mort", "description": "Peut ressusciter {value} fois", "value": 1}
        ],
        "lore": "Forgee dans les flammes du purgatoire, cette ancre fut trempe dans les larmes d'un dieu dechu."
    },
    "divine_seal": {
        "name": "Sceau Divin",
        "description": "Embleme celeste confere par les Anciens, il accorde l'autorite divine.",
        "rarity": EvolutionArtifactRarity.TRANSCENDENT.value,
        "evolution_stage": "divine",
        "power_bonus": 2.0,
        "stat_bonuses": {"divine_power": 1.5, "all_stats": 1.4, "power": 1.75, "wisdom": 1.5},
        "visual_effects": ["divine_crown", "holy_halo", "celestial_wings", "star_field", "divine_aura"],
        "color_primary": "#ffffff",
        "color_secondary": "#ffdd88",
        "glow_intensity": 2.5,
        "abilities": [
            {"id": "divine_authority", "name": "Autorite Divine", "description": "Commande aux etres inferieurs", "value": 100},
            {"id": "celestial_judgment", "name": "Jugement Celeste", "description": "Inflige {value}% degats sacres supplementaires", "value": 75},
            {"id": "holy_protection", "name": "Protection Sacree", "description": "Immunite aux effets negatifs pendant {value}s", "value": 10},
            {"id": "divine_blessing", "name": "Benediction Divine", "description": "Augmente les stats des allies de {value}%", "value": 25}
        ],
        "lore": "Seuls les elus peuvent porter ce sceau. Les Anciens l'ont cree pour distinguer ceux dignes de l'ascension."
    },
    "origin_key": {
        "name": "Cle de l'Origine",
        "description": "Artefact primordial qui deverrouille les secrets de la creation elle-meme.",
        "rarity": EvolutionArtifactRarity.PRIMORDIAL.value,
        "evolution_stage": "primordial",
        "power_bonus": 3.0,
        "stat_bonuses": {"primordial_power": 2.0, "all_stats": 1.75, "power": 2.5, "divine": 2.0, "wisdom": 2.0},
        "visual_effects": ["reality_warp", "cosmos_background", "primordial_flames", "origin_crown", 
                          "universe_projection", "eternal_wings", "genesis_aura"],
        "color_primary": "#ff00ff",
        "color_secondary": "#aa00aa",
        "glow_intensity": 3.5,
        "abilities": [
            {"id": "genesis_power", "name": "Pouvoir de Genese", "description": "Cree de la matiere a partir du neant", "value": 1},
            {"id": "reality_shaping", "name": "Faconner la Realite", "description": "Modifie les lois de la physique dans un rayon de {value}m", "value": 50},
            {"id": "cosmic_dominion", "name": "Domination Cosmique", "description": "Controle {value} dimensions simultanement", "value": 7},
            {"id": "eternal_existence", "name": "Existence Eternelle", "description": "Immunite totale a la mort", "value": 1},
            {"id": "origin_command", "name": "Commandement de l'Origine", "description": "Tous les artefacts obeissent", "value": 100}
        ],
        "lore": "Nul ne sait qui a forge cette cle, ni quand. Elle existait avant le Nexus, avant le temps lui-meme."
    }
}


class EvolutionArtifactSystem:
    """Systeme de gestion des artefacts d'evolution"""
    
    # Probabilites de distribution par tier de vault
    DISTRIBUTION_RATES = {
        "supreme": {  # Vaults 1-33
            "genesis_glyph": 1.0,  # Garanti
            "cosmic_lens": 0.8,
            "infinity_fragment": 0.5,
            "soul_anchor": 0.3,
            "divine_seal": 0.15,
            "origin_key": 0.05
        },
        "legendary": {  # Vaults 34-100
            "genesis_glyph": 1.0,
            "cosmic_lens": 0.6,
            "infinity_fragment": 0.3,
            "soul_anchor": 0.15,
            "divine_seal": 0.05,
            "origin_key": 0.01
        },
        "elite": {  # Vaults 101-1000
            "genesis_glyph": 0.8,
            "cosmic_lens": 0.4,
            "infinity_fragment": 0.15,
            "soul_anchor": 0.05,
            "divine_seal": 0.01,
            "origin_key": 0.001
        },
        "pioneer": {  # Vaults 1001-10000
            "genesis_glyph": 0.5,
            "cosmic_lens": 0.2,
            "infinity_fragment": 0.05,
            "soul_anchor": 0.01,
            "divine_seal": 0.001,
            "origin_key": 0.0
        },
        "standard": {  # Vaults 10001+
            "genesis_glyph": 0.2,
            "cosmic_lens": 0.05,
            "infinity_fragment": 0.01,
            "soul_anchor": 0.001,
            "divine_seal": 0.0,
            "origin_key": 0.0
        }
    }
    
    def __init__(self, storage_path: str = "./artifact_vault/evolution_artifacts"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._load_existing_artifacts()
    
    def _load_existing_artifacts(self):
        """Charge les artefacts existants"""
        self.artifacts: Dict[str, EvolutionArtifact] = {}
        for file in self.storage_path.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    artifact = EvolutionArtifact.from_dict(data)
                    self.artifacts[artifact.artifact_id] = artifact
            except Exception:
                pass
    
    def _get_vault_tier(self, vault_number: int) -> str:
        """Determine le tier du vault"""
        if vault_number <= 33:
            return "supreme"
        elif vault_number <= 100:
            return "legendary"
        elif vault_number <= 1000:
            return "elite"
        elif vault_number <= 10000:
            return "pioneer"
        else:
            return "standard"
    
    def _generate_artifact_id(self, artifact_type: str, vault_id: str) -> str:
        """Genere un ID unique pour l'artefact"""
        seed = f"{artifact_type}_{vault_id}_{datetime.now().isoformat()}_{secrets.token_hex(8)}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]
    
    def create_artifact(self, artifact_type: str, vault_id: str, vault_number: int) -> Optional[EvolutionArtifact]:
        """Cree un artefact d'evolution"""
        if artifact_type not in EVOLUTION_ARTIFACT_DEFINITIONS:
            return None
        
        definition = EVOLUTION_ARTIFACT_DEFINITIONS[artifact_type]
        artifact_id = self._generate_artifact_id(artifact_type, vault_id)
        
        # Bonus base sur le numero de vault
        tier = self._get_vault_tier(vault_number)
        power_mult = 1.0
        if tier == "supreme":
            power_mult = 1.5
        elif tier == "legendary":
            power_mult = 1.3
        elif tier == "elite":
            power_mult = 1.15
        
        # Creer l'artefact
        artifact = EvolutionArtifact(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            name=definition["name"],
            description=definition["description"],
            rarity=definition["rarity"],
            evolution_stage=definition["evolution_stage"],
            power_bonus=definition["power_bonus"] * power_mult,
            stat_bonuses=definition["stat_bonuses"].copy(),
            visual_effects=definition["visual_effects"].copy(),
            color_primary=definition["color_primary"],
            color_secondary=definition["color_secondary"],
            glow_intensity=definition["glow_intensity"],
            abilities=definition["abilities"].copy(),
            vault_id=vault_id,
            origin_vault=vault_number,
            current_vault=vault_number
        )
        
        # Sauvegarder
        self._save_artifact(artifact)
        self.artifacts[artifact_id] = artifact
        
        return artifact
    
    def _save_artifact(self, artifact: EvolutionArtifact):
        """Sauvegarde un artefact"""
        file_path = self.storage_path / f"{artifact.artifact_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(artifact.to_dict(), f, indent=2, ensure_ascii=False)
    
    def distribute_artifacts_for_vault(self, vault_id: str, vault_number: int, 
                                       vault_seed: bytes = None) -> List[EvolutionArtifact]:
        """Distribue les artefacts lors de la creation d'un vault"""
        tier = self._get_vault_tier(vault_number)
        rates = self.DISTRIBUTION_RATES[tier]
        
        # Utiliser le seed du vault pour le RNG deterministe
        if vault_seed:
            rng_state = hashlib.sha512(vault_seed).digest()
        else:
            rng_state = secrets.token_bytes(64)
        
        distributed = []
        
        for artifact_type, rate in rates.items():
            # RNG deterministe
            rng_state = hashlib.sha512(rng_state + artifact_type.encode()).digest()
            roll = int.from_bytes(rng_state[:4], 'big') / (2**32)
            
            if roll < rate:
                artifact = self.create_artifact(artifact_type, vault_id, vault_number)
                if artifact:
                    distributed.append(artifact)
        
        return distributed
    
    def get_vault_artifacts(self, vault_id: str) -> List[EvolutionArtifact]:
        """Recupere tous les artefacts d'un vault par vault_id"""
        return [a for a in self.artifacts.values() if a.vault_id == vault_id]
    
    def get_vault_artifacts_by_number(self, vault_number: int) -> List[EvolutionArtifact]:
        """Recupere tous les artefacts d'un vault par numero"""
        return [a for a in self.artifacts.values() 
                if a.current_vault == vault_number or a.origin_vault == vault_number]
    
    def get_artifact(self, artifact_id: str) -> Optional[EvolutionArtifact]:
        """Recupere un artefact par son ID"""
        return self.artifacts.get(artifact_id)
    
    def bind_to_avatar(self, artifact_id: str, avatar_id: str) -> Dict:
        """Lie un artefact a un avatar"""
        artifact = self.artifacts.get(artifact_id)
        if not artifact:
            return {"success": False, "error": "Artefact non trouve"}
        
        if artifact.is_bound:
            return {"success": False, "error": "Artefact deja lie"}
        
        artifact.bound_to_avatar = avatar_id
        artifact.is_bound = True
        self._save_artifact(artifact)
        
        return {
            "success": True,
            "artifact": artifact.name,
            "avatar": avatar_id,
            "evolution_stage": artifact.evolution_stage,
            "bonuses": artifact.stat_bonuses
        }
    
    def get_artifact_for_evolution_stage(self, stage: str) -> Optional[dict]:
        """Retourne la definition de l'artefact requis pour un stade"""
        for artifact_type, definition in EVOLUTION_ARTIFACT_DEFINITIONS.items():
            if definition["evolution_stage"] == stage:
                return {"type": artifact_type, **definition}
        return None
    
    def check_artifact_requirement(self, vault_artifacts: List[str], required_stage: str) -> bool:
        """Verifie si le vault possede l'artefact requis pour un stade"""
        required = self.get_artifact_for_evolution_stage(required_stage)
        if not required:
            return True  # Pas de requirement
        
        required_type = required["type"]
        for artifact_id in vault_artifacts:
            artifact = self.artifacts.get(artifact_id)
            if artifact and artifact.artifact_type == required_type:
                return True
        
        return False


# Singleton
_artifact_system: Optional[EvolutionArtifactSystem] = None

def get_evolution_artifact_system() -> EvolutionArtifactSystem:
    global _artifact_system
    if _artifact_system is None:
        _artifact_system = EvolutionArtifactSystem()
    return _artifact_system


def format_artifact_display(artifact: EvolutionArtifact) -> str:
    """Formate l'affichage d'un artefact"""
    lines = []
    lines.append(f"\n{'='*50}")
    lines.append(f"  {artifact.name}")
    lines.append(f"  [{artifact.rarity.upper()}] - Stade: {artifact.evolution_stage.upper()}")
    lines.append(f"{'='*50}")
    lines.append(f"\n  {artifact.description}")
    lines.append(f"\n  BONUS DE PUISSANCE: x{artifact.power_bonus:.2f}")
    
    if artifact.stat_bonuses:
        lines.append(f"\n  BONUS DE STATS:")
        for stat, value in artifact.stat_bonuses.items():
            if isinstance(value, float) and value < 10:
                lines.append(f"    - {stat}: x{value:.2f}")
            else:
                lines.append(f"    - {stat}: +{value}")
    
    if artifact.abilities:
        lines.append(f"\n  CAPACITES:")
        for ability in artifact.abilities:
            lines.append(f"    * {ability['name']}: {ability['description']}")
    
    if artifact.visual_effects:
        lines.append(f"\n  EFFETS VISUELS: {', '.join(artifact.visual_effects)}")
    
    lines.append(f"\n{'='*50}\n")
    return "\n".join(lines)
