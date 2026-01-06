#!/usr/bin/env python3
"""
Transfer USDC depuis le Vault Poly-Spinor Nexus 7D
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.complete_key_generator import CompleteKeyFileGenerator, CompletePolySpinorKeyGenerator
from core.evm_wallet import VaultHDWallet, EVMChain

# === CONFIGURATION ===
USDC_CONTRACTS = {
    'ethereum': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
    'polygon': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
    'arbitrum': '0xaf88d065e77c8cC2239327C5EDb3A432268e5831',
    'base': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
}

def connect_vault():
    """Charge la cle et retourne le vault_key"""
    psnx_path = 'vault_storage/keys/vault_key_monvaultsecurise_0d3e2fa2.psnx'
    
    generator = CompletePolySpinorKeyGenerator()
    file_gen = CompleteKeyFileGenerator(generator)
    key_data, vault_key = file_gen.extract_key_from_file(psnx_path)
    
    return vault_key, key_data


def main():
    print('='*70)
    print('  TRANSFER USDC - POLY-SPINOR NEXUS 7D')
    print('='*70)
    
    # === PARAMETRES DU TRANSFER ===
    AMOUNT_USDC = 13.777
    DESTINATION = input('\nAdresse de destination (0x...): ').strip()
    
    if not DESTINATION.startswith('0x') or len(DESTINATION) != 42:
        print('[ERREUR] Adresse invalide!')
        return
    
    # Choix de la chaine
    print('\nChaines disponibles:')
    print('  1. Ethereum Mainnet (gas eleve)')
    print('  2. Polygon (gas faible)')
    print('  3. Arbitrum (gas moyen)')
    print('  4. Base (gas faible)')
    
    chain_choice = input('\nChoisir la chaine (1-4): ').strip()
    
    chains = {
        '1': ('ethereum', EVMChain.ETHEREUM_MAINNET),
        '2': ('polygon', EVMChain.POLYGON_MAINNET),
        '3': ('arbitrum', EVMChain.ARBITRUM_ONE),
        '4': ('base', EVMChain.BASE_MAINNET),
    }
    
    if chain_choice not in chains:
        print('[ERREUR] Choix invalide!')
        return
    
    chain_name, chain_enum = chains[chain_choice]
    usdc_contract = USDC_CONTRACTS[chain_name]
    
    # === CONNEXION AU VAULT ===
    print('\n[1] Connexion au vault...')
    vault_key, key_data = connect_vault()
    print(f'    Vault: {key_data.user_name}')
    print(f'    Fingerprint: {key_data.key_id}')
    
    # === CREATION DU WALLET ===
    print('\n[2] Derivation du wallet HD...')
    wallet = VaultHDWallet(vault_key, key_data.key_id)
    
    print(f'    Adresse: {wallet.address}')
    print(f'    Chaine: {chain_enum._name}')
    
    # === VERIFICATION DU SOLDE ===
    print('\n[3] Verification des soldes...')
    
    try:
        # Solde natif (ETH/MATIC pour gas)
        native_balance = wallet.get_native_balance(chain_enum)
        print(f'    {native_balance.symbol}: {native_balance.formatted_balance()}')
        
        # Solde USDC
        usdc_balance = wallet.get_erc20_balance(chain_enum, usdc_contract)
        print(f'    USDC: {usdc_balance.formatted_balance()}')
        
        usdc_available = float(usdc_balance.formatted_balance())
        native_available = float(native_balance.formatted_balance())
        
    except Exception as e:
        print(f'\n    [!] Impossible de verifier le solde on-chain: {e}')
        print(f'    [!] Le RPC public peut etre indisponible.')
        usdc_available = 0
        native_available = 0
    
    # === AFFICHAGE DU TRANSFER ===
    print('\n' + '='*70)
    print('  RESUME DU TRANSFER')
    print('='*70)
    print(f'''
    De:          {wallet.address}
    Vers:        {DESTINATION}
    Montant:     {AMOUNT_USDC} USDC
    Chaine:      {chain_name.upper()}
    Contrat:     {usdc_contract}
    ''')
    
    # === VERIFICATION ===
    if usdc_available < AMOUNT_USDC:
        print(f'''
    [!] ATTENTION: Solde USDC insuffisant!
        Solde actuel: {usdc_available} USDC
        Requis:       {AMOUNT_USDC} USDC
    
    Pour effectuer ce transfer, vous devez d'abord:
    1. Envoyer des USDC a votre adresse vault: {wallet.address}
    2. Envoyer du {native_balance.symbol if native_available > 0 else 'ETH/MATIC'} pour les frais de gas
        ''')
    
    if native_available < 0.001:
        print(f'''
    [!] ATTENTION: Gas insuffisant!
        Vous avez besoin de {native_balance.symbol if native_available > 0 else 'ETH/MATIC'} pour payer les frais.
        ''')
    
    # === CONFIRMATION ===
    if usdc_available >= AMOUNT_USDC and native_available >= 0.001:
        confirm = input('\nConfirmer le transfer? (oui/non): ').strip().lower()
        
        if confirm == 'oui':
            print('\n[4] Envoi de la transaction...')
            
            # Convertir en unites (USDC a 6 decimales)
            amount_units = int(AMOUNT_USDC * 10**6)
            
            try:
                result = wallet.send_erc20(
                    chain=chain_enum,
                    token_address=usdc_contract,
                    to_address=DESTINATION,
                    amount=amount_units
                )
                
                if result.success:
                    print(f'''
    [OK] TRANSFER REUSSI!
    
    Transaction: {result.tx_hash}
    Block:       {result.block_number}
    Gas utilise: {result.gas_used}
    
    Explorer: {wallet.get_web3(chain_enum).eth.chain_id}
                    ''')
                else:
                    print(f'\n    [ERREUR] {result.error}')
                    
            except Exception as e:
                print(f'\n    [ERREUR] Transaction echouee: {e}')
        else:
            print('\n    Transfer annule.')
    else:
        print('\n    [INFO] Transfer non effectue (fonds insuffisants)')
        print(f'\n    Votre adresse pour recevoir des fonds:')
        print(f'    {wallet.address}')
    
    # === GENERER LA TRANSACTION (sans l'envoyer) ===
    print('\n' + '='*70)
    print('  TRANSACTION PREPAREE (pour envoi manuel)')
    print('='*70)
    
    # Encoder l'appel transfer(address,uint256)
    amount_units = int(AMOUNT_USDC * 10**6)
    # transfer(address,uint256) selector = 0xa9059cbb
    data = '0xa9059cbb'
    data += DESTINATION[2:].lower().zfill(64)  # address padded
    data += hex(amount_units)[2:].zfill(64)    # amount padded
    
    print(f'''
    To:       {usdc_contract}
    Data:     {data[:50]}...
    Value:    0
    
    Vous pouvez utiliser cette data dans MetaMask ou un autre wallet
    en important votre cle privee derivee du vault.
    ''')


if __name__ == "__main__":
    main()
