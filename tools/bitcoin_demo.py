#!/usr/bin/env python3
"""
Demo Bitcoin - Eidolon
Support BRC-20, ARC-20, Runes, Ordinals, Bitmap
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.complete_key_generator import CompleteKeyFileGenerator, CompletePolySpinorKeyGenerator
from core.bitcoin_wallet import (
    VaultBitcoinWallet, BitcoinAssetManager,
    BitcoinNetwork, AddressType, BitcoinAssetType
)


def connect_vault():
    """Charge la cle vault"""
    psnx_path = 'vault_storage/keys/vault_key_monvaultsecurise_0d3e2fa2.psnx'
    
    if not os.path.exists(psnx_path):
        print("[ERREUR] Fichier cle non trouve!")
        print("Generez d'abord une cle avec: python scripts/generate_key.py")
        return None, None
    
    generator = CompletePolySpinorKeyGenerator()
    file_gen = CompleteKeyFileGenerator(generator)
    key_data, vault_key = file_gen.extract_key_from_file(psnx_path)
    
    return vault_key, key_data


def main():
    print('='*70)
    print('  BITCOIN WALLET - EIDOLON')
    print('  Support: BTC, Ordinals, BRC-20, ARC-20, Runes, Bitmap')
    print('='*70)
    
    # === Connexion au vault ===
    print('\n[1] Connexion au vault...')
    vault_key, key_data = connect_vault()
    
    if vault_key is None:
        return
    
    print(f'    Vault: {key_data.user_name}')
    print(f'    Key ID: {key_data.key_id}')
    
    # === Creation du wallet Bitcoin ===
    print('\n[2] Creation du wallet Bitcoin...')
    
    # Wallet Taproot (recommande pour Ordinals/Runes)
    wallet = VaultBitcoinWallet(
        vault_key=vault_key,
        vault_id=key_data.key_id,
        network=BitcoinNetwork.MAINNET,
        address_type=AddressType.P2TR
    )
    
    print(f'    Reseau: {wallet.network._name}')
    print(f'    Type adresse: {wallet.address_type.value}')
    
    # === Adresses ===
    print('\n[3] Adresses Bitcoin derivees du vault:')
    print('-'*70)
    
    addresses = wallet.get_all_addresses()
    print(f'    Legacy (P2PKH):      {addresses["p2pkh"]}')
    print(f'    SegWit (P2WPKH):     {addresses["p2wpkh"]}')
    print(f'    Taproot (P2TR):      {addresses["p2tr"]}')
    print(f'\n    Adresse principale: {wallet.address}')
    
    # === Cle privee (WIF) ===
    print('\n[4] Cle privee (WIF) - NE JAMAIS PARTAGER!')
    print('-'*70)
    show_key = input('    Afficher la cle privee? (oui/non): ').strip().lower()
    if show_key == 'oui':
        print(f'    WIF: {wallet.private_key_wif}')
    
    # === Verification des soldes ===
    print('\n[5] Verification des actifs Bitcoin...')
    print('-'*70)
    
    try:
        balance = wallet.get_balance(force_refresh=True)
        
        print(f'\n    === BTC Natif ===')
        print(f'    Confirme:     {balance.btc_confirmed:,} sats')
        print(f'    Non confirme: {balance.btc_unconfirmed:,} sats')
        print(f'    Total:        {balance.btc_formatted}')
        
        print(f'\n    === Ordinals (Inscriptions) ===')
        if balance.inscriptions:
            for insc in balance.inscriptions[:5]:
                print(f'    #{insc.inscription_number}: {insc.content_type} ({insc.sat_rarity})')
        else:
            print(f'    Aucune inscription')
        
        print(f'\n    === BRC-20 Tokens ===')
        if balance.brc20_tokens:
            for token in balance.brc20_tokens:
                print(f'    {token.tick}: {token.formatted_balance()}')
        else:
            print(f'    Aucun token BRC-20')
        
        print(f'\n    === ARC-20 Tokens (Atomicals) ===')
        if balance.arc20_tokens:
            for token in balance.arc20_tokens:
                print(f'    {token.ticker}: {token.balance}')
        else:
            print(f'    Aucun token ARC-20')
        
        print(f'\n    === Runes ===')
        if balance.runes:
            for rune in balance.runes:
                print(f'    {rune.name} ({rune.symbol}): {rune.formatted_balance()}')
        else:
            print(f'    Aucune Rune')
        
        print(f'\n    === Bitmap ===')
        if balance.bitmaps:
            for bitmap in balance.bitmaps:
                print(f'    Block #{bitmap.block_number}')
        else:
            print(f'    Aucun Bitmap')
            
    except Exception as e:
        print(f'    [!] Erreur API: {e}')
        print(f'    (Les APIs publiques peuvent etre indisponibles)')
    
    # === Estimation des frais ===
    print('\n[6] Estimation des frais de transaction:')
    print('-'*70)
    
    try:
        fees = wallet.get_fee_estimates()
        print(f'    Rapide (~10 min):  {fees.get("fastestFee", "N/A")} sat/vB')
        print(f'    Normal (~30 min):  {fees.get("halfHourFee", "N/A")} sat/vB')
        print(f'    Economique (~1h):  {fees.get("hourFee", "N/A")} sat/vB')
        print(f'    Minimum:           {fees.get("minimumFee", "N/A")} sat/vB')
    except Exception as e:
        print(f'    [!] Erreur: {e}')
    
    # === Exemple de transfert BRC-20 ===
    print('\n[7] Exemple: Preparer un transfert BRC-20')
    print('-'*70)
    
    transfer = wallet.prepare_brc20_transfer(
        tick="ordi",
        amount=100,
        to_address="bc1p..."
    )
    
    print(f'    Type: {transfer["type"]}')
    print(f'    Tick: {transfer["tick"]}')
    print(f'    Amount: {transfer["amount"]}')
    print(f'\n    Contenu inscription:')
    print(f'    {transfer["inscription_content"]}')
    print(f'\n    Etapes:')
    for step in transfer['steps']:
        print(f'      - {step}')
    
    # === Resume ===
    print('\n' + '='*70)
    print('  RESUME DU WALLET BITCOIN')
    print('='*70)
    print(f'''
    Vault:           {key_data.user_name}
    Adresse Taproot: {wallet.address}
    Reseau:          {wallet.network._name}
    
    Actifs supportes:
    - BTC (Bitcoin natif)
    - Ordinals (Inscriptions NFT)
    - BRC-20 (Tokens sur Ordinals)
    - ARC-20 (Tokens Atomicals)
    - Runes (Tokens fongibles)
    - Bitmap (Metaverse)
    
    Pour recevoir des actifs:
    Envoyez a l'adresse: {wallet.address}
    
    Pour importer dans un wallet externe:
    Utilisez la cle WIF avec Unisat, Xverse, ou OKX Wallet
    ''')


if __name__ == "__main__":
    main()
