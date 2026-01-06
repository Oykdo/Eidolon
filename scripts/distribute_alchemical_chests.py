"""
Distribution des Coffres Alchimiques aux Vaults
Selon leur tier et la rarete de leur artefact
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.alchemical_items import (
    AlchemicalItemManager, AlchemicalItem, AlchemicalChest,
    AlchemicalCategory, ItemRarity, ChestTier,
    ALCHEMICAL_ITEMS, format_item_display, format_chest_display
)


def main():
    print("\n" + "="*70)
    print("  ALCHEMICAL CHEST DISTRIBUTION")
    print("  Based on Vault Tier & Artifact Rarity")
    print("="*70)
    
    base_path = Path(__file__).parent.parent
    genesis_dir = base_path / "genesis_data" / "blocks"
    
    manager = AlchemicalItemManager()
    
    # Stats initiales
    initial_stats = manager.get_statistics()
    print(f"\n[*] Initial state: {initial_stats['total_chests']} chests, {initial_stats['total_items']} items")
    
    print("\n[*] Distributing chests to vaults...\n")
    
    total_chests = 0
    total_items = 0
    vault_results = []
    
    for block_file in sorted(genesis_dir.glob("block_*.json")):
        try:
            with open(block_file, 'r', encoding='utf-8') as f:
                block = json.load(f)
            
            vault_num = block.get('vault_number', 0)
            tier = block.get('tier', 'rare')
            artifact = block.get('artifact', {})
            artifact_rarity = artifact.get('rarity', 'common')
            
            print(f"  === VAULT #{vault_num} ===")
            print(f"  Tier: {tier.upper()}")
            print(f"  Artifact: [{artifact_rarity.upper()}] {artifact.get('name', 'N/A')[:30]}")
            
            # Verifier si deja distribue
            existing_chests = manager.get_vault_chests(vault_num)
            if existing_chests:
                print(f"  [SKIP] Already has {len(existing_chests)} chests")
                vault_results.append({
                    'vault': vault_num,
                    'chests': len(existing_chests),
                    'items': 0,
                    'skipped': True
                })
                continue
            
            # Distribuer les coffres
            chests = manager.distribute_chests_for_vault(
                vault_num, tier, artifact_rarity
            )
            
            print(f"  Distributed {len(chests)} chests:")
            
            vault_items = 0
            for chest in chests:
                tier_enum = next((t for t in ChestTier if t.tier_id == chest.tier), ChestTier.COMMON)
                print(f"    📦 {tier_enum.display_name} ({chest.item_count} items)")
                vault_items += chest.item_count
            
            total_chests += len(chests)
            total_items += vault_items
            
            vault_results.append({
                'vault': vault_num,
                'chests': len(chests),
                'items': vault_items,
                'skipped': False
            })
            
        except Exception as e:
            print(f"[ERROR] {block_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Ouvrir automatiquement les coffres pour les fondateurs (demo)
    print("\n\n[*] Opening chests for founder vaults (demo)...\n")
    
    opened_items = []
    for vault_num in range(1, 7):
        vault_chests = manager.get_vault_chests(vault_num, unopened_only=True)
        
        if not vault_chests:
            continue
        
        print(f"\n  === VAULT #{vault_num} OPENING ===")
        
        for chest in vault_chests:
            success, items, msg = manager.open_chest(chest.chest_id, vault_num)
            
            if success:
                tier_enum = next((t for t in ChestTier if t.tier_id == chest.tier), ChestTier.COMMON)
                print(f"\n    📦 {tier_enum.display_name}:")
                
                # Afficher les items par rarete
                by_rarity = {}
                for item in items:
                    rarity = item.rarity
                    if rarity not in by_rarity:
                        by_rarity[rarity] = []
                    by_rarity[rarity].append(item)
                
                # Ordre de rarete
                rarity_order = ['primordial', 'mythical', 'legendary', 'masterwork', 
                               'exquisite', 'superior', 'refined', 'common', 'crude']
                
                for rarity in rarity_order:
                    if rarity in by_rarity:
                        rarity_enum = next((r for r in ItemRarity if r.rarity_id == rarity), ItemRarity.COMMON)
                        for item in by_rarity[rarity]:
                            cat = next((c for c in AlchemicalCategory if c.cat_id == item.category), None)
                            symbol = cat.symbol if cat else "?"
                            print(f"      {symbol} [{rarity_enum.display_name[:4].upper()}] {item.display_name}")
                
                opened_items.extend(items)
    
    # Stats finales
    print("\n\n" + "="*70)
    print("  DISTRIBUTION COMPLETE")
    print("="*70)
    
    final_stats = manager.get_statistics()
    
    print(f"\n  CHESTS:")
    print(f"    Total: {final_stats['total_chests']}")
    print(f"    Opened: {final_stats['total_chests'] - final_stats['unopened_chests']}")
    print(f"    Unopened: {final_stats['unopened_chests']}")
    
    print(f"\n  ITEMS:")
    print(f"    Total: {final_stats['total_items']}")
    print(f"    Total Value: {final_stats['total_value']:,.0f}")
    
    print(f"\n  BY CATEGORY:")
    for cat in AlchemicalCategory:
        count = final_stats['by_category'].get(cat.cat_id, 0)
        if count > 0:
            print(f"    {cat.symbol} {cat.display_name:15}: {count}")
    
    print(f"\n  BY RARITY:")
    for rarity in ItemRarity:
        count = final_stats['by_rarity'].get(rarity.rarity_id, 0)
        if count > 0:
            print(f"    [{rarity.display_name:12}]: {count}")
    
    print(f"\n  VAULT SUMMARY:")
    for vr in vault_results:
        status = "[SKIP]" if vr['skipped'] else f"{vr['chests']} chests, {vr['items']} potential items"
        print(f"    Vault #{vr['vault']:02d}: {status}")
    
    # Highlight rare finds
    print(f"\n  RARE FINDS (Legendary+):")
    rare_items = [i for i in opened_items 
                  if i.rarity in ['legendary', 'mythical', 'primordial']]
    
    if rare_items:
        for item in rare_items:
            rarity = next((r for r in ItemRarity if r.rarity_id == item.rarity), ItemRarity.COMMON)
            cat = next((c for c in AlchemicalCategory if c.cat_id == item.category), None)
            print(f"    ★ [{rarity.display_name}] {item.display_name}")
            print(f"      Effect: {item.effect_description}")
    else:
        print("    No legendary+ items found yet")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
