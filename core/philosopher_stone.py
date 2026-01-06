"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              LA PIERRE PHILOSOPHALE - Le Coeur de l'Alchimie                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  "Celui qui possede la Pierre possede la cle de toute transformation."       ║
║                                                                              ║
║  La Pierre Philosophale est le fragment ultime, capable de:                  ║
║  - Transmuter les metaux vils en or (gemmes communes en divines)             ║
║  - Ressusciter les ames des gemmes brisees                                   ║
║  - Ouvrir des portails dimensionnels entre vaults                            ║
║  - Amplifier le pouvoir des artefacts                                        ║
║  - Conferer l'immortalite aux fragments (protection contre le decay)         ║
║  - Reveler les propheties cachees                                            ║
║  - Deverrouiller les recettes secretes de l'alchimie                         ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import json
import hashlib
import secrets
import math
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ============================================================================
# REGLE FONDAMENTALE: LIMITE DES 21 PIERRES
# ============================================================================

PHILOSOPHER_STONE_MAX_VAULT = 21
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    REGLE IMMUABLE DES 21 PIERRES                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Les Pierres Philosophales sont STRICTEMENT LIMITEES.                        ║
║                                                                              ║
║  SEULS les vaults #1 a #21 peuvent posseder une Pierre Philosophale.         ║
║  Apres la creation du 21eme vault, AUCUNE nouvelle Pierre ne sera            ║
║  jamais generee, quelle que soit la rarete ou le tier du vault.              ║
║                                                                              ║
║  Cette regle est PERMANENTE et IMMUABLE.                                     ║
║                                                                              ║
║  Consequences:                                                               ║
║  - Maximum de 21 Pierres dans tout l'ecosysteme                              ║
║  - Les detenteurs controlent l'alchimie supreme                              ║
║  - Valeur croissante a mesure que de nouveaux vaults sont crees              ║
║  - Aucun moyen de creer de nouvelles Pierres apres le vault #21              ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


# ============================================================================
# ETATS DE LA PIERRE PHILOSOPHALE
# ============================================================================

class PhilosopherStoneState(Enum):
    """Etats possibles de la Pierre"""
    DORMANT = "dormant"           # Nouvellement creee, pas encore activee
    AWAKENED = "awakened"         # Activee, prete a l'usage
    CHARGING = "charging"         # En cours de recharge
    DEPLETED = "depleted"         # Epuisee temporairement
    TRANSCENDENT = "transcendent" # Etat ultime, pouvoir illimite
    CORRUPTED = "corrupted"       # Corrompue par mauvais usage


class PhilosopherAbility(Enum):
    """Capacites de la Pierre Philosophale"""
    
    # Transmutation (transformer les gemmes)
    TRANSMUTE_GEM = ("transmute_gem", "Transmutation de Gemme", 
                     "Eleve la rarete d'une gemme d'un niveau", 20)
    TRANSMUTE_DIVINE = ("transmute_divine", "Transmutation Divine",
                        "Transforme n'importe quelle gemme en Divine", 100)
    
    # Resurrection (ramener les gemmes brisees)
    RESURRECT_SOUL = ("resurrect_soul", "Resurrection d'Ame",
                      "Ressuscite une gemme a partir de son fragment d'ame", 50)
    SOUL_FUSION = ("soul_fusion", "Fusion des Ames",
                   "Fusionne plusieurs ames en une gemme puissante", 75)
    
    # Portails dimensionnels
    OPEN_PORTAL = ("open_portal", "Ouverture de Portail",
                   "Ouvre un portail temporaire entre deux vaults", 30)
    PERMANENT_GATE = ("permanent_gate", "Porte Permanente",
                      "Cree une connexion permanente entre vaults", 150)
    
    # Amplification
    AMPLIFY_ARTIFACT = ("amplify_artifact", "Amplification d'Artefact",
                        "Augmente la puissance d'un artefact de 50%", 40)
    AMPLIFY_FRAGMENT = ("amplify_fragment", "Amplification de Fragment",
                        "Double la masse d'un fragment", 25)
    
    # Immortalite
    GRANT_IMMORTALITY = ("grant_immortality", "Don d'Immortalite",
                         "Protege un fragment contre le decay eternellement", 60)
    RESTORE_PURITY = ("restore_purity", "Restauration de Purete",
                      "Restaure la purete a 100%", 15)
    
    # Prophetie
    REVEAL_PROPHECY = ("reveal_prophecy", "Revelation de Prophetie",
                       "Revele une prophetie cachee", 10)
    FULFILL_PROPHECY = ("fulfill_prophecy", "Accomplissement de Prophetie",
                        "Force une prophetie a se realiser", 80)
    
    # Recettes
    UNLOCK_RECIPE = ("unlock_recipe", "Deverrouillage de Recette",
                     "Revele une recette alchimique secrete", 35)
    MASTER_ALCHEMY = ("master_alchemy", "Maitrise Alchimique",
                      "Debloque toutes les recettes", 200)
    
    # Gouvernance
    CROWN_BLESSING = ("crown_blessing", "Benediction de la Couronne",
                      "Confere temporairement le pouvoir Crown", 90)
    VETO_OVERRIDE = ("veto_override", "Annulation de Veto",
                     "Annule un veto sur une proposition", 70)
    
    # Constellation
    STAR_CREATION = ("star_creation", "Creation d'Etoile",
                     "Cree un fragment Star pour les constellations", 45)
    CONSTELLATION_ACTIVATION = ("constellation_activation", "Activation de Constellation",
                                "Active une constellation incomplete", 120)
    
    # Ultime
    GENESIS_CREATION = ("genesis_creation", "Creation de Genese",
                        "Cree un nouveau Genesis Block", 500)
    TRANSCENDENCE = ("transcendence", "Transcendance",
                     "Eleve la Pierre a l'etat Transcendant", 1000)
    
    def __init__(self, ability_id: str, name: str, description: str, energy_cost: int):
        self.ability_id = ability_id
        self.display_name = name
        self.description = description
        self.energy_cost = energy_cost


# ============================================================================
# PIERRE PHILOSOPHALE
# ============================================================================

@dataclass
class PhilosopherStone:
    """
    La Pierre Philosophale - Fragment ultime de l'alchimie
    """
    # Identite
    stone_id: str
    fragment_id: str  # Lien vers le fragment source
    
    # Energie
    max_energy: int = 1000
    current_energy: int = 1000
    energy_regen_rate: float = 1.0  # par heure
    
    # Etat
    state: str = "dormant"
    awakening_date: Optional[str] = None
    transcendence_date: Optional[str] = None
    
    # Stats
    transmutations_performed: int = 0
    souls_resurrected: int = 0
    portals_opened: int = 0
    artifacts_amplified: int = 0
    prophecies_revealed: int = 0
    recipes_unlocked: List[str] = field(default_factory=list)
    
    # Corruption
    corruption_level: float = 0.0  # 0-100%
    failed_transmutations: int = 0
    
    # Affinites (bonus aux certaines actions)
    affinities: Dict[str, float] = field(default_factory=dict)
    
    # Origine
    origin_vault: int = 0
    created_at: str = ""
    
    # Historique
    usage_history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "PhilosopherStone":
        return cls(**data)
    
    @property
    def is_usable(self) -> bool:
        """La pierre est-elle utilisable?"""
        return self.state in ["awakened", "transcendent"] and self.corruption_level < 100
    
    @property
    def energy_percentage(self) -> float:
        return (self.current_energy / self.max_energy) * 100
    
    def can_use_ability(self, ability: PhilosopherAbility) -> Tuple[bool, str]:
        """Verifie si une capacite peut etre utilisee"""
        if not self.is_usable:
            return False, f"Pierre non utilisable (etat: {self.state})"
        
        if self.current_energy < ability.energy_cost:
            return False, f"Energie insuffisante ({self.current_energy}/{ability.energy_cost})"
        
        # Transcendance requise pour certaines capacites
        transcendent_only = ["genesis_creation", "transcendence", "master_alchemy"]
        if ability.ability_id in transcendent_only and self.state != "transcendent":
            return False, "Necessite l'etat Transcendant"
        
        return True, "OK"
    
    def use_energy(self, amount: int) -> bool:
        """Consomme de l'energie"""
        if self.current_energy >= amount:
            self.current_energy -= amount
            return True
        return False
    
    def recharge(self, hours_passed: float = 1.0):
        """Recharge l'energie avec le temps"""
        if self.state == "transcendent":
            # Recharge instantanee
            self.current_energy = self.max_energy
        else:
            regen = int(hours_passed * self.energy_regen_rate * 10)
            self.current_energy = min(self.max_energy, self.current_energy + regen)
    
    def add_corruption(self, amount: float):
        """Ajoute de la corruption"""
        self.corruption_level = min(100, self.corruption_level + amount)
        if self.corruption_level >= 100:
            self.state = "corrupted"
    
    def purify(self, amount: float):
        """Purifie la pierre"""
        self.corruption_level = max(0, self.corruption_level - amount)
        if self.corruption_level < 50 and self.state == "corrupted":
            self.state = "awakened"


# ============================================================================
# RECETTES SECRETES (debloquees par la Pierre)
# ============================================================================

SECRET_RECIPES = {
    "divine_fusion": {
        "name": "Fusion Divine",
        "description": "Fusionne 7 gemmes de rarete differente en une gemme Divine",
        "unlock_cost": 35,
        "discovery_text": "Les 7 raretes unies forment la perfection divine..."
    },
    "soul_crystal": {
        "name": "Cristal d'Ame",
        "description": "Cristallise une ame de fragment en gemme permanente",
        "unlock_cost": 50,
        "discovery_text": "L'ame peut etre preservee dans un cristal eternel..."
    },
    "nexus_key": {
        "name": "Cle du Nexus",
        "description": "Cree une cle permettant de controler le Nexus",
        "unlock_cost": 75,
        "discovery_text": "Le Nexus ne s'ouvre qu'a celui qui possede la cle..."
    },
    "temporal_anchor": {
        "name": "Ancre Temporelle",
        "description": "Fixe un fragment dans le temps, immunise au decay",
        "unlock_cost": 40,
        "discovery_text": "Le temps peut etre arrete pour ceux qui connaissent le secret..."
    },
    "dimensional_weave": {
        "name": "Tissage Dimensionnel",
        "description": "Tisse les 7 dimensions en un fragment unique",
        "unlock_cost": 100,
        "discovery_text": "Les 7 dimensions ne sont que des fils d'une meme toile..."
    },
    "primordial_echo": {
        "name": "Echo Primordial",
        "description": "Invoque un echo du premier fragment jamais cree",
        "unlock_cost": 150,
        "discovery_text": "Au commencement etait le Fragment, et le Fragment etait tout..."
    },
    "crown_forging": {
        "name": "Forge de la Couronne",
        "description": "Forge une Couronne de gouvernance supreme",
        "unlock_cost": 200,
        "discovery_text": "Le pouvoir supreme ne peut etre conquis, il doit etre forge..."
    },
}


# ============================================================================
# GESTIONNAIRE DE PIERRES PHILOSOPHALES
# ============================================================================

class PhilosopherStoneManager:
    """Gestionnaire des Pierres Philosophales"""
    
    def __init__(self, data_dir: str = None):
        base_path = Path(__file__).parent.parent
        self.data_dir = Path(data_dir) if data_dir else base_path / "philosopher_stones"
        self.stones_dir = self.data_dir / "stones"
        self.portals_dir = self.data_dir / "portals"
        
        self.stones_dir.mkdir(parents=True, exist_ok=True)
        self.portals_dir.mkdir(parents=True, exist_ok=True)
        
        self._stones: Dict[str, PhilosopherStone] = {}
        self._load_stones()
    
    def _load_stones(self):
        """Charge toutes les pierres"""
        for f in self.stones_dir.glob("stone_*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                self._stones[data['stone_id']] = PhilosopherStone.from_dict(data)
            except Exception as e:
                print(f"[WARN] Error loading {f}: {e}")
    
    def _save_stone(self, stone: PhilosopherStone):
        """Sauvegarde une pierre"""
        filepath = self.stones_dir / f"stone_{stone.stone_id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(stone.to_dict(), f, indent=2, ensure_ascii=False)
        self._stones[stone.stone_id] = stone
    
    def create_stone(self, fragment_id: str, vault_number: int) -> PhilosopherStone:
        """Cree une nouvelle Pierre Philosophale"""
        stone_id = hashlib.sha256(
            f"{fragment_id}{datetime.now().isoformat()}{secrets.token_hex(8)}".encode()
        ).hexdigest()[:16]
        
        # Affinites aleatoires
        affinities = {}
        for ability in PhilosopherAbility:
            affinities[ability.ability_id] = 0.8 + secrets.randbelow(40) / 100
        
        stone = PhilosopherStone(
            stone_id=stone_id,
            fragment_id=fragment_id,
            max_energy=1000,
            current_energy=500,  # Commence a moitie charge
            state="dormant",
            origin_vault=vault_number,
            created_at=datetime.now().isoformat(),
            affinities=affinities
        )
        
        self._save_stone(stone)
        return stone
    
    def awaken_stone(self, stone_id: str) -> Tuple[bool, str]:
        """Eveille une pierre dormante"""
        stone = self._stones.get(stone_id)
        if not stone:
            return False, "Pierre non trouvee"
        
        if stone.state != "dormant":
            return False, f"Pierre deja eveillee (etat: {stone.state})"
        
        stone.state = "awakened"
        stone.awakening_date = datetime.now().isoformat()
        stone.current_energy = stone.max_energy
        
        self._save_stone(stone)
        return True, "Pierre eveillee! Elle est maintenant prete a l'usage."
    
    # ========================================================================
    # CAPACITES DE LA PIERRE
    # ========================================================================
    
    def transmute_gem(self, stone_id: str, gem_data: Dict) -> Tuple[bool, Dict, str]:
        """Transmute une gemme pour elever sa rarete"""
        stone = self._stones.get(stone_id)
        if not stone:
            return False, {}, "Pierre non trouvee"
        
        ability = PhilosopherAbility.TRANSMUTE_GEM
        can_use, msg = stone.can_use_ability(ability)
        if not can_use:
            return False, {}, msg
        
        # Hierarchie des raretes
        rarity_ladder = [
            "cracked", "flawed", "common", "polished", "refined",
            "pristine", "perfect", "flawless", "transcendent", "divine"
        ]
        
        current_rarity = gem_data.get('rarity', 'common').lower()
        current_idx = rarity_ladder.index(current_rarity) if current_rarity in rarity_ladder else 2
        
        if current_idx >= len(rarity_ladder) - 1:
            return False, {}, "Gemme deja au niveau maximum (Divine)"
        
        # Calculer le succes
        base_success = 0.8 - (current_idx * 0.05)  # Plus dur pour les hautes raretes
        affinity_bonus = stone.affinities.get(ability.ability_id, 1.0)
        success_chance = base_success * affinity_bonus
        
        stone.use_energy(ability.energy_cost)
        
        if secrets.randbelow(100) < success_chance * 100:
            # Succes!
            new_rarity = rarity_ladder[current_idx + 1]
            gem_data['rarity'] = new_rarity
            gem_data['base_power'] = gem_data.get('base_power', 100) * 1.5
            
            stone.transmutations_performed += 1
            stone.usage_history.append({
                "action": "transmute_gem",
                "success": True,
                "from_rarity": current_rarity,
                "to_rarity": new_rarity,
                "timestamp": datetime.now().isoformat()
            })
            
            self._save_stone(stone)
            return True, gem_data, f"Transmutation reussie! {current_rarity} -> {new_rarity}"
        else:
            # Echec
            stone.failed_transmutations += 1
            stone.add_corruption(5)
            
            stone.usage_history.append({
                "action": "transmute_gem",
                "success": False,
                "timestamp": datetime.now().isoformat()
            })
            
            self._save_stone(stone)
            return False, gem_data, "Transmutation echouee. Corruption +5%"
    
    def resurrect_soul(self, stone_id: str, soul_fragment: Dict) -> Tuple[bool, Dict, str]:
        """Ressuscite une gemme a partir de son ame"""
        stone = self._stones.get(stone_id)
        if not stone:
            return False, {}, "Pierre non trouvee"
        
        ability = PhilosopherAbility.RESURRECT_SOUL
        can_use, msg = stone.can_use_ability(ability)
        if not can_use:
            return False, {}, msg
        
        soul = soul_fragment.get('soul')
        if not soul:
            return False, {}, "Ce fragment ne contient pas d'ame"
        
        stone.use_energy(ability.energy_cost)
        
        # La resurrection depend de la corruption de l'ame
        soul_corruption = soul.get('corruption_level', 0)
        success_chance = 0.9 - (soul_corruption * 0.5)
        
        if secrets.randbelow(100) < success_chance * 100:
            # Ressusciter la gemme
            resurrected_gem = {
                "gem_id": hashlib.sha256(
                    f"resurrected_{datetime.now().isoformat()}".encode()
                ).hexdigest()[:16],
                "gem_type": soul.get('origin_gem_type', 'void_crystal'),
                "rarity": "common",  # Ressuscite a common
                "base_power": soul.get('residual_power', 100) * 2,
                "resonance": 50,
                "purity": 70,
                "stability": 80,
                "resurrected": True,
                "original_rarity": soul.get('origin_gem_rarity', 'unknown'),
                "memories_preserved": len(soul.get('memories', []))
            }
            
            stone.souls_resurrected += 1
            stone.usage_history.append({
                "action": "resurrect_soul",
                "success": True,
                "gem_type": resurrected_gem['gem_type'],
                "timestamp": datetime.now().isoformat()
            })
            
            self._save_stone(stone)
            return True, resurrected_gem, f"Ame ressuscitee en gemme {resurrected_gem['gem_type']}!"
        else:
            stone.add_corruption(10)
            self._save_stone(stone)
            return False, {}, "La resurrection a echoue. L'ame s'est dissipee."
    
    def open_portal(self, stone_id: str, from_vault: int, to_vault: int) -> Tuple[bool, Dict, str]:
        """Ouvre un portail entre deux vaults"""
        stone = self._stones.get(stone_id)
        if not stone:
            return False, {}, "Pierre non trouvee"
        
        ability = PhilosopherAbility.OPEN_PORTAL
        can_use, msg = stone.can_use_ability(ability)
        if not can_use:
            return False, {}, msg
        
        if from_vault == to_vault:
            return False, {}, "Les vaults doivent etre differents"
        
        stone.use_energy(ability.energy_cost)
        
        # Creer le portail
        portal = {
            "portal_id": hashlib.sha256(
                f"portal_{from_vault}_{to_vault}_{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16],
            "from_vault": from_vault,
            "to_vault": to_vault,
            "created_by": stone_id,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
            "is_permanent": False,
            "uses_remaining": 10
        }
        
        # Sauvegarder le portail
        filepath = self.portals_dir / f"portal_{portal['portal_id']}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(portal, f, indent=2)
        
        stone.portals_opened += 1
        stone.usage_history.append({
            "action": "open_portal",
            "from_vault": from_vault,
            "to_vault": to_vault,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_stone(stone)
        return True, portal, f"Portail ouvert! Vault #{from_vault} <-> Vault #{to_vault}"
    
    def amplify_artifact(self, stone_id: str, artifact_data: Dict) -> Tuple[bool, Dict, str]:
        """Amplifie la puissance d'un artefact"""
        stone = self._stones.get(stone_id)
        if not stone:
            return False, {}, "Pierre non trouvee"
        
        ability = PhilosopherAbility.AMPLIFY_ARTIFACT
        can_use, msg = stone.can_use_ability(ability)
        if not can_use:
            return False, {}, msg
        
        stone.use_energy(ability.energy_cost)
        
        # Amplifier
        stats = artifact_data.get('stats', {})
        old_power = stats.get('effective_power', 0)
        
        multiplier = 1.5 * stone.affinities.get(ability.ability_id, 1.0)
        stats['effective_power'] = old_power * multiplier
        stats['base_power'] = stats.get('base_power', 0) * multiplier
        stats['philosopher_amplified'] = True
        stats['amplification_date'] = datetime.now().isoformat()
        
        artifact_data['stats'] = stats
        
        stone.artifacts_amplified += 1
        stone.usage_history.append({
            "action": "amplify_artifact",
            "artifact_name": artifact_data.get('name', 'Unknown'),
            "power_increase": f"{old_power:.0f} -> {stats['effective_power']:.0f}",
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_stone(stone)
        return True, artifact_data, f"Artefact amplifie! Puissance: {old_power:.0f} -> {stats['effective_power']:.0f}"
    
    def unlock_recipe(self, stone_id: str, recipe_id: str = None) -> Tuple[bool, str, str]:
        """Deverrouille une recette secrete"""
        stone = self._stones.get(stone_id)
        if not stone:
            return False, "", "Pierre non trouvee"
        
        ability = PhilosopherAbility.UNLOCK_RECIPE
        can_use, msg = stone.can_use_ability(ability)
        if not can_use:
            return False, "", msg
        
        # Si pas de recipe_id specifie, choisir aleatoirement
        available = [r for r in SECRET_RECIPES.keys() if r not in stone.recipes_unlocked]
        if not available:
            return False, "", "Toutes les recettes sont deja debloquees!"
        
        if recipe_id and recipe_id not in available:
            if recipe_id in stone.recipes_unlocked:
                return False, "", "Cette recette est deja debloquee"
            return False, "", "Recette inconnue"
        
        target_recipe = recipe_id if recipe_id else secrets.choice(available)
        recipe = SECRET_RECIPES[target_recipe]
        
        # Verifier le cout
        cost = recipe['unlock_cost']
        if stone.current_energy < cost:
            return False, "", f"Energie insuffisante ({stone.current_energy}/{cost})"
        
        stone.use_energy(cost)
        stone.recipes_unlocked.append(target_recipe)
        
        stone.usage_history.append({
            "action": "unlock_recipe",
            "recipe": target_recipe,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_stone(stone)
        return True, target_recipe, f"Recette debloquee: {recipe['name']}\n\"{recipe['discovery_text']}\""
    
    def reveal_prophecy(self, stone_id: str) -> Tuple[bool, str, str]:
        """Revele une prophetie cachee"""
        stone = self._stones.get(stone_id)
        if not stone:
            return False, "", "Pierre non trouvee"
        
        ability = PhilosopherAbility.REVEAL_PROPHECY
        can_use, msg = stone.can_use_ability(ability)
        if not can_use:
            return False, "", msg
        
        stone.use_energy(ability.energy_cost)
        
        # Generer une prophetie
        prophecies = [
            "La septieme constellation s'alignera quand sept Pierres brilleront ensemble.",
            "Le Vault qui possede la Couronne forgee dominera le Nexus pour {n} cycles.",
            "Une gemme Divine naitra de la fusion de {n} ames ressuscitees.",
            "Le portail vers la dimension primordiale s'ouvrira au {n}eme jour.",
            "Celui qui transcende sa Pierre deviendra gardien du Nexus eternel.",
            "Les 7 essences fusionnees reveleront le secret de l'immortalite.",
            "La corruption peut etre vaincue par la purete de {n} Larmes Celestes.",
            "Le prochain fragment Primordial apparaitra dans le Vault #{vault}.",
            "L'equilibre du pouvoir changera quand {n} Decrets deviendront Couronnes.",
            "La Pierre Philosophale ultime attend au coeur de la constellation du Nexus.",
        ]
        
        prophecy = secrets.choice(prophecies).format(
            n=secrets.randbelow(10) + 3,
            vault=secrets.randbelow(100) + 1
        )
        
        stone.prophecies_revealed += 1
        stone.usage_history.append({
            "action": "reveal_prophecy",
            "prophecy": prophecy,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_stone(stone)
        return True, prophecy, f"Prophetie revelee!"
    
    def transcend(self, stone_id: str) -> Tuple[bool, str]:
        """Fait transcender une pierre a l'etat ultime"""
        stone = self._stones.get(stone_id)
        if not stone:
            return False, "Pierre non trouvee"
        
        if stone.state == "transcendent":
            return False, "Pierre deja transcendante"
        
        # Requirements pour transcender
        if stone.transmutations_performed < 10:
            return False, f"Necessite 10+ transmutations ({stone.transmutations_performed}/10)"
        if stone.souls_resurrected < 3:
            return False, f"Necessite 3+ resurrections ({stone.souls_resurrected}/3)"
        if len(stone.recipes_unlocked) < 3:
            return False, f"Necessite 3+ recettes ({len(stone.recipes_unlocked)}/3)"
        if stone.corruption_level > 20:
            return False, f"Corruption trop elevee ({stone.corruption_level:.1f}% > 20%)"
        
        ability = PhilosopherAbility.TRANSCENDENCE
        if stone.current_energy < ability.energy_cost:
            return False, f"Energie insuffisante ({stone.current_energy}/{ability.energy_cost})"
        
        # Transcender!
        stone.use_energy(ability.energy_cost)
        stone.state = "transcendent"
        stone.transcendence_date = datetime.now().isoformat()
        stone.max_energy = 5000  # Quintuple l'energie max
        stone.current_energy = 5000
        stone.energy_regen_rate = 10.0  # 10x plus rapide
        stone.corruption_level = 0  # Purifie completement
        
        # Bonus d'affinite
        for key in stone.affinities:
            stone.affinities[key] = min(2.0, stone.affinities[key] * 1.5)
        
        stone.usage_history.append({
            "action": "transcendence",
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_stone(stone)
        return True, "LA PIERRE A TRANSCENDE! Pouvoir illimite deverrouille."
    
    # ========================================================================
    # UTILITAIRES
    # ========================================================================
    
    def get_stone(self, stone_id: str) -> Optional[PhilosopherStone]:
        return self._stones.get(stone_id)
    
    def get_vault_stones(self, vault_number: int) -> List[PhilosopherStone]:
        return [s for s in self._stones.values() if s.origin_vault == vault_number]
    
    def get_all_stones(self) -> List[PhilosopherStone]:
        return list(self._stones.values())
    
    def get_statistics(self) -> Dict:
        stones = self.get_all_stones()
        
        return {
            "total_stones": len(stones),
            "awakened": sum(1 for s in stones if s.state == "awakened"),
            "transcendent": sum(1 for s in stones if s.state == "transcendent"),
            "dormant": sum(1 for s in stones if s.state == "dormant"),
            "corrupted": sum(1 for s in stones if s.state == "corrupted"),
            "total_transmutations": sum(s.transmutations_performed for s in stones),
            "total_resurrections": sum(s.souls_resurrected for s in stones),
            "total_portals": sum(s.portals_opened for s in stones),
            "total_energy": sum(s.current_energy for s in stones),
            "recipes_discovered": len(set(r for s in stones for r in s.recipes_unlocked)),
        }


# ============================================================================
# AFFICHAGE
# ============================================================================

def format_stone_display(stone: PhilosopherStone) -> str:
    """Format d'affichage d'une Pierre"""
    state_icons = {
        "dormant": "💤",
        "awakened": "✨",
        "charging": "⚡",
        "depleted": "🔋",
        "transcendent": "🌟",
        "corrupted": "💀"
    }
    
    icon = state_icons.get(stone.state, "?")
    corruption = f" CORR:{stone.corruption_level:.0f}%" if stone.corruption_level > 0 else ""
    
    return (f"☿ {icon} Pierre #{stone.stone_id[:8]} | "
            f"Energie: {stone.current_energy}/{stone.max_energy} | "
            f"Trans: {stone.transmutations_performed} | "
            f"Ames: {stone.souls_resurrected}{corruption}")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  LA PIERRE PHILOSOPHALE - Systeme Alchimique")
    print("="*70)
    
    manager = PhilosopherStoneManager()
    stats = manager.get_statistics()
    
    print(f"\n  Total Pierres: {stats['total_stones']}")
    print(f"  Eveillee: {stats['awakened']}")
    print(f"  Transcendantes: {stats['transcendent']}")
    print(f"  Dormantes: {stats['dormant']}")
    print(f"  Corrompues: {stats['corrupted']}")
    
    print(f"\n  ACTIVITE GLOBALE:")
    print(f"  Transmutations: {stats['total_transmutations']}")
    print(f"  Resurrections: {stats['total_resurrections']}")
    print(f"  Portails: {stats['total_portals']}")
    print(f"  Recettes decouvertes: {stats['recipes_discovered']}/{len(SECRET_RECIPES)}")
    
    print(f"\n  CAPACITES DISPONIBLES:")
    for ability in PhilosopherAbility:
        print(f"    ☿ {ability.display_name:30} | Cout: {ability.energy_cost:4} | {ability.description}")
    
    print(f"\n  RECETTES SECRETES:")
    for recipe_id, recipe in SECRET_RECIPES.items():
        print(f"    📜 {recipe['name']:25} | Cout: {recipe['unlock_cost']:3} | {recipe['description']}")
    
    # Lister les pierres existantes
    stones = manager.get_all_stones()
    if stones:
        print(f"\n  PIERRES EXISTANTES:")
        for stone in stones:
            print(f"    {format_stone_display(stone)}")
    
    print("\n" + "="*70)
