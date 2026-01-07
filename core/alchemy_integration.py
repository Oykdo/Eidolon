"""
Intégration Alchemy API pour Eidolon
Composants Web3 avancés utilisant l'infrastructure Alchemy

Fonctionnalités:
- NFT API: récupération NFTs, métadonnées, ownership
- Token API: balances ERC20, transfers, prix
- Enhanced API: gas estimation, transaction simulation
- Webhooks: notifications temps réel (transfers, mints, etc.)
- Multi-chain: Ethereum, Polygon, Arbitrum, Optimism, Base

IMPORTANT: Nécessite une clé API Alchemy (https://www.alchemy.com/)
"""

import os
import json
import hashlib
import hmac
import time
from typing import Optional, Dict, List, Any, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime
from decimal import Decimal
import requests
from urllib.parse import urljoin


# ============================================================================
# CONFIGURATION
# ============================================================================

class AlchemyNetwork(Enum):
    """Réseaux supportés par Alchemy"""
    # Ethereum
    ETH_MAINNET = ("eth-mainnet", 1)
    ETH_SEPOLIA = ("eth-sepolia", 11155111)
    ETH_HOLESKY = ("eth-holesky", 17000)
    
    # Polygon
    POLYGON_MAINNET = ("polygon-mainnet", 137)
    POLYGON_AMOY = ("polygon-amoy", 80002)
    
    # Arbitrum
    ARB_MAINNET = ("arb-mainnet", 42161)
    ARB_SEPOLIA = ("arb-sepolia", 421614)
    
    # Optimism
    OPT_MAINNET = ("opt-mainnet", 10)
    OPT_SEPOLIA = ("opt-sepolia", 11155420)
    
    # Base
    BASE_MAINNET = ("base-mainnet", 8453)
    BASE_SEPOLIA = ("base-sepolia", 84532)
    
    # Zksync
    ZKSYNC_MAINNET = ("zksync-mainnet", 324)
    ZKSYNC_SEPOLIA = ("zksync-sepolia", 300)
    
    def __init__(self, network_id: str, chain_id: int):
        self.network_id = network_id
        self.chain_id = chain_id
    
    @property
    def base_url(self) -> str:
        return f"https://{self.network_id}.g.alchemy.com"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class AlchemyNFT:
    """Représentation d'un NFT via Alchemy API"""
    contract_address: str
    token_id: str
    token_type: str  # ERC721, ERC1155
    name: Optional[str]
    description: Optional[str]
    image_url: Optional[str]
    external_url: Optional[str]
    attributes: List[Dict[str, Any]]
    raw_metadata: Dict[str, Any]
    balance: int = 1  # Pour ERC1155
    collection_name: Optional[str] = None
    collection_symbol: Optional[str] = None
    spam_info: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AlchemyToken:
    """Représentation d'un token ERC20 via Alchemy API"""
    contract_address: str
    name: str
    symbol: str
    decimals: int
    balance: int
    logo_url: Optional[str] = None
    
    @property
    def formatted_balance(self) -> str:
        return str(Decimal(self.balance) / Decimal(10 ** self.decimals))
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['formatted_balance'] = self.formatted_balance
        return d


@dataclass
class AlchemyTransfer:
    """Représentation d'un transfer via Alchemy API"""
    block_num: int
    tx_hash: str
    from_address: str
    to_address: str
    value: Optional[str]
    asset: str
    category: str  # external, internal, erc20, erc721, erc1155
    token_id: Optional[str] = None
    raw_contract: Optional[Dict] = None


@dataclass
class AlchemyGasEstimate:
    """Estimation de gas via Alchemy API"""
    max_fee_per_gas: int
    max_priority_fee_per_gas: int
    base_fee: int
    estimated_gas: int
    total_cost_wei: int
    total_cost_gwei: float
    confidence: str  # low, medium, high


@dataclass  
class WebhookConfig:
    """Configuration d'un webhook Alchemy"""
    webhook_id: str
    webhook_url: str
    webhook_type: str
    network: str
    is_active: bool
    addresses: List[str] = field(default_factory=list)
    signing_key: Optional[str] = None


# ============================================================================
# ALCHEMY CLIENT PRINCIPAL
# ============================================================================

class AlchemyClient:
    """
    Client principal pour l'API Alchemy.
    
    Usage:
        client = AlchemyClient(api_key="your_key", network=AlchemyNetwork.ETH_MAINNET)
        nfts = client.get_nfts_for_owner("0x...")
        tokens = client.get_token_balances("0x...")
    """
    
    API_VERSION_NFT = "v3"
    API_VERSION_TOKEN = "v2"
    REQUEST_TIMEOUT = 30
    
    def __init__(self, api_key: str, network: AlchemyNetwork = AlchemyNetwork.ETH_MAINNET):
        """
        Args:
            api_key: Clé API Alchemy
            network: Réseau cible
        """
        self.api_key = api_key
        self.network = network
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
    
    def _get_base_url(self, api_type: str = "rpc") -> str:
        """Construit l'URL de base selon le type d'API"""
        if api_type == "nft":
            return f"{self.network.base_url}/nft/{self.API_VERSION_NFT}/{self.api_key}"
        elif api_type == "token":
            return f"{self.network.base_url}/{self.API_VERSION_TOKEN}/{self.api_key}"
        else:  # rpc
            return f"{self.network.base_url}/{self.API_VERSION_TOKEN}/{self.api_key}"
    
    def _make_request(self, method: str, url: str, 
                      params: Optional[Dict] = None,
                      json_data: Optional[Dict] = None) -> Dict:
        """Effectue une requête HTTP"""
        try:
            if method.upper() == "GET":
                resp = self._session.get(url, params=params, timeout=self.REQUEST_TIMEOUT)
            else:
                resp = self._session.post(url, json=json_data, timeout=self.REQUEST_TIMEOUT)
            
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            raise AlchemyAPIError(f"Requête échouée: {e}")
    
    def _rpc_call(self, method: str, params: List[Any]) -> Any:
        """Appel JSON-RPC"""
        url = self._get_base_url("rpc")
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        result = self._make_request("POST", url, json_data=payload)
        
        if "error" in result:
            raise AlchemyAPIError(f"RPC Error: {result['error']}")
        
        return result.get("result")
    
    # ========================================================================
    # NFT API
    # ========================================================================
    
    def get_nfts_for_owner(self, owner: str, 
                           contract_addresses: Optional[List[str]] = None,
                           exclude_filters: Optional[List[str]] = None,
                           include_filters: Optional[List[str]] = None,
                           page_size: int = 100,
                           page_key: Optional[str] = None) -> Tuple[List[AlchemyNFT], Optional[str]]:
        """
        Récupère tous les NFTs d'une adresse.
        
        Args:
            owner: Adresse du propriétaire
            contract_addresses: Filtrer par contrats spécifiques
            exclude_filters: Exclure certains types (SPAM, AIRDROPS)
            include_filters: Inclure certains attributs (METADATA, ATTRIBUTE_RARITY)
            page_size: Nombre de résultats par page (max 100)
            page_key: Clé de pagination
        
        Returns:
            Tuple (liste NFTs, clé page suivante)
        """
        url = f"{self._get_base_url('nft')}/getNFTsForOwner"
        
        params: Dict[str, Any] = {
            "owner": owner,
            "pageSize": min(page_size, 100),
            "withMetadata": "true"
        }
        
        if contract_addresses:
            params["contractAddresses[]"] = contract_addresses
        if exclude_filters:
            params["excludeFilters[]"] = exclude_filters
        if include_filters:
            params["includeFilters[]"] = include_filters
        if page_key:
            params["pageKey"] = page_key
        
        data = self._make_request("GET", url, params=params)
        
        nfts = []
        for nft_data in data.get("ownedNfts", []):
            nft = self._parse_nft(nft_data)
            nfts.append(nft)
        
        next_page = data.get("pageKey")
        return nfts, next_page
    
    def get_all_nfts_for_owner(self, owner: str, **kwargs) -> List[AlchemyNFT]:
        """Récupère TOUS les NFTs (pagination automatique)"""
        all_nfts = []
        page_key = None
        
        while True:
            nfts, page_key = self.get_nfts_for_owner(owner, page_key=page_key, **kwargs)
            all_nfts.extend(nfts)
            
            if not page_key:
                break
        
        return all_nfts
    
    def get_nft_metadata(self, contract_address: str, token_id: str,
                         token_type: str = "ERC721") -> AlchemyNFT:
        """Récupère les métadonnées d'un NFT spécifique"""
        url = f"{self._get_base_url('nft')}/getNFTMetadata"
        
        params = {
            "contractAddress": contract_address,
            "tokenId": token_id,
            "tokenType": token_type,
            "refreshCache": "false"
        }
        
        data = self._make_request("GET", url, params=params)
        return self._parse_nft(data)
    
    def get_owners_for_nft(self, contract_address: str, token_id: str) -> List[str]:
        """Récupère les propriétaires d'un NFT (utile pour ERC1155)"""
        url = f"{self._get_base_url('nft')}/getOwnersForNFT"
        
        params = {
            "contractAddress": contract_address,
            "tokenId": token_id
        }
        
        data = self._make_request("GET", url, params=params)
        return data.get("owners", [])
    
    def get_contracts_for_owner(self, owner: str, 
                                 include_filters: Optional[List[str]] = None) -> List[Dict]:
        """Récupère les contrats NFT pour lesquels l'adresse possède des tokens"""
        url = f"{self._get_base_url('nft')}/getContractsForOwner"
        
        params: Dict[str, Any] = {"owner": owner}
        if include_filters:
            params["includeFilters[]"] = include_filters
        
        data = self._make_request("GET", url, params=params)
        return data.get("contracts", [])
    
    def get_nft_sales(self, contract_address: str, token_id: str,
                      marketplace: Optional[str] = None,
                      limit: int = 100) -> List[Dict]:
        """Récupère l'historique des ventes d'un NFT"""
        url = f"{self._get_base_url('nft')}/getNFTSales"
        
        params = {
            "contractAddress": contract_address,
            "tokenId": token_id,
            "limit": limit
        }
        if marketplace:
            params["marketplace"] = marketplace
        
        data = self._make_request("GET", url, params=params)
        return data.get("nftSales", [])
    
    def is_spam_contract(self, contract_address: str) -> bool:
        """Vérifie si un contrat est marqué comme spam"""
        url = f"{self._get_base_url('nft')}/isSpamContract"
        params = {"contractAddress": contract_address}
        
        data = self._make_request("GET", url, params=params)
        return data.get("isSpamContract", False)
    
    def _parse_nft(self, data: Dict) -> AlchemyNFT:
        """Parse les données NFT de l'API"""
        contract = data.get("contract", {})
        raw_metadata = data.get("raw", {}).get("metadata", {})
        image = data.get("image", {})
        
        # Gérer différents formats d'image
        image_url = None
        if image:
            image_url = image.get("cachedUrl") or image.get("originalUrl") or image.get("pngUrl")
        
        return AlchemyNFT(
            contract_address=contract.get("address", ""),
            token_id=data.get("tokenId", ""),
            token_type=data.get("tokenType", "ERC721"),
            name=data.get("name") or raw_metadata.get("name"),
            description=data.get("description") or raw_metadata.get("description"),
            image_url=image_url,
            external_url=raw_metadata.get("external_url"),
            attributes=raw_metadata.get("attributes", []),
            raw_metadata=raw_metadata,
            balance=int(data.get("balance", 1)),
            collection_name=contract.get("name"),
            collection_symbol=contract.get("symbol"),
            spam_info=data.get("spamInfo")
        )
    
    # ========================================================================
    # TOKEN API
    # ========================================================================
    
    def get_token_balances(self, address: str, 
                           contract_addresses: Optional[List[str]] = None) -> List[AlchemyToken]:
        """
        Récupère les balances de tokens ERC20.
        
        Args:
            address: Adresse du wallet
            contract_addresses: Liste de contrats spécifiques (None = tous)
        """
        if contract_addresses:
            params = [address, contract_addresses]
        else:
            params = [address, "erc20"]
        
        result = self._rpc_call("alchemy_getTokenBalances", params)
        
        tokens = []
        for token_data in result.get("tokenBalances", []):
            contract = token_data.get("contractAddress")
            balance_hex = token_data.get("tokenBalance", "0x0")
            
            if balance_hex == "0x0" or balance_hex == "0x":
                continue
            
            balance = int(balance_hex, 16)
            
            # Récupérer les métadonnées du token
            metadata = self.get_token_metadata(contract)
            
            tokens.append(AlchemyToken(
                contract_address=contract,
                name=metadata.get("name", "Unknown"),
                symbol=metadata.get("symbol", "???"),
                decimals=metadata.get("decimals", 18),
                balance=balance,
                logo_url=metadata.get("logo")
            ))
        
        return tokens
    
    def get_token_metadata(self, contract_address: str) -> Dict:
        """Récupère les métadonnées d'un token ERC20"""
        result = self._rpc_call("alchemy_getTokenMetadata", [contract_address])
        return result or {}
    
    def get_token_allowance(self, contract_address: str, 
                            owner: str, spender: str) -> int:
        """Récupère l'allowance ERC20"""
        # Encoder l'appel allowance(owner, spender)
        # allowance selector: 0xdd62ed3e
        owner_padded = owner[2:].lower().zfill(64)
        spender_padded = spender[2:].lower().zfill(64)
        data = f"0xdd62ed3e{owner_padded}{spender_padded}"
        
        result = self._rpc_call("eth_call", [
            {"to": contract_address, "data": data},
            "latest"
        ])
        
        return int(result, 16) if result else 0
    
    # ========================================================================
    # TRANSFERS API
    # ========================================================================
    
    def get_asset_transfers(self, from_address: Optional[str] = None,
                            to_address: Optional[str] = None,
                            contract_addresses: Optional[List[str]] = None,
                            category: Optional[List[str]] = None,
                            from_block: str = "0x0",
                            to_block: str = "latest",
                            max_count: int = 1000,
                            page_key: Optional[str] = None) -> Tuple[List[AlchemyTransfer], Optional[str]]:
        """
        Récupère l'historique des transfers.
        
        Args:
            from_address: Filtrer par expéditeur
            to_address: Filtrer par destinataire
            contract_addresses: Filtrer par contrats
            category: Types de transfers (external, internal, erc20, erc721, erc1155)
            from_block: Bloc de départ (hex)
            to_block: Bloc de fin
            max_count: Nombre max de résultats
            page_key: Clé de pagination
        """
        params = {
            "fromBlock": from_block,
            "toBlock": to_block,
            "maxCount": hex(max_count),
            "withMetadata": True
        }
        
        if from_address:
            params["fromAddress"] = from_address
        if to_address:
            params["toAddress"] = to_address
        if contract_addresses:
            params["contractAddresses"] = contract_addresses
        if category:
            params["category"] = category
        else:
            params["category"] = ["external", "erc20", "erc721", "erc1155"]
        if page_key:
            params["pageKey"] = page_key
        
        result = self._rpc_call("alchemy_getAssetTransfers", [params])
        
        transfers = []
        for tx in result.get("transfers", []):
            transfers.append(AlchemyTransfer(
                block_num=int(tx.get("blockNum", "0x0"), 16),
                tx_hash=tx.get("hash", ""),
                from_address=tx.get("from", ""),
                to_address=tx.get("to", ""),
                value=tx.get("value"),
                asset=tx.get("asset", ""),
                category=tx.get("category", ""),
                token_id=tx.get("tokenId"),
                raw_contract=tx.get("rawContract")
            ))
        
        next_page = result.get("pageKey")
        return transfers, next_page
    
    # ========================================================================
    # GAS & TRANSACTIONS
    # ========================================================================
    
    def get_gas_price(self) -> Dict[str, int]:
        """Récupère les prix de gas actuels"""
        result = self._rpc_call("eth_gasPrice", [])
        gas_price = int(result, 16)
        
        # Aussi récupérer les fees EIP-1559
        fee_history = self._rpc_call("eth_feeHistory", ["0x5", "latest", [25, 50, 75]])
        
        base_fees = fee_history.get("baseFeePerGas", [])
        latest_base = int(base_fees[-1], 16) if base_fees else gas_price
        
        priority_fees = fee_history.get("reward", [[]])
        avg_priority = sum(int(f[1], 16) for f in priority_fees if f) // max(len(priority_fees), 1)
        
        return {
            "gas_price": gas_price,
            "base_fee": latest_base,
            "priority_fee_low": int(priority_fees[-1][0], 16) if priority_fees and priority_fees[-1] else avg_priority,
            "priority_fee_medium": int(priority_fees[-1][1], 16) if priority_fees and priority_fees[-1] else avg_priority,
            "priority_fee_high": int(priority_fees[-1][2], 16) if priority_fees and priority_fees[-1] else avg_priority
        }
    
    def estimate_gas(self, tx: Dict) -> AlchemyGasEstimate:
        """Estime le gas pour une transaction"""
        gas_limit = self._rpc_call("eth_estimateGas", [tx])
        gas_limit = int(gas_limit, 16)
        
        prices = self.get_gas_price()
        
        max_fee = prices["base_fee"] + prices["priority_fee_medium"]
        total_cost = gas_limit * max_fee
        
        return AlchemyGasEstimate(
            max_fee_per_gas=max_fee,
            max_priority_fee_per_gas=prices["priority_fee_medium"],
            base_fee=prices["base_fee"],
            estimated_gas=gas_limit,
            total_cost_wei=total_cost,
            total_cost_gwei=total_cost / 1e9,
            confidence="medium"
        )
    
    def simulate_transaction(self, tx: Dict) -> Dict:
        """Simule une transaction (Alchemy Transact API)"""
        result = self._rpc_call("alchemy_simulateExecution", [tx])
        return result
    
    def send_raw_transaction(self, signed_tx: str) -> str:
        """Envoie une transaction signée"""
        result = self._rpc_call("eth_sendRawTransaction", [signed_tx])
        return result
    
    def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict]:
        """Récupère le reçu d'une transaction"""
        result = self._rpc_call("eth_getTransactionReceipt", [tx_hash])
        return result
    
    def wait_for_transaction(self, tx_hash: str, timeout: int = 120,
                              poll_interval: float = 2.0) -> Dict:
        """Attend qu'une transaction soit minée"""
        start = time.time()
        
        while time.time() - start < timeout:
            receipt = self.get_transaction_receipt(tx_hash)
            if receipt:
                return receipt
            time.sleep(poll_interval)
        
        raise AlchemyAPIError(f"Timeout waiting for transaction {tx_hash}")
    
    # ========================================================================
    # BLOCK & CHAIN DATA
    # ========================================================================
    
    def get_block_number(self) -> int:
        """Récupère le numéro de bloc actuel"""
        result = self._rpc_call("eth_blockNumber", [])
        return int(result, 16)
    
    def get_block(self, block_number: Union[int, str] = "latest",
                   full_transactions: bool = False) -> Dict:
        """Récupère les données d'un bloc"""
        if isinstance(block_number, int):
            block_number = hex(block_number)
        
        result = self._rpc_call("eth_getBlockByNumber", [block_number, full_transactions])
        return result
    
    def get_balance(self, address: str, block: str = "latest") -> int:
        """Récupère le balance native (ETH, MATIC, etc.)"""
        result = self._rpc_call("eth_getBalance", [address, block])
        return int(result, 16)
    
    # ========================================================================
    # UTILITAIRES
    # ========================================================================
    
    def switch_network(self, network: AlchemyNetwork):
        """Change de réseau"""
        self.network = network
    
    def get_supported_networks(self) -> List[str]:
        """Liste des réseaux supportés"""
        return [n.network_id for n in AlchemyNetwork]


# ============================================================================
# GESTIONNAIRE DE WEBHOOKS
# ============================================================================

class AlchemyWebhookManager:
    """
    Gestionnaire de webhooks Alchemy pour notifications temps réel.
    
    Types de webhooks:
    - ADDRESS_ACTIVITY: Transfers entrants/sortants pour des adresses
    - NFT_ACTIVITY: Transfers de NFTs spécifiques
    - MINED_TRANSACTION: Transaction minée
    - DROPPED_TRANSACTION: Transaction droppée
    """
    
    NOTIFY_API_URL = "https://dashboard.alchemy.com/api"
    
    def __init__(self, auth_token: str):
        """
        Args:
            auth_token: Token d'authentification Alchemy (depuis le dashboard)
        """
        self.auth_token = auth_token
        self._session = requests.Session()
        self._session.headers.update({
            "X-Alchemy-Token": auth_token,
            "Content-Type": "application/json"
        })
    
    def create_address_webhook(self, webhook_url: str, network: AlchemyNetwork,
                                addresses: List[str]) -> WebhookConfig:
        """Crée un webhook pour surveiller des adresses"""
        payload = {
            "network": network.network_id.upper().replace("-", "_"),
            "webhook_type": "ADDRESS_ACTIVITY",
            "webhook_url": webhook_url,
            "addresses": addresses
        }
        
        resp = self._session.post(f"{self.NOTIFY_API_URL}/create-webhook", json=payload)
        resp.raise_for_status()
        data = resp.json()
        
        return WebhookConfig(
            webhook_id=data.get("id", ""),
            webhook_url=webhook_url,
            webhook_type="ADDRESS_ACTIVITY",
            network=network.network_id,
            is_active=data.get("is_active", True),
            addresses=addresses,
            signing_key=data.get("signing_key")
        )
    
    def create_nft_webhook(self, webhook_url: str, network: AlchemyNetwork,
                           nft_filters: List[Dict[str, str]]) -> WebhookConfig:
        """
        Crée un webhook pour surveiller des NFTs.
        
        Args:
            nft_filters: Liste de {"contract_address": "0x...", "token_id": "123"}
        """
        payload = {
            "network": network.network_id.upper().replace("-", "_"),
            "webhook_type": "NFT_ACTIVITY",
            "webhook_url": webhook_url,
            "nft_filters": nft_filters
        }
        
        resp = self._session.post(f"{self.NOTIFY_API_URL}/create-webhook", json=payload)
        resp.raise_for_status()
        data = resp.json()
        
        return WebhookConfig(
            webhook_id=data.get("id", ""),
            webhook_url=webhook_url,
            webhook_type="NFT_ACTIVITY",
            network=network.network_id,
            is_active=data.get("is_active", True),
            signing_key=data.get("signing_key")
        )
    
    def update_webhook_addresses(self, webhook_id: str, 
                                  addresses_to_add: Optional[List[str]] = None,
                                  addresses_to_remove: Optional[List[str]] = None):
        """Met à jour les adresses surveillées par un webhook"""
        payload: Dict[str, Any] = {"webhook_id": webhook_id}
        
        if addresses_to_add:
            payload["addresses_to_add"] = addresses_to_add
        if addresses_to_remove:
            payload["addresses_to_remove"] = addresses_to_remove
        
        resp = self._session.patch(f"{self.NOTIFY_API_URL}/update-webhook-addresses", json=payload)
        resp.raise_for_status()
        return resp.json()
    
    def delete_webhook(self, webhook_id: str) -> bool:
        """Supprime un webhook"""
        resp = self._session.delete(f"{self.NOTIFY_API_URL}/delete-webhook", 
                                    json={"webhook_id": webhook_id})
        return resp.status_code == 200
    
    def list_webhooks(self) -> List[WebhookConfig]:
        """Liste tous les webhooks"""
        resp = self._session.get(f"{self.NOTIFY_API_URL}/team-webhooks")
        resp.raise_for_status()
        
        webhooks = []
        for data in resp.json().get("data", []):
            webhooks.append(WebhookConfig(
                webhook_id=data.get("id", ""),
                webhook_url=data.get("webhook_url", ""),
                webhook_type=data.get("webhook_type", ""),
                network=data.get("network", ""),
                is_active=data.get("is_active", False),
                addresses=data.get("addresses", [])
            ))
        
        return webhooks
    
    @staticmethod
    def verify_signature(payload: bytes, signature: str, signing_key: str) -> bool:
        """
        Vérifie la signature d'un webhook entrant.
        
        Args:
            payload: Corps de la requête (bytes)
            signature: Header X-Alchemy-Signature
            signing_key: Clé de signature du webhook
        """
        expected = hmac.new(
            signing_key.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)


# ============================================================================
# INTÉGRATION AVEC VAULT WALLET
# ============================================================================

class AlchemyVaultIntegration:
    """
    Intégration d'Alchemy avec le VaultHDWallet existant.
    
    Combine les fonctionnalités du wallet vault avec l'API Alchemy
    pour une expérience Web3 complète.
    """
    
    def __init__(self, api_key: str, network: AlchemyNetwork = AlchemyNetwork.ETH_MAINNET):
        self.client = AlchemyClient(api_key, network)
        self._wallet = None
    
    def connect_wallet(self, wallet):
        """Connecte un VaultHDWallet"""
        self._wallet = wallet
    
    @property
    def address(self) -> Optional[str]:
        return self._wallet.address if self._wallet else None
    
    def get_portfolio(self) -> Dict[str, Any]:
        """
        Récupère le portfolio complet (native + tokens + NFTs).
        
        Returns:
            Dict avec native_balance, tokens, nfts, total_value_usd
        """
        if not self._wallet:
            raise ValueError("Wallet non connecté")
        
        address = self._wallet.address
        
        # Balance native
        native_balance = self.client.get_balance(address)
        
        # Tokens ERC20
        tokens = self.client.get_token_balances(address)
        
        # NFTs
        nfts, _ = self.client.get_nfts_for_owner(address, exclude_filters=["SPAM"])
        
        return {
            "address": address,
            "network": self.client.network.network_id,
            "native_balance_wei": native_balance,
            "native_balance_eth": native_balance / 1e18,
            "tokens": [t.to_dict() for t in tokens],
            "nfts": [n.to_dict() for n in nfts],
            "token_count": len(tokens),
            "nft_count": len(nfts),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def get_transaction_history(self, limit: int = 100) -> List[Dict]:
        """Récupère l'historique des transactions"""
        if not self._wallet:
            raise ValueError("Wallet non connecté")
        
        # Transfers sortants
        outgoing, _ = self.client.get_asset_transfers(
            from_address=self._wallet.address,
            max_count=limit // 2
        )
        
        # Transfers entrants
        incoming, _ = self.client.get_asset_transfers(
            to_address=self._wallet.address,
            max_count=limit // 2
        )
        
        # Combiner et trier
        all_transfers = []
        for tx in outgoing:
            all_transfers.append({
                "direction": "out",
                "block": tx.block_num,
                "hash": tx.tx_hash,
                "from": tx.from_address,
                "to": tx.to_address,
                "value": tx.value,
                "asset": tx.asset,
                "category": tx.category
            })
        
        for tx in incoming:
            all_transfers.append({
                "direction": "in",
                "block": tx.block_num,
                "hash": tx.tx_hash,
                "from": tx.from_address,
                "to": tx.to_address,
                "value": tx.value,
                "asset": tx.asset,
                "category": tx.category
            })
        
        return sorted(all_transfers, key=lambda x: x["block"], reverse=True)
    
    def estimate_transfer_gas(self, to: str, value_wei: int) -> AlchemyGasEstimate:
        """Estime le gas pour un transfer natif"""
        tx = {
            "from": self._wallet.address if self._wallet else "0x0",
            "to": to,
            "value": hex(value_wei)
        }
        return self.client.estimate_gas(tx)


# ============================================================================
# EXCEPTIONS
# ============================================================================

class AlchemyAPIError(Exception):
    """Erreur de l'API Alchemy"""
    pass


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def create_alchemy_client(api_key: str, 
                          network: str = "eth-mainnet") -> AlchemyClient:
    """
    Crée un client Alchemy.
    
    Args:
        api_key: Clé API Alchemy
        network: ID du réseau (eth-mainnet, polygon-mainnet, etc.)
    
    Returns:
        AlchemyClient configuré
    """
    # Trouver le réseau
    network_enum = None
    for n in AlchemyNetwork:
        if n.network_id == network:
            network_enum = n
            break
    
    if not network_enum:
        raise ValueError(f"Réseau inconnu: {network}. Disponibles: {[n.network_id for n in AlchemyNetwork]}")
    
    return AlchemyClient(api_key, network_enum)


def get_api_key_from_env() -> Optional[str]:
    """Récupère la clé API depuis les variables d'environnement"""
    return os.environ.get("ALCHEMY_API_KEY")


# ============================================================================
# EXEMPLE D'UTILISATION
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  ALCHEMY INTEGRATION - EIDOLON")
    print("=" * 60)
    
    # Vérifier si une clé API est disponible
    api_key = get_api_key_from_env()
    
    if not api_key:
        print("\n[INFO] Clé API non configurée.")
        print("Pour utiliser ce module:")
        print("  1. Créer un compte sur https://www.alchemy.com/")
        print("  2. Créer une app et copier l'API key")
        print("  3. Définir la variable d'environnement ALCHEMY_API_KEY")
        print("\nExemple d'utilisation:")
        print("""
    from core.alchemy_integration import AlchemyClient, AlchemyNetwork
    
    client = AlchemyClient(
        api_key="votre_cle_api",
        network=AlchemyNetwork.ETH_MAINNET
    )
    
    # Récupérer les NFTs d'une adresse
    nfts, _ = client.get_nfts_for_owner("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
    for nft in nfts[:5]:
        print(f"- {nft.name} ({nft.collection_name})")
    
    # Récupérer les tokens ERC20
    tokens = client.get_token_balances("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
    for token in tokens:
        print(f"- {token.symbol}: {token.formatted_balance}")
        """)
    else:
        print(f"\n[OK] Clé API détectée")
        
        # Test basique
        client = AlchemyClient(api_key, AlchemyNetwork.ETH_MAINNET)
        
        print(f"\nTest de connexion à {client.network.network_id}...")
        try:
            block = client.get_block_number()
            print(f"[OK] Bloc actuel: {block}")
            
            gas = client.get_gas_price()
            print(f"[OK] Gas price: {gas['gas_price'] / 1e9:.2f} Gwei")
            print(f"[OK] Base fee: {gas['base_fee'] / 1e9:.2f} Gwei")
            
        except Exception as e:
            print(f"[ERREUR] {e}")
    
    print(f"\n{'='*60}")
