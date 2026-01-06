#!/usr/bin/env python3
"""Affiche le contenu du vault"""
import sys
sys.path.insert(0, '.')

from core.complete_key_generator import CompleteKeyFileGenerator, CompletePolySpinorKeyGenerator
from core.persistent_vault import PersistentVaultManager

# Connexion
psnx_path = 'vault_storage/keys/vault_key_monvaultsecurise_0d3e2fa2.psnx'
generator = CompletePolySpinorKeyGenerator()
file_gen = CompleteKeyFileGenerator(generator)
key_data, vault_key = file_gen.extract_key_from_file(psnx_path)

vault = PersistentVaultManager(vault_key, key_data.user_name)
stats = vault.get_stats()

print('='*60)
print(f'  CONTENU DU VAULT: {key_data.user_name}')
print('='*60)

print('\n--- STATISTIQUES ---')
print(f'  Actifs:     {stats["asset_count"]}')
print(f'  Documents:  {stats["document_count"]}')
print(f'  Transfers:  {stats["pending_transfers"]}')

print('\n--- ACTIFS ---')
assets = vault.list_assets()
if assets:
    for a in assets:
        name = a.get('name', 'Sans nom')
        atype = a.get('asset_type', '?')
        chain = a.get('chain', 'N/A')
        aid = a.get('id', '?')[:8]
        print(f'  [{aid}] {name}')
        print(f'            Type: {atype} | Chain: {chain}')
        meta = a.get('metadata', {})
        if 'symbol' in meta:
            print(f'            Balance: {meta.get("balance", "?")} {meta["symbol"]}')
        if 'token_id' in a:
            print(f'            Token ID: {a["token_id"]}')
else:
    print('  (vide)')

print('\n--- DOCUMENTS ---')
docs = vault.list_documents()
if docs:
    for d in docs:
        did = d.get('id', '?')[:8]
        dname = d.get('original_name', 'Document')
        print(f'  [{did}] {dname}')
        meta = d.get('metadata', {})
        if meta:
            print(f'            Categorie: {meta.get("category", "N/A")}')
            print(f'            Sensibilite: {meta.get("sensitivity", "N/A")}')
else:
    print('  (vide)')

print('\n--- TRANSFERS PROGRAMMES ---')
transfers = vault.get_pending_transfers()
if transfers:
    for t in transfers:
        tid = t.get('id', '?')[:8]
        ttype = t.get('transfer_type', '?')
        dest = t.get('destination', '?')[:24]
        exp = t.get('expiry', '?')
        print(f'  [{tid}] {ttype}')
        print(f'            Vers: {dest}...')
        print(f'            Expire: {exp}')
        meta = t.get('metadata', {})
        if 'reason' in meta:
            print(f'            Raison: {meta["reason"]}')
else:
    print('  (aucun)')

print()
