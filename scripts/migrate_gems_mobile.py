"""
Migration des gemmes existantes vers le systeme mobile
Extrait les gemmes des artefacts et les rend detachables
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

from typing import List
from core.gem_vault import (
    GemVault, MobileGem, GemType, GemRarity, GemCategory,
    GEM_POWERS, format_gem_display
)


def migrate_artifact_gems(artifact_data: dict, vault_number: int, gem_vault: GemVault) -> List:
    """Migre les gemmes d'un artefact vers le systeme mobile"""
    migrated = []
    
    glyph_array = artifact_data.get('glyph_array', {})
    if not glyph_array:
        return migrated
    
    for glyph in glyph_array.get('glyphs', []):
        glyph_id = glyph.get('glyph_id', '')
        glyph_type = glyph.get('glyph_type', '')
        
        for i, gem_data in enumerate(glyph.get('gems', [])):
            # Convertir l'ancienne gemme en MobileGem
            old_type = gem_data.get('gem_type', 'void_crystal')
            old_rarity = gem_data.get('rarity', 'common')
            
            # Mapper vers les nouveaux types
            new_type = map_gem_type(old_type)
            new_rarity = map_gem_rarity(old_rarity)
            
            # Creer la gemme mobile
            gem = gem_vault.generate_gem(
                vault_number=vault_number,
                force_type=new_type,
                force_rarity=new_rarity,
                seed=hashlib.sha256(
                    f"{gem_data.get('gem_id', '')}{glyph_id}{i}".encode()
                ).digest()
            )
            
            # Mettre a jour avec les stats originales si disponibles
            if 'base_power' in gem_data:
                gem.base_power = gem_data['base_power']
            if 'resonance' in gem_data:
                gem.resonance = gem_data['resonance']
            if 'purity' in gem_data:
                gem.purity = gem_data['purity']
            
            # Enchasser dans le glyphe
            gem.current_glyph = glyph_id
            gem.socket_position = i
            gem.status = "socketed"
            gem.origin_glyph = glyph_id
            
            # Sauvegarder
            gem_vault._save_gem(gem)
            migrated.append(gem)
    
    return migrated


def map_gem_type(old_type: str) -> GemType:
    """Mappe les anciens types vers les nouveaux"""
    mapping = {
        'void_crystal': GemType.VOID_CRYSTAL,
        'quantum_shard': GemType.QUANTUM_SHARD,
        'temporal_essence': GemType.TEMPORAL_GEM,
        'spatial_prism': GemType.SPATIAL_PRISM,
        'entropic_core': GemType.ENTROPIC_CORE,
        'harmonic_gem': GemType.HARMONIC_CRYSTAL,
        'celestial_tear': GemType.CELESTIAL_TEAR,
        'spinor_fragment': GemType.SPINOR_MATRIX,
        'bell_resonator': GemType.BELL_RESONATOR,
        'dirac_pearl': GemType.DIRAC_STONE,
        'clifford_stone': GemType.CLIFFORD_JEWEL,
        'merkle_ruby': GemType.MERKLE_ROOT,
        'entropy_sapphire': GemType.ENTROPY_SINGULARITY,
        'nexus_emerald': GemType.NEXUS_KEYSTONE,
    }
    
    result = mapping.get(old_type)
    if result:
        return result
    
    # Sinon choisir aleatoirement
    all_types = list(GemType)
    return all_types[secrets.randbelow(len(all_types))]


def map_gem_rarity(old_rarity: str) -> GemRarity:
    """Mappe les anciennes raretes vers les nouvelles"""
    mapping = {
        'flawed': GemRarity.FLAWED,
        'standard': GemRarity.COMMON,
        'polished': GemRarity.POLISHED,
        'pristine': GemRarity.PRISTINE,
        'perfect': GemRarity.PERFECT,
        'transcendent': GemRarity.TRANSCENDENT,
    }
    
    return mapping.get(old_rarity, GemRarity.COMMON)


def main():
    print("\n" + "="*70)
    print("  GEM MIGRATION - Converting to Mobile Gems")
    print("="*70 + "\n")
    
    base_path = Path(__file__).parent.parent
    genesis_dir = base_path / "genesis_data" / "blocks"
    
    gem_vault = GemVault()
    
    # Compter gemmes existantes
    existing = len(gem_vault.get_all_gems())
    print(f"[*] Existing mobile gems: {existing}")
    
    if existing > 0:
        print("[!] Gems already migrated. Use --force to re-migrate.")
        
        # Afficher les stats
        stats = gem_vault.get_gem_stats()
        print(f"\n  Total: {stats['total_gems']} gems")
        print(f"  Power: {stats['total_power']:,.0f}")
        print(f"\n  By rarity:")
        for r, count in sorted(stats['rarity_breakdown'].items()):
            print(f"    {r}: {count}")
        return
    
    # Migrer les gemmes de chaque bloc
    total_migrated = 0
    
    for block_file in sorted(genesis_dir.glob("block_*.json")):
        try:
            with open(block_file, 'r', encoding='utf-8') as f:
                block = json.load(f)
            
            vault_num = block.get('vault_number', 0)
            artifact = block.get('artifact', {})
            
            if not artifact.get('glyph_array'):
                continue
            
            print(f"\n[+] Migrating Vault #{vault_num}...")
            
            migrated = migrate_artifact_gems(artifact, vault_num, gem_vault)
            total_migrated += len(migrated)
            
            print(f"    Migrated {len(migrated)} gems:")
            
            # Afficher par rarete
            by_rarity = {}
            for gem in migrated:
                by_rarity[gem.rarity] = by_rarity.get(gem.rarity, 0) + 1
            
            for rarity, count in sorted(by_rarity.items()):
                rarity_enum = next((r for r in GemRarity if r.rarity_id == rarity), GemRarity.COMMON)
                print(f"      {rarity_enum.display_name}: {count}")
                
        except Exception as e:
            print(f"[ERROR] {block_file.name}: {e}")
    
    print("\n" + "="*70)
    print(f"  MIGRATION COMPLETE")
    print(f"  Total gems migrated: {total_migrated}")
    print("="*70)
    
    # Generer des gemmes bonus pour les fondateurs
    print("\n[*] Generating founder bonus gems...\n")
    
    founder_blocks = sorted(genesis_dir.glob("block_*.json"))[:6]
    
    bonus_count = 0
    for block_file in founder_blocks:
        with open(block_file, 'r', encoding='utf-8') as f:
            block = json.load(f)
        
        vault_num = block.get('vault_number', 0)
        tier = block.get('tier', 'standard')
        
        # Bonus selon le tier
        if tier == 'quantum_pioneer':
            bonus_gems = 5
            min_rarity = GemRarity.REFINED
        else:
            bonus_gems = 2
            min_rarity = GemRarity.POLISHED
        
        print(f"  Vault #{vault_num} ({tier}): +{bonus_gems} bonus gems")
        
        for _ in range(bonus_gems):
            # Forcer une bonne rarete pour les fondateurs
            rarities = [r for r in GemRarity if r.multiplier >= min_rarity.multiplier]
            force_rarity = rarities[secrets.randbelow(len(rarities))]
            
            gem = gem_vault.generate_gem(
                vault_number=vault_num,
                force_rarity=force_rarity
            )
            print(f"    + {format_gem_display(gem)}")
            bonus_count += 1
    
    print(f"\n  Total bonus gems: {bonus_count}")
    
    # Stats finales
    print("\n" + "="*70)
    print("  FINAL GEM STATISTICS")
    print("="*70)
    
    stats = gem_vault.get_gem_stats()
    print(f"\n  Total Gems: {stats['total_gems']}")
    print(f"  Total Power: {stats['total_power']:,.0f}")
    
    print(f"\n  By Rarity:")
    for rarity in GemRarity:
        count = stats['rarity_breakdown'].get(rarity.rarity_id, 0)
        if count > 0:
            print(f"    {rarity.display_name:15} : {count}")
    
    print(f"\n  By Category:")
    for cat in GemCategory:
        count = stats['category_breakdown'].get(cat.value, 0)
        if count > 0:
            print(f"    {cat.value.upper():15} : {count}")


if __name__ == "__main__":
    from typing import List
    main()
