"""
Script de mise a niveau des artefacts existants
Ajoute les 7 glyphes et 21 gemmes aux artefacts deja crees
"""

import sys
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime

# Fix encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.glyph_gem_system import PolySpinorGlyphGenerator, format_array_display


def upgrade_artifact_with_glyphs(artifact_data: dict) -> dict:
    """
    Met a niveau un artefact en ajoutant les glyphes et gemmes.
    Utilise le seed original pour la reproductibilite.
    """
    # Recuperer le seed original
    signature = artifact_data.get('signature', {})
    seed_7d = signature.get('seed_7d', [])
    quantum_state = signature.get('quantum_state', '')
    artifact_id = artifact_data.get('artifact_id', '')
    
    # Creer un seed deterministe base sur les donnees existantes
    seed_source = f"{artifact_id}{quantum_state}{json.dumps(seed_7d, sort_keys=True)}"
    master_seed = hashlib.sha512(seed_source.encode()).digest()
    
    # Generer le glyph array
    generator = PolySpinorGlyphGenerator(master_seed)
    array = generator.generate_glyph_array()
    
    # Ajouter au artifact
    artifact_data['glyph_array'] = array.to_dict()
    
    # Mettre a jour les stats avec la puissance des glyphes
    if artifact_data.get('stats'):
        stats = artifact_data['stats']
        old_power = stats.get('effective_power', 0)
        
        # Ajouter 10% de la puissance des glyphes
        glyph_bonus = array.total_power * 0.1
        stats['base_power'] = stats.get('base_power', 0) + glyph_bonus
        
        # Recalculer la puissance effective
        rarity_mults = {
            'common': 1.0, 'uncommon': 1.5, 'rare': 2.5, 'epic': 4.0,
            'legendary': 7.0, 'mythic': 12.0, 'transcendent': 20.0, 'primordial': 50.0
        }
        rarity = artifact_data.get('rarity', 'common')
        rarity_mult = rarity_mults.get(rarity, 1.0)
        
        resonance = stats.get('spinor_resonance', 0)
        entropy_coef = stats.get('entropy_coefficient', 1.0)
        
        stats['total_multiplier'] = rarity_mult * (1 + resonance / 100)
        stats['effective_power'] = stats['base_power'] * stats['total_multiplier'] * entropy_coef
        
        artifact_data['stats'] = stats
    
    return artifact_data, array


def main():
    print("\n" + "="*70)
    print("  ARTIFACT GLYPH UPGRADE - Poly-Spinor Nexus 7D")
    print("="*70 + "\n")
    
    base_path = Path(__file__).parent.parent
    artifacts_dir = base_path / "artifact_vault" / "artifacts"
    genesis_dir = base_path / "genesis_data" / "blocks"
    
    if not artifacts_dir.exists():
        print("[ERROR] Artifact vault not found")
        return
    
    # Compter les artefacts
    artifact_files = list(artifacts_dir.glob("artifact_*.json"))
    print(f"[*] Found {len(artifact_files)} artifacts to upgrade\n")
    
    upgraded_count = 0
    skipped_count = 0
    
    for artifact_file in sorted(artifact_files):
        try:
            with open(artifact_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            artifact_data = data.get('artifact_data', data)
            artifact_id = artifact_data.get('artifact_id', 'unknown')
            name = artifact_data.get('name', 'Unknown')
            rarity = artifact_data.get('rarity', 'unknown').upper()
            vault_num = data.get('origin_vault_number', artifact_data.get('vault_number', '?'))
            
            # Verifier si deja upgrade
            if artifact_data.get('glyph_array'):
                print(f"  [SKIP] #{vault_num} {name} - Already has glyphs")
                skipped_count += 1
                continue
            
            # Upgrade
            print(f"  [+] Upgrading #{vault_num} [{rarity}] {name}...")
            
            upgraded_artifact, array = upgrade_artifact_with_glyphs(artifact_data)
            
            # Mettre a jour le fichier artifact_vault
            if 'artifact_data' in data:
                data['artifact_data'] = upgraded_artifact
            else:
                data = upgraded_artifact
            
            with open(artifact_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Mettre a jour le genesis block correspondant
            if vault_num and vault_num != '?':
                block_file = genesis_dir / f"block_{int(vault_num):08d}.json"
                if block_file.exists():
                    with open(block_file, 'r', encoding='utf-8') as f:
                        block_data = json.load(f)
                    
                    if block_data.get('artifact'):
                        block_data['artifact'] = upgraded_artifact
                        
                        with open(block_file, 'w', encoding='utf-8') as f:
                            json.dump(block_data, f, indent=2, ensure_ascii=False)
                        
                        print(f"      -> Updated genesis block #{vault_num}")
            
            # Stats
            new_power = upgraded_artifact.get('stats', {}).get('effective_power', 0)
            total_gems = array.total_gems
            glyph_power = array.total_power
            
            print(f"      -> Added {total_gems} gems, glyph power: {glyph_power:,.0f}")
            print(f"      -> New total power: {new_power:,.0f}")
            
            upgraded_count += 1
            
        except Exception as e:
            print(f"  [ERROR] {artifact_file.name}: {e}")
    
    print("\n" + "="*70)
    print(f"  UPGRADE COMPLETE")
    print(f"  Upgraded: {upgraded_count}")
    print(f"  Skipped: {skipped_count}")
    print("="*70 + "\n")
    
    # Afficher le nouveau leaderboard
    print("[*] Updated Leaderboard:\n")
    try:
        from core.artifact_ranking import ArtifactPowerSystem
        system = ArtifactPowerSystem()
        print(system.format_leaderboard_display(10))
    except Exception as e:
        print(f"  Could not display leaderboard: {e}")


if __name__ == "__main__":
    main()
