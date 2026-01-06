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

Fichiers générés:
- .psnx      : Données cryptographiques compressées
- .blend_data : Structure 3D pour vérification visuelle

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


def print_banner():
    """Affiche la banniere"""
    print("""
+====================================================================+
|     Poly-Spinor Nexus 7D - Generateur de Cle                       |
|     Cryptographie Post-Quantique + Verification Bell               |
+====================================================================+
    """)


def generate_full_key(name: str, output_dir: str, generate_blend: bool = True):
    """
    Génère une clé complète avec toutes les phases.
    
    Args:
        name: Nom du vault/utilisateur
        output_dir: Répertoire de sortie
        generate_blend: Générer le fichier .blend_data
    
    Returns:
        (psnx_path, blend_path, vault_key, entropy_bits)
    """
    from core.complete_key_generator import (
        CompletePolySpinorKeyGenerator,
        CompleteKeyFileGenerator,
        PQ_AVAILABLE
    )
    
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
    
    return psnx_path, blend_path, vault_key, key_data.total_entropy_bits, key_data


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
    
    args = parser.parse_args()
    
    if not args.quiet:
        print_banner()
    
    # Obtenir le nom si non fourni
    if args.name:
        name = args.name
    else:
        name = input("Nom du vault: ").strip()
        if not name:
            name = f"vault_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"[INFO] Nom par défaut: {name}")
    
    # Résoudre le chemin de sortie
    output_dir = os.path.abspath(args.output)
    
    try:
        if args.simple:
            # Mode simplifié
            psnx_path, vault_key, entropy = generate_simple_key(name, output_dir)
            blend_path = None
        else:
            # Mode complet
            psnx_path, blend_path, vault_key, entropy, key_data = generate_full_key(
                name, 
                output_dir,
                generate_blend=not args.no_blend
            )
        
        # Vérifier les fichiers
        verify_key_files(psnx_path, blend_path)
        
        # Resume
        print("\n" + "="*60)
        print("GENERATION TERMINEE")
        print("="*60)
        print(f"""
Fichiers generes:
  PSNX:       {psnx_path}
  Blend:      {blend_path or 'Non genere'}

Cle vault (hex): {vault_key.hex()[:32]}...
Entropie:        {entropy:,} bits

** IMPORTANT **
   - Sauvegardez ces fichiers en lieu sur!
   - Les DEUX fichiers sont necessaires pour acceder au vault
   - Ne partagez JAMAIS ces fichiers
   - Faites des copies de sauvegarde sur supports separes
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
