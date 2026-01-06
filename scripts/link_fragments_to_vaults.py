"""
Liaison des Fragments aux Vaults selon le rang de Pionnier
RNG Poly-Spinoral optimise par tier

╔══════════════════════════════════════════════════════════════════════════════╗
║                    REGLE DES 21 PIERRES PHILOSOPHALES                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Les Pierres Philosophales sont STRICTEMENT LIMITEES aux 21 premiers vaults. ║
║                                                                              ║
║  Apres la creation du 21eme vault, plus AUCUNE Pierre Philosophale ne sera   ║
║  jamais generee dans l'ecosysteme. Cette regle est IMMUABLE.                 ║
║                                                                              ║
║  Cela fait des Pierres Philosophales les artefacts les plus rares et         ║
║  precieux de tout le Nexus, conferant un avantage permanent aux premiers     ║
║  pionniers.                                                                  ║
║                                                                              ║
║  Distribution estimee (basee sur les probabilites par tier):                 ║
║  - Vaults 1-6 (Quantum Pioneers): ~6 pierres garanties                       ║
║  - Vaults 7-21: Selon tier et chance (0.5% a 25%)                           ║
║  - Vaults 22+: ZERO pierre possible                                         ║
║                                                                              ║
║  Maximum theorique: 21 Pierres Philosophales                                 ║
║  Ces 21 Pierres controlent l'alchimie de tout l'ecosysteme.                 ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import json
import hashlib
import secrets
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.fragment_nexus import (
    FragmentNexus, Fragment, FragmentEssence, FragmentType,
    FragmentSoul, CosmicCycle, CONSTELLATIONS, ALCHEMICAL_RECIPES,
    format_fragment_display
)


# ============================================================================
# CONSTANTE IMMUABLE: LIMITE DES PIERRES PHILOSOPHALES
# ============================================================================

PHILOSOPHER_STONE_MAX_VAULT = 21
"""
Les Pierres Philosophales ne peuvent etre generees QUE pour les vaults 1 a 21.
Apres le vault #21, plus AUCUNE Pierre ne sera jamais creee.
Cette limite est PERMANENTE et ne peut pas etre modifiee.

Maximum theorique: 21 Pierres (si tous les vaults 1-21 en obtiennent une)
Estimation realiste: ~10-15 Pierres (selon les probabilites)
"""


# ============================================================================
# CONFIGURATION PAR RANG DE PIONNIER
# ============================================================================

PIONEER_FRAGMENT_CONFIG = {
    # PRIMORDIAL - Le plus haut rang
    "primordial": {
        "base_fragments": 15,
        "governance_tier": 3,  # Crown
        "governance_type": "crown",
        "special_fragments": ["oracle", "nexus", "star", "star", "star"],
        "essence_quality": 0.95,
        "mass_multiplier": 5.0,
        "purity_range": (80, 100),
        "stability_range": (75, 95),
        "prophecy_power": 3,
        "philosopher_chance": 0.15,
    },
    # TRANSCENDENT
    "transcendent": {
        "base_fragments": 12,
        "governance_tier": 2,  # Decree
        "governance_type": "decree",
        "special_fragments": ["prophecy", "bond", "star", "star"],
        "essence_quality": 0.85,
        "mass_multiplier": 3.5,
        "purity_range": (70, 95),
        "stability_range": (65, 90),
        "prophecy_power": 2,
        "philosopher_chance": 0.08,
    },
    # MYTHIC
    "mythic": {
        "base_fragments": 10,
        "governance_tier": 2,  # Decree
        "governance_type": "decree",
        "special_fragments": ["omen", "echo", "star", "star"],
        "essence_quality": 0.75,
        "mass_multiplier": 2.5,
        "purity_range": (60, 90),
        "stability_range": (55, 85),
        "prophecy_power": 1,
        "philosopher_chance": 0.05,
    },
    # LEGENDARY
    "legendary": {
        "base_fragments": 8,
        "governance_tier": 1,  # Voice
        "governance_type": "voice",
        "special_fragments": ["omen", "star"],
        "essence_quality": 0.65,
        "mass_multiplier": 2.0,
        "purity_range": (50, 85),
        "stability_range": (50, 80),
        "prophecy_power": 1,
        "philosopher_chance": 0.02,
    },
    # EPIC
    "epic": {
        "base_fragments": 6,
        "governance_tier": 1,  # Voice
        "governance_type": "voice",
        "special_fragments": ["star"],
        "essence_quality": 0.55,
        "mass_multiplier": 1.5,
        "purity_range": (45, 80),
        "stability_range": (45, 75),
        "prophecy_power": 0,
        "philosopher_chance": 0.01,
    },
    # RARE
    "rare": {
        "base_fragments": 5,
        "governance_tier": 1,
        "governance_type": "voice",
        "special_fragments": [],
        "essence_quality": 0.45,
        "mass_multiplier": 1.2,
        "purity_range": (40, 75),
        "stability_range": (40, 70),
        "prophecy_power": 0,
        "philosopher_chance": 0.005,
    },
    # QUANTUM PIONEER (tier special pour les premiers)
    "quantum_pioneer": {
        "base_fragments": 12,
        "governance_tier": 2,
        "governance_type": "decree",
        "special_fragments": ["oracle", "bond", "star", "star", "catalyst"],
        "essence_quality": 0.80,
        "mass_multiplier": 3.0,
        "purity_range": (65, 92),
        "stability_range": (60, 88),
        "prophecy_power": 2,
        "philosopher_chance": 0.10,
    },
}

# Mapping des types d'artefacts vers les tiers
ARTIFACT_RARITY_TO_TIER = {
    "primordial": "primordial",
    "transcendent": "transcendent",
    "mythic": "mythic",
    "legendary": "legendary",
    "epic": "epic",
    "rare": "rare",
    "uncommon": "rare",
    "common": "rare",
}


# ============================================================================
# RNG POLY-SPINORAL OPTIMISE
# ============================================================================

class PolySpinorFragmentRNG:
    """
    Generateur RNG base sur l'algebre de Clifford Cl(0,7)
    pour une distribution deterministe mais imprevisible
    """
    
    def __init__(self, seed: bytes):
        """Initialise avec un seed de 64 bytes minimum"""
        self.master_seed = hashlib.sha512(seed).digest()
        self.state = np.frombuffer(self.master_seed, dtype=np.uint8)
        self.counter = 0
        
        # Matrices de Clifford pour les 7 dimensions
        self._init_clifford_matrices()
    
    def _init_clifford_matrices(self):
        """Initialise les matrices de base de Cl(0,7)"""
        # Matrices de Pauli etendues
        sigma_x = np.array([[0, 1], [1, 0]], dtype=np.float64)
        sigma_y = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
        sigma_z = np.array([[1, 0], [0, -1]], dtype=np.float64)
        I2 = np.eye(2, dtype=np.float64)
        
        # Les 7 generateurs de Cl(0,7)
        self.gamma = []
        for i in range(7):
            # Construction via produit de Kronecker
            components = [I2] * 7
            components[i] = sigma_x if i % 3 == 0 else (sigma_y.real if i % 3 == 1 else sigma_z)
            
            result = components[0]
            for c in components[1:]:
                result = np.kron(result, c)
            
            # Reduire la taille pour performance
            self.gamma.append(result[:16, :16])
    
    def _advance_state(self):
        """Avance l'etat RNG"""
        self.counter += 1
        combined = self.master_seed + self.counter.to_bytes(8, 'big')
        self.state = np.frombuffer(hashlib.sha512(combined).digest(), dtype=np.uint8)
    
    def next_float(self, dimension: int = 0) -> float:
        """Genere un float entre 0 et 1 avec biais dimensionnel"""
        self._advance_state()
        
        # Appliquer la matrice gamma de la dimension
        dim_idx = dimension % 7
        gamma = self.gamma[dim_idx]
        
        # Projeter l'etat
        state_vec = self.state[:16].astype(np.float64) / 255.0
        projected = np.abs(gamma @ state_vec)
        
        # Normaliser et extraire
        value = np.sum(projected) / (16 * 2)  # Normalise entre 0 et 1
        return min(1.0, max(0.0, value))
    
    def next_int(self, min_val: int, max_val: int, dimension: int = 0) -> int:
        """Genere un entier dans une plage"""
        f = self.next_float(dimension)
        return min_val + int(f * (max_val - min_val + 1))
    
    def next_weighted_choice(self, weights: Dict[str, float], dimension: int = 0) -> str:
        """Choix pondere"""
        total = sum(weights.values())
        roll = self.next_float(dimension) * total
        
        cumulative = 0
        for key, weight in weights.items():
            cumulative += weight
            if roll < cumulative:
                return key
        
        return list(weights.keys())[-1]
    
    def get_entropy_bits(self) -> int:
        """Retourne le nombre de bits d'entropie generes"""
        return self.counter * 512


# ============================================================================
# GENERATEUR DE FRAGMENTS PAR TIER
# ============================================================================

class TierFragmentGenerator:
    """Genere des fragments selon le tier du vault"""
    
    def __init__(self, nexus: FragmentNexus):
        self.nexus = nexus
    
    def generate_for_vault(self, vault_number: int, tier: str, 
                          artifact_rarity: str, seed: bytes) -> List[Fragment]:
        """Genere les fragments pour un vault selon son tier ET la rarete de l'artefact"""
        
        # Determiner la config de base selon le tier
        base_config = PIONEER_FRAGMENT_CONFIG.get(tier, PIONEER_FRAGMENT_CONFIG.get("quantum_pioneer"))
        
        # Obtenir la config bonus selon la rarete de l'artefact
        mapped_tier = ARTIFACT_RARITY_TO_TIER.get(artifact_rarity.lower(), "rare")
        artifact_config = PIONEER_FRAGMENT_CONFIG.get(mapped_tier, PIONEER_FRAGMENT_CONFIG["rare"])
        
        # Fusionner: prendre le meilleur entre tier et artifact
        config = {
            "base_fragments": max(base_config["base_fragments"], artifact_config["base_fragments"]),
            "governance_tier": max(base_config["governance_tier"], artifact_config["governance_tier"]),
            "governance_type": base_config["governance_type"] if base_config["governance_tier"] >= artifact_config["governance_tier"] else artifact_config["governance_type"],
            "special_fragments": list(set(base_config["special_fragments"] + artifact_config["special_fragments"])),
            "essence_quality": max(base_config["essence_quality"], artifact_config["essence_quality"]),
            "mass_multiplier": max(base_config["mass_multiplier"], artifact_config["mass_multiplier"]),
            "purity_range": (max(base_config["purity_range"][0], artifact_config["purity_range"][0]),
                           max(base_config["purity_range"][1], artifact_config["purity_range"][1])),
            "stability_range": (max(base_config["stability_range"][0], artifact_config["stability_range"][0]),
                              max(base_config["stability_range"][1], artifact_config["stability_range"][1])),
            "prophecy_power": max(base_config["prophecy_power"], artifact_config["prophecy_power"]),
            "philosopher_chance": max(base_config["philosopher_chance"], artifact_config["philosopher_chance"]),
        }
        
        # Bonus special pour PRIMORDIAL: upgrade gouvernance en Crown!
        if artifact_rarity.lower() == "primordial":
            config["governance_tier"] = 3
            config["governance_type"] = "crown"
            config["special_fragments"].extend(["nexus", "sun", "comet"])
            config["philosopher_chance"] = 0.25
        
        # Initialiser le RNG
        rng = PolySpinorFragmentRNG(seed)
        
        fragments = []
        
        # 1. Generer les fragments de base (Shards/Splinters)
        for i in range(config["base_fragments"]):
            # Essence basee sur la dimension
            dimension = i % 7
            essence = list(FragmentEssence)[dimension]
            
            # Type de fragment
            type_weights = {
                "shard": 60 + config["essence_quality"] * 20,
                "splinter": 30,
                "dust": 10 - config["essence_quality"] * 5,
            }
            ftype_id = rng.next_weighted_choice(type_weights, dimension)
            ftype = next(f for f in FragmentType if f.type_id == ftype_id)
            
            # Stats avec bonus de tier
            min_p, max_p = config["purity_range"]
            min_s, max_s = config["stability_range"]
            
            mass = rng.next_int(100, 500, dimension) * config["mass_multiplier"]
            purity = rng.next_int(min_p, max_p, dimension)
            stability = rng.next_int(min_s, max_s, dimension)
            
            # Creer le fragment
            fragment = self._create_fragment(
                vault_number, ftype, essence, mass, purity, stability, rng
            )
            fragments.append(fragment)
        
        # 2. Fragment de gouvernance
        gov_type = config["governance_type"]
        gov_ftype = next(f for f in FragmentType if f.type_id == gov_type)
        
        gov_mass = rng.next_int(1000, 2000, 5) * config["mass_multiplier"]
        gov_fragment = self._create_fragment(
            vault_number, gov_ftype, FragmentEssence.HARMONIC,
            gov_mass, 
            rng.next_int(70, 95, 5),
            rng.next_int(65, 90, 5),
            rng
        )
        
        # Configurer le pouvoir de gouvernance
        gov_tiers = {1: 25, 2: 100, 3: 500}
        gov_fragment.governance_tier = config["governance_tier"]
        gov_fragment.voting_power = gov_tiers.get(config["governance_tier"], 25)
        
        self.nexus._save_fragment(gov_fragment)
        fragments.append(gov_fragment)
        
        # 3. Fragments speciaux
        for special_type in config["special_fragments"]:
            try:
                special_ftype = next(f for f in FragmentType if f.type_id == special_type)
            except StopIteration:
                continue
            
            # Essence selon le type special
            if special_type in ["oracle", "prophecy", "omen"]:
                essence = FragmentEssence.TEMPORAL
            elif special_type in ["nexus", "bond", "echo"]:
                essence = FragmentEssence.QUANTUM
            elif special_type == "star":
                essence = FragmentEssence.CELESTIAL
            elif special_type == "catalyst":
                essence = FragmentEssence.ENTROPIC
            else:
                essence = list(FragmentEssence)[rng.next_int(0, 6, 6)]
            
            special_mass = rng.next_int(500, 1500, 6) * config["mass_multiplier"]
            special_fragment = self._create_fragment(
                vault_number, special_ftype, essence,
                special_mass,
                rng.next_int(60, 95, 6),
                rng.next_int(55, 90, 6),
                rng
            )
            
            # Prophetie pour les fragments prophetiques
            if special_type in ["oracle", "prophecy", "omen"] and config["prophecy_power"] > 0:
                special_fragment.prophecy_text = self._generate_prophecy(
                    vault_number, config["prophecy_power"], rng
                )
            
            self.nexus._save_fragment(special_fragment)
            fragments.append(special_fragment)
        
        # 4. Chance de Pierre Philosophale (tres rare)
        # LIMITE: Seuls les 21 premiers vaults peuvent obtenir une Pierre Philosophale
        # Apres le vault #21, plus aucune Pierre ne sera jamais creee
        # Voir: PHILOSOPHER_STONE_MAX_VAULT
        
        if vault_number <= PHILOSOPHER_STONE_MAX_VAULT:
            # Les premiers vaults ont une chance de Pierre
            if rng.next_float(0) < config["philosopher_chance"]:
                phil_ftype = next(f for f in FragmentType if f.type_id == "philosopher")
                phil_fragment = self._create_fragment(
                    vault_number, phil_ftype, FragmentEssence.VOID,
                    5000 * config["mass_multiplier"],
                    95, 90, rng
                )
                phil_fragment.prophecy_text = f"Pierre Philosophale #{vault_number} - L'une des 21 pierres originelles. Apres le 21eme vault, plus aucune ne sera jamais creee."
                self.nexus._save_fragment(phil_fragment)
                fragments.append(phil_fragment)
        # Vaults > 21: Aucune chance de Pierre Philosophale
        
        return fragments
    
    def _create_fragment(self, vault_number: int, ftype: FragmentType,
                        essence: FragmentEssence, mass: float,
                        purity: float, stability: float,
                        rng: PolySpinorFragmentRNG) -> Fragment:
        """Cree un fragment avec le RNG poly-spinoral"""
        
        fragment_id = hashlib.sha256(
            f"{ftype.type_id}{essence.essence_id}{mass}"
            f"{datetime.now().isoformat()}{rng.counter}".encode()
        ).hexdigest()[:16]
        
        # Frequence de resonance basee sur l'essence et le RNG
        resonance = essence.dimension * 1000 + rng.next_int(0, 1000, essence.dimension)
        
        # Cycle cosmique
        cycle_idx, _, _, _, _ = CosmicCycle.get_current_phase()
        
        # Cycles optimaux
        optimal = [(essence.dimension + i) % 8 for i in range(3)]
        
        # Valeur de marche
        market_value = mass * (purity / 100) * CosmicCycle.get_market_modifier()
        
        fragment = Fragment(
            fragment_id=fragment_id,
            fragment_type=ftype.type_id,
            essence=essence.essence_id,
            mass=round(mass, 1),
            purity=round(purity, 1),
            stability=round(stability, 1),
            resonance_frequency=resonance,
            birth_cycle=cycle_idx,
            optimal_cycles=optimal,
            market_value=round(market_value, 2),
            origin_vault=vault_number,
            current_vault=vault_number,
            created_at=datetime.now().isoformat()
        )
        
        self.nexus._save_fragment(fragment)
        return fragment
    
    def _generate_prophecy(self, vault_number: int, power: int, 
                          rng: PolySpinorFragmentRNG) -> str:
        """Genere une prophetie selon le pouvoir"""
        
        prophecies = {
            1: [
                "Un changement approche pour le Vault #{vault}.",
                "Les cycles favoriseront bientot l'essence {essence}.",
                "Une fusion inattendue produira des resultats remarquables.",
            ],
            2: [
                "Le Vault #{vault} jouera un role crucial dans la prochaine constellation.",
                "Sept fragments de {essence} reveleront un secret ancien.",
                "La Pierre Philosophale attend celui qui maitrise les 7 essences.",
                "Une alliance entre les Vaults {v1} et {v2} changera l'equilibre.",
            ],
            3: [
                "Le Nexus s'eveillera quand la Couronne sera forgee.",
                "Celui qui possede l'Oracle verra au-dela du temps.",
                "Les 7 Constellations alignees ouvriront le portail primordial.",
                "Le Vault #{vault} est destine a gouverner le Nexus.",
                "La prophetie finale sera revelee au {n}eme cycle de la Pleine Lune.",
            ]
        }
        
        templates = prophecies.get(power, prophecies[1])
        template = templates[rng.next_int(0, len(templates) - 1, 2)]
        
        return template.format(
            vault=vault_number,
            essence=list(FragmentEssence)[rng.next_int(0, 6, 2)].display_name,
            v1=rng.next_int(1, 10, 3),
            v2=rng.next_int(1, 10, 4),
            n=rng.next_int(3, 12, 5)
        )


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "="*70)
    print("  FRAGMENT NEXUS - Pioneer Tier Integration")
    print("  Poly-Spinor RNG Optimization")
    print("="*70)
    
    base_path = Path(__file__).parent.parent
    genesis_dir = base_path / "genesis_data" / "blocks"
    
    # Nettoyer les anciens fragments
    nexus = FragmentNexus()
    old_count = len(nexus.get_all_fragments())
    
    if old_count > 0:
        print(f"\n[!] Removing {old_count} old fragments...")
        for f in nexus.fragments_dir.glob("fragment_*.json"):
            f.unlink()
        nexus._fragments.clear()
    
    generator = TierFragmentGenerator(nexus)
    
    print("\n[*] Generating fragments based on Pioneer tiers...\n")
    
    total_fragments = 0
    total_voting_power = 0
    vault_stats = []
    
    for block_file in sorted(genesis_dir.glob("block_*.json")):
        try:
            with open(block_file, 'r', encoding='utf-8') as f:
                block = json.load(f)
            
            vault_num = block.get('vault_number', 0)
            tier = block.get('tier', 'rare')
            artifact = block.get('artifact', {})
            artifact_rarity = artifact.get('rarity', 'common')
            
            # Creer un seed deterministe base sur le block
            block_hash = block.get('block_hash', block.get('block_id', ''))
            seed = hashlib.sha512(
                f"{block_hash}{vault_num}{tier}".encode()
            ).digest()
            
            print(f"\n  === VAULT #{vault_num} ===")
            print(f"  Tier: {tier.upper()}")
            print(f"  Artifact: [{artifact_rarity.upper()}] {artifact.get('name', 'N/A')}")
            
            # Generer les fragments
            fragments = generator.generate_for_vault(
                vault_num, tier, artifact_rarity, seed
            )
            
            # Stats
            vault_power = sum(f.voting_power for f in fragments)
            vault_mass = sum(f.mass for f in fragments)
            
            gov_fragments = [f for f in fragments if f.governance_tier > 0]
            special_fragments = [f for f in fragments if f.fragment_type not in ['shard', 'splinter', 'dust']]
            
            print(f"  Generated: {len(fragments)} fragments")
            print(f"  Total Mass: {vault_mass:,.0f}")
            print(f"  Voting Power: {vault_power}")
            
            if gov_fragments:
                gov = gov_fragments[0]
                gov_name = next(
                    (t.display_name for t in FragmentType if t.type_id == gov.fragment_type),
                    gov.fragment_type
                )
                print(f"  Governance: {gov_name} (Tier {gov.governance_tier})")
            
            if special_fragments:
                special_types = [f.fragment_type for f in special_fragments if f.fragment_type not in ['voice', 'decree', 'crown']]
                if special_types:
                    print(f"  Special: {', '.join(set(special_types))}")
            
            # Propheties
            prophecy_frags = [f for f in fragments if f.prophecy_text]
            if prophecy_frags:
                print(f"  Prophecy: \"{prophecy_frags[0].prophecy_text[:60]}...\"")
            
            total_fragments += len(fragments)
            total_voting_power += vault_power
            
            vault_stats.append({
                'vault': vault_num,
                'tier': tier,
                'fragments': len(fragments),
                'mass': vault_mass,
                'voting_power': vault_power
            })
            
        except Exception as e:
            print(f"[ERROR] {block_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Resume
    print("\n\n" + "="*70)
    print("  GENERATION COMPLETE")
    print("="*70)
    
    print(f"\n  Total Fragments: {total_fragments}")
    print(f"  Total Voting Power: {total_voting_power}")
    
    stats = nexus.get_statistics()
    print(f"  Total Mass: {stats['total_mass']:,.0f}")
    
    print(f"\n  BY ESSENCE:")
    for essence in FragmentEssence:
        count = stats['by_essence'].get(essence.essence_id, 0)
        if count > 0:
            print(f"    {essence.symbol} {essence.display_name:20}: {count}")
    
    print(f"\n  BY TYPE:")
    for ftype in FragmentType:
        count = stats['by_type'].get(ftype.type_id, 0)
        if count > 0:
            print(f"    {ftype.symbol} {ftype.display_name:20}: {count}")
    
    print(f"\n  VAULT LEADERBOARD (by Voting Power):")
    for vs in sorted(vault_stats, key=lambda x: x['voting_power'], reverse=True):
        print(f"    #{vs['vault']:02d} [{vs['tier']:15}] | Frags: {vs['fragments']:2d} | Vote: {vs['voting_power']:>3.0f} | Mass: {vs['mass']:>8,.0f}")
    
    # Entropie generee
    print(f"\n  Poly-Spinor Entropy Generated: ~{total_fragments * 512:,} bits")


if __name__ == "__main__":
    main()
