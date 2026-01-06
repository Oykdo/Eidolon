"""
Initialisation du Fragment Nexus
Genere des fragments fondateurs pour les premiers vaults
"""

import sys
import os
import secrets
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.fragment_nexus import (
    FragmentNexus, Fragment, FragmentEssence, FragmentType,
    CosmicCycle, CONSTELLATIONS, ALCHEMICAL_RECIPES,
    format_fragment_display
)


def main():
    print("\n" + "="*70)
    print("  FRAGMENT NEXUS INITIALIZATION")
    print("  Decentralized Alchemical Economy")
    print("="*70)
    
    nexus = FragmentNexus()
    
    # Verifier s'il y a deja des fragments
    existing = nexus.get_all_fragments()
    if existing:
        print(f"\n[!] Nexus already initialized with {len(existing)} fragments")
        stats = nexus.get_statistics()
        print(f"    Mass: {stats['total_mass']:,.1f}")
        print(f"    Voting Power: {stats['total_voting_power']:,.1f}")
        return
    
    print("\n[*] Creating Founder Fragments...\n")
    
    # Fragments fondateurs pour les 6 premiers vaults
    founder_allocations = {
        1: {
            "shards": 7,
            "governance": "decree",  # Vault 1 = leader initial
            "special": ["star", "oracle"],
            "essence_bias": FragmentEssence.VOID
        },
        2: {
            "shards": 5,
            "governance": "voice",
            "special": ["star", "catalyst"],
            "essence_bias": FragmentEssence.QUANTUM
        },
        3: {
            "shards": 5,
            "governance": "voice",
            "special": ["star", "omen"],
            "essence_bias": FragmentEssence.TEMPORAL
        },
        4: {
            "shards": 5,
            "governance": "voice",
            "special": ["star", "catalyst"],
            "essence_bias": FragmentEssence.ENTROPIC
        },
        5: {
            "shards": 5,
            "governance": "voice",
            "special": ["star", "echo"],
            "essence_bias": FragmentEssence.HARMONIC
        },
        6: {
            "shards": 4,
            "governance": "voice",
            "special": ["star"],
            "essence_bias": FragmentEssence.CELESTIAL
        },
    }
    
    total_created = 0
    total_voting_power = 0
    
    for vault_num, allocation in founder_allocations.items():
        print(f"\n  === VAULT #{vault_num} ===")
        
        # Creer les shards de base
        for i in range(allocation["shards"]):
            # Varier les essences mais avec un biais
            if secrets.randbelow(100) < 60:
                essence = allocation["essence_bias"]
            else:
                essence = list(FragmentEssence)[secrets.randbelow(7)]
            
            # Type de fragment
            if secrets.randbelow(100) < 70:
                ftype = FragmentType.SHARD
            elif secrets.randbelow(100) < 90:
                ftype = FragmentType.SPLINTER
            else:
                ftype = FragmentType.DUST
            
            mass = 100 + secrets.randbelow(500)
            
            fragment = nexus._create_fragment(
                vault_number=vault_num,
                fragment_type=ftype,
                essence=essence,
                mass=mass
            )
            
            print(f"    {format_fragment_display(fragment)}")
            total_created += 1
        
        # Creer le fragment de gouvernance
        gov_type = allocation["governance"]
        gov_ftype = next(f for f in FragmentType if f.type_id == gov_type)
        
        gov_fragment = nexus._create_fragment(
            vault_number=vault_num,
            fragment_type=gov_ftype,
            essence=FragmentEssence.HARMONIC,
            mass=1000 + secrets.randbelow(1000)
        )
        
        # Configurer la gouvernance
        if gov_type == "decree":
            gov_fragment.governance_tier = 2
            gov_fragment.voting_power = 100
        else:
            gov_fragment.governance_tier = 1
            gov_fragment.voting_power = 25
        
        nexus._save_fragment(gov_fragment)
        total_voting_power += gov_fragment.voting_power
        
        print(f"    {format_fragment_display(gov_fragment)} [GOV: {gov_type.upper()}]")
        total_created += 1
        
        # Creer les fragments speciaux
        for special_type in allocation["special"]:
            special_ftype = next(f for f in FragmentType if f.type_id == special_type)
            
            special_fragment = nexus._create_fragment(
                vault_number=vault_num,
                fragment_type=special_ftype,
                essence=allocation["essence_bias"],
                mass=500 + secrets.randbelow(1000)
            )
            
            # Configuration speciale selon le type
            if special_type == "oracle":
                special_fragment.prophecy_text = "Le Nexus s'eveille. Les sept essences cherchent leur unite."
            elif special_type == "star":
                # Les etoiles peuvent former des constellations
                pass
            elif special_type == "catalyst":
                special_fragment.purity = 80 + secrets.randbelow(20)
            
            nexus._save_fragment(special_fragment)
            
            print(f"    {format_fragment_display(special_fragment)} [SPECIAL]")
            total_created += 1
    
    # Creer quelques intrications initiales
    print("\n\n  === CREATING INITIAL ENTANGLEMENTS ===")
    
    all_fragments = nexus.get_all_fragments()
    echoes = [f for f in all_fragments if f.fragment_type == "echo"]
    
    if len(echoes) >= 2:
        # Les echos peuvent se lier facilement
        success, msg = nexus.create_entanglement(echoes[0].fragment_id, all_fragments[0].fragment_id)
        if success:
            print(f"    {msg}")
    
    # Statistiques finales
    print("\n\n" + "="*70)
    print("  INITIALIZATION COMPLETE")
    print("="*70)
    
    stats = nexus.get_statistics()
    
    print(f"\n  Total Fragments Created: {total_created}")
    print(f"  Total Mass: {stats['total_mass']:,.1f}")
    print(f"  Total Voting Power: {total_voting_power}")
    print(f"  Entanglement Pairs: {stats['entanglement_pairs']}")
    
    # Cycle cosmique
    _, _, sym, name, mods = CosmicCycle.get_current_phase()
    print(f"\n  Current Cosmic Cycle: {sym} {name}")
    print(f"  Market Modifier: x{stats['market_modifier']:.2f}")
    
    # Recettes disponibles
    print(f"\n  Discovered Recipes: {stats['discovered_recipes']}")
    for recipe_id in nexus._discovered_recipes:
        recipe = ALCHEMICAL_RECIPES.get(recipe_id)
        if recipe:
            print(f"    - {recipe.name}")
    
    # Constellations possibles
    print(f"\n  Constellations to Form: {len(CONSTELLATIONS)}")
    for const in CONSTELLATIONS.values():
        positions = len(const.pattern)
        print(f"    - {const.name} ({positions} positions): {const.description}")
    
    # Guide
    print("\n" + "="*70)
    print("  NEXT STEPS:")
    print("="*70)
    print("""
  1. TRANSMUTATION
     Utilisez les recettes pour creer de nouveaux fragments:
     - basic_fusion: 3 eclats -> 1 eclat puissant
     - essence_purification: 7 poussieres -> 1 eclat
     
  2. GOUVERNANCE
     Les detenteurs de Voice/Decree/Crown peuvent:
     - Voter sur les propositions
     - Creer de nouvelles propositions (Decree+)
     - Vetoing (Crown only)
     
  3. CONSTELLATIONS
     Placez des fragments STAR dans les patterns pour:
     - "La Forge": +20% succes transmutation
     - "Le Conseil": x2 pouvoir de vote
     - "L'Oracle": Revele les propheties
     - "Le Nexus": Controle du reseau
     - "La Couronne": Pouvoir supreme
     
  4. RESONANCE
     Liez des fragments entre vaults pour:
     - Propager des effets
     - Augmenter la puissance collective
     - Former des reseaux d'intrication
     
  5. PROPHETIES
     Les fragments Oracle/Omen/Prophecy peuvent:
     - Predire des evenements
     - Influencer les cycles
     - Reveler des recettes cachees
""")


if __name__ == "__main__":
    main()
