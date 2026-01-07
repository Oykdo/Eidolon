#!/usr/bin/env python3
"""
Poly-Spinor Nexus 7D - Générateur de Clé Sécurisée
===================================================

Ce script génère une nouvelle paire de clés cryptographiques pour sécuriser un vault.

La clé utilise 9 phases de génération d'entropie:
1. Seed maître (512 bits)
2. Capture spatiale 7D avec calibration EPR
3. Simulation physique des 7 polyèdres
4. Transformation spinorielle Cl(0,7)
5. Vérification des inégalités de Bell 7D
6. Hash spinoriel composite
7. Chiffrement post-quantique (Kyber, Dilithium)
8. Construction de l'arbre de Merkle
9. Dérivation de la clé vault finale

+ GENESIS SYSTEM: Les 100,000 premiers utilisateurs recoivent un Easter Egg!
  - Tier 1 (1-100): Quantum Pioneer - Mythic - 1 milliard runes
  - Tier 2 (101-1000): Spinor Visionary - Legendary - 100M runes
  - Tier 3 (1001-10000): Bell Verifier - Epic - 10M runes
  - Tier 4 (10001-100000): Post-Quantum Guardian - Rare - 1M runes

Fichiers générés:
- .psnx      : Données cryptographiques compressées
- .blend_data : Structure 3D pour vérification visuelle
- genesis_XXXXXX.json : Bloc Genesis avec Easter Egg (si fondateur)

IMPORTANT: Les deux fichiers sont nécessaires pour déverrouiller le vault!

Usage:
    python scripts/generate_key.py
    python scripts/generate_key.py --name "MonVault" --output ./mes_cles
    python scripts/generate_key.py --simple  # Mode simplifié (sans Blender)
"""

import os
import sys
import argparse
import getpass
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.identity_registry import IdentityRegistry, interactive_name_selection


def print_banner():
    """Affiche la banniere"""
    print("""
+====================================================================+
|     Poly-Spinor Nexus 7D - Generateur de Cle                       |
|     Cryptographie Post-Quantique + Verification Bell               |
+====================================================================+
    """)


def generate_full_key(name: str, output_dir: str, generate_blend: bool = True, wallet_address: str = None):
    """
    Génère une clé complète avec toutes les phases + Genesis Block.
    
    Args:
        name: Nom du vault/utilisateur
        output_dir: Répertoire de sortie
        generate_blend: Générer le fichier .blend_data
        wallet_address: Adresse wallet optionnelle pour le Genesis
    
    Returns:
        (psnx_path, blend_path, vault_key, entropy_bits, key_data, genesis_block)
    """
    from core.complete_key_generator import (
        CompletePolySpinorKeyGenerator,
        CompleteKeyFileGenerator,
        PQ_AVAILABLE
    )
    from core.genesis_system import GenesisManager, EasterEggGenerator
    
    print(f"\n[INFO] Génération de clé pour: {name}")
    print(f"[INFO] Post-Quantique disponible: {PQ_AVAILABLE}")
    print(f"[INFO] Répertoire de sortie: {output_dir}")
    print("\n" + "="*60)
    
    # Créer le répertoire
    os.makedirs(output_dir, exist_ok=True)
    
    # Callback de progression (ASCII compatible)
    def progress_callback(phase, progress, message):
        bar_length = 30
        filled = int(bar_length * progress)
        bar = '#' * filled + '-' * (bar_length - filled)
        print(f"\r  Phase {phase}/9 [{bar}] {int(progress*100)}% - {message}", end='', flush=True)
        if progress >= 1.0:
            print()
    
    # Créer le générateur
    generator = CompletePolySpinorKeyGenerator(
        surface_material="granite",
        enable_pq=PQ_AVAILABLE,
        progress_callback=progress_callback
    )
    
    file_generator = CompleteKeyFileGenerator(generator)
    
    # Générer les fichiers
    import secrets
    key_id = secrets.token_hex(4)
    safe_name = name.lower().replace(' ', '_').replace('/', '_')
    filename = f"vault_key_{safe_name}_{key_id}.psnx"
    output_path = os.path.join(output_dir, filename)
    
    print(f"\n[1/9] Génération seed maître...")
    psnx_path, vault_key, blend_path = file_generator.generate_key_file(
        output_path,
        name,
        generate_blend=generate_blend
    )
    
    # Extraire les infos
    key_data, _ = file_generator.extract_key_from_file(psnx_path)
    
    # === GENESIS SYSTEM ===
    print("\n" + "="*60)
    print("  GENESIS SYSTEM - EASTER EGG")
    print("="*60)
    
    # Initialiser le Genesis Manager
    genesis_dir = os.path.join(output_dir, "..", "genesis_data")
    genesis_manager = GenesisManager(genesis_dir)
    
    # Previsualiser le tier
    next_num = genesis_manager.counter["total_inscriptions"] + 1
    tier_info = genesis_manager.get_tier_info(next_num)
    
    print(f"\n  [INFO] Prochaine inscription: #{next_num}")
    print(f"  [INFO] Tier: {tier_info['tier']} - {tier_info['name']}")
    
    if next_num <= 100000:
        print(f"  [INFO] FELICITATIONS! Vous etes un FONDATEUR!")
    
    # Creer le Genesis Block
    user_data = {
        "wallet_address": wallet_address or f"psnx_{key_data.key_id}",
        "vault_name": name,
        "key_id": key_data.key_id,
        "entropy_bits": key_data.total_entropy_bits
    }
    
    print(f"\n  [*] Creation du Genesis Block...")
    genesis_block = genesis_manager.create_genesis_block(user_data, difficulty=12)
    
    # Afficher les infos Easter Egg
    print(f"\n  {'='*50}")
    print(f"  VOTRE GENESIS BLOCK")
    print(f"  {'='*50}")
    print(f"  Inscription #: {genesis_block.inscription_number}")
    print(f"  Block Hash: {genesis_block.block_hash[:24]}...")
    print(f"  Rune Symbol: {genesis_block.rune_symbol}")
    print(f"  Rune Amount: {genesis_block.rune_amount:,}")
    
    if genesis_block.easter_egg_type:
        print(f"\n  [EASTER EGG]")
        print(f"  Type: {genesis_block.easter_egg_type}")
        print(f"  Tier: {genesis_block.tier}")
        if genesis_block.easter_egg_data:
            attrs = genesis_block.easter_egg_data.get('attributes', {})
            rewards = genesis_block.easter_egg_data.get('rewards', {})
            print(f"  Rarete: {attrs.get('rarity', 'N/A')}")
            print(f"  Couleur: {attrs.get('color', 'N/A')}")
            print(f"  Animation: {attrs.get('animation', 'N/A')}")
            print(f"  Multiplicateur Rune: {rewards.get('rune_multiplier', 1)}x")
            print(f"  Airdrop Futur: {'Oui' if rewards.get('future_airdrop') else 'Non'}")
            print(f"  Pouvoir Governance: {rewards.get('governance_power', 0)}")
    
    return psnx_path, blend_path, vault_key, key_data.total_entropy_bits, key_data, genesis_block


def generate_simple_key(name: str, output_dir: str):
    """
    Génère une clé simplifiée (sans Blender, entropie réduite).
    Plus rapide mais moins sécurisé.
    
    Args:
        name: Nom du vault
        output_dir: Répertoire de sortie
    
    Returns:
        (key_path, vault_key)
    """
    import secrets
    import hashlib
    import json
    import zlib
    from datetime import datetime
    
    print(f"\n[INFO] Génération de clé simplifiée pour: {name}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Générer l'entropie de base
    print("[1/4] Génération de l'entropie...")
    master_seed = secrets.token_bytes(64)  # 512 bits
    
    # Dériver des clés
    print("[2/4] Dérivation des clés...")
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    
    salt = hashlib.sha256(name.encode()).digest()
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    vault_key = kdf.derive(master_seed)
    
    # Créer les données de clé
    print("[3/4] Construction des métadonnées...")
    key_id = secrets.token_hex(8)
    key_data = {
        'version': 1,
        'type': 'simple',
        'key_id': key_id,
        'name': name,
        'created_at': datetime.utcnow().isoformat(),
        'master_seed_hash': hashlib.sha256(master_seed).hexdigest(),
        'vault_key_hash': hashlib.sha256(vault_key).hexdigest(),
        'entropy_bits': 512
    }
    
    # Sauvegarder
    print("[4/4] Sauvegarde...")
    safe_name = name.lower().replace(' ', '_')
    filename = f"simple_key_{safe_name}_{key_id[:8]}.psnx"
    output_path = os.path.join(output_dir, filename)
    
    # Format simplifié
    import base64
    file_data = {
        'marker': 'PSNX_SIMPLE',
        'key_data': key_data,
        'encrypted_seed': base64.b64encode(
            # Chiffrer la seed avec la clé dérivée
            _simple_encrypt(master_seed, vault_key)
        ).decode()
    }
    
    compressed = zlib.compress(json.dumps(file_data).encode(), level=9)
    
    with open(output_path, 'wb') as f:
        f.write(b'PSNX')
        f.write(len(compressed).to_bytes(4, 'big'))
        f.write(compressed)
    
    return output_path, vault_key, 512


def _simple_encrypt(data: bytes, key: bytes) -> bytes:
    """Chiffrement simple avec AES-GCM"""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import os
    
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return nonce + ciphertext


def verify_key_files(psnx_path: str, blend_path: str = None):
    """
    Vérifie les fichiers de clé générés.
    
    Args:
        psnx_path: Chemin du fichier .psnx
        blend_path: Chemin du fichier .blend_data (optionnel)
    """
    print("\n" + "="*60)
    print("VÉRIFICATION DES FICHIERS")
    print("="*60)
    
    # Vérifier le fichier PSNX
    if os.path.exists(psnx_path):
        size = os.path.getsize(psnx_path)
        print(f"[OK] Fichier PSNX: {psnx_path}")
        print(f"     Taille: {size:,} bytes")
    else:
        print(f"[ERREUR] Fichier PSNX non trouvé: {psnx_path}")
        return False
    
    # Vérifier le fichier blend_data
    if blend_path:
        if os.path.exists(blend_path):
            size = os.path.getsize(blend_path)
            print(f"[OK] Fichier Blend: {blend_path}")
            print(f"     Taille: {size:,} bytes")
        else:
            print(f"[WARN] Fichier Blend non trouvé: {blend_path}")
    
    return True


def check_machine_lock():
    """Verifie si cette machine peut creer un nouveau vault."""
    try:
        from core.machine_lock import MachineLock, get_machine_info
        
        lock = MachineLock()
        can_create, message = lock.can_create_vault()
        
        if not can_create:
            print("\n" + "=" * 60)
            print("  ERREUR: MACHINE DEJA ENREGISTREE")
            print("=" * 60)
            print(f"\n{message}")
            return False, lock
        
        return True, lock
    except ImportError:
        # Module non disponible, continuer sans verification
        return True, None


def main():
    parser = argparse.ArgumentParser(
        description="Générateur de clé Poly-Spinor Nexus 7D",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s                              # Génération interactive
  %(prog)s --name "MonVault"            # Avec nom spécifié
  %(prog)s --simple                     # Mode simplifié (rapide)
  %(prog)s --output ./mes_cles          # Répertoire personnalisé
  %(prog)s --list                       # Lister les identités existantes
  %(prog)s --machine-info               # Afficher les infos machine
        """
    )
    
    parser.add_argument(
        "--name", "-n",
        help="Nom du vault/utilisateur"
    )
    parser.add_argument(
        "--output", "-o",
        default="./vault_storage/keys",
        help="Répertoire de sortie (défaut: ./vault_storage/keys)"
    )
    parser.add_argument(
        "--simple", "-s",
        action="store_true",
        help="Mode simplifié (plus rapide, moins d'entropie)"
    )
    parser.add_argument(
        "--no-blend",
        action="store_true",
        help="Ne pas générer le fichier .blend_data"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Mode silencieux"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Lister les identités enregistrées"
    )
    parser.add_argument(
        "--no-registry",
        action="store_true",
        help="Ne pas enregistrer dans le registre d'identités"
    )
    parser.add_argument(
        "--machine-info",
        action="store_true",
        help="Afficher les informations de la machine"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forcer la creation (ignorer le verrouillage machine - ADMIN ONLY)"
    )
    
    args = parser.parse_args()
    
    # Mode info machine
    if args.machine_info:
        try:
            from core.machine_lock import MachineLock, get_machine_info
            
            print("\n" + "=" * 60)
            print("  INFORMATIONS MACHINE")
            print("=" * 60)
            
            info = get_machine_info()
            print(f"\n  Machine Hash: {info['machine_hash'][:32]}...")
            print(f"  Short ID: {info['short_id']}")
            print(f"  Platform: {info['platform']}")
            print(f"  Node: {info['node']}")
            
            lock = MachineLock()
            existing = lock.get_registered_vault()
            
            if existing:
                print(f"\n  [VAULT ENREGISTRE SUR CETTE MACHINE]")
                print(f"  Nom: {existing.get('vault_name')}")
                print(f"  Numero: #{existing.get('vault_number')}")
                print(f"  Cree le: {existing.get('created_at', '')[:19]}")
            else:
                print(f"\n  Aucun vault enregistre sur cette machine.")
                print(f"  Vous pouvez creer un nouveau vault.")
            
            print()
        except ImportError as e:
            print(f"\n[ERREUR] Module machine_lock non disponible: {e}")
        return
    
    # Initialiser le registre d'identités
    registry = IdentityRegistry()
    
    # Mode liste des identités
    if args.list:
        print("\n" + "="*60)
        print("  IDENTITES ENREGISTREES")
        print("="*60)
        
        identities = registry.list_identities()
        if not identities:
            print("\n  Aucune identité enregistrée.\n")
        else:
            print(f"\n  {len(identities)} identité(s) trouvée(s):\n")
            for identity in identities:
                status = "OK" if identity.psnx_path and os.path.exists(identity.psnx_path) else "?"
                print(f"  [{status}] {identity.full_id}")
                print(f"      Nom: {identity.name}")
                print(f"      Créé: {identity.created_at[:19]}")
                if identity.psnx_path:
                    print(f"      PSNX: {identity.psnx_path}")
                print()
        return
    
    if not args.quiet:
        print_banner()
    
    # === VERIFICATION VERROUILLAGE MACHINE ===
    machine_lock = None
    if not args.force:
        can_create, machine_lock = check_machine_lock()
        if not can_create:
            print("\n[INFO] Utilisez --machine-info pour voir les details")
            print("[INFO] Si vous etes administrateur, utilisez --force\n")
            sys.exit(1)
    else:
        print("\n[WARN] Mode force active - verification machine ignoree!")
    
    # Obtenir le nom avec vérification d'unicité
    if args.name:
        name = args.name
        # Vérifier disponibilité
        available, error = registry.check_name_available(name)
        if not available:
            print(f"\n[ERREUR] {error}")
            print("[INFO] Utilisez --list pour voir les identités existantes")
            print("[INFO] Ou choisissez un autre nom\n")
            sys.exit(1)
    else:
        # Mode interactif avec vérification
        name = interactive_name_selection(registry)
    
    # Résoudre le chemin de sortie
    output_dir = os.path.abspath(args.output)
    
    try:
        if args.simple:
            # Mode simplifié
            psnx_path, vault_key, entropy = generate_simple_key(name, output_dir)
            blend_path = None
            genesis_block = None
        else:
            # Mode complet
            psnx_path, blend_path, vault_key, entropy, key_data, genesis_block = generate_full_key(
                name, 
                output_dir,
                generate_blend=not args.no_blend
            )
        
        # Vérifier les fichiers
        verify_key_files(psnx_path, blend_path)
        
        # === ENREGISTREMENT IDENTITE ===
        identity = None
        if not args.no_registry:
            print("\n" + "="*60)
            print("  ENREGISTREMENT IDENTITE")
            print("="*60)
            
            success, identity, error = registry.register_identity(
                name=name,
                vault_key=vault_key,
                psnx_path=psnx_path,
                blend_path=blend_path,
                metadata={
                    "entropy_bits": entropy,
                    "genesis_inscription": genesis_block.inscription_number if genesis_block else None,
                    "simple_mode": args.simple
                }
            )
            
            if success:
                print(f"\n  [OK] Identité enregistrée avec succès!")
                print(f"  [ID] {identity.full_id}")
                print(f"\n  Votre identité unique: {identity.name}_{identity.fingerprint}")
            else:
                print(f"\n  [WARN] Impossible d'enregistrer l'identité: {error}")
        
        # === VERROUILLAGE MACHINE ===
        if machine_lock and not args.force:
            print("\n" + "="*60)
            print("  VERROUILLAGE MACHINE")
            print("="*60)
            
            import hashlib
            vault_key_hash = hashlib.sha256(vault_key).hexdigest()
            vault_number = genesis_block.inscription_number if genesis_block else 0
            
            lock_success, lock_msg = machine_lock.register_vault(
                vault_name=name,
                vault_number=vault_number,
                vault_key_hash=vault_key_hash,
                psnx_path=psnx_path
            )
            
            if lock_success:
                print(f"\n  [OK] Machine verrouillée!")
                print(f"  Cette machine est maintenant liée à ce vault.")
                print(f"  Aucun autre vault ne pourra être créé sur cet ordinateur.")
            else:
                print(f"\n  [WARN] {lock_msg}")
        
        # Resume
        print("\n" + "="*60)
        print("GENERATION TERMINEE")
        print("="*60)
        
        genesis_info = ""
        if genesis_block:
            genesis_info = f"""
  [GENESIS]
  Inscription #:  {genesis_block.inscription_number}
  Tier:           {genesis_block.tier or 'STANDARD'}
  Easter Egg:     {genesis_block.easter_egg_type or 'Aucun'}
  Rune:           {genesis_block.rune_symbol}
  Rune Amount:    {genesis_block.rune_amount:,}
"""
        
        identity_info = ""
        if identity:
            identity_info = f"""
  [IDENTITE]
  Nom:            {identity.name}
  Fingerprint:    {identity.fingerprint}
  Full ID:        {identity.full_id}
"""
        
        print(f"""
Fichiers generes:
  PSNX:       {psnx_path}
  Blend:      {blend_path or 'Non genere'}

Cle vault (hex): {vault_key.hex()[:32]}...
Entropie:        {entropy:,} bits
{identity_info}{genesis_info}
** IMPORTANT **
   - Sauvegardez ces fichiers en lieu sur!
   - Les DEUX fichiers sont necessaires pour acceder au vault
   - Ne partagez JAMAIS ces fichiers
   - Faites des copies de sauvegarde sur supports separes
   - Utilisez 'python scripts/generate_key.py --list' pour voir vos identités
""")
        
        # Proposer de lancer le vault
        print("\nPour utiliser cette clé:")
        print(f"  python launch_vault_monitor.py --psnx \"{psnx_path}\"", end="")
        if blend_path:
            print(f" --blend \"{blend_path}\"")
        else:
            print()
        
    except ImportError as e:
        print(f"\n[ERREUR] Module manquant: {e}")
        print("Installez les dépendances: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERREUR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
