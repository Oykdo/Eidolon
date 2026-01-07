#!/usr/bin/env python3
"""
Distribue les avatars aux vaults pionniers EXISTANTS uniquement (1-10000)
Les vaults non encore generes devront tenter leur chance avec le RNG normal
"""

import sys
import os
import json
import hashlib
import secrets
from pathlib import Path
from datetime import datetime

# Ajouter le chemin parent
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.avatar_system import (
    AvatarManager,
    QuantumAvatarGenerator,
    PIONEER_AVATAR_LIMIT,
    PIONEER_TIERS,
    PIONEER_RARITY_BONUS,
    PIONEER_MIN_RARITY,
    PIONEER_ATTRIBUTE_MULTIPLIER
)


# ============================================================================
# CONFIGURATION
# ============================================================================

# Adresses Bitcoin par defaut pour les vaults (peuvent etre mises a jour plus tard)
def generate_placeholder_address(vault_num: int) -> str:
    """Genere une adresse placeholder basee sur le vault"""
    # Format bech32 valide pour placeholder
    hash_data = hashlib.sha256(f"vault_{vault_num}_pioneer".encode()).hexdigest()
    return f"bc1q{hash_data[:38]}"


def get_existing_vaults() -> set:
    """
    Detecte les vaults existants en scannant les pierres philosophales.
    Retourne un set des numeros de vaults existants.
    """
    base_path = Path(__file__).parent.parent
    stones_dir = base_path / "philosopher_stones" / "stones"
    
    existing_vaults = set()
    
    if stones_dir.exists():
        for stone_file in stones_dir.glob("*.json"):
            try:
                with open(stone_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                vault_num = data.get('origin_vault')
                if vault_num and isinstance(vault_num, int):
                    existing_vaults.add(vault_num)
            except Exception as e:
                print(f"[WARN] Cannot read {stone_file}: {e}")
    
    return existing_vaults


# ============================================================================
# DISTRIBUTION
# ============================================================================

def distribute_avatars(
    existing_only: bool = True,
    skip_existing: bool = True,
    dry_run: bool = False
) -> dict:
    """
    Distribue les avatars aux vaults pionniers EXISTANTS uniquement.
    
    Args:
        existing_only: Si True, distribue seulement aux vaults existants (defaut: True)
        skip_existing: Ignorer les vaults qui ont deja un avatar
        dry_run: Simulation sans creation reelle
    
    Returns:
        Rapport de distribution
    """
    print("=" * 70)
    print("  DISTRIBUTION DES AVATARS PIONNIERS")
    print("=" * 70)
    print()
    
    # Detecter les vaults existants
    existing_vaults = get_existing_vaults()
    print(f"Vaults existants detectes: {len(existing_vaults)}")
    print(f"Numeros: {sorted(existing_vaults)}")
    print()
    print(f"Mode: {'SIMULATION' if dry_run else 'PRODUCTION'}")
    print(f"Existing only: {existing_only}")
    print(f"Skip existing avatars: {skip_existing}")
    print()
    
    if not existing_vaults:
        print("[WARN] Aucun vault existant detecte!")
        return {"total_processed": 0, "created": 0}
    
    # Initialiser le manager
    manager = AvatarManager()
    
    # Stats
    stats = {
        "total_processed": 0,
        "created": 0,
        "skipped_existing": 0,
        "skipped_ineligible": 0,
        "skipped_not_created": 0,
        "errors": 0,
        "by_tier": {tier: {"count": 0, "rarities": {}} for tier in PIONEER_TIERS.keys()},
        "by_rarity": {},
        "by_type": {},
        "avatars": []
    }
    
    # Parcourir les vaults existants uniquement
    vaults_to_process = sorted(existing_vaults) if existing_only else range(1, PIONEER_AVATAR_LIMIT + 1)
    
    for vault_num in vaults_to_process:
        stats["total_processed"] += 1
        
        # Verifier eligibilite (doit etre <= 10000)
        can_have, reason = QuantumAvatarGenerator.can_have_avatar(vault_num)
        if not can_have:
            stats["skipped_ineligible"] += 1
            print(f"[SKIP] Vault #{vault_num}: {reason}")
            continue
        
        # Si mode existing_only, verifier que le vault existe
        if existing_only and vault_num not in existing_vaults:
            stats["skipped_not_created"] += 1
            continue
        
        # Verifier si deja un avatar
        if skip_existing:
            existing_avatars = manager.get_avatars_owned_by_vault(vault_num)
            if existing_avatars:
                stats["skipped_existing"] += 1
                print(f"[SKIP] Vault #{vault_num}: Avatar deja existant")
                continue
        
        # Determiner le tier
        tier = None
        for t, (min_n, max_n) in PIONEER_TIERS.items():
            if min_n <= vault_num <= max_n:
                tier = t
                break
        
        if not tier:
            stats["skipped_ineligible"] += 1
            continue
        
        # Generer les donnees du vault
        vault_id = f"vault_{vault_num:05d}"
        vault_data = f"{vault_id}_pioneer_{secrets.token_hex(16)}".encode()
        owner_address = generate_placeholder_address(vault_num)
        
        if dry_run:
            # Simulation: juste calculer les stats
            gen = QuantumAvatarGenerator(
                vault_data=vault_data,
                vault_id=vault_id,
                vault_number=vault_num
            )
            rarity = gen.dna.rarity_tier
            geo_type = gen.dna.geometric_name
            
            print(f"[SIM] Vault #{vault_num:>5} ({tier.upper():10}): {rarity.upper():10} - {geo_type}")
            
            stats["created"] += 1
            stats["by_tier"][tier]["count"] += 1
            stats["by_tier"][tier]["rarities"][rarity] = stats["by_tier"][tier]["rarities"].get(rarity, 0) + 1
            stats["by_rarity"][rarity] = stats["by_rarity"].get(rarity, 0) + 1
            stats["by_type"][geo_type] = stats["by_type"].get(geo_type, 0) + 1
            
        else:
            # Production: creer l'avatar
            try:
                avatar = manager.create_avatar(
                    vault_data=vault_data,
                    vault_id=vault_id,
                    vault_number=vault_num,
                    owner_address=owner_address,
                    generation=1,
                    soul_bound=False
                )
                
                rarity = avatar.rarity_tier
                geo_type = avatar.geometry_type
                
                print(f"[OK] Vault #{vault_num:>5} ({tier.upper():10}): {rarity.upper():10} - {geo_type} - PWR:{avatar.effective_power:.0f}")
                
                stats["created"] += 1
                stats["by_tier"][tier]["count"] += 1
                stats["by_tier"][tier]["rarities"][rarity] = stats["by_tier"][tier]["rarities"].get(rarity, 0) + 1
                stats["by_rarity"][rarity] = stats["by_rarity"].get(rarity, 0) + 1
                stats["by_type"][geo_type] = stats["by_type"].get(geo_type, 0) + 1
                
                stats["avatars"].append({
                    "vault_num": vault_num,
                    "tier": tier,
                    "avatar_id": avatar.avatar_id,
                    "rarity": rarity,
                    "type": geo_type,
                    "power": avatar.effective_power
                })
                
            except Exception as e:
                print(f"[ERR] Vault #{vault_num}: {e}")
                stats["errors"] += 1
        
        # Progress tous les 100 vaults
        if vault_num % 100 == 0 and vault_num > start_vault:
            print(f"--- Progress: {vault_num}/{end_vault} ({stats['created']} crees) ---")
    
    # Rapport final
    print()
    print("=" * 70)
    print("  RAPPORT DE DISTRIBUTION")
    print("=" * 70)
    print()
    print(f"Total traites:    {stats['total_processed']}")
    print(f"Avatars crees:    {stats['created']}")
    print(f"Deja existants:   {stats['skipped_existing']}")
    print(f"Non eligibles:    {stats['skipped_ineligible']}")
    print(f"Erreurs:          {stats['errors']}")
    print()
    
    print("PAR TIER:")
    for tier, data in stats["by_tier"].items():
        if data["count"] > 0:
            range_info = PIONEER_TIERS[tier]
            bonus = PIONEER_RARITY_BONUS.get(tier, 0)
            mult = PIONEER_ATTRIBUTE_MULTIPLIER.get(tier, 1.0)
            min_rar = PIONEER_MIN_RARITY.get(tier, "common")
            print(f"  {tier.upper():12} (#{range_info[0]}-{range_info[1]}): {data['count']:>5} avatars")
            print(f"    Bonus: +{bonus} rarete, x{mult} attrs, min {min_rar.upper()}")
            if data["rarities"]:
                rar_str = ", ".join([f"{r}: {c}" for r, c in sorted(data["rarities"].items())])
                print(f"    Raretes: {rar_str}")
    
    print()
    print("PAR RARETE:")
    for rarity in ["primordial", "mythical", "legendary", "epic", "rare", "uncommon", "common"]:
        count = stats["by_rarity"].get(rarity, 0)
        if count > 0:
            pct = (count / stats["created"] * 100) if stats["created"] > 0 else 0
            print(f"  {rarity.upper():12}: {count:>5} ({pct:5.1f}%)")
    
    print()
    print("PAR TYPE GEOMETRIQUE:")
    for geo_type, count in sorted(stats["by_type"].items(), key=lambda x: -x[1]):
        pct = (count / stats["created"] * 100) if stats["created"] > 0 else 0
        print(f"  {geo_type:20}: {count:>5} ({pct:5.1f}%)")
    
    return stats


def save_distribution_report(stats: dict, output_path: str = None):
    """Sauvegarde le rapport de distribution"""
    if output_path is None:
        output_path = Path(__file__).parent.parent / "avatar_distribution_report.json"
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "pioneer_limit": PIONEER_AVATAR_LIMIT,
        "tiers": PIONEER_TIERS,
        "stats": {
            "total_processed": stats["total_processed"],
            "created": stats["created"],
            "skipped_existing": stats["skipped_existing"],
            "errors": stats["errors"]
        },
        "by_tier": stats["by_tier"],
        "by_rarity": stats["by_rarity"],
        "by_type": stats["by_type"],
        "avatars": stats.get("avatars", [])[:1000]  # Limiter pour le fichier
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nRapport sauvegarde: {output_path}")
    return output_path


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Distribue les avatars aux vaults pionniers EXISTANTS")
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans creation")
    parser.add_argument("--force", action="store_true", help="Recreer meme si avatar existant")
    parser.add_argument("--all", action="store_true", help="Distribuer a tous les vaults (pas seulement existants)")
    
    args = parser.parse_args()
    
    print()
    print("NOTE: Ce script distribue les avatars UNIQUEMENT aux vaults deja crees.")
    print("      Les nouveaux vaults devront generer leur avatar eux-memes")
    print("      et auront les bonus RNG selon leur numero.")
    print()
    
    # Executer
    stats = distribute_avatars(
        existing_only=not args.all,
        skip_existing=not args.force,
        dry_run=args.dry_run
    )
    
    # Sauvegarder le rapport
    if not args.dry_run and stats["created"] > 0:
        save_distribution_report(stats)
    
    print()
    print("=" * 70)
    print("  DISTRIBUTION TERMINEE")
    print("=" * 70)
