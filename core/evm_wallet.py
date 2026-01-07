"""
Module Wallet EVM pour Eidolon
Gestion des tokens ERC20 et NFTs ERC721 sur chaines compatibles EVM

Fonctionnalites:
- Generation de wallet HD depuis la cle vault
- Reception/Envoi de tokens ERC20
- Reception/Envoi de NFTs ERC721/ERC1155
- Support multi-chaines (Ethereum, Polygon, Arbitrum, BSC, etc.)
- Stockage securise des cles privees dans le vault
"""

import os
import sys
import json
import hashlib
import secrets
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from decimal import Decimal
import struct

# Web3 imports
try:
    from web3 import Web3
    from eth_account import Account
    # Le middleware POA a change dans web3 v7
    try:
        from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
    except ImportError:
        try:
            from web3.middleware import geth_poa_middleware
        except ImportError:
            geth_poa_middleware = None
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    Web3 = None  # Type stub
    Account = None
    geth_poa_middleware = None
    print("[INFO] web3 non disponible. Installer avec: pip install web3 eth-account")

# Cryptography
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


# ============================================================================
# CONSTANTES ET CONFIGURATIONS
# ============================================================================

# ABIs standards
ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_from", "type": "address"}, {"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transferFrom", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
]

ERC721_ABI = [
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_tokenId", "type": "uint256"}], "name": "tokenURI", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_tokenId", "type": "uint256"}], "name": "ownerOf", "outputs": [{"name": "", "type": "address"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_from", "type": "address"}, {"name": "_to", "type": "address"}, {"name": "_tokenId", "type": "uint256"}], "name": "transferFrom", "outputs": [], "type": "function"},
    {"constant": False, "inputs": [{"name": "_from", "type": "address"}, {"name": "_to", "type": "address"}, {"name": "_tokenId", "type": "uint256"}], "name": "safeTransferFrom", "outputs": [], "type": "function"},
    {"constant": False, "inputs": [{"name": "_approved", "type": "address"}, {"name": "_tokenId", "type": "uint256"}], "name": "approve", "outputs": [], "type": "function"},
    {"constant": False, "inputs": [{"name": "_operator", "type": "address"}, {"name": "_approved", "type": "bool"}], "name": "setApprovalForAll", "outputs": [], "type": "function"},
    {"constant": True, "inputs": [{"name": "_tokenId", "type": "uint256"}], "name": "getApproved", "outputs": [{"name": "", "type": "address"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_operator", "type": "address"}], "name": "isApprovedForAll", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
]

ERC1155_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_id", "type": "uint256"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owners", "type": "address[]"}, {"name": "_ids", "type": "uint256[]"}], "name": "balanceOfBatch", "outputs": [{"name": "", "type": "uint256[]"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_from", "type": "address"}, {"name": "_to", "type": "address"}, {"name": "_id", "type": "uint256"}, {"name": "_value", "type": "uint256"}, {"name": "_data", "type": "bytes"}], "name": "safeTransferFrom", "outputs": [], "type": "function"},
    {"constant": False, "inputs": [{"name": "_from", "type": "address"}, {"name": "_to", "type": "address"}, {"name": "_ids", "type": "uint256[]"}, {"name": "_values", "type": "uint256[]"}, {"name": "_data", "type": "bytes"}], "name": "safeBatchTransferFrom", "outputs": [], "type": "function"},
    {"constant": True, "inputs": [{"name": "_id", "type": "uint256"}], "name": "uri", "outputs": [{"name": "", "type": "string"}], "type": "function"},
]


class EVMChain(Enum):
    """Chaines EVM supportees"""
    ETHEREUM_MAINNET = ("ethereum", 1, "https://eth.llamarpc.com")
    ETHEREUM_SEPOLIA = ("sepolia", 11155111, "https://rpc.sepolia.org")
    POLYGON_MAINNET = ("polygon", 137, "https://polygon-rpc.com")
    POLYGON_MUMBAI = ("mumbai", 80001, "https://rpc-mumbai.maticvigil.com")
    ARBITRUM_ONE = ("arbitrum", 42161, "https://arb1.arbitrum.io/rpc")
    OPTIMISM = ("optimism", 10, "https://mainnet.optimism.io")
    BSC_MAINNET = ("bsc", 56, "https://bsc-dataseed.binance.org")
    AVALANCHE_C = ("avalanche", 43114, "https://api.avax.network/ext/bc/C/rpc")
    BASE_MAINNET = ("base", 8453, "https://mainnet.base.org")
    
    def __init__(self, name: str, chain_id: int, rpc_url: str):
        self._name = name
        self.chain_id = chain_id
        self.default_rpc = rpc_url


@dataclass
class TokenInfo:
    """Information sur un token"""
    address: str
    name: str
    symbol: str
    decimals: int
    balance: int
    chain: str
    token_type: str  # 'ERC20', 'ERC721', 'ERC1155', 'NATIVE'
    
    def formatted_balance(self) -> str:
        """Balance formatee avec decimales"""
        if self.token_type == 'ERC721':
            return str(self.balance)
        return str(Decimal(self.balance) / Decimal(10 ** self.decimals))


@dataclass
class NFTInfo:
    """Information sur un NFT"""
    contract_address: str
    token_id: int
    name: str
    symbol: str
    token_uri: str
    metadata: Dict[str, Any]
    chain: str
    token_type: str  # 'ERC721', 'ERC1155'


@dataclass
class TransactionResult:
    """Resultat d'une transaction"""
    success: bool
    tx_hash: str
    block_number: int
    gas_used: int
    error: Optional[str] = None


# ============================================================================
# WALLET HD DERIVE DU VAULT
# ============================================================================

class VaultHDWallet:
    """
    Wallet HD (Hierarchical Deterministic) derive de la cle vault Poly-Spinor.
    
    La cle privee Ethereum est derivee de maniere deterministe depuis
    le master seed du vault, garantissant que:
    - La meme cle vault genere toujours la meme adresse
    - La cle privee n'est jamais stockee en clair
    - Le wallet peut etre regenere depuis le vault
    """
    
    DERIVATION_PATH = "m/44'/60'/0'/0/0"  # BIP-44 Ethereum
    
    def __init__(self, vault_key: bytes, key_id: str):
        """
        Args:
            vault_key: Cle vault 32 bytes (AES-256)
            key_id: Identifiant de la cle vault
        """
        if not WEB3_AVAILABLE:
            raise ImportError("web3 requis. Installer avec: pip install web3 eth-account")
        
        self.key_id = key_id
        self._vault_key = vault_key
        
        # Deriver la cle privee Ethereum depuis le vault
        self._private_key = self._derive_eth_private_key(vault_key, key_id)
        self._account = Account.from_key(self._private_key)
        
        self.address = self._account.address
        
        # Connexions Web3
        self._web3_connections: Dict[str, Web3] = {}
    
    def _derive_eth_private_key(self, vault_key: bytes, key_id: str) -> bytes:
        """Derive la cle privee Ethereum depuis la cle vault via HKDF"""
        # Utiliser HKDF pour deriver une cle 32 bytes
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=key_id.encode('utf-8'),
            info=b"poly-spinor-evm-wallet-v1"
        )
        return hkdf.derive(vault_key)
    
    def get_web3(self, chain: EVMChain, custom_rpc: Optional[str] = None) -> Web3:
        """Obtient une connexion Web3 pour une chaine"""
        chain_key = f"{chain._name}_{custom_rpc or 'default'}"
        
        if chain_key not in self._web3_connections:
            rpc_url = custom_rpc or chain.default_rpc
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            # Middleware pour les chaines PoA (Polygon, BSC, etc.)
            if geth_poa_middleware and chain in [EVMChain.POLYGON_MAINNET, 
                        EVMChain.POLYGON_MUMBAI, EVMChain.BSC_MAINNET]:
                try:
                    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                except Exception:
                    pass  # Ignorer si le middleware ne fonctionne pas
            
            self._web3_connections[chain_key] = w3
        
        return self._web3_connections[chain_key]
    
    def get_native_balance(self, chain: EVMChain, custom_rpc: Optional[str] = None) -> TokenInfo:
        """Obtient le solde en token natif (ETH, MATIC, BNB, etc.)"""
        w3 = self.get_web3(chain, custom_rpc)
        balance = w3.eth.get_balance(self.address)
        
        native_symbols = {
            EVMChain.ETHEREUM_MAINNET: ("ETH", "Ether"),
            EVMChain.ETHEREUM_SEPOLIA: ("ETH", "Sepolia Ether"),
            EVMChain.POLYGON_MAINNET: ("MATIC", "Polygon"),
            EVMChain.POLYGON_MUMBAI: ("MATIC", "Mumbai MATIC"),
            EVMChain.ARBITRUM_ONE: ("ETH", "Arbitrum Ether"),
            EVMChain.OPTIMISM: ("ETH", "Optimism Ether"),
            EVMChain.BSC_MAINNET: ("BNB", "BNB"),
            EVMChain.AVALANCHE_C: ("AVAX", "Avalanche"),
            EVMChain.BASE_MAINNET: ("ETH", "Base Ether"),
        }
        
        symbol, name = native_symbols.get(chain, ("ETH", "Ether"))
        
        return TokenInfo(
            address="0x0000000000000000000000000000000000000000",
            name=name,
            symbol=symbol,
            decimals=18,
            balance=balance,
            chain=chain._name,
            token_type="NATIVE"
        )
    
    def get_erc20_balance(self, chain: EVMChain, token_address: str,
                          custom_rpc: Optional[str] = None) -> TokenInfo:
        """Obtient le solde d'un token ERC20"""
        w3 = self.get_web3(chain, custom_rpc)
        token_address = Web3.to_checksum_address(token_address)
        
        contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
        
        try:
            name = contract.functions.name().call()
            symbol = contract.functions.symbol().call()
            decimals = contract.functions.decimals().call()
            balance = contract.functions.balanceOf(self.address).call()
        except Exception as e:
            raise ValueError(f"Erreur lecture token ERC20: {e}")
        
        return TokenInfo(
            address=token_address,
            name=name,
            symbol=symbol,
            decimals=decimals,
            balance=balance,
            chain=chain._name,
            token_type="ERC20"
        )
    
    def get_erc721_balance(self, chain: EVMChain, contract_address: str,
                           custom_rpc: Optional[str] = None) -> int:
        """Obtient le nombre de NFTs ERC721 possedes"""
        w3 = self.get_web3(chain, custom_rpc)
        contract_address = Web3.to_checksum_address(contract_address)
        
        contract = w3.eth.contract(address=contract_address, abi=ERC721_ABI)
        return contract.functions.balanceOf(self.address).call()
    
    def get_nft_info(self, chain: EVMChain, contract_address: str, token_id: int,
                     custom_rpc: Optional[str] = None) -> NFTInfo:
        """Obtient les informations d'un NFT specifique"""
        w3 = self.get_web3(chain, custom_rpc)
        contract_address = Web3.to_checksum_address(contract_address)
        
        contract = w3.eth.contract(address=contract_address, abi=ERC721_ABI)
        
        try:
            name = contract.functions.name().call()
            symbol = contract.functions.symbol().call()
            token_uri = contract.functions.tokenURI(token_id).call()
            owner = contract.functions.ownerOf(token_id).call()
        except Exception as e:
            raise ValueError(f"Erreur lecture NFT: {e}")
        
        # Verifier que nous possedons le NFT
        if owner.lower() != self.address.lower():
            raise ValueError(f"NFT #{token_id} n'appartient pas a ce wallet")
        
        # Tenter de recuperer les metadata
        metadata = {}
        if token_uri:
            try:
                import requests
                # Convertir IPFS en HTTP si necessaire
                if token_uri.startswith("ipfs://"):
                    token_uri = f"https://ipfs.io/ipfs/{token_uri[7:]}"
                
                resp = requests.get(token_uri, timeout=10)
                if resp.status_code == 200:
                    metadata = resp.json()
            except:
                pass
        
        return NFTInfo(
            contract_address=contract_address,
            token_id=token_id,
            name=name,
            symbol=symbol,
            token_uri=token_uri,
            metadata=metadata,
            chain=chain._name,
            token_type="ERC721"
        )
    
    # ========================================================================
    # TRANSACTIONS
    # ========================================================================
    
    def _build_and_send_tx(self, w3: Web3, tx_data: Dict, 
                           gas_limit: Optional[int] = None,
                           max_fee_gwei: Optional[float] = None) -> TransactionResult:
        """Construit, signe et envoie une transaction"""
        try:
            # Nonce
            nonce = w3.eth.get_transaction_count(self.address)
            
            # Gas
            if gas_limit is None:
                gas_limit = w3.eth.estimate_gas(tx_data)
            
            # Prix du gas (EIP-1559 si supporte)
            try:
                base_fee = w3.eth.get_block('latest')['baseFeePerGas']
                priority_fee = w3.to_wei(2, 'gwei')
                max_fee = max_fee_gwei and w3.to_wei(max_fee_gwei, 'gwei') or base_fee * 2 + priority_fee
                
                tx_data['maxFeePerGas'] = max_fee
                tx_data['maxPriorityFeePerGas'] = priority_fee
                tx_data['type'] = 2
            except:
                # Legacy gas price
                tx_data['gasPrice'] = w3.eth.gas_price
            
            tx_data['nonce'] = nonce
            tx_data['gas'] = int(gas_limit * 1.1)  # +10% marge
            tx_data['from'] = self.address
            
            # Signer
            signed_tx = w3.eth.account.sign_transaction(tx_data, self._private_key)
            
            # Envoyer
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Attendre confirmation
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return TransactionResult(
                success=receipt['status'] == 1,
                tx_hash=tx_hash.hex(),
                block_number=receipt['blockNumber'],
                gas_used=receipt['gasUsed'],
                error=None if receipt['status'] == 1 else "Transaction reverted"
            )
            
        except Exception as e:
            return TransactionResult(
                success=False,
                tx_hash="",
                block_number=0,
                gas_used=0,
                error=str(e)
            )
    
    def send_native(self, chain: EVMChain, to_address: str, amount_wei: int,
                    custom_rpc: Optional[str] = None,
                    max_fee_gwei: Optional[float] = None) -> TransactionResult:
        """Envoie des tokens natifs (ETH, MATIC, etc.)"""
        w3 = self.get_web3(chain, custom_rpc)
        to_address = Web3.to_checksum_address(to_address)
        
        tx_data = {
            'to': to_address,
            'value': amount_wei,
            'chainId': chain.chain_id
        }
        
        return self._build_and_send_tx(w3, tx_data, gas_limit=21000, max_fee_gwei=max_fee_gwei)
    
    def send_erc20(self, chain: EVMChain, token_address: str, to_address: str,
                   amount: int, custom_rpc: Optional[str] = None,
                   max_fee_gwei: Optional[float] = None) -> TransactionResult:
        """Envoie des tokens ERC20"""
        w3 = self.get_web3(chain, custom_rpc)
        token_address = Web3.to_checksum_address(token_address)
        to_address = Web3.to_checksum_address(to_address)
        
        contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
        
        tx_data = contract.functions.transfer(to_address, amount).build_transaction({
            'chainId': chain.chain_id,
            'from': self.address
        })
        
        return self._build_and_send_tx(w3, tx_data, max_fee_gwei=max_fee_gwei)
    
    def send_erc721(self, chain: EVMChain, contract_address: str, to_address: str,
                    token_id: int, custom_rpc: Optional[str] = None,
                    max_fee_gwei: Optional[float] = None,
                    use_safe_transfer: bool = True) -> TransactionResult:
        """Envoie un NFT ERC721"""
        w3 = self.get_web3(chain, custom_rpc)
        contract_address = Web3.to_checksum_address(contract_address)
        to_address = Web3.to_checksum_address(to_address)
        
        contract = w3.eth.contract(address=contract_address, abi=ERC721_ABI)
        
        # Verifier que nous possedons le NFT
        owner = contract.functions.ownerOf(token_id).call()
        if owner.lower() != self.address.lower():
            return TransactionResult(
                success=False, tx_hash="", block_number=0, gas_used=0,
                error=f"NFT #{token_id} n'appartient pas a ce wallet"
            )
        
        # Utiliser safeTransferFrom ou transferFrom
        if use_safe_transfer:
            tx_data = contract.functions.safeTransferFrom(
                self.address, to_address, token_id
            ).build_transaction({
                'chainId': chain.chain_id,
                'from': self.address
            })
        else:
            tx_data = contract.functions.transferFrom(
                self.address, to_address, token_id
            ).build_transaction({
                'chainId': chain.chain_id,
                'from': self.address
            })
        
        return self._build_and_send_tx(w3, tx_data, max_fee_gwei=max_fee_gwei)
    
    def send_erc1155(self, chain: EVMChain, contract_address: str, to_address: str,
                     token_id: int, amount: int = 1,
                     custom_rpc: Optional[str] = None,
                     max_fee_gwei: Optional[float] = None) -> TransactionResult:
        """Envoie des tokens ERC1155 (NFT ou semi-fongibles)"""
        w3 = self.get_web3(chain, custom_rpc)
        contract_address = Web3.to_checksum_address(contract_address)
        to_address = Web3.to_checksum_address(to_address)
        
        contract = w3.eth.contract(address=contract_address, abi=ERC1155_ABI)
        
        # Verifier le solde
        balance = contract.functions.balanceOf(self.address, token_id).call()
        if balance < amount:
            return TransactionResult(
                success=False, tx_hash="", block_number=0, gas_used=0,
                error=f"Solde insuffisant: {balance} < {amount}"
            )
        
        tx_data = contract.functions.safeTransferFrom(
            self.address, to_address, token_id, amount, b''
        ).build_transaction({
            'chainId': chain.chain_id,
            'from': self.address
        })
        
        return self._build_and_send_tx(w3, tx_data, max_fee_gwei=max_fee_gwei)
    
    # ========================================================================
    # APPROVALS (pour DeFi/Marketplaces)
    # ========================================================================
    
    def approve_erc20(self, chain: EVMChain, token_address: str, spender: str,
                      amount: int, custom_rpc: Optional[str] = None) -> TransactionResult:
        """Approuve un spender pour utiliser des tokens ERC20"""
        w3 = self.get_web3(chain, custom_rpc)
        token_address = Web3.to_checksum_address(token_address)
        spender = Web3.to_checksum_address(spender)
        
        contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
        
        tx_data = contract.functions.approve(spender, amount).build_transaction({
            'chainId': chain.chain_id,
            'from': self.address
        })
        
        return self._build_and_send_tx(w3, tx_data)
    
    def approve_erc721(self, chain: EVMChain, contract_address: str,
                       operator: str, token_id: int,
                       custom_rpc: Optional[str] = None) -> TransactionResult:
        """Approuve un operateur pour un NFT specifique"""
        w3 = self.get_web3(chain, custom_rpc)
        contract_address = Web3.to_checksum_address(contract_address)
        operator = Web3.to_checksum_address(operator)
        
        contract = w3.eth.contract(address=contract_address, abi=ERC721_ABI)
        
        tx_data = contract.functions.approve(operator, token_id).build_transaction({
            'chainId': chain.chain_id,
            'from': self.address
        })
        
        return self._build_and_send_tx(w3, tx_data)
    
    def set_approval_for_all_erc721(self, chain: EVMChain, contract_address: str,
                                     operator: str, approved: bool = True,
                                     custom_rpc: Optional[str] = None) -> TransactionResult:
        """Approuve un operateur pour tous les NFTs d'une collection"""
        w3 = self.get_web3(chain, custom_rpc)
        contract_address = Web3.to_checksum_address(contract_address)
        operator = Web3.to_checksum_address(operator)
        
        contract = w3.eth.contract(address=contract_address, abi=ERC721_ABI)
        
        tx_data = contract.functions.setApprovalForAll(operator, approved).build_transaction({
            'chainId': chain.chain_id,
            'from': self.address
        })
        
        return self._build_and_send_tx(w3, tx_data)
    
    # ========================================================================
    # UTILITAIRES
    # ========================================================================
    
    def get_all_token_balances(self, chain: EVMChain, token_addresses: List[str],
                               custom_rpc: Optional[str] = None) -> List[TokenInfo]:
        """Obtient les soldes de plusieurs tokens"""
        balances = [self.get_native_balance(chain, custom_rpc)]
        
        for addr in token_addresses:
            try:
                balances.append(self.get_erc20_balance(chain, addr, custom_rpc))
            except Exception as e:
                print(f"Erreur lecture {addr}: {e}")
        
        return balances
    
    def export_address_info(self) -> Dict[str, str]:
        """Exporte les informations publiques du wallet"""
        return {
            'address': self.address,
            'vault_key_id': self.key_id,
            'derivation': self.DERIVATION_PATH
        }
    
    def sign_message(self, message: str) -> str:
        """Signe un message (pour verification d'identite)"""
        from eth_account.messages import encode_defunct
        
        message_hash = encode_defunct(text=message)
        signed = self._account.sign_message(message_hash)
        return signed.signature.hex()
    
    def verify_signature(self, message: str, signature: str, address: str) -> bool:
        """Verifie une signature"""
        from eth_account.messages import encode_defunct
        
        message_hash = encode_defunct(text=message)
        recovered = Account.recover_message(message_hash, signature=signature)
        return recovered.lower() == address.lower()


# ============================================================================
# GESTIONNAIRE D'ACTIFS VAULT
# ============================================================================

@dataclass
class VaultAsset:
    """Actif stocke dans le vault"""
    asset_id: str
    asset_type: str  # 'ERC20', 'ERC721', 'ERC1155', 'NATIVE'
    chain: str
    contract_address: str
    token_id: Optional[int]  # Pour NFTs
    amount: int
    symbol: str
    name: str
    metadata: Dict[str, Any]
    added_at: str
    last_sync: str


class VaultAssetManager:
    """Gestionnaire des actifs EVM du vault"""
    
    def __init__(self, wallet: VaultHDWallet, storage_path: str):
        self.wallet = wallet
        self.storage_path = storage_path
        self.assets_file = os.path.join(storage_path, 'evm_assets.json')
        
        os.makedirs(storage_path, exist_ok=True)
        self._assets: Dict[str, VaultAsset] = {}
        self._load_assets()
    
    def _load_assets(self):
        """Charge les actifs depuis le fichier"""
        if os.path.exists(self.assets_file):
            try:
                with open(self.assets_file, 'r') as f:
                    data = json.load(f)
                for asset_id, asset_data in data.items():
                    self._assets[asset_id] = VaultAsset(**asset_data)
            except:
                self._assets = {}
    
    def _save_assets(self):
        """Sauvegarde les actifs"""
        data = {aid: asdict(asset) for aid, asset in self._assets.items()}
        with open(self.assets_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _generate_asset_id(self, chain: str, contract: str, token_id: Optional[int]) -> str:
        """Genere un ID unique pour un actif"""
        key = f"{chain}:{contract}:{token_id or 'fungible'}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    def track_erc20(self, chain: EVMChain, contract_address: str) -> VaultAsset:
        """Ajoute un token ERC20 au suivi"""
        token_info = self.wallet.get_erc20_balance(chain, contract_address)
        
        asset_id = self._generate_asset_id(chain._name, contract_address, None)
        now = datetime.utcnow().isoformat() if 'datetime' in dir() else ""
        
        from datetime import datetime
        now = datetime.utcnow().isoformat()
        
        asset = VaultAsset(
            asset_id=asset_id,
            asset_type="ERC20",
            chain=chain._name,
            contract_address=contract_address,
            token_id=None,
            amount=token_info.balance,
            symbol=token_info.symbol,
            name=token_info.name,
            metadata={'decimals': token_info.decimals},
            added_at=now,
            last_sync=now
        )
        
        self._assets[asset_id] = asset
        self._save_assets()
        return asset
    
    def track_nft(self, chain: EVMChain, contract_address: str, token_id: int) -> VaultAsset:
        """Ajoute un NFT au suivi"""
        nft_info = self.wallet.get_nft_info(chain, contract_address, token_id)
        
        asset_id = self._generate_asset_id(chain._name, contract_address, token_id)
        
        from datetime import datetime
        now = datetime.utcnow().isoformat()
        
        asset = VaultAsset(
            asset_id=asset_id,
            asset_type=nft_info.token_type,
            chain=chain._name,
            contract_address=contract_address,
            token_id=token_id,
            amount=1,
            symbol=nft_info.symbol,
            name=f"{nft_info.name} #{token_id}",
            metadata=nft_info.metadata,
            added_at=now,
            last_sync=now
        )
        
        self._assets[asset_id] = asset
        self._save_assets()
        return asset
    
    def sync_all(self, chain: EVMChain):
        """Synchronise tous les actifs d'une chaine"""
        from datetime import datetime
        
        for asset_id, asset in self._assets.items():
            if asset.chain != chain._name:
                continue
            
            try:
                if asset.asset_type == "ERC20":
                    info = self.wallet.get_erc20_balance(chain, asset.contract_address)
                    asset.amount = info.balance
                elif asset.asset_type in ["ERC721", "ERC1155"]:
                    # Verifier si on possede toujours le NFT
                    try:
                        self.wallet.get_nft_info(chain, asset.contract_address, asset.token_id)
                        asset.amount = 1
                    except:
                        asset.amount = 0
                
                asset.last_sync = datetime.utcnow().isoformat()
            except Exception as e:
                print(f"Erreur sync {asset_id}: {e}")
        
        self._save_assets()
    
    def list_assets(self, chain: Optional[str] = None) -> List[VaultAsset]:
        """Liste les actifs"""
        if chain:
            return [a for a in self._assets.values() if a.chain == chain]
        return list(self._assets.values())
    
    def get_asset(self, asset_id: str) -> Optional[VaultAsset]:
        """Obtient un actif par ID"""
        return self._assets.get(asset_id)
    
    def remove_asset(self, asset_id: str) -> bool:
        """Retire un actif du suivi"""
        if asset_id in self._assets:
            del self._assets[asset_id]
            self._save_assets()
            return True
        return False
    
    def send_asset(self, asset_id: str, to_address: str,
                   amount: Optional[int] = None) -> TransactionResult:
        """Envoie un actif"""
        asset = self._assets.get(asset_id)
        if not asset:
            return TransactionResult(False, "", 0, 0, "Actif non trouve")
        
        chain = None
        for c in EVMChain:
            if c._name == asset.chain:
                chain = c
                break
        
        if not chain:
            return TransactionResult(False, "", 0, 0, f"Chaine inconnue: {asset.chain}")
        
        if asset.asset_type == "ERC20":
            send_amount = amount if amount else asset.amount
            return self.wallet.send_erc20(chain, asset.contract_address, to_address, send_amount)
        
        elif asset.asset_type == "ERC721":
            return self.wallet.send_erc721(chain, asset.contract_address, to_address, asset.token_id)
        
        elif asset.asset_type == "ERC1155":
            send_amount = amount if amount else 1
            return self.wallet.send_erc1155(chain, asset.contract_address, to_address, 
                                            asset.token_id, send_amount)
        
        return TransactionResult(False, "", 0, 0, f"Type non supporte: {asset.asset_type}")


# ============================================================================
# FONCTION UTILITAIRE
# ============================================================================

def create_vault_wallet(vault_key: bytes, key_id: str) -> VaultHDWallet:
    """Cree un wallet EVM depuis une cle vault"""
    return VaultHDWallet(vault_key, key_id)


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  TEST MODULE EVM WALLET")
    print("=" * 60)
    
    if not WEB3_AVAILABLE:
        print("\n[ERREUR] web3 non installe")
        print("Installer avec: pip install web3 eth-account")
        sys.exit(1)
    
    # Simuler une cle vault
    vault_key = secrets.token_bytes(32)
    key_id = "test_key_001"
    
    print(f"\nCreation du wallet...")
    wallet = VaultHDWallet(vault_key, key_id)
    
    print(f"\n  Adresse EVM: {wallet.address}")
    print(f"  Key ID: {wallet.key_id}")
    
    # Test connexion
    print(f"\nTest connexion Ethereum Sepolia...")
    try:
        balance = wallet.get_native_balance(EVMChain.ETHEREUM_SEPOLIA)
        print(f"  Balance: {balance.formatted_balance()} {balance.symbol}")
    except Exception as e:
        print(f"  Erreur connexion: {e}")
    
    # Test signature
    print(f"\nTest signature de message...")
    message = "Test Poly-Spinor Vault"
    signature = wallet.sign_message(message)
    print(f"  Message: {message}")
    print(f"  Signature: {signature[:40]}...")
    
    verified = wallet.verify_signature(message, signature, wallet.address)
    print(f"  Verification: {'OK' if verified else 'ECHEC'}")
    
    print(f"\n{'='*60}")
    print("Pour recevoir des tokens/NFTs, envoyez-les a:")
    print(f"  {wallet.address}")
    print(f"{'='*60}")
