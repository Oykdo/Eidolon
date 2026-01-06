#!/usr/bin/env python3
"""
Reorganise les items dans des coffres selon les tiers des vaults
Distribue les coffres equitablement
"""

import sys
import os
import json
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.alchemical_items import (
    AlchemicalItemManager, AlchemicalItem, AlchemicalChest,
    ItemRarity, ChestTier, generate_item_mods
)


# Configuration des coffres par tier de vault
VAULT_TIER_CHESTS = {
    "primordial": {
        "chests": [
            {"tier": "primordial", "count": 1},  # 31 items
            {"tier": "legendary", "count": 2},   # 40 items
            {"tier": "epic", "count": 3},        # 30 items
        ],
        "total_items": 101
    },
    "transcendent": {
        "chests": [
            {"tier": "legendary", "count": 2},   # 40 items
            {"tier": "epic", "count": 2},        # 20 items
            {"tier": "rare", "count": 2},        # 10 items
        ],
        "total_items": 70
    },
    "mythic": {
        "chests": [
            {"tier": "legendary", "count": 1},   # 20 items
            {"tier": "epic", "count": 2},        # 20 items
            {"tier": "rare", "count": 3},        # 15 items
        ],
        "total_items": 55
    },
    "legendary": {
        "chests": [
            {"tier": "epic", "count": 2},        # 20 items
            {"tier": "rare", "count": 3},        # 15 items
            {"tier": "common", "count": 2},      # 4 items
        ],
        "total_items": 39
    },
    "quantum_pioneer": {
        "chests": [
            {"tier": "legendary", "count": 1},   # 20 items
            {"tier": "epic", "count": 2},        # 20 items
            {"tier": "rare", "count": 2},        # 10 items
        ],
        "total_items": 50
    },
    # Default pour les tiers non specifies
    "default": {
        "chests": [
            {"tier": "epic", "count": 1},        # 10 items
            {"tier": "rare", "count": 2},        # 10 items
            {"tier": "common", "count": 3},      # 6 items
        ],
        "total_items": 26
    }
}


# Bonus de rarete selon tier du coffre
CHEST_RARITY_BOOST = {
    "primordial": 2.5,
    "legendary": 1.8,
    "epic": 1.2,
    "rare": 0.6,
    "common": 0.0
}


def get_chest_tier_enum(tier_id: str) -> ChestTier:
    return next((t for t in ChestTier if t.tier_id == tier_id), ChestTier.COMMON)


def generate_chest_id(vault: int, tier: str) -> str:
    return hashlib.sha256(
        f"chest_v{vault}_{tier}_{datetime.now().isoformat()}_{secrets.token_hex(4)}".encode()
    ).hexdigest()[:16]


def generate_item_id(vault: int, item_type: str) -> str:
    return hashlib.sha256(
        f"item_v{vault}_{item_type}_{datetime.now().isoformat()}_{secrets.token_hex(4)}".encode()
    ).hexdigest()[:16]


def main():
    print("\n" + "="*70)
    print("  REORGANISATION DES COFFRES ET ITEMS")
    print("  Distribution par Tier de Vault")
    print("="*70)
    
    base_path = Path(__file__).parent.parent
    genesis_dir = base_path / "genesis_data" / "blocks"
    
    # Nettoyer les anciens fichiers
    items_dir = base_path / "alchemical_vault" / "items"
    chests_dir = base_path / "alchemical_vault" / "chests"
    
    print("\n[*] Cleaning old data...")
    
    # Supprimer les anciens fichiers
    for f in items_dir.glob("item_*.json"):
        f.unlink()
    for f in chests_dir.glob("chest_*.json"):
        f.unlink()
    
    items_dir.mkdir(parents=True, exist_ok=True)
    chests_dir.mkdir(parents=True, exist_ok=True)
    
    # Charger les vaults
    vaults = []
    for block_file in sorted(genesis_dir.glob("block_*.json")):
        with open(block_file, 'r', encoding='utf-8') as f:
            vaults.append(json.load(f))
    
    print(f"[*] Found {len(vaults)} vaults")
    
    # Import des types d'items
    from core.alchemical_items import ALCHEMICAL_ITEMS, RARITY_WEIGHTS
    
    all_item_types = list(ALCHEMICAL_ITEMS.keys())
    
    total_chests = 0
    total_items = 0
    global_stats = {
        "by_rarity": {},
        "by_category": {},
        "by_tier": {},
        "perfect_mods": 0,
        "divine_mods": 0,
    }
    
    print("\n[*] Distributing chests and generating items...\n")
    
    for vault in vaults:
        vault_num = vault.get('vault_number', 0)
        vault_tier = vault.get('tier', 'default').lower().replace(' ', '_')
        artifact = vault.get('artifact', {})
        artifact_rarity = artifact.get('rarity', 'common')
        
        print(f"\n{'='*60}")
        print(f"  VAULT #{vault_num} - {vault_tier.upper()}")
        print(f"  Artifact: [{artifact_rarity.upper()}] {artifact.get('name', 'N/A')[:35]}")
        print(f"{'='*60}")
        
        # Obtenir la config de coffres pour ce tier
        tier_config = VAULT_TIER_CHESTS.get(vault_tier, VAULT_TIER_CHESTS['default'])
        
        vault_chests = []
        vault_items = []
        
        for chest_config in tier_config['chests']:
            chest_tier = chest_config['tier']
            chest_count = chest_config['count']
            
            for _ in range(chest_count):
                # Creer le coffre
                chest_tier_enum = get_chest_tier_enum(chest_tier)
                chest_id = generate_chest_id(vault_num, chest_tier)
                
                chest_data = {
                    "chest_id": chest_id,
                    "tier": chest_tier,
                    "items": [],
                    "item_count": chest_tier_enum.item_count,
                    "is_opened": True,
                    "opened_at": datetime.now().isoformat(),
                    "opened_by_vault": vault_num,
                    "origin_vault": vault_num,
                    "created_at": datetime.now().isoformat(),
                    "bonus_rarity_boost": CHEST_RARITY_BOOST.get(chest_tier, 0),
                    "guaranteed_legendary": chest_tier in ['primordial', 'legendary']
                }
                
                # Generer les items pour ce coffre
                rarity_boost = CHEST_RARITY_BOOST.get(chest_tier, 0)
                
                # Garantir un item legendaire pour les coffres haut tier
                guaranteed_legendary_added = False
                
                for i in range(chest_tier_enum.item_count):
                    # Choisir un type d'item aleatoire
                    item_type = secrets.choice(all_item_types)
                    item_def = ALCHEMICAL_ITEMS[item_type]
                    
                    # Determiner la rarete
                    min_rarity = item_def.get('min_rarity')
                    
                    if chest_data['guaranteed_legendary'] and not guaranteed_legendary_added and i == 0:
                        # Premier item garanti legendaire
                        rarity = ItemRarity.LEGENDARY
                        guaranteed_legendary_added = True
                    else:
                        # Roll normal avec boost
                        eligible = list(ItemRarity)
                        if min_rarity:
                            min_idx = [r.rarity_id for r in ItemRarity].index(min_rarity)
                            eligible = [r for r in ItemRarity if list(ItemRarity).index(r) >= min_idx]
                        
                        weights = {}
                        for r in eligible:
                            base_weight = RARITY_WEIGHTS.get(r, 100)
                            idx = list(ItemRarity).index(r)
                            boost_factor = 1 + (rarity_boost * idx / 8)
                            weights[r] = base_weight * boost_factor
                        
                        total_weight = sum(weights.values())
                        roll = secrets.randbelow(int(total_weight))
                        cumulative = 0
                        rarity = ItemRarity.COMMON
                        for r, w in weights.items():
                            cumulative += w
                            if roll < cumulative:
                                rarity = r
                                break
                    
                    # Stats de l'item
                    min_val, max_val = item_def.get('value_range', (1, 100))
                    value = min_val + secrets.randbelow(int(max_val - min_val + 1))
                    value *= rarity.multiplier
                    
                    min_dur, max_dur = item_def.get('duration_range', (0, 0))
                    duration = min_dur + secrets.randbelow(max(1, int(max_dur - min_dur + 1))) if max_dur > 0 else 0
                    
                    # ID unique
                    item_id = generate_item_id(vault_num, item_type)
                    
                    # Generer les mods
                    item_mods = generate_item_mods(rarity, seed=item_id)
                    mods_data = [mod.to_dict() for mod in item_mods]
                    
                    # Compter les mods speciaux
                    for mod in item_mods:
                        if mod.roll_percent >= 95:
                            global_stats["perfect_mods"] += 1
                        if mod.tier == 'divine':
                            global_stats["divine_mods"] += 1
                    
                    # Extra charges
                    extra_charges = 0
                    for mod in item_mods:
                        if mod.mod_id == "mod_charges_extra":
                            extra_charges = int(mod.rolled_value)
                            break
                    
                    max_charges = item_def.get('charges', 1) if isinstance(item_def.get('charges'), int) else 1
                    
                    item_data = {
                        "item_id": item_id,
                        "item_type": item_type,
                        "category": item_def['category'],
                        "rarity": rarity.rarity_id,
                        "value": round(value, 2),
                        "duration": duration,
                        "charges": max_charges + extra_charges,
                        "max_charges": max_charges + extra_charges,
                        "mods": mods_data,
                        "is_used": False,
                        "is_bound": False,
                        "bound_to": None,
                        "linked_gem_id": None,
                        "linked_artifact_id": None,
                        "enchanted_on": None,
                        "origin_vault": vault_num,
                        "origin_chest": chest_id,
                        "created_at": datetime.now().isoformat(),
                        "current_vault": vault_num,
                        "status": "inventory"
                    }
                    
                    # Ajouter au coffre
                    chest_data['items'].append(item_id)
                    vault_items.append(item_data)
                    
                    # Stats
                    global_stats['by_rarity'][rarity.rarity_id] = global_stats['by_rarity'].get(rarity.rarity_id, 0) + 1
                    global_stats['by_category'][item_def['category']] = global_stats['by_category'].get(item_def['category'], 0) + 1
                
                vault_chests.append(chest_data)
        
        # Sauvegarder les coffres et items
        for chest in vault_chests:
            filepath = chests_dir / f"chest_{chest['chest_id']}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(chest, f, indent=2, ensure_ascii=False)
        
        for item in vault_items:
            filepath = items_dir / f"item_{item['item_id']}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(item, f, indent=2, ensure_ascii=False)
        
        # Afficher le resume
        print(f"\n  Coffres distribues: {len(vault_chests)}")
        for chest in vault_chests:
            tier_enum = get_chest_tier_enum(chest['tier'])
            print(f"    📦 {tier_enum.display_name} ({len(chest['items'])} items)")
        
        print(f"\n  Items generes: {len(vault_items)}")
        
        # Stats par rarete pour ce vault
        vault_rarities = {}
        for item in vault_items:
            r = item['rarity']
            vault_rarities[r] = vault_rarities.get(r, 0) + 1
        
        for rarity_id in ['primordial', 'mythical', 'legendary', 'masterwork', 'exquisite', 'superior', 'refined', 'common', 'crude']:
            if rarity_id in vault_rarities:
                print(f"    [{rarity_id.upper()}] x{vault_rarities[rarity_id]}")
        
        # Compter mods
        total_mods = sum(len(item['mods']) for item in vault_items)
        print(f"\n  Total mods: {total_mods} (avg {total_mods/len(vault_items):.1f}/item)")
        
        total_chests += len(vault_chests)
        total_items += len(vault_items)
        global_stats['by_tier'][vault_tier] = global_stats['by_tier'].get(vault_tier, 0) + len(vault_items)
    
    # Resume global
    print("\n\n" + "="*70)
    print("  DISTRIBUTION COMPLETE")
    print("="*70)
    
    print(f"\n  Total Chests: {total_chests}")
    print(f"  Total Items: {total_items}")
    
    print(f"\n  Items by Rarity:")
    for rarity_id in ['primordial', 'mythical', 'legendary', 'masterwork', 'exquisite', 'superior', 'refined', 'common', 'crude']:
        if rarity_id in global_stats['by_rarity']:
            count = global_stats['by_rarity'][rarity_id]
            pct = count / total_items * 100
            bar = "█" * int(pct / 2)
            print(f"    [{rarity_id.upper():12}] {count:4} ({pct:5.1f}%) {bar}")
    
    print(f"\n  Items by Category:")
    for cat, count in sorted(global_stats['by_category'].items(), key=lambda x: -x[1]):
        print(f"    {cat:12} : {count}")
    
    print(f"\n  Items by Vault Tier:")
    for tier, count in sorted(global_stats['by_tier'].items(), key=lambda x: -x[1]):
        print(f"    {tier:20} : {count}")
    
    print(f"\n  Special Mods:")
    print(f"    PERFECT rolls (95%+): {global_stats['perfect_mods']}")
    print(f"    DIVINE tier mods: {global_stats['divine_mods']}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
