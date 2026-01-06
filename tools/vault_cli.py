#!/usr/bin/env python3
"""
Interface CLI Interactive - Poly-Spinor Nexus 7D
Navigation et gestion du vault en ligne de commande
"""

import os
import sys
import json
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.complete_key_generator import CompleteKeyFileGenerator, CompletePolySpinorKeyGenerator
from core.persistent_vault import PersistentVaultManager
from sdk.python.psnx_sdk import Vault, SecretSharing, VaultWeb3Wallet, EVMChain
from core.bitcoin_wallet import VaultBitcoinWallet, BitcoinNetwork, AddressType, BitcoinAssetManager

# Couleurs ANSI
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {title}{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}\n")

def print_menu(options):
    for key, value in options.items():
        print(f"  {Colors.YELLOW}[{key}]{Colors.END} {value}")
    print()

def pause():
    input(f"\n{Colors.CYAN}Appuyez sur Entree pour continuer...{Colors.END}")


class VaultCLI:
    def __init__(self):
        self.vault_manager = None
        self.crypto_vault = None
        self.vault_key = None
        self.key_data = None
        self.wallet = None
        self.btc_wallet = None
        self.connected = False
    
    def connect(self):
        """Connexion au vault"""
        psnx_path = 'vault_storage/keys/vault_key_monvaultsecurise_0d3e2fa2.psnx'
        
        if not os.path.exists(psnx_path):
            print(f"{Colors.RED}[ERREUR] Fichier cle non trouve!{Colors.END}")
            return False
        
        print(f"{Colors.BLUE}Chargement de la cle...{Colors.END}")
        generator = CompletePolySpinorKeyGenerator()
        file_gen = CompleteKeyFileGenerator(generator)
        self.key_data, self.vault_key = file_gen.extract_key_from_file(psnx_path)
        
        self.vault_manager = PersistentVaultManager(self.vault_key, self.key_data.user_name)
        self.crypto_vault = Vault(self.vault_key)
        self.wallet = VaultWeb3Wallet(self.vault_key, EVMChain.ETHEREUM)
        self.btc_wallet = VaultBitcoinWallet(self.vault_key, self.key_data.key_id, BitcoinNetwork.MAINNET, AddressType.P2TR)
        self.connected = True
        
        print(f"{Colors.GREEN}Connecte au vault: {self.key_data.user_name}{Colors.END}")
        return True
    
    def show_dashboard(self):
        """Affiche le tableau de bord"""
        clear_screen()
        print_header("TABLEAU DE BORD")
        
        stats = self.vault_manager.get_stats()
        
        print(f"  {Colors.BOLD}Vault:{Colors.END} {stats['vault_name']}")
        print(f"  {Colors.BOLD}Key ID:{Colors.END} {self.key_data.key_id}")
        print(f"  {Colors.BOLD}Fingerprint:{Colors.END} {self.crypto_vault.get_fingerprint()}")
        print(f"  {Colors.BOLD}Entropie:{Colors.END} {self.key_data.total_entropy_bits:,} bits")
        print(f"  {Colors.BOLD}Bell Quantique:{Colors.END} {'Oui' if self.key_data.bell_data.is_quantum else 'Non'}")
        print()
        print(f"  {Colors.CYAN}--- Contenu ---{Colors.END}")
        print(f"  Actifs:     {Colors.GREEN}{stats['asset_count']}{Colors.END}")
        print(f"  Documents:  {Colors.GREEN}{stats['document_count']}{Colors.END}")
        print(f"  Transfers:  {Colors.YELLOW}{stats['pending_transfers']}{Colors.END}")
        print()
        print(f"  {Colors.CYAN}--- Wallets ---{Colors.END}")
        print(f"  EVM:     {Colors.BOLD}{self.wallet.address}{Colors.END}")
        print(f"  Bitcoin: {Colors.BOLD}{self.btc_wallet.address[:20]}...{Colors.END}")
    
    def list_assets(self):
        """Liste les actifs"""
        clear_screen()
        print_header("LISTE DES ACTIFS")
        
        assets = self.vault_manager.list_assets()
        
        if not assets:
            print(f"  {Colors.YELLOW}Aucun actif enregistre.{Colors.END}")
        else:
            for i, asset in enumerate(assets, 1):
                print(f"  {Colors.BOLD}[{i}]{Colors.END} {asset['name']}")
                print(f"      Type: {asset['asset_type']}")
                print(f"      ID: {asset['id'][:16]}...")
                if 'chain' in asset:
                    print(f"      Chain: {asset['chain']}")
                if 'metadata' in asset:
                    meta = asset['metadata']
                    if 'symbol' in meta:
                        print(f"      Token: {meta.get('balance', '?')} {meta['symbol']}")
                    if 'token_id' in asset:
                        print(f"      Token ID: {asset['token_id']}")
                print()
        
        pause()
    
    def list_documents(self):
        """Liste les documents"""
        clear_screen()
        print_header("DOCUMENTS CHIFFRES")
        
        documents = self.vault_manager.list_documents()
        
        if not documents:
            print(f"  {Colors.YELLOW}Aucun document stocke.{Colors.END}")
        else:
            for i, doc in enumerate(documents, 1):
                print(f"  {Colors.BOLD}[{i}]{Colors.END} {doc.get('original_name', 'Document')}")
                print(f"      ID: {doc['id'][:16]}...")
                print(f"      Taille: {doc.get('size', 'N/A')} bytes")
                if 'metadata' in doc:
                    print(f"      Categorie: {doc['metadata'].get('category', 'N/A')}")
                print()
        
        pause()
    
    def list_transfers(self):
        """Liste les transfers en attente"""
        clear_screen()
        print_header("TRANSFERS PROGRAMMES")
        
        transfers = self.vault_manager.get_pending_transfers()
        
        if not transfers:
            print(f"  {Colors.YELLOW}Aucun transfer en attente.{Colors.END}")
        else:
            for i, t in enumerate(transfers, 1):
                print(f"  {Colors.BOLD}[{i}]{Colors.END} {t['transfer_type']}")
                print(f"      ID: {t['id'][:16]}...")
                print(f"      Destination: {t['destination'][:20]}...")
                print(f"      Expire: {t['expiry']}")
                if 'metadata' in t:
                    print(f"      Raison: {t['metadata'].get('reason', 'N/A')}")
                print()
        
        pause()
    
    def add_asset(self):
        """Ajouter un actif"""
        clear_screen()
        print_header("AJOUTER UN ACTIF")
        
        print("  Type d'actif:")
        print(f"  {Colors.YELLOW}[1]{Colors.END} NFT")
        print(f"  {Colors.YELLOW}[2]{Colors.END} Token ERC-20")
        print(f"  {Colors.YELLOW}[3]{Colors.END} Autre")
        print()
        
        choice = input("  Choix: ").strip()
        
        if choice == '1':
            asset_type = 'NFT'
        elif choice == '2':
            asset_type = 'Token'
        else:
            asset_type = 'Asset'
        
        name = input("  Nom: ").strip()
        contract = input("  Adresse contrat (0x...): ").strip()
        chain = input("  Chaine (Ethereum/Polygon/etc): ").strip() or "Ethereum"
        
        if asset_type == 'NFT':
            token_id = input("  Token ID: ").strip()
        else:
            token_id = None
        
        asset_data = {
            'name': name,
            'asset_type': asset_type,
            'contract': contract,
            'chain': chain,
            'metadata': {
                'added_at': datetime.now().isoformat()
            }
        }
        
        if token_id:
            asset_data['token_id'] = token_id
        
        asset_id = self.vault_manager.add_asset(asset_data)
        print(f"\n  {Colors.GREEN}Actif ajoute avec ID: {asset_id}{Colors.END}")
        
        pause()
    
    def encrypt_data(self):
        """Chiffrer des donnees"""
        clear_screen()
        print_header("CHIFFRER DES DONNEES")
        
        print("  Entrez les donnees a chiffrer (texte):")
        data = input("  > ").strip()
        
        if not data:
            print(f"  {Colors.RED}Aucune donnee fournie.{Colors.END}")
            pause()
            return
        
        encrypted = self.crypto_vault.encrypt(data.encode('utf-8'))
        
        print(f"\n  {Colors.GREEN}Donnees chiffrees:{Colors.END}")
        print(f"  Nonce: {encrypted.nonce.hex()}")
        print(f"  Ciphertext: {encrypted.ciphertext[:32].hex()}...")
        print(f"  Tag: {encrypted.tag.hex()}")
        
        # Sauvegarder?
        save = input("\n  Sauvegarder dans un fichier? (o/n): ").strip().lower()
        if save == 'o':
            filename = input("  Nom du fichier: ").strip() or "encrypted_data.enc"
            filepath = os.path.join("vault_storage", filename)
            os.makedirs("vault_storage", exist_ok=True)
            with open(filepath, 'wb') as f:
                f.write(encrypted.to_bytes())
            print(f"  {Colors.GREEN}Sauvegarde: {filepath}{Colors.END}")
        
        pause()
    
    def decrypt_data(self):
        """Dechiffrer des donnees"""
        clear_screen()
        print_header("DECHIFFRER DES DONNEES")
        
        filepath = input("  Chemin du fichier .enc: ").strip()
        
        if not os.path.exists(filepath):
            print(f"  {Colors.RED}Fichier non trouve!{Colors.END}")
            pause()
            return
        
        try:
            from sdk.python.psnx_sdk.vault import EncryptedData
            
            with open(filepath, 'rb') as f:
                encrypted = EncryptedData.from_bytes(f.read())
            
            decrypted = self.crypto_vault.decrypt(encrypted)
            
            print(f"\n  {Colors.GREEN}Donnees dechiffrees:{Colors.END}")
            try:
                print(f"  {decrypted.decode('utf-8')}")
            except:
                print(f"  (binaire) {decrypted[:50].hex()}...")
        
        except Exception as e:
            print(f"  {Colors.RED}Erreur: {e}{Colors.END}")
        
        pause()
    
    def show_wallet(self):
        """Afficher les infos wallet"""
        clear_screen()
        print_header("WALLET WEB3")
        
        print(f"  {Colors.BOLD}Adresse:{Colors.END} {self.wallet.address}")
        print(f"  {Colors.BOLD}Chaine:{Colors.END} {self.wallet.chain.name}")
        print()
        
        print(f"  {Colors.CYAN}--- Chaines disponibles ---{Colors.END}")
        for chain in EVMChain:
            print(f"  - {chain.name}: Chain ID {chain.value.chain_id}")
        
        print(f"\n  {Colors.CYAN}--- Actions ---{Colors.END}")
        print(f"  {Colors.YELLOW}[1]{Colors.END} Changer de chaine")
        print(f"  {Colors.YELLOW}[2]{Colors.END} Signer un message")
        print(f"  {Colors.YELLOW}[3]{Colors.END} Voir la cle privee")
        print(f"  {Colors.YELLOW}[0]{Colors.END} Retour")
        print()
        
        choice = input("  Choix: ").strip()
        
        if choice == '1':
            chain_name = input("  Nom de la chaine (ETHEREUM/POLYGON/etc): ").strip().upper()
            try:
                new_chain = EVMChain[chain_name]
                self.wallet.switch_chain(new_chain)
                print(f"  {Colors.GREEN}Chaine changee: {new_chain.name}{Colors.END}")
            except KeyError:
                print(f"  {Colors.RED}Chaine inconnue!{Colors.END}")
        
        elif choice == '2':
            message = input("  Message a signer: ").strip()
            signature = self.wallet.sign_message(message)
            print(f"  {Colors.GREEN}Signature: {signature[:50]}...{Colors.END}")
        
        elif choice == '3':
            confirm = input(f"  {Colors.RED}ATTENTION: Ne partagez jamais cette cle!{Colors.END} Continuer? (oui/non): ")
            if confirm.lower() == 'oui':
                from cryptography.hazmat.primitives.kdf.hkdf import HKDF
                from cryptography.hazmat.primitives import hashes
                hkdf = HKDF(algorithm=hashes.SHA256(), length=32, 
                           salt=self.key_data.key_id.encode(), info=b'poly-spinor-evm-wallet-v1')
                pk = hkdf.derive(self.vault_key)
                print(f"\n  Cle privee: {pk.hex()}")
        
        pause()
    
    def export_vault(self):
        """Exporter le vault"""
        clear_screen()
        print_header("EXPORTER LE VAULT")
        
        export_path = 'vault_storage/backups'
        os.makedirs(export_path, exist_ok=True)
        
        backup_file = self.vault_manager.export_vault(export_path)
        
        print(f"  {Colors.GREEN}Backup cree: {backup_file}{Colors.END}")
        print(f"  Taille: {os.path.getsize(backup_file):,} bytes")
        
        pause()
    
    def show_bitcoin_wallet(self):
        """Afficher le wallet Bitcoin"""
        clear_screen()
        print_header("WALLET BITCOIN")
        
        print(f"  {Colors.BOLD}Adresses:{Colors.END}")
        addresses = self.btc_wallet.get_all_addresses()
        print(f"    Legacy (P2PKH):  {addresses['p2pkh']}")
        print(f"    SegWit (P2WPKH): {addresses['p2wpkh']}")
        print(f"    Taproot (P2TR):  {addresses['p2tr']}")
        print()
        print(f"  {Colors.GREEN}Adresse principale: {self.btc_wallet.address}{Colors.END}")
        print()
        
        # Actifs
        print(f"  {Colors.CYAN}--- Verification des actifs ---{Colors.END}")
        try:
            balance = self.btc_wallet.get_balance(force_refresh=True)
            
            print(f"\n  {Colors.BOLD}BTC:{Colors.END} {balance.btc_formatted}")
            print(f"    Confirme: {balance.btc_confirmed:,} sats")
            print(f"    Non confirme: {balance.btc_unconfirmed:,} sats")
            
            print(f"\n  {Colors.BOLD}Ordinals:{Colors.END} {len(balance.inscriptions)} inscriptions")
            for insc in balance.inscriptions[:3]:
                print(f"    #{insc.inscription_number}: {insc.content_type}")
            
            print(f"\n  {Colors.BOLD}BRC-20:{Colors.END} {len(balance.brc20_tokens)} tokens")
            for token in balance.brc20_tokens[:5]:
                print(f"    {token.tick}: {token.formatted_balance()}")
            
            print(f"\n  {Colors.BOLD}Runes:{Colors.END} {len(balance.runes)} runes")
            for rune in balance.runes[:5]:
                print(f"    {rune.name}: {rune.formatted_balance()}")
            
            print(f"\n  {Colors.BOLD}ARC-20:{Colors.END} {len(balance.arc20_tokens)} tokens")
            print(f"  {Colors.BOLD}Bitmap:{Colors.END} {len(balance.bitmaps)} parcelles")
            
        except Exception as e:
            print(f"  {Colors.RED}Erreur API: {e}{Colors.END}")
        
        # Actions
        print(f"\n  {Colors.CYAN}--- Actions ---{Colors.END}")
        print(f"  {Colors.YELLOW}[1]{Colors.END} Voir la cle privee (WIF)")
        print(f"  {Colors.YELLOW}[2]{Colors.END} Estimation des frais")
        print(f"  {Colors.YELLOW}[3]{Colors.END} Preparer transfert BRC-20")
        print(f"  {Colors.YELLOW}[0]{Colors.END} Retour")
        print()
        
        choice = input("  Choix: ").strip()
        
        if choice == '1':
            confirm = input(f"  {Colors.RED}NE JAMAIS PARTAGER!{Colors.END} Afficher? (oui/non): ")
            if confirm.lower() == 'oui':
                print(f"\n  WIF: {self.btc_wallet.private_key_wif}")
        
        elif choice == '2':
            try:
                fees = self.btc_wallet.get_fee_estimates()
                print(f"\n  Rapide (~10 min): {fees.get('fastestFee', 'N/A')} sat/vB")
                print(f"  Normal (~30 min): {fees.get('halfHourFee', 'N/A')} sat/vB")
                print(f"  Economique (~1h): {fees.get('hourFee', 'N/A')} sat/vB")
            except Exception as e:
                print(f"  {Colors.RED}Erreur: {e}{Colors.END}")
        
        elif choice == '3':
            tick = input("  Ticker BRC-20: ").strip()
            amount = input("  Montant: ").strip()
            to_addr = input("  Adresse destination: ").strip()
            
            transfer = self.btc_wallet.prepare_brc20_transfer(tick, float(amount), to_addr)
            print(f"\n  {Colors.GREEN}Inscription a creer:{Colors.END}")
            print(f"  {transfer['inscription_content']}")
        
        pause()
    
    def show_security_info(self):
        """Afficher les infos de securite"""
        clear_screen()
        print_header("INFORMATIONS DE SECURITE")
        
        print(f"  {Colors.BOLD}Phases de generation:{Colors.END}")
        print(f"  - Seed maitre:      512 bits")
        print(f"  - Capture 7D:       {self.key_data.spatial_data.entropy_bits} bits")
        print(f"  - Physique:         {self.key_data.physics_data.entropy_bits} bits")
        print(f"  - Spinor Cl(0,7):   {self.key_data.spinor_data.entropy_bits} bits")
        print(f"  - Bell 7D:          {self.key_data.bell_data.entropy_bits} bits")
        print(f"  - Hash composite:   {self.key_data.hash_data.entropy_bits} bits")
        if self.key_data.pq_data:
            print(f"  - Post-quantique:   {self.key_data.pq_data.entropy_bits} bits")
        print()
        print(f"  {Colors.GREEN}Total: {self.key_data.total_entropy_bits:,} bits{Colors.END}")
        print()
        print(f"  {Colors.BOLD}Verification Bell:{Colors.END}")
        print(f"  - Quantique: {'Oui' if self.key_data.bell_data.is_quantum else 'Non'}")
        print(f"  - Max violation: {self.key_data.bell_data.max_violation:.3f}")
        print()
        print(f"  {Colors.BOLD}Merkle Root:{Colors.END}")
        print(f"  {self.key_data.merkle_root}")
        
        pause()
    
    def main_menu(self):
        """Menu principal"""
        while True:
            clear_screen()
            self.show_dashboard()
            
            print(f"\n  {Colors.CYAN}--- Menu Principal ---{Colors.END}")
            options = {
                '1': 'Voir les actifs',
                '2': 'Voir les documents',
                '3': 'Voir les transfers',
                '4': 'Ajouter un actif',
                '5': 'Chiffrer des donnees',
                '6': 'Dechiffrer des donnees',
                '7': 'Wallet EVM (Ethereum/Polygon...)',
                '8': 'Wallet Bitcoin (BRC-20/Runes...)',
                '9': 'Exporter le vault',
                'S': 'Infos securite',
                '0': 'Quitter'
            }
            print_menu(options)
            
            choice = input(f"  {Colors.BOLD}Choix:{Colors.END} ").strip().upper()
            
            if choice == '1':
                self.list_assets()
            elif choice == '2':
                self.list_documents()
            elif choice == '3':
                self.list_transfers()
            elif choice == '4':
                self.add_asset()
            elif choice == '5':
                self.encrypt_data()
            elif choice == '6':
                self.decrypt_data()
            elif choice == '7':
                self.show_wallet()
            elif choice == '8':
                self.show_bitcoin_wallet()
            elif choice == '9':
                self.export_vault()
            elif choice == 'S':
                self.show_security_info()
            elif choice == '0':
                print(f"\n  {Colors.GREEN}Au revoir!{Colors.END}\n")
                break
    
    def run(self):
        """Lance l'interface"""
        clear_screen()
        print_header("POLY-SPINOR NEXUS 7D")
        
        if not self.connect():
            return
        
        pause()
        self.main_menu()


if __name__ == "__main__":
    cli = VaultCLI()
    cli.run()
