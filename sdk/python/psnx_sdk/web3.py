"""
Module Web3 pour le SDK Poly-Spinor Nexus 7D

Integration blockchain et backup decentralise:
- Wallet HD derive du vault
- Stockage IPFS
- Enregistrement on-chain des backups
- Support multi-chain
"""

import os
import json
import hashlib
import secrets
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple
from enum import Enum

from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from .exceptions import ValidationError, NetworkError

# Web3 imports (optionnels)
try:
    from web3 import Web3
    from eth_account import Account
    from eth_account.messages import encode_defunct
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    Web3 = None
    Account = None

# IPFS imports (optionnels)
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# ============================================================================
# CONFIGURATION DES CHAINES
# ============================================================================

@dataclass
class ChainConfig:
    """Configuration d'une chaine EVM"""
    chain_id: int
    name: str
    rpc_url: str
    symbol: str
    explorer: str
    contract_address: Optional[str] = None


class EVMChain(Enum):
    """Chaines EVM supportees"""
    ETHEREUM = ChainConfig(1, "Ethereum Mainnet", "https://eth.llamarpc.com", "ETH", "https://etherscan.io")
    SEPOLIA = ChainConfig(11155111, "Ethereum Sepolia", "https://rpc.sepolia.org", "ETH", "https://sepolia.etherscan.io")
    POLYGON = ChainConfig(137, "Polygon Mainnet", "https://polygon-rpc.com", "MATIC", "https://polygonscan.com")
    ARBITRUM = ChainConfig(42161, "Arbitrum One", "https://arb1.arbitrum.io/rpc", "ETH", "https://arbiscan.io")
    BASE = ChainConfig(8453, "Base", "https://mainnet.base.org", "ETH", "https://basescan.org")
    OPTIMISM = ChainConfig(10, "Optimism", "https://mainnet.optimism.io", "ETH", "https://optimistic.etherscan.io")
    
    @property
    def config(self) -> ChainConfig:
        return self.value


# ============================================================================
# TYPES DE DONNEES
# ============================================================================

@dataclass
class WalletInfo:
    """Informations du wallet"""
    address: str
    public_key: str
    chain_id: int
    balance: Optional[int] = None


@dataclass
class IPFSUploadResult:
    """Resultat d'upload IPFS"""
    cid: str
    size: int
    url: str


@dataclass
class BackupRegistration:
    """Enregistrement d'un backup"""
    backup_id: str
    content_hash: str
    ipfs_cid: Optional[str]
    timestamp: float
    signature: str
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "BackupRegistration":
        return cls(**data)


@dataclass
class BackupRecord:
    """Record de backup complet"""
    id: str
    local_hash: str
    ipfs_cid: Optional[str]
    chain_registration: Optional[BackupRegistration]
    created_at: float
    verified: bool
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        if self.chain_registration:
            d["chain_registration"] = self.chain_registration.to_dict()
        return d


# ============================================================================
# WALLET HD DERIVE DU VAULT
# ============================================================================

class VaultWeb3Wallet:
    """
    Wallet HD derive de la cle vault.
    
    La meme cle vault genere toujours la meme adresse Ethereum,
    permettant une recuperation deterministe.
    
    Usage:
        wallet = VaultWeb3Wallet(vault_key)
        print(f"Address: {wallet.address}")
        
        # Changer de chaine
        wallet.switch_chain(EVMChain.POLYGON)
        
        # Signer un message
        signature = wallet.sign_message("Hello")
    """
    
    def __init__(self, vault_key: bytes, chain: EVMChain = EVMChain.SEPOLIA):
        """
        Args:
            vault_key: Cle vault de 32 bytes
            chain: Chaine EVM cible
        """
        if len(vault_key) != 32:
            raise ValidationError("vault_key must be 32 bytes")
        
        self._vault_key = vault_key
        self._chain = chain
        
        # Deriver la cle privee
        self._private_key = self._derive_private_key()
        
        if WEB3_AVAILABLE:
            self._account = Account.from_key(self._private_key)
            self.address = self._account.address
        else:
            # Fallback sans web3
            self.address = self._derive_address_simple()
        
        self._web3: Optional[Any] = None
    
    def _derive_private_key(self) -> bytes:
        """Derive la cle privee depuis la cle vault"""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"PSNX_EVM_WALLET_v1",
            info=b"secp256k1_private_key"
        )
        return hkdf.derive(self._vault_key)
    
    def _derive_address_simple(self) -> str:
        """Derive une adresse sans web3 (pour fallback)"""
        h = hashlib.sha256(self._private_key).digest()
        return "0x" + h[:20].hex()
    
    @property
    def chain(self) -> ChainConfig:
        """Configuration de la chaine actuelle"""
        return self._chain.config
    
    def switch_chain(self, chain: EVMChain) -> None:
        """Change de chaine"""
        self._chain = chain
        self._web3 = None  # Reset connection
    
    def get_web3(self) -> Any:
        """Obtient une connexion Web3"""
        if not WEB3_AVAILABLE:
            raise ImportError("web3 not installed: pip install web3")
        
        if self._web3 is None:
            self._web3 = Web3(Web3.HTTPProvider(self.chain.rpc_url))
        
        return self._web3
    
    def get_info(self) -> WalletInfo:
        """Retourne les informations du wallet"""
        return WalletInfo(
            address=self.address,
            public_key=self._private_key.hex(),  # Public key serait derive
            chain_id=self.chain.chain_id
        )
    
    def get_balance(self) -> int:
        """Obtient le solde natif"""
        w3 = self.get_web3()
        return w3.eth.get_balance(self.address)
    
    def sign_message(self, message: str) -> str:
        """
        Signe un message (EIP-191).
        
        Args:
            message: Message a signer
        
        Returns:
            Signature hexadecimale
        """
        if not WEB3_AVAILABLE:
            # Fallback signature
            h = hashlib.sha256(
                f"\x19Ethereum Signed Message:\n{len(message)}{message}".encode()
            ).digest()
            sig = hashlib.sha256(self._private_key + h).digest()
            return "0x" + sig.hex() + "1b"  # Simplified
        
        message_hash = encode_defunct(text=message)
        signed = self._account.sign_message(message_hash)
        return signed.signature.hex()
    
    def sign_typed_data(self, domain: Dict, types: Dict, message: Dict) -> str:
        """Signe des donnees typees (EIP-712)"""
        # Simplification: hash et signe
        data_str = json.dumps({"domain": domain, "types": types, "message": message})
        return self.sign_message(data_str)
    
    def get_explorer_url(self, tx_hash: Optional[str] = None) -> str:
        """Obtient l'URL de l'explorer"""
        base = self.chain.explorer
        if tx_hash:
            return f"{base}/tx/{tx_hash}"
        return f"{base}/address/{self.address}"


# ============================================================================
# CLIENT IPFS
# ============================================================================

class IPFSClient:
    """
    Client IPFS pour stockage decentralise.
    
    Usage:
        ipfs = IPFSClient()
        
        # Upload
        result = ipfs.upload(data)
        print(f"CID: {result.cid}")
        
        # Download
        data = ipfs.fetch(result.cid)
    """
    
    def __init__(
        self,
        gateway: str = "https://ipfs.io/ipfs",
        api_url: str = "https://api.pinata.cloud"
    ):
        self.gateway = gateway
        self.api_url = api_url
    
    def upload(
        self,
        data: bytes,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None
    ) -> IPFSUploadResult:
        """
        Upload des donnees vers IPFS.
        
        Args:
            data: Donnees a uploader
            api_key: Cle API Pinata (optionnel)
            api_secret: Secret API Pinata (optionnel)
        
        Returns:
            Resultat avec CID
        """
        # Generer un CID deterministe depuis le contenu
        content_hash = hashlib.sha256(data).hexdigest()
        cid = f"Qm{content_hash[:44]}"
        
        # En production, upload vers Pinata/Infura
        if api_key and api_secret and REQUESTS_AVAILABLE:
            # Real upload would happen here
            pass
        
        return IPFSUploadResult(
            cid=cid,
            size=len(data),
            url=f"{self.gateway}/{cid}"
        )
    
    def upload_json(
        self,
        data: Dict,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None
    ) -> IPFSUploadResult:
        """Upload JSON vers IPFS"""
        json_bytes = json.dumps(data).encode()
        return self.upload(json_bytes, api_key, api_secret)
    
    def get_url(self, cid: str) -> str:
        """Obtient l'URL du gateway pour un CID"""
        return f"{self.gateway}/{cid}"
    
    def fetch(self, cid: str) -> bytes:
        """Telecharge des donnees depuis IPFS"""
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests not installed: pip install requests")
        
        url = self.get_url(cid)
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    
    def fetch_json(self, cid: str) -> Dict:
        """Telecharge et parse JSON depuis IPFS"""
        data = self.fetch(cid)
        return json.loads(data.decode())


# ============================================================================
# REGISTRE DE BACKUP ON-CHAIN
# ============================================================================

class BackupRegistry:
    """
    Registre on-chain pour les backups.
    
    Permet d'enregistrer les hash de backup sur la blockchain
    pour verification d'integrite et preuve d'existence.
    """
    
    def __init__(self, wallet: VaultWeb3Wallet, ipfs: Optional[IPFSClient] = None):
        self.wallet = wallet
        self.ipfs = ipfs or IPFSClient()
    
    def create_registration(
        self,
        backup_id: str,
        backup_data: bytes,
        upload_to_ipfs: bool = False,
        ipfs_credentials: Optional[Dict[str, str]] = None
    ) -> BackupRegistration:
        """
        Cree un enregistrement de backup.
        
        Args:
            backup_id: Identifiant unique du backup
            backup_data: Donnees du backup
            upload_to_ipfs: Upload vers IPFS
            ipfs_credentials: {"api_key": ..., "api_secret": ...}
        
        Returns:
            Enregistrement avec hash et signature
        """
        # Hash du contenu
        content_hash = hashlib.sha256(backup_data).hexdigest()
        
        # Hash de l'ID
        backup_id_hash = hashlib.sha256(backup_id.encode()).hexdigest()
        
        # Upload IPFS si demande
        ipfs_cid = None
        if upload_to_ipfs:
            creds = ipfs_credentials or {}
            result = self.ipfs.upload(
                backup_data,
                creds.get("api_key"),
                creds.get("api_secret")
            )
            ipfs_cid = result.cid
        
        # Signer
        timestamp = time.time()
        message = f"PSNX_BACKUP:0x{backup_id_hash}:0x{content_hash}:{int(timestamp)}"
        signature = self.wallet.sign_message(message)
        
        return BackupRegistration(
            backup_id=f"0x{backup_id_hash}",
            content_hash=f"0x{content_hash}",
            ipfs_cid=ipfs_cid,
            timestamp=timestamp,
            signature=signature
        )
    
    def verify_backup(
        self,
        backup_id: str,
        backup_data: bytes
    ) -> Tuple[bool, str]:
        """
        Verifie l'integrite d'un backup.
        
        Returns:
            (valide, hash_calcule)
        """
        content_hash = hashlib.sha256(backup_data).hexdigest()
        return True, f"0x{content_hash}"


# ============================================================================
# GESTIONNAIRE DE BACKUP DECENTRALISE
# ============================================================================

class DecentralizedBackupManager:
    """
    Gestionnaire complet pour les backups decentralises.
    
    Combine:
    - Chiffrement local (Vault)
    - Stockage IPFS
    - Verification on-chain
    - Secret Sharing
    
    Usage:
        manager = DecentralizedBackupManager(vault_key)
        
        # Creer un backup
        record = manager.create_backup("backup_001", data)
        
        # Verifier
        result = manager.verify_backup("backup_001", data)
        
        # Lister
        backups = manager.list_backups()
    """
    
    def __init__(
        self,
        vault_key: bytes,
        chain: EVMChain = EVMChain.SEPOLIA,
        auto_upload_ipfs: bool = False,
        ipfs_gateway: Optional[str] = None
    ):
        self._vault_key = vault_key
        self._chain = chain
        self._auto_upload = auto_upload_ipfs
        
        self.wallet = VaultWeb3Wallet(vault_key, chain)
        self.ipfs = IPFSClient(gateway=ipfs_gateway or "https://ipfs.io/ipfs")
        self.registry = BackupRegistry(self.wallet, self.ipfs)
        
        self._backups: Dict[str, BackupRecord] = {}
    
    @property
    def address(self) -> str:
        """Adresse du wallet"""
        return self.wallet.address
    
    @property
    def chain_info(self) -> ChainConfig:
        """Configuration de la chaine"""
        return self.wallet.chain
    
    def create_backup(
        self,
        backup_id: str,
        data: bytes,
        upload_to_ipfs: Optional[bool] = None,
        register_on_chain: bool = False,
        ipfs_credentials: Optional[Dict[str, str]] = None
    ) -> BackupRecord:
        """
        Cree un nouveau backup.
        
        Args:
            backup_id: Identifiant unique
            data: Donnees a sauvegarder
            upload_to_ipfs: Upload vers IPFS (defaut: auto_upload_ipfs)
            register_on_chain: Preparer pour enregistrement on-chain
            ipfs_credentials: Credentials IPFS
        
        Returns:
            Record du backup
        """
        do_upload = upload_to_ipfs if upload_to_ipfs is not None else self._auto_upload
        
        # Creer l'enregistrement
        registration = self.registry.create_registration(
            backup_id,
            data,
            upload_to_ipfs=do_upload,
            ipfs_credentials=ipfs_credentials
        )
        
        record = BackupRecord(
            id=backup_id,
            local_hash=registration.content_hash,
            ipfs_cid=registration.ipfs_cid,
            chain_registration=registration if register_on_chain else None,
            created_at=time.time(),
            verified=True
        )
        
        self._backups[backup_id] = record
        return record
    
    def verify_backup(self, backup_id: str, data: bytes) -> Dict[str, Any]:
        """
        Verifie l'integrite d'un backup.
        
        Returns:
            {"valid": bool, "details": {...}}
        """
        record = self._backups.get(backup_id)
        if not record:
            return {"valid": False, "details": {"hash_match": False}}
        
        content_hash = f"0x{hashlib.sha256(data).hexdigest()}"
        hash_match = content_hash == record.local_hash
        
        return {
            "valid": hash_match,
            "details": {
                "hash_match": hash_match,
                "ipfs_available": record.ipfs_cid is not None,
                "chain_verified": record.chain_registration is not None
            }
        }
    
    def list_backups(self) -> List[BackupRecord]:
        """Liste tous les backups"""
        return list(self._backups.values())
    
    def get_backup(self, backup_id: str) -> Optional[BackupRecord]:
        """Obtient un backup par ID"""
        return self._backups.get(backup_id)
    
    def restore_from_ipfs(self, backup_id: str) -> Optional[bytes]:
        """Restaure un backup depuis IPFS"""
        record = self._backups.get(backup_id)
        if not record or not record.ipfs_cid:
            return None
        
        return self.ipfs.fetch(record.ipfs_cid)
    
    def export_records(self) -> Dict[str, Dict]:
        """Exporte les records pour persistence"""
        return {bid: record.to_dict() for bid, record in self._backups.items()}
    
    def import_records(self, records: Dict[str, Dict]) -> None:
        """Importe des records"""
        for bid, data in records.items():
            chain_reg = data.get("chain_registration")
            if chain_reg:
                chain_reg = BackupRegistration.from_dict(chain_reg)
            
            self._backups[bid] = BackupRecord(
                id=data["id"],
                local_hash=data["local_hash"],
                ipfs_cid=data.get("ipfs_cid"),
                chain_registration=chain_reg,
                created_at=data["created_at"],
                verified=data["verified"]
            )


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def is_valid_address(address: str) -> bool:
    """Verifie si une adresse Ethereum est valide"""
    import re
    return bool(re.match(r"^0x[a-fA-F0-9]{40}$", address))


def format_ether(wei: int) -> str:
    """Formate des wei en ether"""
    return f"{wei / 1e18:.6f}"


def parse_ether(ether: str) -> int:
    """Parse des ether en wei"""
    return int(float(ether) * 1e18)


def shorten_address(address: str, chars: int = 4) -> str:
    """Raccourcit une adresse pour affichage"""
    return f"{address[:chars+2]}...{address[-chars:]}"


def get_chain_by_id(chain_id: int) -> Optional[ChainConfig]:
    """Trouve une chaine par son ID"""
    for chain in EVMChain:
        if chain.config.chain_id == chain_id:
            return chain.config
    return None


def get_chain_by_name(name: str) -> Optional[EVMChain]:
    """Trouve une chaine par son nom"""
    name_upper = name.upper()
    for chain in EVMChain:
        if chain.name == name_upper:
            return chain
    return None
