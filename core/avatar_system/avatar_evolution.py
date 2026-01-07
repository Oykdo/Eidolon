#!/usr/bin/env python3
"""
Systeme d'evolution des Avatars - Poly-Spinor Nexus 7D
Les avatars commencent bruts et evoluent via materiaux, artefacts et criteres
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


class EvolutionStage(Enum):
    """Stades d'evolution de l'avatar"""
    RAW = "raw"                    # Brut - forme initiale
    AWAKENED = "awakened"          # Eveille - premier niveau
    EVOLVED = "evolved"            # Evolue - niveau intermediaire
    ASCENDED = "ascended"          # Ascensionne - niveau avance
    TRANSCENDENT = "transcendent"  # Transcendant - niveau superieur
    DIVINE = "divine"              # Divin - niveau supreme
    PRIMORDIAL = "primordial"      # Primordial - forme ultime


@dataclass
class EvolutionMaterial:
    """Materiau utilisable pour l'evolution"""
    id: str
    name: str
    description: str
    rarity: str
    xp_value: int
    category: str
    special_effect: Optional[str] = None
    required_stage: Optional[EvolutionStage] = None


@dataclass
class EvolutionRequirement:
    """Prerequis pour une evolution"""
    type: str  # "material", "artifact", "gem", "fragment", "stone", "stat", "vault_rank", "time"
    target_id: Optional[str] = None
    target_category: Optional[str] = None
    quantity: int = 1
    min_value: Optional[float] = None
    description: str = ""


@dataclass
class EvolutionPath:
    """Chemin d'evolution vers un stade superieur"""
    from_stage: EvolutionStage
    to_stage: EvolutionStage
    requirements: List[EvolutionRequirement]
    xp_required: int
    stat_bonuses: Dict[str, float]
    visual_unlocks: List[str]
    ability_unlocks: List[str]
    title: str = ""


@dataclass
class AvatarEvolutionState:
    """Etat d'evolution d'un avatar"""
    avatar_id: str
    vault_id: str
    current_stage: str = "raw"
    evolution_xp: int = 0
    materials_consumed: Dict[str, int] = field(default_factory=dict)
    artifacts_bound: List[str] = field(default_factory=list)
    gems_fused: List[str] = field(default_factory=list)
    fragments_absorbed: Dict[str, int] = field(default_factory=dict)
    stone_essence: int = 0
    unlocked_visuals: List[str] = field(default_factory=list)
    unlocked_abilities: List[str] = field(default_factory=list)
    stat_modifiers: Dict[str, float] = field(default_factory=dict)
    evolution_history: List[Dict] = field(default_factory=list)
    titles_earned: List[str] = field(default_factory=list)
    created_at: str = ""
    last_evolution_at: Optional[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class AvatarEvolutionSystem:
    """Systeme de gestion de l'evolution des avatars"""
    
    # === MATERIAUX D'EVOLUTION ===
    EVOLUTION_MATERIALS = {
        # Poussieres (communes)
        "quantum_dust": EvolutionMaterial(
            id="quantum_dust",
            name="Poussiere Quantique",
            description="Residus d'operations quantiques",
            rarity="common",
            xp_value=50,
            category="dust"
        ),
        "entropy_dust": EvolutionMaterial(
            id="entropy_dust",
            name="Poussiere d'Entropie",
            description="Particules de chaos ordonne",
            rarity="common",
            xp_value=50,
            category="dust"
        ),
        "nexus_dust": EvolutionMaterial(
            id="nexus_dust",
            name="Poussiere de Nexus",
            description="Essence de connexions brisees",
            rarity="uncommon",
            xp_value=75,
            category="dust"
        ),
        
        # Eclats (peu communs)
        "crystal_shard": EvolutionMaterial(
            id="crystal_shard",
            name="Eclat Cristallin",
            description="Fragment de cristal dimensionnel",
            rarity="uncommon",
            xp_value=100,
            category="shard"
        ),
        "void_shard": EvolutionMaterial(
            id="void_shard",
            name="Eclat du Vide",
            description="Morceau de neant solidifie",
            rarity="rare",
            xp_value=200,
            category="shard"
        ),
        "stellar_shard": EvolutionMaterial(
            id="stellar_shard",
            name="Eclat Stellaire",
            description="Fragment d'etoile morte",
            rarity="rare",
            xp_value=250,
            category="shard"
        ),
        
        # Essences (rares)
        "primordial_essence": EvolutionMaterial(
            id="primordial_essence",
            name="Essence Primordiale",
            description="Energie pure de la creation",
            rarity="epic",
            xp_value=500,
            category="essence",
            special_effect="boost_all_stats_5%"
        ),
        "divine_essence": EvolutionMaterial(
            id="divine_essence",
            name="Essence Divine",
            description="Souffle des anciens",
            rarity="legendary",
            xp_value=1000,
            category="essence",
            special_effect="unlock_divine_visual"
        ),
        "origin_essence": EvolutionMaterial(
            id="origin_essence",
            name="Essence de l'Origine",
            description="La premiere etincelle",
            rarity="mythical",
            xp_value=2500,
            category="essence",
            required_stage=EvolutionStage.TRANSCENDENT,
            special_effect="unlock_primordial_form"
        ),
        
        # Coeurs (epiques)
        "nexus_core": EvolutionMaterial(
            id="nexus_core",
            name="Coeur de Nexus",
            description="Noyau d'un nexus dimensionnel",
            rarity="epic",
            xp_value=750,
            category="core"
        ),
        "stellar_core": EvolutionMaterial(
            id="stellar_core",
            name="Coeur Stellaire",
            description="Noyau d'une etoile effondree",
            rarity="legendary",
            xp_value=1500,
            category="core",
            special_effect="cosmic_aura"
        ),
        "void_core": EvolutionMaterial(
            id="void_core",
            name="Coeur du Vide",
            description="Centre du neant absolu",
            rarity="mythical",
            xp_value=3000,
            category="core",
            required_stage=EvolutionStage.DIVINE,
            special_effect="reality_distortion"
        ),
    }
    
    # === ARTEFACTS REQUIS POUR EVOLUTION ===
    EVOLUTION_ARTIFACTS = {
        "genesis_glyph": {
            "name": "Glyphe de Genese",
            "required_for": EvolutionStage.AWAKENED,
            "category": "glyph",
            "bonus": {"power": 1.1}
        },
        "cosmic_lens": {
            "name": "Lentille Cosmique",
            "required_for": EvolutionStage.EVOLVED,
            "category": "lens",
            "bonus": {"perception": 25, "power": 1.15}
        },
        "infinity_fragment": {
            "name": "Fragment d'Infini",
            "required_for": EvolutionStage.ASCENDED,
            "category": "fragment",
            "bonus": {"all_stats": 1.2}
        },
        "soul_anchor": {
            "name": "Ancre d'Ame",
            "required_for": EvolutionStage.TRANSCENDENT,
            "category": "anchor",
            "bonus": {"immortality": 0.05, "power": 1.35}
        },
        "divine_seal": {
            "name": "Sceau Divin",
            "required_for": EvolutionStage.DIVINE,
            "category": "seal",
            "bonus": {"divine_power": 1.5, "all_stats": 1.4}
        },
        "origin_key": {
            "name": "Cle de l'Origine",
            "required_for": EvolutionStage.PRIMORDIAL,
            "category": "key",
            "bonus": {"primordial_power": 2.0, "all_stats": 1.75}
        },
    }
    
    # === GEMS POUR EVOLUTION ===
    EVOLUTION_GEMS = {
        "power_gem": {"min_rarity": "rare", "xp_mult": 1.0, "stat": "power"},
        "wisdom_gem": {"min_rarity": "rare", "xp_mult": 1.0, "stat": "wisdom"},
        "vitality_gem": {"min_rarity": "rare", "xp_mult": 1.0, "stat": "vitality"},
        "divine_gem": {"min_rarity": "legendary", "xp_mult": 2.0, "stat": "divine_power"},
        "primordial_gem": {"min_rarity": "mythical", "xp_mult": 3.0, "stat": "primordial_power"},
    }
    
    # === FRAGMENTS ALCHIMIQUES ===
    ALCHEMY_FRAGMENTS = {
        "ignis": {"element": "fire", "xp": 100, "visual": "flame_particles"},
        "aqua": {"element": "water", "xp": 100, "visual": "water_ripples"},
        "terra": {"element": "earth", "xp": 100, "visual": "crystal_growth"},
        "aer": {"element": "air", "xp": 100, "visual": "wind_trails"},
        "lux": {"element": "light", "xp": 150, "visual": "light_rays"},
        "umbra": {"element": "shadow", "xp": 150, "visual": "shadow_tendrils"},
        "vita": {"element": "life", "xp": 200, "visual": "life_aura"},
        "mortis": {"element": "death", "xp": 200, "visual": "death_mist"},
        "tempus": {"element": "time", "xp": 300, "visual": "time_distortion"},
        "spatium": {"element": "space", "xp": 300, "visual": "space_rift"},
    }
    
    # === CHEMINS D'EVOLUTION ===
    EVOLUTION_PATHS = {
        "raw_to_awakened": EvolutionPath(
            from_stage=EvolutionStage.RAW,
            to_stage=EvolutionStage.AWAKENED,
            xp_required=1000,
            requirements=[
                EvolutionRequirement(type="material", target_id="quantum_dust", quantity=10),
                EvolutionRequirement(type="material", target_id="crystal_shard", quantity=3),
            ],
            stat_bonuses={"power": 1.15, "vitality": 1.1},
            visual_unlocks=["soft_glow", "pulse_aura"],
            ability_unlocks=["energy_shield"],
            title="L'Eveille"
        ),
        "awakened_to_evolved": EvolutionPath(
            from_stage=EvolutionStage.AWAKENED,
            to_stage=EvolutionStage.EVOLVED,
            xp_required=3500,
            requirements=[
                EvolutionRequirement(type="material", target_id="nexus_dust", quantity=15),
                EvolutionRequirement(type="material", target_id="void_shard", quantity=5),
                EvolutionRequirement(type="artifact", target_id="cosmic_lens"),
                EvolutionRequirement(type="gem", target_category="power_gem", quantity=1),
            ],
            stat_bonuses={"power": 1.25, "vitality": 1.15, "wisdom": 1.1},
            visual_unlocks=["particle_orbit", "energy_core", "enhanced_glow"],
            ability_unlocks=["phase_shift", "energy_burst"],
            title="L'Evolue"
        ),
        "evolved_to_ascended": EvolutionPath(
            from_stage=EvolutionStage.EVOLVED,
            to_stage=EvolutionStage.ASCENDED,
            xp_required=10000,
            requirements=[
                EvolutionRequirement(type="material", target_id="stellar_shard", quantity=10),
                EvolutionRequirement(type="material", target_id="primordial_essence", quantity=3),
                EvolutionRequirement(type="artifact", target_id="infinity_fragment"),
                EvolutionRequirement(type="fragment", target_category="any", quantity=5,
                                    description="5 fragments alchimiques differents"),
            ],
            stat_bonuses={"power": 1.4, "vitality": 1.25, "wisdom": 1.2, "luck": 1.15},
            visual_unlocks=["cosmic_particles", "stellar_aura", "energy_wings_small"],
            ability_unlocks=["dimension_walk", "stellar_strike", "cosmic_shield"],
            title="L'Ascensionne"
        ),
        "ascended_to_transcendent": EvolutionPath(
            from_stage=EvolutionStage.ASCENDED,
            to_stage=EvolutionStage.TRANSCENDENT,
            xp_required=25000,
            requirements=[
                EvolutionRequirement(type="material", target_id="nexus_core", quantity=3),
                EvolutionRequirement(type="material", target_id="divine_essence", quantity=2),
                EvolutionRequirement(type="artifact", target_id="soul_anchor"),
                EvolutionRequirement(type="stone", description="Posseder une Pierre Philosophale"),
                EvolutionRequirement(type="gem", target_category="divine_gem", quantity=1),
            ],
            stat_bonuses={"power": 1.6, "vitality": 1.4, "wisdom": 1.35, "luck": 1.25, "divine": 1.2},
            visual_unlocks=["transcendent_aura", "reality_ripples", "energy_wings_medium", "halo_ring"],
            ability_unlocks=["time_slow", "reality_anchor", "transcendent_form"],
            title="Le Transcendant"
        ),
        "transcendent_to_divine": EvolutionPath(
            from_stage=EvolutionStage.TRANSCENDENT,
            to_stage=EvolutionStage.DIVINE,
            xp_required=75000,
            requirements=[
                EvolutionRequirement(type="material", target_id="stellar_core", quantity=2),
                EvolutionRequirement(type="material", target_id="origin_essence", quantity=1),
                EvolutionRequirement(type="artifact", target_id="divine_seal"),
                EvolutionRequirement(type="fragment", target_category="all",
                                    description="Tous les 10 fragments alchimiques"),
                EvolutionRequirement(type="vault_rank", min_value=500,
                                    description="Vault dans le top 500"),
            ],
            stat_bonuses={"power": 2.0, "vitality": 1.6, "wisdom": 1.5, "luck": 1.4, "divine": 1.75},
            visual_unlocks=["divine_wings", "holy_halo", "celestial_aura", "star_field", "divine_crown"],
            ability_unlocks=["divine_judgment", "celestial_rain", "resurrection", "divine_shield"],
            title="Le Divin"
        ),
        "divine_to_primordial": EvolutionPath(
            from_stage=EvolutionStage.DIVINE,
            to_stage=EvolutionStage.PRIMORDIAL,
            xp_required=200000,
            requirements=[
                EvolutionRequirement(type="material", target_id="void_core", quantity=1),
                EvolutionRequirement(type="material", target_id="origin_essence", quantity=3),
                EvolutionRequirement(type="artifact", target_id="origin_key"),
                EvolutionRequirement(type="vault_rank", min_value=100,
                                    description="Vault dans le top 100"),
                EvolutionRequirement(type="gem", target_category="primordial_gem", quantity=1),
                EvolutionRequirement(type="stone", target_category="rule_of_1000",
                                    description="Pierre avec Rule of 1000"),
            ],
            stat_bonuses={"power": 3.0, "vitality": 2.0, "wisdom": 1.8, "luck": 1.6, 
                         "divine": 2.5, "primordial": 2.0},
            visual_unlocks=["reality_warp", "cosmos_background", "primordial_flames", 
                           "origin_crown", "universe_projection", "eternal_wings"],
            ability_unlocks=["genesis_power", "reality_shaping", "eternal_existence", 
                            "cosmic_dominion", "origin_command"],
            title="Le Primordial"
        ),
    }
    
    # === BONUS PAR STADE ===
    STAGE_BASE_BONUSES = {
        EvolutionStage.RAW: {"complexity": 1.0, "effects": []},
        EvolutionStage.AWAKENED: {"complexity": 1.3, "effects": ["glow"]},
        EvolutionStage.EVOLVED: {"complexity": 1.6, "effects": ["glow", "particles"]},
        EvolutionStage.ASCENDED: {"complexity": 2.0, "effects": ["glow", "particles", "energy_core"]},
        EvolutionStage.TRANSCENDENT: {"complexity": 2.5, "effects": ["glow", "particles", "energy_core", "aura", "halo"]},
        EvolutionStage.DIVINE: {"complexity": 3.5, "effects": ["glow", "particles", "energy_core", "aura", "halo", "wings", "divine_aura"]},
        EvolutionStage.PRIMORDIAL: {"complexity": 5.0, "effects": ["all"]},
    }
    
    def __init__(self, storage_path: str = "./alchemical_vault/avatar_evolution"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def get_evolution_state(self, avatar_id: str, vault_id: str = "") -> AvatarEvolutionState:
        """Recupere ou cree l'etat d'evolution d'un avatar"""
        state_file = self.storage_path / f"{avatar_id[:32]}_evolution.json"
        
        if state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return AvatarEvolutionState(**data)
        
        state = AvatarEvolutionState(avatar_id=avatar_id, vault_id=vault_id)
        self._save_state(state)
        return state
    
    def _save_state(self, state: AvatarEvolutionState):
        """Sauvegarde l'etat d'evolution"""
        state_file = self.storage_path / f"{state.avatar_id[:32]}_evolution.json"
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(state), f, indent=2, ensure_ascii=False)
    
    def consume_material(self, avatar_id: str, material_id: str, quantity: int = 1) -> Dict:
        """Consomme un materiau pour gagner de l'XP"""
        if material_id not in self.EVOLUTION_MATERIALS:
            return {"success": False, "error": f"Materiau inconnu: {material_id}"}
        
        material = self.EVOLUTION_MATERIALS[material_id]
        state = self.get_evolution_state(avatar_id)
        
        # Verifier le stade requis
        if material.required_stage:
            current = EvolutionStage(state.current_stage)
            if list(EvolutionStage).index(current) < list(EvolutionStage).index(material.required_stage):
                return {
                    "success": False, 
                    "error": f"Stade {material.required_stage.value} requis pour ce materiau"
                }
        
        # Consommer
        if material_id not in state.materials_consumed:
            state.materials_consumed[material_id] = 0
        state.materials_consumed[material_id] += quantity
        
        xp_gained = material.xp_value * quantity
        state.evolution_xp += xp_gained
        
        # Effet special
        effect_result = None
        if material.special_effect:
            effect_result = self._apply_special_effect(state, material.special_effect)
        
        self._save_state(state)
        
        return {
            "success": True,
            "material": material.name,
            "quantity": quantity,
            "xp_gained": xp_gained,
            "total_xp": state.evolution_xp,
            "special_effect": effect_result
        }
    
    def _apply_special_effect(self, state: AvatarEvolutionState, effect: str) -> str:
        """Applique un effet special de materiau"""
        if effect == "boost_all_stats_5%":
            if "all_stats_boost" not in state.stat_modifiers:
                state.stat_modifiers["all_stats_boost"] = 1.0
            state.stat_modifiers["all_stats_boost"] *= 1.05
            return "Stats globales +5%"
        
        elif effect == "unlock_divine_visual":
            if "divine_glow" not in state.unlocked_visuals:
                state.unlocked_visuals.append("divine_glow")
            return "Lueur divine debloquee"
        
        elif effect == "unlock_primordial_form":
            if "primordial_shimmer" not in state.unlocked_visuals:
                state.unlocked_visuals.append("primordial_shimmer")
            return "Forme primordiale activee"
        
        elif effect == "cosmic_aura":
            if "cosmic_aura" not in state.unlocked_visuals:
                state.unlocked_visuals.append("cosmic_aura")
            return "Aura cosmique debloquee"
        
        elif effect == "reality_distortion":
            if "reality_distortion" not in state.unlocked_visuals:
                state.unlocked_visuals.append("reality_distortion")
            return "Distorsion de realite activee"
        
        return None
    
    def bind_artifact(self, avatar_id: str, artifact_id: str) -> Dict:
        """Lie un artefact a l'avatar pour l'evolution"""
        if artifact_id not in self.EVOLUTION_ARTIFACTS:
            return {"success": False, "error": "Artefact non reconnu pour evolution"}
        
        state = self.get_evolution_state(avatar_id)
        
        if artifact_id in state.artifacts_bound:
            return {"success": False, "error": "Artefact deja lie"}
        
        artifact = self.EVOLUTION_ARTIFACTS[artifact_id]
        state.artifacts_bound.append(artifact_id)
        
        # Appliquer bonus
        for stat, value in artifact.get("bonus", {}).items():
            if stat not in state.stat_modifiers:
                state.stat_modifiers[stat] = 1.0 if isinstance(value, float) and value < 10 else 0
            if isinstance(value, float) and value < 10:
                state.stat_modifiers[stat] *= value
            else:
                state.stat_modifiers[stat] += value
        
        self._save_state(state)
        
        return {
            "success": True,
            "artifact": artifact["name"],
            "bonuses": artifact.get("bonus", {}),
            "message": f"{artifact['name']} lie avec succes"
        }
    
    def fuse_gem(self, avatar_id: str, gem_type: str, gem_rarity: str, gem_power: int) -> Dict:
        """Fusionne une gem avec l'avatar"""
        state = self.get_evolution_state(avatar_id)
        
        gem_id = f"{gem_type}_{gem_rarity}_{gem_power}"
        state.gems_fused.append(gem_id)
        
        # XP basee sur la puissance
        xp_gained = int(gem_power * 0.1)
        state.evolution_xp += xp_gained
        
        self._save_state(state)
        
        return {
            "success": True,
            "gem_fused": gem_id,
            "xp_gained": xp_gained,
            "total_gems": len(state.gems_fused)
        }
    
    def absorb_fragment(self, avatar_id: str, fragment_type: str, quantity: int = 1) -> Dict:
        """Absorbe des fragments alchimiques"""
        if fragment_type not in self.ALCHEMY_FRAGMENTS:
            return {"success": False, "error": f"Fragment inconnu: {fragment_type}"}
        
        fragment = self.ALCHEMY_FRAGMENTS[fragment_type]
        state = self.get_evolution_state(avatar_id)
        
        if fragment_type not in state.fragments_absorbed:
            state.fragments_absorbed[fragment_type] = 0
        state.fragments_absorbed[fragment_type] += quantity
        
        xp_gained = fragment["xp"] * quantity
        state.evolution_xp += xp_gained
        
        # Debloquer le visuel associe
        if fragment["visual"] not in state.unlocked_visuals:
            state.unlocked_visuals.append(fragment["visual"])
        
        self._save_state(state)
        
        return {
            "success": True,
            "fragment": fragment_type,
            "element": fragment["element"],
            "xp_gained": xp_gained,
            "visual_unlocked": fragment["visual"]
        }
    
    def infuse_stone_essence(self, avatar_id: str, stone_power: int, is_rule_of_1000: bool = False) -> Dict:
        """Infuse l'essence d'une Pierre Philosophale"""
        state = self.get_evolution_state(avatar_id)
        
        essence_value = int(stone_power * 0.05)
        if is_rule_of_1000:
            essence_value *= 3  # Triple pour Rule of 1000
        
        state.stone_essence += essence_value
        state.evolution_xp += essence_value * 10
        
        if "philosopher_aura" not in state.unlocked_visuals:
            state.unlocked_visuals.append("philosopher_aura")
        
        if is_rule_of_1000 and "rule_of_1000_crown" not in state.unlocked_visuals:
            state.unlocked_visuals.append("rule_of_1000_crown")
        
        self._save_state(state)
        
        return {
            "success": True,
            "essence_gained": essence_value,
            "total_essence": state.stone_essence,
            "xp_gained": essence_value * 10,
            "special": "Rule of 1000 bonus applique!" if is_rule_of_1000 else None
        }
    
    def check_evolution(self, avatar_id: str, vault_number: int = None,
                        owned_artifacts: List[str] = None,
                        owned_stones: List[Dict] = None,
                        owned_gems: List[Dict] = None) -> Dict:
        """Verifie si l'avatar peut evoluer"""
        state = self.get_evolution_state(avatar_id)
        current_stage = EvolutionStage(state.current_stage)
        
        # Trouver le chemin d'evolution
        stage_order = list(EvolutionStage)
        current_idx = stage_order.index(current_stage)
        
        if current_idx >= len(stage_order) - 1:
            return {
                "can_evolve": False,
                "reason": "Stade maximum atteint (PRIMORDIAL)",
                "current_stage": current_stage.value
            }
        
        next_stage = stage_order[current_idx + 1]
        path_key = f"{current_stage.value}_to_{next_stage.value}"
        
        if path_key not in self.EVOLUTION_PATHS:
            return {"can_evolve": False, "reason": "Chemin d'evolution non defini"}
        
        path = self.EVOLUTION_PATHS[path_key]
        requirements_status = []
        all_met = True
        
        # Verifier XP
        xp_met = state.evolution_xp >= path.xp_required
        requirements_status.append({
            "name": "XP d'Evolution",
            "met": xp_met,
            "current": state.evolution_xp,
            "required": path.xp_required,
            "progress": f"{min(100, state.evolution_xp / path.xp_required * 100):.1f}%"
        })
        if not xp_met:
            all_met = False
        
        # Verifier chaque prerequis
        for req in path.requirements:
            met = False
            current_val = 0
            required_val = req.quantity or 1
            
            if req.type == "material":
                current_val = state.materials_consumed.get(req.target_id, 0)
                met = current_val >= required_val
                
            elif req.type == "artifact":
                artifacts = owned_artifacts or []
                met = req.target_id in artifacts or req.target_id in state.artifacts_bound
                current_val = 1 if met else 0
                required_val = 1
                
            elif req.type == "gem":
                gems = owned_gems or []
                matching = [g for g in gems if g.get("type") == req.target_category]
                current_val = len(matching)
                met = current_val >= required_val
                
            elif req.type == "fragment":
                if req.target_category == "any":
                    current_val = len(state.fragments_absorbed)
                    met = current_val >= required_val
                elif req.target_category == "all":
                    current_val = len(state.fragments_absorbed)
                    required_val = len(self.ALCHEMY_FRAGMENTS)
                    met = current_val >= required_val
                    
            elif req.type == "stone":
                stones = owned_stones or []
                if req.target_category == "rule_of_1000":
                    met = any(s.get("is_rule_of_1000") for s in stones)
                else:
                    met = len(stones) > 0
                current_val = 1 if met else 0
                required_val = 1
                
            elif req.type == "vault_rank":
                if vault_number:
                    met = vault_number <= req.min_value
                    current_val = vault_number
                    required_val = f"Top {int(req.min_value)}"
            
            requirements_status.append({
                "name": req.description or f"{req.type}: {req.target_id or req.target_category}",
                "met": met,
                "current": current_val,
                "required": required_val
            })
            
            if not met:
                all_met = False
        
        return {
            "can_evolve": all_met,
            "current_stage": current_stage.value,
            "next_stage": next_stage.value,
            "path_title": path.title,
            "requirements": requirements_status,
            "rewards": {
                "stat_bonuses": path.stat_bonuses,
                "visual_unlocks": path.visual_unlocks,
                "ability_unlocks": path.ability_unlocks,
                "title": path.title
            }
        }
    
    def evolve(self, avatar_id: str, **kwargs) -> Dict:
        """Execute l'evolution de l'avatar"""
        check = self.check_evolution(avatar_id, **kwargs)
        
        if not check["can_evolve"]:
            missing = [r for r in check.get("requirements", []) if not r["met"]]
            return {
                "success": False,
                "reason": "Prerequis manquants",
                "missing": missing
            }
        
        state = self.get_evolution_state(avatar_id)
        old_stage = EvolutionStage(state.current_stage)
        new_stage = EvolutionStage(check["next_stage"])
        
        path_key = f"{old_stage.value}_to_{new_stage.value}"
        path = self.EVOLUTION_PATHS[path_key]
        
        # Appliquer l'evolution
        state.current_stage = new_stage.value
        state.last_evolution_at = datetime.now().isoformat()
        
        # Bonus de stats
        for stat, value in path.stat_bonuses.items():
            if stat not in state.stat_modifiers:
                state.stat_modifiers[stat] = 1.0
            state.stat_modifiers[stat] *= value
        
        # Visuels
        for visual in path.visual_unlocks:
            if visual not in state.unlocked_visuals:
                state.unlocked_visuals.append(visual)
        
        # Capacites
        for ability in path.ability_unlocks:
            if ability not in state.unlocked_abilities:
                state.unlocked_abilities.append(ability)
        
        # Titre
        if path.title and path.title not in state.titles_earned:
            state.titles_earned.append(path.title)
        
        # Historique
        state.evolution_history.append({
            "from": old_stage.value,
            "to": new_stage.value,
            "timestamp": datetime.now().isoformat(),
            "title_earned": path.title
        })
        
        self._save_state(state)
        
        return {
            "success": True,
            "evolution": f"{old_stage.value} -> {new_stage.value}",
            "new_stage": new_stage.value,
            "title_earned": path.title,
            "stat_bonuses": path.stat_bonuses,
            "visuals_unlocked": path.visual_unlocks,
            "abilities_unlocked": path.ability_unlocks,
            "total_evolutions": len(state.evolution_history)
        }
    
    def get_visual_config(self, avatar_id: str) -> Dict:
        """Retourne la configuration visuelle pour le rendu 3D"""
        state = self.get_evolution_state(avatar_id)
        current_stage = EvolutionStage(state.current_stage)
        base = self.STAGE_BASE_BONUSES[current_stage]
        
        return {
            "stage": state.current_stage,
            "stage_index": list(EvolutionStage).index(current_stage),
            "complexity_multiplier": base["complexity"],
            "base_effects": base["effects"],
            "unlocked_visuals": state.unlocked_visuals,
            "active_effects": {
                "glow": "glow" in base["effects"] or "soft_glow" in state.unlocked_visuals,
                "particles": "particles" in base["effects"] or "particle_orbit" in state.unlocked_visuals,
                "energy_core": "energy_core" in base["effects"] or "energy_core" in state.unlocked_visuals,
                "aura": "aura" in base["effects"] or any("aura" in v for v in state.unlocked_visuals),
                "halo": "halo" in base["effects"] or any("halo" in v for v in state.unlocked_visuals),
                "wings": "wings" in base["effects"] or any("wings" in v for v in state.unlocked_visuals),
                "divine": "divine_aura" in base["effects"] or "divine_glow" in state.unlocked_visuals,
                "primordial": current_stage == EvolutionStage.PRIMORDIAL,
                "reality_warp": "reality_warp" in state.unlocked_visuals or "reality_distortion" in state.unlocked_visuals,
                "cosmos": "cosmos_background" in state.unlocked_visuals or "cosmic_aura" in state.unlocked_visuals,
            },
            "element_visuals": [
                self.ALCHEMY_FRAGMENTS[f]["visual"] 
                for f in state.fragments_absorbed.keys()
            ],
            "stat_modifiers": state.stat_modifiers,
            "abilities": state.unlocked_abilities,
            "titles": state.titles_earned
        }
    
    def get_summary(self, avatar_id: str) -> Dict:
        """Resume complet de l'evolution"""
        state = self.get_evolution_state(avatar_id)
        current_stage = EvolutionStage(state.current_stage)
        visual_config = self.get_visual_config(avatar_id)
        
        stage_order = list(EvolutionStage)
        current_idx = stage_order.index(current_stage)
        
        if current_idx < len(stage_order) - 1:
            next_stage = stage_order[current_idx + 1]
            path_key = f"{current_stage.value}_to_{next_stage.value}"
            if path_key in self.EVOLUTION_PATHS:
                path = self.EVOLUTION_PATHS[path_key]
                progress = min(100, state.evolution_xp / path.xp_required * 100)
            else:
                progress = 0
        else:
            next_stage = None
            progress = 100
        
        return {
            "avatar_id": state.avatar_id,
            "current_stage": state.current_stage,
            "stage_name": current_stage.name,
            "stage_index": current_idx,
            "max_stage_index": len(stage_order) - 1,
            "evolution_xp": state.evolution_xp,
            "progress_to_next": f"{progress:.1f}%",
            "next_stage": next_stage.value if next_stage else "MAX",
            "materials_consumed": len(state.materials_consumed),
            "artifacts_bound": len(state.artifacts_bound),
            "gems_fused": len(state.gems_fused),
            "fragments_absorbed": len(state.fragments_absorbed),
            "stone_essence": state.stone_essence,
            "evolutions_completed": len(state.evolution_history),
            "abilities": state.unlocked_abilities,
            "titles": state.titles_earned,
            "visual_complexity": visual_config["complexity_multiplier"],
            "active_effects": [k for k, v in visual_config["active_effects"].items() if v]
        }


# Singleton
_evolution_system: Optional[AvatarEvolutionSystem] = None

def get_evolution_system() -> AvatarEvolutionSystem:
    global _evolution_system
    if _evolution_system is None:
        _evolution_system = AvatarEvolutionSystem()
    return _evolution_system
