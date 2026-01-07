#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         INITIALISATION DES VAULTS SUPREMES (#1-33)                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Ce script initialise les 33 premiers vaults avec:                           ║
║  - Une Pierre Philosophale unique                                            ║
║  - Des coffres alchimiques bonus                                             ║
║  - Des items exclusifs Supreme                                               ║
║  - Des fragments speciaux                                                    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import json
import hashlib
import secrets
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.genesis_system import SUPREME_COUNT, GenesisTier, EasterEggGenerator
from core.philosopher_stone import (
    PhilosopherStoneManager, PhilosopherStone, PhilosopherAbility,
    format_stone_display
)
from core.alchemical_items import (
    AlchemicalItemManager, AlchemicalItem, AlchemicalChest,
    AlchemicalCategory, ItemRarity, ChestTier
)


def create_supreme_stone(stone_manager: PhilosopherStoneManager, 
                         vault_number: int) -> PhilosopherStone:
    """Cree une Pierre Philosophale Supreme pour un vault fondateur."""
    
    # Generer un fragment ID unique pour cette pierre
    fragment_id = hashlib.sha256(
        f"supreme_fragment_{vault_number}_{datetime.now().isoformat()}".encode()
    ).hexdigest()
    
    # Creer la pierre
    stone = stone_manager.create_stone(fragment_id, vault_number)
    
    # Bonus Supreme: energie augmentee
    base_energy = 1000
    supreme_bonus = (SUPREME_COUNT - vault_number + 1) * 100  # Plus le vault est tot, plus le bonus
    stone.max_energy = base_energy + supreme_bonus
    stone.current_energy = stone.max_energy
    
    # Taux de regeneration accelere
    stone.energy_regen_rate = 2.0 + (SUPREME_COUNT - vault_number + 1) * 0.1
    
    # Affinites Supreme (toutes augmentees)
    for ability in PhilosopherAbility:
        stone.affinities[ability.ability_id] = 1.33  # 33% bonus
    
    # Vault #1 a des affinites encore plus fortes
    if vault_number == 1:
        for ability in PhilosopherAbility:
            stone.affinities[ability.ability_id] = 2.0  # 100% bonus
        stone.max_energy = 3333
        stone.current_energy = 3333
        stone.energy_regen_rate = 10.0
    
    # Eveiller automatiquement
    stone.state = "awakened"
    stone.awakening_date = datetime.now().isoformat()
    
    stone_manager._save_stone(stone)
    
    return stone


def create_supreme_items(item_manager: AlchemicalItemManager,
                         vault_number: int) -> list:
    """Cree des items exclusifs Supreme."""
    
    items = []
    
    # Items Supreme exclusifs
    supreme_items_config = [
        {
            "item_type": "crown_supreme",
            "category": "artifact",
            "rarity": "primordial",
            "display_name": f"Couronne Supreme #{vault_number}",
            "description": "Couronne des Architectes Supremes, symbole du pouvoir absolu",
            "effects": ["governance_power_x3", "veto_power", "supreme_aura"],
            "stat_power": 10000 + (SUPREME_COUNT - vault_number) * 500
        },
        {
            "item_type": "scepter_authority",
            "category": "artifact",
            "rarity": "mythical",
            "display_name": f"Sceptre d'Autorite #{vault_number}",
            "description": "Sceptre conferant l'autorite supreme sur les fragments",
            "effects": ["fragment_mastery", "transmutation_x2"],
            "stat_power": 8000 + (SUPREME_COUNT - vault_number) * 300
        },
        {
            "item_type": "orb_genesis",
            "category": "orb",
            "rarity": "mythical",
            "display_name": "Orbe de la Genese",
            "description": "Contient l'essence de la creation",
            "effects": ["creation_power", "energy_amplify"],
            "stat_power": 7500
        },
        {
            "item_type": "elixir_immortality",
            "category": "potion",
            "rarity": "legendary",
            "display_name": "Elixir d'Immortalite",
            "description": "Confere l'immortalite aux fragments",
            "effects": ["immortality_24h", "decay_immunity"],
            "charges": 3,
            "stat_power": 5000
        },
        {
            "item_type": "rune_supreme",
            "category": "rune",
            "rarity": "legendary",
            "display_name": f"Rune Supreme #{vault_number}",
            "description": "Rune gravee par les Architectes",
            "effects": ["power_boost_33", "luck_boost"],
            "stat_power": 4500
        }
    ]
    
    for config in supreme_items_config:
        item_id = hashlib.sha256(
            f"{config['item_type']}_{vault_number}_{secrets.token_hex(4)}".encode()
        ).hexdigest()[:16]
        
        item = AlchemicalItem(
            item_id=item_id,
            item_type=config["item_type"],
            category=config["category"],
            rarity=config["rarity"],
            value=config.get("stat_power", 1000),
            duration=0,
            stat_power=config.get("stat_power", 1000),
            charges=config.get("charges", 0),
            max_charges=config.get("charges", 0),
            origin_vault=vault_number,
            current_vault=vault_number,
            created_at=datetime.now().isoformat(),
            status="inventory"
        )
        
        item_manager._save_item(item)
        items.append(item)
    
    return items


def create_supreme_chests(item_manager: AlchemicalItemManager,
                          vault_number: int) -> list:
    """Cree des coffres bonus pour les Supremes."""
    
    chests = []
    
    # Configuration des coffres Supreme
    chest_configs = [
        {"tier": "primordial", "count": 1, "items": 10},
        {"tier": "legendary", "count": 2, "items": 8},
        {"tier": "masterwork", "count": 3, "items": 6},
    ]
    
    # Vault #1 obtient plus
    if vault_number == 1:
        chest_configs.append({"tier": "primordial", "count": 2, "items": 15})
    
    for config in chest_configs:
        for _ in range(config["count"]):
            chest_id = secrets.token_hex(8)
            
            chest = AlchemicalChest(
                chest_id=chest_id,
                tier=config["tier"],
                item_count=config["items"],
                origin_vault=vault_number,
                created_at=datetime.now().isoformat(),
                is_opened=False,
                bonus_rarity_boost=0.33,  # Supreme bonus
                guaranteed_legendary=True
            )
            
            item_manager._save_chest(chest)
            chests.append(chest)
    
    return chests


def main():
    print("\n" + "="*70)
    print("  INITIALISATION DES VAULTS SUPREMES (#1-33)")
    print("  Les Architectes Supremes du Poly-Spinor Nexus")
    print("="*70)
    
    print(f"\n[*] SUPREME_COUNT = {SUPREME_COUNT}")
    print(f"[*] Initialisation des vaults #1 a #{SUPREME_COUNT}...")
    
    # Managers
    stone_manager = PhilosopherStoneManager()
    item_manager = AlchemicalItemManager()
    
    # Stats initiales
    existing_stones = stone_manager.get_all_stones()
    print(f"\n[*] Pierres existantes: {len(existing_stones)}")
    
    results = []
    
    for vault_num in range(1, SUPREME_COUNT + 1):
        print(f"\n{'='*50}")
        print(f"  VAULT #{vault_num} - SUPREME ARCHITECT")
        print(f"{'='*50}")
        
        # Verifier si le vault a deja une pierre
        vault_stones = stone_manager.get_vault_stones(vault_num)
        
        if vault_stones:
            print(f"  [EXISTS] Pierre deja presente: {vault_stones[0].stone_id[:8]}")
            stone = vault_stones[0]
        else:
            # Creer la Pierre Philosophale
            print(f"  [NEW] Creation de la Pierre Philosophale...")
            stone = create_supreme_stone(stone_manager, vault_num)
            print(f"        Stone ID: {stone.stone_id[:8]}")
            print(f"        Energie: {stone.current_energy}/{stone.max_energy}")
            print(f"        Regen: {stone.energy_regen_rate:.1f}/h")
        
        # Creer les items Supreme
        print(f"\n  [ITEMS] Distribution des items Supreme...")
        items = create_supreme_items(item_manager, vault_num)
        for item in items:
            print(f"        - [{item.rarity.upper()[:4]}] {item.display_name}")
        
        # Creer les coffres bonus
        print(f"\n  [CHESTS] Distribution des coffres bonus...")
        chests = create_supreme_chests(item_manager, vault_num)
        for chest in chests:
            print(f"        - [{chest.tier.upper()}] {chest.item_count} items")
        
        # Easter egg info
        egg = EasterEggGenerator.get_easter_egg(vault_num)
        print(f"\n  [TIER] {egg['name']}")
        print(f"        Gouvernance: {egg['rewards']['governance_power']}")
        print(f"        Multiplicateur: {egg['rewards']['rune_multiplier']}x")
        
        results.append({
            "vault": vault_num,
            "stone_id": stone.stone_id,
            "stone_energy": stone.max_energy,
            "items_count": len(items),
            "chests_count": len(chests),
            "tier": egg['name']
        })
    
    # Resume final
    print("\n\n" + "="*70)
    print("  INITIALISATION COMPLETE")
    print("="*70)
    
    print(f"\n  STATISTIQUES:")
    print(f"  - Vaults Supreme initialises: {len(results)}")
    print(f"  - Pierres Philosophales creees: {sum(1 for r in results if 'stone_id' in r)}")
    print(f"  - Items Supreme distribues: {sum(r['items_count'] for r in results)}")
    print(f"  - Coffres bonus distribues: {sum(r['chests_count'] for r in results)}")
    
    # Tableau recapitulatif
    print(f"\n  RECAPITULATIF PAR VAULT:")
    print(f"  {'Vault':<8} {'Pierre':<12} {'Energie':<10} {'Items':<8} {'Coffres':<8}")
    print(f"  {'-'*50}")
    
    for r in results:
        print(f"  #{r['vault']:<7} {r['stone_id'][:10]:<12} {r['stone_energy']:<10} {r['items_count']:<8} {r['chests_count']:<8}")
    
    # Sauvegarder le rapport
    report_path = Path(__file__).parent.parent / "supreme_distribution_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "supreme_count": SUPREME_COUNT,
            "vaults": results,
            "total_items": sum(r['items_count'] for r in results),
            "total_chests": sum(r['chests_count'] for r in results)
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n  Rapport sauvegarde: {report_path}")
    
    print("\n" + "="*70)
    print("  LES ARCHITECTES SUPREMES SONT PRETS")
    print("="*70)
    print("""
  Chaque Supreme Architect possede maintenant:
  
  ☿ PIERRE PHILOSOPHALE
    - Energie augmentee (jusqu'a 3333 pour Vault #1)
    - Regeneration acceleree
    - Affinites Supreme (+33% toutes capacites)
    - Eveillee et prete a l'usage
    
  👑 COURONNE SUPREME
    - Pouvoir de gouvernance x3
    - Droit de veto
    - Aura Supreme
    
  ⚔ SCEPTRE D'AUTORITE
    - Maitrise des fragments
    - Transmutation x2
    
  🔮 ORBE DE LA GENESE
    - Pouvoir de creation
    - Amplification d'energie
    
  ⚗ ELIXIR D'IMMORTALITE (x3)
    - Protection contre le decay
    - Immortalite 24h
    
  ᚠ RUNE SUPREME
    - +33% puissance
    - Bonus de chance
    
  📦 COFFRES BONUS
    - 1 Primordial (10 items)
    - 2 Legendary (8 items chacun)
    - 3 Masterwork (6 items chacun)
""")


if __name__ == "__main__":
    main()
