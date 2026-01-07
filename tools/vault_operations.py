#!/usr/bin/env python3
"""
Operations sur le Vault Eidolon
Exemples pratiques d'utilisation
"""

import sys
import os
import json
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.complete_key_generator import CompleteKeyFileGenerator, CompletePolySpinorKeyGenerator
from core.persistent_vault import PersistentVaultManager
from sdk.python.psnx_sdk import Vault, SecretSharing, VaultWeb3Wallet, EVMChain

# === CONNEXION AU VAULT ===
def connect_vault():
    """Charge la cle et initialise le vault"""
    psnx_path = 'vault_storage/keys/vault_key_monvaultsecurise_0d3e2fa2.psnx'
    
    generator = CompletePolySpinorKeyGenerator()
    file_gen = CompleteKeyFileGenerator(generator)
    key_data, vault_key = file_gen.extract_key_from_file(psnx_path)
    
    vault_manager = PersistentVaultManager(vault_key, key_data.user_name)
    crypto_vault = Vault(vault_key)
    
    return vault_manager, crypto_vault, vault_key, key_data


def main():
    print('='*70)
    print('  OPERATIONS VAULT - EIDOLON')
    print('='*70)
    
    # Connexion
    print('\n[*] Connexion au vault...')
    vault, crypto, vault_key, key_data = connect_vault()
    print(f'    Connecte: {key_data.user_name}')
    print(f'    Fingerprint: {crypto.get_fingerprint()}')
    
    # =========================================================================
    # 1. AJOUTER UN NFT
    # =========================================================================
    print('\n' + '='*70)
    print('[1] AJOUTER UN NFT')
    print('='*70)
    
    nft_data = {
        'name': 'CryptoPunk #7804',
        'asset_type': 'NFT',
        'contract': '0xb47e3cd837dDF8e4c57F05d70Ab865de6e193BBB',
        'token_id': '7804',
        'chain': 'Ethereum',
        'metadata': {
            'collection': 'CryptoPunks',
            'rarity': 'Legendary',
            'attributes': ['Alien', 'Cap Forward', 'Pipe', 'Small Shades'],
            'acquired_date': datetime.now().isoformat(),
            'purchase_price_eth': 4200.0
        }
    }
    
    nft_id = vault.add_asset(nft_data)
    print(f'    NFT ajoute!')
    print(f'    ID: {nft_id}')
    print(f'    Nom: {nft_data["name"]}')
    print(f'    Contrat: {nft_data["contract"][:20]}...')
    
    # =========================================================================
    # 2. AJOUTER DES TOKENS
    # =========================================================================
    print('\n' + '='*70)
    print('[2] AJOUTER DES TOKENS ERC-20')
    print('='*70)
    
    tokens = [
        {
            'name': 'USDC Holdings',
            'asset_type': 'Token',
            'contract': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
            'chain': 'Ethereum',
            'metadata': {
                'symbol': 'USDC',
                'decimals': 6,
                'balance': '50000.00',
                'wallet': '0x742d35Cc6634C0532925a3b844Bc9e7595f5bB0a'
            }
        },
        {
            'name': 'Ethereum Staking',
            'asset_type': 'Token',
            'contract': '0x0000000000000000000000000000000000000000',
            'chain': 'Ethereum',
            'metadata': {
                'symbol': 'ETH',
                'decimals': 18,
                'balance': '32.5',
                'staked': True,
                'validator': '0x1234...'
            }
        }
    ]
    
    for token in tokens:
        token_id = vault.add_asset(token)
        print(f'    Token ajoute: {token["name"]} ({token["metadata"]["symbol"]})')
        print(f'      Balance: {token["metadata"]["balance"]} {token["metadata"]["symbol"]}')
    
    # =========================================================================
    # 3. STOCKER UN DOCUMENT CHIFFRE
    # =========================================================================
    print('\n' + '='*70)
    print('[3] STOCKER UN DOCUMENT CHIFFRE')
    print('='*70)
    
    # Creer un document de test
    document_content = """
    ===============================================
    DOCUMENT CONFIDENTIEL
    ===============================================
    
    Seed Phrase Wallet Principal:
    abandon abandon abandon abandon abandon abandon
    abandon abandon abandon abandon abandon about
    
    Cles API:
    - Alchemy: aBcDeFgHiJkLmNoPqRsTuVwXyZ123456
    - Infura: 0x9876543210abcdef
    
    Mots de passe:
    - Exchange A: P@ssw0rd!Secure#2024
    - Exchange B: MyStr0ng&P@ss!
    
    ===============================================
    NE JAMAIS PARTAGER CE DOCUMENT
    ===============================================
    """
    
    # Sauvegarder temporairement
    temp_doc = 'temp_secret_document.txt'
    with open(temp_doc, 'w') as f:
        f.write(document_content)
    
    # Ajouter au vault (sera chiffre automatiquement)
    doc_id = vault.add_document(temp_doc, metadata={
        'category': 'credentials',
        'sensitivity': 'critical',
        'created_by': 'admin',
        'expiry': '2025-12-31'
    })
    
    print(f'    Document chiffre et stocke!')
    print(f'    ID: {doc_id}')
    print(f'    Fichier original: {temp_doc}')
    
    # Verifier l'integrite
    is_valid = vault.verify_document(doc_id)
    print(f'    Integrite: {"OK" if is_valid else "ERREUR"}')
    
    # Supprimer le fichier temporaire (le vault a sa copie chiffree)
    os.remove(temp_doc)
    print(f'    Fichier temporaire supprime (securite)')
    
    # =========================================================================
    # 4. CHIFFRER DES DONNEES ARBITRAIRES
    # =========================================================================
    print('\n' + '='*70)
    print('[4] CHIFFRER DES DONNEES ARBITRAIRES')
    print('='*70)
    
    # Donnees sensibles
    api_keys = {
        'openai': 'sk-proj-xxxxxxxxxxxxxxxxxxxxx',
        'aws_access': 'AKIAIOSFODNN7EXAMPLE',
        'aws_secret': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
        'stripe': 'sk_live_xxxxxxxxxxxxxxxxxxxxx'
    }
    
    # Chiffrer
    data_bytes = json.dumps(api_keys).encode('utf-8')
    encrypted = crypto.encrypt(data_bytes, metadata={'type': 'api_keys'})
    
    print(f'    Donnees originales: {len(data_bytes)} bytes')
    print(f'    Nonce: {encrypted.nonce.hex()}')
    print(f'    Ciphertext: {len(encrypted.ciphertext)} bytes')
    print(f'    Tag: {encrypted.tag.hex()}')
    
    # Dechiffrer pour verifier
    decrypted = crypto.decrypt(encrypted)
    recovered = json.loads(decrypted.decode('utf-8'))
    print(f'    Verification: {"OK" if recovered == api_keys else "ERREUR"}')
    
    # Sauvegarder le chiffre
    encrypted_file = 'vault_storage/encrypted_api_keys.enc'
    os.makedirs('vault_storage', exist_ok=True)
    with open(encrypted_file, 'wb') as f:
        f.write(encrypted.to_bytes())
    print(f'    Sauvegarde: {encrypted_file}')
    
    # =========================================================================
    # 5. PROGRAMMER UN TRANSFER
    # =========================================================================
    print('\n' + '='*70)
    print('[5] PROGRAMMER UN TRANSFER AVEC DELAI')
    print('='*70)
    
    transfer = {
        'transfer_type': 'NFT',
        'asset_id': nft_id,
        'destination': '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045',  # vitalik.eth
        'delay_days': 30,
        'metadata': {
            'reason': 'Donation programmee',
            'beneficiary': 'Vitalik Buterin',
            'notes': 'Transfer automatique dans 30 jours si non annule'
        }
    }
    
    transfer_id = vault.schedule_transfer(transfer)
    print(f'    Transfer programme!')
    print(f'    ID: {transfer_id}')
    print(f'    Actif: {nft_data["name"]}')
    print(f'    Destination: {transfer["destination"][:20]}...')
    print(f'    Delai: {transfer["delay_days"]} jours')
    
    # =========================================================================
    # 6. WALLET WEB3 DERIVE
    # =========================================================================
    print('\n' + '='*70)
    print('[6] WALLET WEB3 DERIVE DU VAULT')
    print('='*70)
    
    wallet = VaultWeb3Wallet(vault_key, EVMChain.ETHEREUM)
    
    print(f'    Adresse Ethereum: {wallet.address}')
    print(f'    Chaine: {wallet.chain.name}')
    
    # Changer de chaine
    wallet.switch_chain(EVMChain.POLYGON)
    print(f'    Chaine Polygon: {wallet.chain.name}')
    print(f'    (Meme adresse: {wallet.address})')
    
    # Signer un message
    message = "Verification de propriete du vault"
    signature = wallet.sign_message(message)
    print(f'    Message signe: {message}')
    print(f'    Signature: {signature[:40]}...')
    
    # =========================================================================
    # 7. VOIR LE CONTENU DU VAULT
    # =========================================================================
    print('\n' + '='*70)
    print('[7] CONTENU DU VAULT')
    print('='*70)
    
    assets = vault.list_assets()
    print(f'\n    ACTIFS ({len(assets)}):')
    for asset in assets:
        print(f'      [{asset["id"][:8]}] {asset["name"]}')
        print(f'                Type: {asset["asset_type"]}')
        if 'chain' in asset:
            print(f'                Chain: {asset["chain"]}')
    
    documents = vault.list_documents()
    print(f'\n    DOCUMENTS ({len(documents)}):')
    for doc in documents:
        print(f'      [{doc["id"][:8]}] {doc.get("original_name", "Document")}')
        if 'metadata' in doc:
            print(f'                Category: {doc["metadata"].get("category", "N/A")}')
    
    pending = vault.get_pending_transfers()
    print(f'\n    TRANSFERS EN ATTENTE ({len(pending)}):')
    for t in pending:
        print(f'      [{t["id"][:8]}] {t["transfer_type"]} -> {t["destination"][:16]}...')
        print(f'                Expire: {t["expiry"]}')
    
    # =========================================================================
    # 8. STATISTIQUES
    # =========================================================================
    print('\n' + '='*70)
    print('[8] STATISTIQUES DU VAULT')
    print('='*70)
    
    stats = vault.get_stats()
    print(f'''
    Nom:              {stats["vault_name"]}
    Version:          {stats["version"]}
    Cree le:          {stats["created"]}
    
    Actifs:           {stats["asset_count"]}
    Documents:        {stats["document_count"]}
    Transfers:        {stats["pending_transfers"]}
    
    Fingerprint:      {crypto.get_fingerprint()}
    Entropie cle:     {key_data.total_entropy_bits:,} bits
    Bell quantique:   {"Oui" if key_data.bell_data.is_quantum else "Non"}
    ''')
    
    # =========================================================================
    # 9. EXPORTER LE VAULT
    # =========================================================================
    print('='*70)
    print('[9] EXPORTER LE VAULT')
    print('='*70)
    
    export_path = 'vault_storage/backups'
    os.makedirs(export_path, exist_ok=True)
    
    backup_file = vault.export_vault(export_path)
    print(f'    Backup cree: {backup_file}')
    print(f'    Taille: {os.path.getsize(backup_file):,} bytes')
    
    # =========================================================================
    # RESUME
    # =========================================================================
    print('\n' + '='*70)
    print('  OPERATIONS TERMINEES')
    print('='*70)
    print(f'''
  Votre vault contient maintenant:
    - {stats["asset_count"]} actifs (NFTs, Tokens)
    - {stats["document_count"]} documents chiffres
    - {stats["pending_transfers"]} transfers programmes
  
  Fichiers:
    - Cle: vault_storage/keys/vault_key_monvaultsecurise_*.psnx
    - Backup: {backup_file}
    - Donnees chiffrees: vault_storage/encrypted_api_keys.enc
  
  Pour extraire un document:
    vault.extract_document(doc_id, 'output.txt')
  
  Pour annuler un transfer:
    vault.cancel_transfer(transfer_id)
    ''')


if __name__ == "__main__":
    main()
