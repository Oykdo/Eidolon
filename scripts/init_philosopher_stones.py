"""
Initialisation des Pierres Philosophales
A partir des fragments Philosopher existants
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.fragment_nexus import FragmentNexus, Fragment
from core.philosopher_stone import (
    PhilosopherStoneManager, PhilosopherStone, PhilosopherAbility,
    SECRET_RECIPES, format_stone_display
)


def main():
    print("\n" + "="*70)
    print("  PHILOSOPHER STONE INITIALIZATION")
    print("  Creating stones from existing fragments")
    print("="*70)
    
    nexus = FragmentNexus()
    stone_manager = PhilosopherStoneManager()
    
    # Trouver tous les fragments Philosopher
    all_fragments = nexus.get_all_fragments()
    philosopher_fragments = [f for f in all_fragments if f.fragment_type == "philosopher"]
    
    print(f"\n[*] Found {len(philosopher_fragments)} Philosopher fragments")
    
    existing_stones = stone_manager.get_all_stones()
    existing_fragment_ids = {s.fragment_id for s in existing_stones}
    
    print(f"[*] Existing stones: {len(existing_stones)}")
    
    new_stones = []
    
    for frag in philosopher_fragments:
        if frag.fragment_id in existing_fragment_ids:
            print(f"  [SKIP] Fragment {frag.fragment_id[:8]} already has a stone")
            continue
        
        print(f"\n  [+] Creating stone for Vault #{frag.current_vault}...")
        print(f"      Fragment: {frag.fragment_id[:8]}")
        print(f"      Mass: {frag.mass:,.0f}")
        print(f"      Purity: {frag.purity:.1f}%")
        
        # Creer la pierre
        stone = stone_manager.create_stone(frag.fragment_id, frag.current_vault)
        
        # Bonus selon la masse et purete du fragment
        mass_bonus = frag.mass / 1000  # 1 energie bonus par 1000 masse
        purity_bonus = frag.purity / 10  # 1% regen bonus par 10% purete
        
        stone.max_energy = int(1000 + mass_bonus * 100)
        stone.current_energy = stone.max_energy // 2
        stone.energy_regen_rate = 1.0 + purity_bonus
        
        # Affinites basees sur l'essence du fragment
        if frag.essence == "void":
            stone.affinities["resurrect_soul"] = 1.3
            stone.affinities["transmute_divine"] = 1.2
        elif frag.essence == "quantum":
            stone.affinities["open_portal"] = 1.3
            stone.affinities["permanent_gate"] = 1.2
        elif frag.essence == "temporal":
            stone.affinities["grant_immortality"] = 1.3
            stone.affinities["fulfill_prophecy"] = 1.2
        elif frag.essence == "celestial":
            stone.affinities["star_creation"] = 1.3
            stone.affinities["constellation_activation"] = 1.2
        
        stone_manager._save_stone(stone)
        new_stones.append(stone)
        
        print(f"      Stone ID: {stone.stone_id[:8]}")
        print(f"      Max Energy: {stone.max_energy}")
        print(f"      Regen Rate: {stone.energy_regen_rate:.2f}/h")
    
    # Eveiller automatiquement les pierres des Vaults fondateurs (1-6)
    print("\n\n[*] Awakening founder stones...")
    
    for stone in new_stones:
        if stone.origin_vault <= 6:
            success, msg = stone_manager.awaken_stone(stone.stone_id)
            if success:
                print(f"  [+] Vault #{stone.origin_vault}: {msg}")
    
    # Stats finales
    print("\n\n" + "="*70)
    print("  INITIALIZATION COMPLETE")
    print("="*70)
    
    stats = stone_manager.get_statistics()
    
    print(f"\n  Total Stones: {stats['total_stones']}")
    print(f"  Awakened: {stats['awakened']}")
    print(f"  Dormant: {stats['dormant']}")
    print(f"  Total Energy Pool: {stats['total_energy']:,}")
    
    print(f"\n  STONES BY VAULT:")
    for vault_num in range(1, 7):
        vault_stones = stone_manager.get_vault_stones(vault_num)
        if vault_stones:
            stone = vault_stones[0]
            print(f"    Vault #{vault_num}: {format_stone_display(stone)}")
    
    print(f"\n  AVAILABLE ABILITIES ({len(list(PhilosopherAbility))}):")
    for ability in list(PhilosopherAbility)[:10]:
        print(f"    ☿ {ability.display_name:30} | {ability.energy_cost:4} energy")
    print(f"    ... and {len(list(PhilosopherAbility)) - 10} more")
    
    print(f"\n  SECRET RECIPES TO DISCOVER ({len(SECRET_RECIPES)}):")
    for recipe_id, recipe in list(SECRET_RECIPES.items())[:5]:
        print(f"    📜 {recipe['name']:25} | {recipe['unlock_cost']:3} energy")
    print(f"    ... and {len(SECRET_RECIPES) - 5} more")
    
    # Guide d'utilisation
    print("\n" + "="*70)
    print("  HOW TO USE PHILOSOPHER STONES")
    print("="*70)
    print("""
  TRANSMUTATION:
    stone_manager.transmute_gem(stone_id, gem_data)
    -> Eleve la rarete d'une gemme (Common -> Divine)
    -> Cout: 20 energie, 80% succes de base
    
  RESURRECTION:
    stone_manager.resurrect_soul(stone_id, soul_fragment)
    -> Ressuscite une gemme a partir de son ame
    -> Cout: 50 energie
    
  PORTAILS:
    stone_manager.open_portal(stone_id, from_vault, to_vault)
    -> Ouvre un passage entre deux vaults (24h)
    -> Cout: 30 energie
    
  AMPLIFICATION:
    stone_manager.amplify_artifact(stone_id, artifact_data)
    -> +50% puissance d'artefact
    -> Cout: 40 energie
    
  RECETTES:
    stone_manager.unlock_recipe(stone_id, recipe_id)
    -> Deverrouille une recette secrete
    -> Cout: 35-200 energie selon la recette
    
  PROPHETIE:
    stone_manager.reveal_prophecy(stone_id)
    -> Revele une prophetie cachee
    -> Cout: 10 energie
    
  TRANSCENDANCE:
    stone_manager.transcend(stone_id)
    -> Eleve la pierre a l'etat ultime
    -> Requires: 10 transmutations, 3 resurrections, 3 recettes
    -> Cout: 1000 energie
    -> Resultat: 5x energie max, 10x regen, capacites ultimes
""")


if __name__ == "__main__":
    main()
