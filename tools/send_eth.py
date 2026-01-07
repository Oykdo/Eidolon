#!/usr/bin/env python3
"""
Envoi d'ETH depuis le Vault Eidolon
"""
import sys
sys.path.insert(0, '.')

from core.complete_key_generator import CompleteKeyFileGenerator, CompletePolySpinorKeyGenerator
from core.evm_wallet import VaultHDWallet, EVMChain

# === PARAMETRES ===
DESTINATION = "0x5D4bECA30Faf14f02341d46d52b631Fd12b810ba"
AMOUNT_ETH = 3.0

def main():
    print('='*60)
    print('  ENVOI ETH - EIDOLON')
    print('='*60)
    
    # Connexion au vault
    print('\n[1] Connexion au vault...')
    psnx_path = 'vault_storage/keys/vault_key_monvaultsecurise_0d3e2fa2.psnx'
    generator = CompletePolySpinorKeyGenerator()
    file_gen = CompleteKeyFileGenerator(generator)
    key_data, vault_key = file_gen.extract_key_from_file(psnx_path)
    
    print(f'    Vault: {key_data.user_name}')
    
    # Creation du wallet
    print('\n[2] Wallet EVM...')
    wallet = VaultHDWallet(vault_key, key_data.key_id)
    
    print(f'    Adresse: {wallet.address}')
    
    # Verification du solde
    print('\n[3] Verification du solde sur Ethereum Mainnet...')
    
    try:
        balance = wallet.get_native_balance(EVMChain.ETHEREUM_MAINNET)
        balance_eth = float(balance.formatted_balance())
        print(f'    Solde: {balance_eth} ETH')
    except Exception as e:
        print(f'    Erreur RPC: {e}')
        balance_eth = 0
    
    # Resume
    print('\n' + '='*60)
    print('  RESUME DE LA TRANSACTION')
    print('='*60)
    print(f'''
    De:      {wallet.address}
    Vers:    {DESTINATION}
    Montant: {AMOUNT_ETH} ETH
    Reseau:  Ethereum Mainnet
    ''')
    
    # Verification des fonds
    if balance_eth < AMOUNT_ETH:
        print(f'''
    [!] SOLDE INSUFFISANT
    
    Votre solde actuel: {balance_eth} ETH
    Montant requis:     {AMOUNT_ETH} ETH + gas
    
    Pour effectuer cette transaction, envoyez d'abord des ETH a:
    {wallet.address}
        ''')
        
        # Afficher quand meme la transaction preparee
        print('\n[Transaction preparee - en attente de fonds]')
        
        # Preparer la transaction (sans l'envoyer)
        amount_wei = int(AMOUNT_ETH * 10**18)
        
        print(f'''
    Transaction raw:
    ----------------
    to:    {DESTINATION}
    value: {amount_wei} wei ({AMOUNT_ETH} ETH)
    data:  0x (transfert simple)
    
    Pour envoyer manuellement:
    1. Importez la cle privee dans MetaMask
    2. Envoyez {AMOUNT_ETH} ETH a {DESTINATION}
        ''')
        
        # Afficher la cle privee si demande
        show = input('\n    Afficher la cle privee pour import? (oui/non): ').strip().lower()
        if show == 'oui':
            from cryptography.hazmat.primitives.kdf.hkdf import HKDF
            from cryptography.hazmat.primitives import hashes
            hkdf = HKDF(algorithm=hashes.SHA256(), length=32,
                       salt=key_data.key_id.encode(), info=b'poly-spinor-evm-wallet-v1')
            pk = hkdf.derive(vault_key)
            print(f'\n    Cle privee: {pk.hex()}')
            print(f'    [!] NE JAMAIS PARTAGER CETTE CLE')
        
    else:
        # Fonds suffisants - demander confirmation
        print(f'    Solde suffisant: {balance_eth} ETH')
        
        confirm = input('\n    Confirmer l\'envoi de 3 ETH? (oui/non): ').strip().lower()
        
        if confirm == 'oui':
            print('\n[4] Envoi de la transaction...')
            
            try:
                result = wallet.send_native(
                    chain=EVMChain.ETHEREUM_MAINNET,
                    to_address=DESTINATION,
                    amount_wei=int(AMOUNT_ETH * 10**18)
                )
                
                if result.success:
                    print(f'''
    [OK] TRANSACTION ENVOYEE!
    
    Hash: {result.tx_hash}
    Block: {result.block_number}
    Gas: {result.gas_used}
    
    Voir sur Etherscan:
    https://etherscan.io/tx/{result.tx_hash}
                    ''')
                else:
                    print(f'\n    [ERREUR] {result.error}')
            
            except Exception as e:
                print(f'\n    [ERREUR] {e}')
        else:
            print('\n    Transaction annulee.')


if __name__ == "__main__":
    main()
