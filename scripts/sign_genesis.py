#!/usr/bin/env python3
"""
Poly-Spinor Nexus 7D - Signature des Blocs Genesis
====================================================

Ce script permet de signer vos blocs Genesis avec votre cle vault,
prouvant cryptographiquement votre propriete des runes.

Usage:
    python scripts/sign_genesis.py                    # Signer tous vos blocs
    python scripts/sign_genesis.py --block 1         # Signer un bloc specifique
    python scripts/sign_genesis.py --list            # Lister les blocs
    python scripts/sign_genesis.py --verify          # Verifier les signatures
"""

import os
import sys
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature


class GenesisBlockSigner:
    """Gestionnaire de signature des blocs Genesis"""
    
    def __init__(self, genesis_dir: str = None):
        if genesis_dir is None:
            base_path = Path(__file__).parent.parent
            genesis_dir = base_path / "genesis_data"
        
        self.genesis_dir = Path(genesis_dir)
        self.blocks_dir = self.genesis_dir / "blocks"
        
        if not self.blocks_dir.exists():
            raise FileNotFoundError(f"Repertoire genesis non trouve: {self.blocks_dir}")
    
    def list_blocks(self) -> List[Dict]:
        """Liste tous les blocs Genesis"""
        blocks = []
        
        for block_file in sorted(self.blocks_dir.glob("block_*.json")):
            with open(block_file, 'r', encoding='utf-8') as f:
                block_data = json.load(f)
                block_data['_file'] = str(block_file)
                blocks.append(block_data)
        
        return blocks
    
    def get_block(self, vault_number: int) -> Optional[Dict]:
        """Recupere un bloc par son numero"""
        block_file = self.blocks_dir / f"block_{vault_number:08d}.json"
        
        if not block_file.exists():
            return None
        
        with open(block_file, 'r', encoding='utf-8') as f:
            block_data = json.load(f)
            block_data['_file'] = str(block_file)
            return block_data
    
    def derive_signing_key(self, vault_key: bytes) -> ec.EllipticCurvePrivateKey:
        """Derive une cle de signature ECDSA depuis la cle vault"""
        # Utiliser la cle vault comme seed pour generer une cle ECDSA deterministe
        seed = hashlib.sha256(vault_key + b"PSNX_GENESIS_SIGN_v1").digest()
        
        # Creer une cle privee ECDSA depuis le seed
        private_key = ec.derive_private_key(
            int.from_bytes(seed, 'big') % (2**256 - 1),
            ec.SECP256K1(),
            default_backend()
        )
        
        return private_key
    
    def get_public_key_hex(self, private_key: ec.EllipticCurvePrivateKey) -> str:
        """Obtient la cle publique en hexadecimal"""
        public_key = private_key.public_key()
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.CompressedPoint
        )
        return public_bytes.hex()
    
    def create_signature_payload(self, block_data: Dict) -> bytes:
        """Cree le payload a signer"""
        # Elements critiques du bloc
        payload = {
            "block_id": block_data.get("block_id"),
            "vault_number": block_data.get("vault_number"),
            "vault_name": block_data.get("vault_name"),
            "block_hash": block_data.get("block_hash"),
            "tier": block_data.get("tier"),
            "rune_balance": block_data.get("rune_balance"),
            "spinor_seed": block_data.get("spinor_seed"),
            "merkle_root": block_data.get("merkle_root"),
        }
        
        # Inscription runique
        if block_data.get("runic_inscription"):
            payload["inscription_id"] = block_data["runic_inscription"].get("inscription_id")
            payload["rune_symbols"] = block_data["runic_inscription"].get("rune_symbols")
        
        # Serialiser de maniere deterministe
        payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return payload_json.encode('utf-8')
    
    def sign_block(self, block_data: Dict, vault_key: bytes) -> Tuple[str, str]:
        """
        Signe un bloc Genesis.
        
        Returns:
            (signature_hex, public_key_hex)
        """
        private_key = self.derive_signing_key(vault_key)
        payload = self.create_signature_payload(block_data)
        
        # Signer avec ECDSA
        signature = private_key.sign(
            payload,
            ec.ECDSA(hashes.SHA256())
        )
        
        signature_hex = signature.hex()
        public_key_hex = self.get_public_key_hex(private_key)
        
        return signature_hex, public_key_hex
    
    def verify_signature(self, block_data: Dict, signature_hex: str, public_key_hex: str) -> bool:
        """Verifie une signature de bloc"""
        try:
            # Reconstruire la cle publique
            public_bytes = bytes.fromhex(public_key_hex)
            public_key = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256K1(),
                public_bytes
            )
            
            # Reconstruire le payload
            payload = self.create_signature_payload(block_data)
            signature = bytes.fromhex(signature_hex)
            
            # Verifier
            public_key.verify(signature, payload, ec.ECDSA(hashes.SHA256()))
            return True
            
        except (InvalidSignature, ValueError, Exception):
            return False
    
    def save_block(self, block_data: Dict):
        """Sauvegarde un bloc modifie"""
        file_path = block_data.get('_file')
        if not file_path:
            vault_num = block_data.get('vault_number', 0)
            file_path = self.blocks_dir / f"block_{vault_num:08d}.json"
        
        # Retirer le champ temporaire
        save_data = {k: v for k, v in block_data.items() if not k.startswith('_')}
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
    
    def sign_and_save(self, vault_number: int, vault_key: bytes) -> Dict:
        """Signe un bloc et sauvegarde"""
        block_data = self.get_block(vault_number)
        if not block_data:
            raise ValueError(f"Bloc #{vault_number} non trouve")
        
        # Signer
        signature, public_key = self.sign_block(block_data, vault_key)
        
        # Mettre a jour le bloc
        block_data['signature'] = signature
        block_data['signer_public_key'] = public_key
        block_data['signed_at'] = datetime.utcnow().isoformat()
        
        # Sauvegarder
        self.save_block(block_data)
        
        return {
            "vault_number": vault_number,
            "signature": signature[:32] + "...",
            "public_key": public_key,
            "signed_at": block_data['signed_at']
        }


def load_vault_key(psnx_path: str) -> bytes:
    """Charge la cle vault depuis un fichier .psnx"""
    from core.complete_key_generator import CompleteKeyFileGenerator, CompletePolySpinorKeyGenerator
    
    generator = CompletePolySpinorKeyGenerator()
    file_gen = CompleteKeyFileGenerator(generator)
    key_data, vault_key = file_gen.extract_key_from_file(psnx_path)
    
    return vault_key


def interactive_key_selection() -> bytes:
    """Selection interactive de la cle"""
    from tkinter import Tk, filedialog
    
    print("\n  Selection du fichier .psnx...")
    
    root = Tk()
    root.withdraw()
    
    psnx_path = filedialog.askopenfilename(
        title="Selectionnez votre fichier .psnx",
        filetypes=[("PSNX files", "*.psnx"), ("All files", "*.*")]
    )
    
    root.destroy()
    
    if not psnx_path:
        raise ValueError("Aucun fichier selectionne")
    
    print(f"  Fichier: {psnx_path}")
    return load_vault_key(psnx_path)


def main():
    parser = argparse.ArgumentParser(
        description="Signature des blocs Genesis Poly-Spinor Nexus 7D"
    )
    
    parser.add_argument("--list", "-l", action="store_true",
                       help="Lister tous les blocs Genesis")
    parser.add_argument("--block", "-b", type=int,
                       help="Numero du bloc a signer")
    parser.add_argument("--all", "-a", action="store_true",
                       help="Signer tous les blocs non signes")
    parser.add_argument("--verify", "-v", action="store_true",
                       help="Verifier les signatures existantes")
    parser.add_argument("--psnx", "-p", type=str,
                       help="Chemin du fichier .psnx")
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("  POLY-SPINOR NEXUS 7D - SIGNATURE GENESIS")
    print("="*60)
    
    signer = GenesisBlockSigner()
    blocks = signer.list_blocks()
    
    # Mode liste
    if args.list:
        print(f"\n  {len(blocks)} bloc(s) Genesis trouve(s):\n")
        for block in blocks:
            vault_num = block.get('vault_number', '?')
            tier = block.get('tier', 'standard')
            runes = block.get('runic_inscription', {}).get('rune_symbols', '')
            signed = "SIGNE" if block.get('signature') else "NON SIGNE"
            balance = block.get('rune_balance', 0)
            
            print(f"  #{vault_num:05d} | {tier:<20} | {runes} | {balance:>13,} runes | [{signed}]")
        print()
        return
    
    # Mode verification
    if args.verify:
        print(f"\n  Verification de {len(blocks)} bloc(s)...\n")
        
        for block in blocks:
            vault_num = block.get('vault_number', '?')
            signature = block.get('signature', '')
            public_key = block.get('signer_public_key', '')
            
            if not signature:
                print(f"  #{vault_num:05d} | [ ] Non signe")
            elif not public_key:
                print(f"  #{vault_num:05d} | [?] Signature sans cle publique")
            else:
                valid = signer.verify_signature(block, signature, public_key)
                status = "[OK]" if valid else "[X]"
                print(f"  #{vault_num:05d} | {status} {'Valide' if valid else 'INVALIDE'}")
        
        print()
        return
    
    # Mode signature - charger la cle
    if args.psnx:
        vault_key = load_vault_key(args.psnx)
    else:
        vault_key = interactive_key_selection()
    
    # Signer un bloc specifique
    if args.block:
        print(f"\n  Signature du bloc #{args.block}...")
        result = signer.sign_and_save(args.block, vault_key)
        
        print(f"\n  [OK] Bloc #{result['vault_number']} signe!")
        print(f"  Signature: {result['signature']}")
        print(f"  Cle publique: {result['public_key']}")
        print(f"  Date: {result['signed_at']}")
        return
    
    # Signer tous les blocs non signes
    if args.all:
        unsigned = [b for b in blocks if not b.get('signature')]
        
        if not unsigned:
            print("\n  Tous les blocs sont deja signes!")
            return
        
        print(f"\n  Signature de {len(unsigned)} bloc(s) non signe(s)...\n")
        
        for block in unsigned:
            vault_num = block.get('vault_number')
            result = signer.sign_and_save(vault_num, vault_key)
            runes = block.get('runic_inscription', {}).get('rune_symbols', '')
            print(f"  [OK] #{vault_num:05d} {runes} signe")
        
        print(f"\n  {len(unsigned)} bloc(s) signe(s) avec succes!")
        return
    
    # Par defaut, proposer de tout signer
    unsigned = [b for b in blocks if not b.get('signature')]
    
    if not unsigned:
        print("\n  Tous vos blocs Genesis sont deja signes!")
        print("  Utilisez --verify pour verifier les signatures.")
    else:
        print(f"\n  {len(unsigned)} bloc(s) non signe(s) detecte(s).")
        print("  Utilisez --all pour les signer tous.")
        print("  Utilisez --block N pour signer un bloc specifique.")


if __name__ == "__main__":
    main()
