#!/usr/bin/env python3
"""
Upgrade tous les items existants avec le nouveau systeme de mods
"""

import sys
import os
import json
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.alchemical_items import (
    AlchemicalItemManager, AlchemicalItem, ItemRarity,
    generate_item_mods, ItemMod, ModTier, ITEM_MODS
)


def main():
    print("\n" + "="*70)
    print("  UPGRADE ITEMS - Ajout du Systeme de Mods")
    print("="*70)
    
    base_path = Path(__file__).parent.parent
    items_dir = base_path / "alchemical_vault" / "items"
    
    if not items_dir.exists():
        print("\n[!] No items directory found")
        return
    
    # Charger tous les items
    items = []
    for f in items_dir.glob("item_*.json"):
        with open(f, 'r', encoding='utf-8') as file:
            items.append((f, json.load(file)))
    
    print(f"\n[*] Found {len(items)} items to upgrade")
    
    # Stats
    upgraded = 0
    total_mods = 0
    perfect_rolls = 0
    divine_mods = 0
    mods_by_category = {}
    mods_by_tier = {}
    
    for filepath, item_data in items:
        # Skip si deja des mods
        if item_data.get('mods') and len(item_data['mods']) > 0:
            continue
        
        # Determiner la rarete
        rarity_id = item_data.get('rarity', 'common')
        rarity = next((r for r in ItemRarity if r.rarity_id == rarity_id), ItemRarity.COMMON)
        
        # Generer les mods
        item_id = item_data.get('item_id', '')
        mods = generate_item_mods(rarity, seed=item_id)
        
        if not mods:
            item_data['mods'] = []
        else:
            mods_data = [mod.to_dict() for mod in mods]
            item_data['mods'] = mods_data
            
            total_mods += len(mods)
            
            for mod in mods:
                # Stats
                cat = mod.category
                mods_by_category[cat] = mods_by_category.get(cat, 0) + 1
                
                tier = mod.tier
                mods_by_tier[tier] = mods_by_tier.get(tier, 0) + 1
                
                if mod.roll_percent >= 95:
                    perfect_rolls += 1
                
                if mod.tier == 'divine':
                    divine_mods += 1
        
        # Sauvegarder
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(item_data, f, indent=2, ensure_ascii=False)
        
        upgraded += 1
    
    print(f"\n[+] Upgraded {upgraded} items")
    print(f"    Total mods added: {total_mods}")
    print(f"    Average mods/item: {total_mods/max(upgraded,1):.1f}")
    
    print(f"\n[*] Mods by Category:")
    for cat, count in sorted(mods_by_category.items(), key=lambda x: -x[1]):
        cat_symbol = {"offensive": "⚔️", "defensive": "🛡️", "utility": "⚙️",
                     "elemental": "🔥", "arcane": "✨", "cosmic": "🌟",
                     "corruption": "☠️"}.get(cat, "?")
        print(f"    {cat_symbol} {cat.capitalize()}: {count}")
    
    print(f"\n[*] Mods by Tier:")
    tier_order = ['minor', 'standard', 'greater', 'superior', 'prime', 'divine']
    for tier in tier_order:
        if tier in mods_by_tier:
            tier_enum = next((t for t in ModTier if t.tier_id == tier), None)
            if tier_enum:
                print(f"    [{tier_enum.display_name}] x{mods_by_tier[tier]}")
    
    print(f"\n[*] Special Rolls:")
    print(f"    PERFECT (95%+): {perfect_rolls}")
    print(f"    DIVINE tier: {divine_mods}")
    
    # Afficher quelques exemples
    print("\n" + "-"*70)
    print("  SAMPLE ITEMS WITH MODS")
    print("-"*70)
    
    # Recharger quelques items pour afficher
    sample_count = 0
    for filepath, _ in items[:20]:
        with open(filepath, 'r', encoding='utf-8') as f:
            item_data = json.load(f)
        
        if not item_data.get('mods'):
            continue
        
        item = AlchemicalItem.from_dict(item_data)
        
        if item.mod_count >= 2:
            print(f"\n  {item.display_name} [{item.rarity.upper()}]")
            print(f"  Base Value: {item.value:.0f} | Effective Power: {item.effective_power:.0f}")
            print(f"  Mods ({item.mod_count}):")
            print(item.format_mods_display())
            
            sample_count += 1
            if sample_count >= 5:
                break
    
    print("\n" + "="*70)
    print("  UPGRADE COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
