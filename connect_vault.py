#!/usr/bin/env python3
"""
Script de connexion au Vault avec cle Poly-Spinor Nexus 7D
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.complete_key_generator import CompleteKeyFileGenerator, CompletePolySpinorKeyGenerator
from core.persistent_vault import PersistentVaultManager
from sdk.python.psnx_sdk import Vault, SecretSharing

def main():
    psnx_path = 'vault_storage/keys/vault_key_monvaultsecurise_0d3e2fa2.psnx'
    blend_path = 'vault_storage/keys/vault_key_monvaultsecurise_0d3e2fa2.blend_data'

    print('='*60)
    print('  CONNEXION AU VAULT POLY-SPINOR NEXUS 7D')
    print('='*60)

    # === PHASE 1: Extraction de la cle ===
    print('\n[1] EXTRACTION DE LA CLE DEPUIS FICHIER PSNX')
    print('-'*50)
    
    generator = CompletePolySpinorKeyGenerator()
    file_gen = CompleteKeyFileGenerator(generator)
    key_data, vault_key = file_gen.extract_key_from_file(psnx_path)

    print(f'    Key ID:          {key_data.key_id}')
    print(f'    Utilisateur:     {key_data.user_name}')
    print(f'    Date creation:   {key_data.created_at}')
    print(f'    Entropie:        {key_data.total_entropy_bits:,} bits')
    
    # Details des phases
    print(f'\n    [Phases de generation]')
    print(f'    - Seed maitre:   512 bits')
    print(f'    - Capture 7D:    {key_data.spatial_data.entropy_bits} bits ({key_data.spatial_data.total_points} points)')
    print(f'    - Physique:      {key_data.physics_data.entropy_bits} bits ({key_data.physics_data.total_collisions} collisions)')
    print(f'    - Spinor Cl(7):  {key_data.spinor_data.entropy_bits} bits')
    print(f'    - Bell 7D:       {key_data.bell_data.entropy_bits} bits (quantique: {key_data.bell_data.is_quantum})')
    print(f'    - Hash:          {key_data.hash_data.entropy_bits} bits')
    if key_data.pq_data:
        print(f'    - Post-Quantique: {key_data.pq_data.entropy_bits} bits')

    # === PHASE 2: Verification fichier Blend ===
    print('\n[2] VERIFICATION FICHIER BLEND')
    print('-'*50)
    
    if os.path.exists(blend_path):
        size = os.path.getsize(blend_path)
        print(f'    Fichier:   {blend_path}')
        print(f'    Taille:    {size:,} bytes')
        print(f'    Status:    OK')
    else:
        print(f'    ERREUR: Fichier blend non trouve!')
        return

    # === PHASE 3: Initialisation du Vault ===
    print('\n[3] INITIALISATION DU VAULT')
    print('-'*50)
    
    vault = PersistentVaultManager(vault_key, key_data.user_name)
    stats = vault.get_stats()
    
    print(f'    Nom:       {stats["vault_name"]}')
    print(f'    Version:   {stats["version"]}')
    print(f'    Actifs:    {stats["asset_count"]}')
    print(f'    Documents: {stats["document_count"]}')
    print(f'    Transfers: {stats["pending_transfers"]}')

    # === PHASE 4: Test Cryptographique ===
    print('\n[4] TEST DE CHIFFREMENT AES-256-GCM')
    print('-'*50)
    
    crypto_vault = Vault(vault_key)
    test_data = b'Message secret protege par Poly-Spinor Nexus 7D!'
    
    encrypted = crypto_vault.encrypt(test_data)
    decrypted = crypto_vault.decrypt(encrypted)
    
    print(f'    Original:   {test_data.decode()}')
    print(f'    Nonce:      {encrypted.nonce.hex()}')
    print(f'    Ciphertext: {encrypted.ciphertext[:16].hex()}...')
    print(f'    Tag:        {encrypted.tag.hex()}')
    print(f'    Dechiffre:  {decrypted.decode()}')
    print(f'    Integrite:  {"OK" if decrypted == test_data else "ERREUR"}')

    # === PHASE 5: Fingerprint ===
    print('\n[5] IDENTIFIANTS UNIQUES')
    print('-'*50)
    
    fingerprint = crypto_vault.get_fingerprint()
    print(f'    Vault Key (hex): {vault_key.hex()[:32]}...')
    print(f'    Fingerprint:     {fingerprint}')
    print(f'    Merkle Root:     {key_data.merkle_root[:32]}...')

    # === PHASE 6: Secret Sharing ===
    print('\n[6] CREATION PARTS SHAMIR (3-of-5)')
    print('-'*50)
    
    sharing = SecretSharing(threshold=3, total=5)
    shares = sharing.split(vault_key)
    
    print(f'    Parts creees: {len(shares)}')
    for share in shares:
        print(f'      Part {share.index}: checksum={share.checksum}')
    
    # Test reconstruction
    selected = [shares[0], shares[2], shares[4]]
    recovered = sharing.reconstruct(selected)
    print(f'\n    Reconstruction avec parts 1, 3, 5...')
    print(f'    Cle recuperee: {recovered.hex()[:32]}...')
    print(f'    Verification:  {"OK" if recovered == vault_key else "ERREUR"}')

    # === RESUME ===
    print('\n' + '='*60)
    print('  VAULT CONNECTE ET OPERATIONNEL')
    print('='*60)
    print(f'''
  Votre vault "{key_data.user_name}" est pret a utiliser.
  
  Fichiers de cle:
    - PSNX:  {psnx_path}
    - Blend: {blend_path}
  
  Securite:
    - Entropie: {key_data.total_entropy_bits:,} bits (>8000 = excellent)
    - Bell quantique: {"Oui" if key_data.bell_data.is_quantum else "Non"}
    - Post-quantique: {"Actif" if key_data.pq_data else "Inactif"}
  
  Commandes disponibles:
    vault.add_asset(data)        # Ajouter un actif
    vault.add_document(path)     # Ajouter un document
    vault.list_assets()          # Lister les actifs
    vault.export_vault(path)     # Exporter le vault
''')

if __name__ == "__main__":
    main()
