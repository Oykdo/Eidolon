#!/usr/bin/env python3
"""
Eidolon - Avatar NFT Collection System
======================================

Multi-chain avatar NFTs with cross-chain interoperability.
Supports Ethereum (ERC-721) and BSC (BEP-721).

Key features:
- One avatar minted at vault creation (genesis avatar)
- Collection can hold multiple avatars
- Cross-chain bridge (ETH <-> BSC)
- Only exists on ONE chain at a time (no duplicates)
- Avatar locked during bridge transfer

Chains supported:
- Ethereum Mainnet (chainId: 1)
- BSC Mainnet (chainId: 56)
- Ethereum Sepolia Testnet (chainId: 11155111)
- BSC Testnet (chainId: 97)
"""

import hashlib
import json
import secrets
import struct
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ============================================================================
# CONSTANTS
# ============================================================================

# Contract addresses (to be deployed)
CONTRACTS = {
    "ethereum": {
        "mainnet": {
            "chainId": 1,
            "avatar_nft": None,  # To deploy
            "bridge": None,
        },
        "sepolia": {
            "chainId": 11155111,
            "avatar_nft": None,
            "bridge": None,
        }
    },
    "bsc": {
        "mainnet": {
            "chainId": 56,
            "avatar_nft": None,
            "bridge": None,
        },
        "testnet": {
            "chainId": 97,
            "avatar_nft": None,
            "bridge": None,
        }
    }
}

# NFT metadata base URI
METADATA_BASE_URI = "ipfs://"

# Bridge lock time (seconds)
BRIDGE_LOCK_TIME = 300  # 5 minutes

# Max avatars per vault
MAX_AVATARS_PER_VAULT = 100


# ============================================================================
# ENUMERATIONS
# ============================================================================

class ChainType(Enum):
    """Supported blockchains"""
    ETHEREUM = "ethereum"
    BSC = "bsc"


class NetworkType(Enum):
    """Network types"""
    MAINNET = "mainnet"
    TESTNET = "testnet"


class AvatarNFTStatus(Enum):
    """NFT Status"""
    DRAFT = "draft"              # Not minted yet
    MINTING = "minting"          # Mint transaction pending
    MINTED = "minted"            # Successfully minted
    BRIDGING = "bridging"        # Being bridged to another chain
    LOCKED = "locked"            # Locked during bridge
    BURNED = "burned"            # Burned (for bridge)


class BridgeStatus(Enum):
    """Bridge transfer status"""
    INITIATED = "initiated"
    SOURCE_LOCKED = "source_locked"
    SOURCE_BURNED = "source_burned"
    DEST_MINTING = "dest_minting"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class AvatarNFTMetadata:
    """ERC-721/BEP-721 compliant metadata"""
    name: str
    description: str
    image: str  # IPFS URI
    external_url: str
    
    # Standard attributes
    attributes: List[Dict[str, Any]] = field(default_factory=list)
    
    # Eidolon specific
    animation_url: Optional[str] = None  # 3D model IPFS
    background_color: str = "000000"
    
    def to_json(self) -> str:
        """Export as ERC-721 compliant JSON"""
        data = {
            "name": self.name,
            "description": self.description,
            "image": self.image,
            "external_url": self.external_url,
            "attributes": self.attributes,
        }
        if self.animation_url:
            data["animation_url"] = self.animation_url
        if self.background_color:
            data["background_color"] = self.background_color
        return json.dumps(data, indent=2)
    
    @classmethod
    def from_avatar_data(cls, avatar_data: Dict) -> 'AvatarNFTMetadata':
        """Create metadata from avatar generator data"""
        dna = avatar_data.get("dna", {})
        rarity = avatar_data.get("rarity", {})
        
        attributes = [
            {"trait_type": "Geometric Type", "value": dna.get("geometric_type", "Unknown")},
            {"trait_type": "Rarity Tier", "value": rarity.get("tier", "Common")},
            {"trait_type": "Rarity Score", "value": rarity.get("score", 0), "display_type": "number"},
            {"trait_type": "Generation", "value": avatar_data.get("generation", 1), "display_type": "number"},
            {"trait_type": "Complexity", "value": dna.get("complexity", 0), "display_type": "number"},
            {"trait_type": "Symmetry", "value": dna.get("symmetry", 0), "display_type": "number"},
        ]
        
        # Add color attributes
        colors = dna.get("colors", {})
        if colors:
            attributes.append({"trait_type": "Primary Color", "value": colors.get("primary", "#000000")})
            attributes.append({"trait_type": "Secondary Color", "value": colors.get("secondary", "#FFFFFF")})
        
        return cls(
            name=f"Eidolon Avatar #{avatar_data.get('avatar_id', 'Unknown')[:8]}",
            description=f"Quantum-generated 3D avatar from Eidolon vault. "
                       f"Rarity: {rarity.get('tier', 'Unknown')} ({rarity.get('score', 0):.2f})",
            image=avatar_data.get("preview_ipfs", ""),
            external_url=f"https://eidolon.io/avatar/{avatar_data.get('avatar_id', '')}",
            attributes=attributes,
            animation_url=avatar_data.get("model_ipfs"),
        )


@dataclass
class AvatarNFT:
    """Avatar NFT representation"""
    # Identifiers
    nft_id: str
    avatar_id: str
    vault_id: str
    
    # Token info
    token_id: Optional[int] = None  # On-chain token ID
    contract_address: Optional[str] = None
    
    # Chain info
    chain: str = "ethereum"  # ethereum or bsc
    network: str = "mainnet"
    chain_id: int = 1
    
    # Status
    status: str = "draft"
    
    # Ownership
    owner_address: Optional[str] = None
    origin_vault: int = 0
    is_genesis_avatar: bool = False
    
    # Metadata
    metadata_uri: Optional[str] = None
    metadata: Optional[Dict] = None
    
    # Blockchain data
    mint_txid: Optional[str] = None
    mint_block: Optional[int] = None
    minted_at: Optional[str] = None
    
    # Bridge data
    bridge_status: Optional[str] = None
    bridge_txid: Optional[str] = None
    source_chain: Optional[str] = None
    locked_at: Optional[str] = None
    
    # Timestamps
    created_at: str = ""
    updated_at: str = ""
    
    # Transfer history
    transfer_history: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AvatarNFT':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def get_chain_id(self) -> int:
        """Get the chain ID for this NFT"""
        if self.chain == "ethereum":
            return 1 if self.network == "mainnet" else 11155111
        elif self.chain == "bsc":
            return 56 if self.network == "mainnet" else 97
        return self.chain_id


@dataclass
class BridgeTransfer:
    """Cross-chain bridge transfer"""
    transfer_id: str
    nft_id: str
    avatar_id: str
    
    # Chains
    source_chain: str
    source_network: str
    dest_chain: str
    dest_network: str
    
    # Addresses
    from_address: str
    to_address: str
    
    # Status
    status: str = "initiated"
    
    # Transactions
    lock_txid: Optional[str] = None
    burn_txid: Optional[str] = None
    mint_txid: Optional[str] = None
    
    # Timestamps
    initiated_at: str = ""
    locked_at: Optional[str] = None
    burned_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Error handling
    error: Optional[str] = None
    retry_count: int = 0
    
    def __post_init__(self):
        if not self.initiated_at:
            self.initiated_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# AVATAR NFT COLLECTION
# ============================================================================

class AvatarNFTCollection:
    """
    Manages a collection of avatar NFTs for a vault.
    
    Features:
    - Store multiple avatars
    - Track active (equipped) avatar
    - Handle cross-chain NFTs
    - Prevent duplicates across chains
    """
    
    def __init__(self, vault_id: str, vault_number: int, owner_address: str, 
                 storage_dir: str = None):
        self.vault_id = vault_id
        self.vault_number = vault_number
        self.owner_address = owner_address
        
        # Storage
        if storage_dir is None:
            base_path = Path(__file__).parent.parent
            storage_dir = base_path / "alchemical_vault" / "avatar_collections"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Collection file
        self.collection_file = self.storage_dir / f"collection_{vault_id[:16]}.json"
        
        # Load or initialize
        self._load_collection()
    
    def _load_collection(self):
        """Load collection from disk"""
        if self.collection_file.exists():
            with open(self.collection_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.avatars: Dict[str, AvatarNFT] = {
                k: AvatarNFT.from_dict(v) for k, v in data.get("avatars", {}).items()
            }
            self.active_avatar_id = data.get("active_avatar_id")
            self.genesis_avatar_id = data.get("genesis_avatar_id")
            self.bridge_transfers: List[BridgeTransfer] = [
                BridgeTransfer(**t) for t in data.get("bridge_transfers", [])
            ]
        else:
            self.avatars = {}
            self.active_avatar_id = None
            self.genesis_avatar_id = None
            self.bridge_transfers = []
    
    def _save_collection(self):
        """Save collection to disk"""
        data = {
            "vault_id": self.vault_id,
            "vault_number": self.vault_number,
            "owner_address": self.owner_address,
            "active_avatar_id": self.active_avatar_id,
            "genesis_avatar_id": self.genesis_avatar_id,
            "avatars": {k: v.to_dict() for k, v in self.avatars.items()},
            "bridge_transfers": [t.to_dict() for t in self.bridge_transfers],
            "updated_at": datetime.utcnow().isoformat(),
        }
        with open(self.collection_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    # =========================================================================
    # COLLECTION MANAGEMENT
    # =========================================================================
    
    def add_avatar(self, avatar_data: Dict, is_genesis: bool = False,
                   chain: str = "ethereum", network: str = "mainnet") -> AvatarNFT:
        """
        Add a new avatar to the collection.
        
        Args:
            avatar_data: Avatar data from generator
            is_genesis: Is this the genesis avatar (created with vault)
            chain: Target blockchain
            network: Network type
        
        Returns:
            Created AvatarNFT
        """
        if len(self.avatars) >= MAX_AVATARS_PER_VAULT:
            raise ValueError(f"Maximum {MAX_AVATARS_PER_VAULT} avatars per vault")
        
        avatar_id = avatar_data.get("avatar_id", secrets.token_hex(16))
        nft_id = hashlib.sha256(f"{self.vault_id}:{avatar_id}:{chain}".encode()).hexdigest()[:32]
        
        # Create metadata
        metadata = AvatarNFTMetadata.from_avatar_data(avatar_data)
        
        # Determine chain ID
        chain_id = 1 if chain == "ethereum" else 56
        if network != "mainnet":
            chain_id = 11155111 if chain == "ethereum" else 97
        
        nft = AvatarNFT(
            nft_id=nft_id,
            avatar_id=avatar_id,
            vault_id=self.vault_id,
            chain=chain,
            network=network,
            chain_id=chain_id,
            owner_address=self.owner_address,
            origin_vault=self.vault_number,
            is_genesis_avatar=is_genesis,
            metadata=avatar_data,
            status="draft",
        )
        
        self.avatars[nft_id] = nft
        
        if is_genesis:
            self.genesis_avatar_id = nft_id
            self.active_avatar_id = nft_id
        
        self._save_collection()
        return nft
    
    def get_avatar(self, nft_id: str) -> Optional[AvatarNFT]:
        """Get avatar by NFT ID"""
        return self.avatars.get(nft_id)
    
    def get_active_avatar(self) -> Optional[AvatarNFT]:
        """Get the currently active (equipped) avatar"""
        if self.active_avatar_id:
            return self.avatars.get(self.active_avatar_id)
        return None
    
    def set_active_avatar(self, nft_id: str) -> bool:
        """Set the active avatar"""
        if nft_id not in self.avatars:
            return False
        
        avatar = self.avatars[nft_id]
        if avatar.status in ["bridging", "locked", "burned"]:
            return False
        
        self.active_avatar_id = nft_id
        self._save_collection()
        return True
    
    def list_avatars(self, chain: str = None, status: str = None) -> List[AvatarNFT]:
        """List avatars with optional filters"""
        result = list(self.avatars.values())
        
        if chain:
            result = [a for a in result if a.chain == chain]
        if status:
            result = [a for a in result if a.status == status]
        
        return result
    
    def get_avatar_count(self) -> Dict[str, int]:
        """Get avatar count by chain"""
        counts = {"ethereum": 0, "bsc": 0, "total": 0}
        for avatar in self.avatars.values():
            if avatar.status not in ["burned"]:
                counts[avatar.chain] = counts.get(avatar.chain, 0) + 1
                counts["total"] += 1
        return counts
    
    # =========================================================================
    # MINTING
    # =========================================================================
    
    def prepare_mint(self, nft_id: str) -> Dict:
        """
        Prepare mint transaction data.
        
        Returns transaction parameters for web3.
        """
        avatar = self.avatars.get(nft_id)
        if not avatar:
            raise ValueError(f"Avatar {nft_id} not found")
        
        if avatar.status != "draft":
            raise ValueError(f"Avatar already in status: {avatar.status}")
        
        # Get contract address
        chain_config = CONTRACTS.get(avatar.chain, {}).get(avatar.network, {})
        contract_address = chain_config.get("avatar_nft")
        
        if not contract_address:
            raise ValueError(f"No contract deployed on {avatar.chain}/{avatar.network}")
        
        # Prepare metadata URI (would upload to IPFS in production)
        metadata = AvatarNFTMetadata.from_avatar_data(avatar.metadata or {})
        
        # Generate mint parameters
        mint_params = {
            "contract": contract_address,
            "chain_id": avatar.chain_id,
            "function": "mint",
            "params": {
                "to": self.owner_address,
                "tokenURI": f"{METADATA_BASE_URI}{nft_id}/metadata.json",
            },
            "metadata": metadata.to_json(),
        }
        
        return mint_params
    
    def confirm_mint(self, nft_id: str, txid: str, token_id: int, 
                     block_number: int) -> AvatarNFT:
        """Confirm successful mint"""
        avatar = self.avatars.get(nft_id)
        if not avatar:
            raise ValueError(f"Avatar {nft_id} not found")
        
        avatar.status = "minted"
        avatar.mint_txid = txid
        avatar.token_id = token_id
        avatar.mint_block = block_number
        avatar.minted_at = datetime.utcnow().isoformat()
        avatar.updated_at = datetime.utcnow().isoformat()
        
        # Add to history
        avatar.transfer_history.append({
            "type": "mint",
            "txid": txid,
            "block": block_number,
            "chain": avatar.chain,
            "to": self.owner_address,
            "timestamp": avatar.minted_at,
        })
        
        self._save_collection()
        return avatar
    
    # =========================================================================
    # CROSS-CHAIN BRIDGE
    # =========================================================================
    
    def initiate_bridge(self, nft_id: str, dest_chain: str, 
                        dest_network: str = "mainnet") -> BridgeTransfer:
        """
        Initiate cross-chain bridge transfer.
        
        The avatar is locked on source chain, burned, then minted on dest chain.
        """
        avatar = self.avatars.get(nft_id)
        if not avatar:
            raise ValueError(f"Avatar {nft_id} not found")
        
        if avatar.status != "minted":
            raise ValueError(f"Can only bridge minted avatars, current status: {avatar.status}")
        
        if avatar.chain == dest_chain:
            raise ValueError(f"Avatar already on {dest_chain}")
        
        # Create bridge transfer
        transfer_id = secrets.token_hex(16)
        transfer = BridgeTransfer(
            transfer_id=transfer_id,
            nft_id=nft_id,
            avatar_id=avatar.avatar_id,
            source_chain=avatar.chain,
            source_network=avatar.network,
            dest_chain=dest_chain,
            dest_network=dest_network,
            from_address=self.owner_address,
            to_address=self.owner_address,
            status="initiated",
        )
        
        # Lock avatar
        avatar.status = "bridging"
        avatar.bridge_status = "initiated"
        avatar.locked_at = datetime.utcnow().isoformat()
        avatar.updated_at = datetime.utcnow().isoformat()
        
        self.bridge_transfers.append(transfer)
        self._save_collection()
        
        return transfer
    
    def get_bridge_lock_tx(self, transfer_id: str) -> Dict:
        """Get transaction data to lock avatar on source chain"""
        transfer = next((t for t in self.bridge_transfers if t.transfer_id == transfer_id), None)
        if not transfer:
            raise ValueError(f"Transfer {transfer_id} not found")
        
        avatar = self.avatars.get(transfer.nft_id)
        chain_config = CONTRACTS.get(transfer.source_chain, {}).get(transfer.source_network, {})
        
        return {
            "contract": chain_config.get("bridge"),
            "chain_id": avatar.chain_id if avatar else 1,
            "function": "lockForBridge",
            "params": {
                "tokenId": avatar.token_id if avatar else 0,
                "destChainId": 56 if transfer.dest_chain == "bsc" else 1,
                "recipient": transfer.to_address,
            }
        }
    
    def confirm_bridge_lock(self, transfer_id: str, txid: str) -> BridgeTransfer:
        """Confirm avatar locked on source chain"""
        transfer = next((t for t in self.bridge_transfers if t.transfer_id == transfer_id), None)
        if not transfer:
            raise ValueError(f"Transfer {transfer_id} not found")
        
        transfer.status = "source_locked"
        transfer.lock_txid = txid
        transfer.locked_at = datetime.utcnow().isoformat()
        
        avatar = self.avatars.get(transfer.nft_id)
        if avatar:
            avatar.bridge_status = "source_locked"
            avatar.bridge_txid = txid
            avatar.status = "locked"
        
        self._save_collection()
        return transfer
    
    def confirm_bridge_burn(self, transfer_id: str, txid: str) -> BridgeTransfer:
        """Confirm avatar burned on source chain"""
        transfer = next((t for t in self.bridge_transfers if t.transfer_id == transfer_id), None)
        if not transfer:
            raise ValueError(f"Transfer {transfer_id} not found")
        
        transfer.status = "source_burned"
        transfer.burn_txid = txid
        transfer.burned_at = datetime.utcnow().isoformat()
        
        self._save_collection()
        return transfer
    
    def complete_bridge(self, transfer_id: str, mint_txid: str, 
                        new_token_id: int) -> Tuple[BridgeTransfer, AvatarNFT]:
        """Complete bridge by minting on destination chain"""
        transfer = next((t for t in self.bridge_transfers if t.transfer_id == transfer_id), None)
        if not transfer:
            raise ValueError(f"Transfer {transfer_id} not found")
        
        avatar = self.avatars.get(transfer.nft_id)
        if not avatar:
            raise ValueError(f"Avatar not found")
        
        # Update transfer
        transfer.status = "completed"
        transfer.mint_txid = mint_txid
        transfer.completed_at = datetime.utcnow().isoformat()
        
        # Update avatar to new chain
        old_chain = avatar.chain
        avatar.chain = transfer.dest_chain
        avatar.network = transfer.dest_network
        avatar.chain_id = 56 if transfer.dest_chain == "bsc" else 1
        if transfer.dest_network != "mainnet":
            avatar.chain_id = 97 if transfer.dest_chain == "bsc" else 11155111
        
        avatar.token_id = new_token_id
        avatar.status = "minted"
        avatar.bridge_status = None
        avatar.source_chain = old_chain
        avatar.updated_at = datetime.utcnow().isoformat()
        
        # Add to history
        avatar.transfer_history.append({
            "type": "bridge",
            "transfer_id": transfer_id,
            "from_chain": old_chain,
            "to_chain": transfer.dest_chain,
            "txid": mint_txid,
            "new_token_id": new_token_id,
            "timestamp": transfer.completed_at,
        })
        
        self._save_collection()
        return transfer, avatar
    
    def cancel_bridge(self, transfer_id: str, reason: str = "cancelled") -> BridgeTransfer:
        """Cancel a bridge transfer (if not yet burned)"""
        transfer = next((t for t in self.bridge_transfers if t.transfer_id == transfer_id), None)
        if not transfer:
            raise ValueError(f"Transfer {transfer_id} not found")
        
        if transfer.status in ["source_burned", "completed"]:
            raise ValueError("Cannot cancel: avatar already burned or bridged")
        
        transfer.status = "failed"
        transfer.error = reason
        
        avatar = self.avatars.get(transfer.nft_id)
        if avatar:
            avatar.status = "minted"
            avatar.bridge_status = None
            avatar.locked_at = None
        
        self._save_collection()
        return transfer
    
    # =========================================================================
    # TRANSFER (same chain)
    # =========================================================================
    
    def prepare_transfer(self, nft_id: str, to_address: str) -> Dict:
        """Prepare same-chain transfer"""
        avatar = self.avatars.get(nft_id)
        if not avatar:
            raise ValueError(f"Avatar {nft_id} not found")
        
        if avatar.status != "minted":
            raise ValueError(f"Can only transfer minted avatars")
        
        chain_config = CONTRACTS.get(avatar.chain, {}).get(avatar.network, {})
        
        return {
            "contract": chain_config.get("avatar_nft"),
            "chain_id": avatar.chain_id,
            "function": "transferFrom",
            "params": {
                "from": self.owner_address,
                "to": to_address,
                "tokenId": avatar.token_id,
            }
        }
    
    def confirm_transfer(self, nft_id: str, txid: str, new_owner: str) -> AvatarNFT:
        """Confirm transfer completed"""
        avatar = self.avatars.get(nft_id)
        if not avatar:
            raise ValueError(f"Avatar {nft_id} not found")
        
        avatar.transfer_history.append({
            "type": "transfer",
            "txid": txid,
            "from": self.owner_address,
            "to": new_owner,
            "chain": avatar.chain,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Remove from collection if transferred out
        if new_owner.lower() != self.owner_address.lower():
            del self.avatars[nft_id]
            if self.active_avatar_id == nft_id:
                self.active_avatar_id = None
        
        self._save_collection()
        return avatar
    
    # =========================================================================
    # RECEIVE (from another vault/address)
    # =========================================================================
    
    def receive_avatar(self, avatar_data: Dict, from_address: str, 
                       txid: str, token_id: int, chain: str, 
                       network: str = "mainnet") -> AvatarNFT:
        """Receive an avatar transferred from another address"""
        if len(self.avatars) >= MAX_AVATARS_PER_VAULT:
            raise ValueError(f"Maximum {MAX_AVATARS_PER_VAULT} avatars per vault")
        
        avatar_id = avatar_data.get("avatar_id", secrets.token_hex(16))
        nft_id = hashlib.sha256(f"{self.vault_id}:{avatar_id}:{chain}".encode()).hexdigest()[:32]
        
        chain_id = 1 if chain == "ethereum" else 56
        if network != "mainnet":
            chain_id = 11155111 if chain == "ethereum" else 97
        
        nft = AvatarNFT(
            nft_id=nft_id,
            avatar_id=avatar_id,
            vault_id=self.vault_id,
            token_id=token_id,
            chain=chain,
            network=network,
            chain_id=chain_id,
            owner_address=self.owner_address,
            origin_vault=avatar_data.get("origin_vault", 0),
            is_genesis_avatar=False,
            metadata=avatar_data,
            status="minted",
            mint_txid=txid,
            minted_at=datetime.utcnow().isoformat(),
            transfer_history=[{
                "type": "receive",
                "txid": txid,
                "from": from_address,
                "to": self.owner_address,
                "chain": chain,
                "timestamp": datetime.utcnow().isoformat(),
            }]
        )
        
        self.avatars[nft_id] = nft
        self._save_collection()
        return nft
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_collection_stats(self) -> Dict:
        """Get collection statistics"""
        stats = {
            "vault_id": self.vault_id,
            "vault_number": self.vault_number,
            "total_avatars": len(self.avatars),
            "by_chain": {"ethereum": 0, "bsc": 0},
            "by_status": {},
            "genesis_avatar": self.genesis_avatar_id,
            "active_avatar": self.active_avatar_id,
            "bridge_transfers": len(self.bridge_transfers),
            "pending_bridges": len([t for t in self.bridge_transfers if t.status not in ["completed", "failed"]]),
        }
        
        for avatar in self.avatars.values():
            stats["by_chain"][avatar.chain] = stats["by_chain"].get(avatar.chain, 0) + 1
            stats["by_status"][avatar.status] = stats["by_status"].get(avatar.status, 0) + 1
        
        return stats


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_genesis_avatar(vault_id: str, vault_number: int, 
                          owner_address: str, avatar_data: Dict,
                          chain: str = "ethereum", 
                          network: str = "mainnet") -> Tuple[AvatarNFTCollection, AvatarNFT]:
    """
    Create a genesis avatar for a new vault.
    Called during vault creation.
    
    Returns:
        (collection, genesis_avatar)
    """
    collection = AvatarNFTCollection(vault_id, vault_number, owner_address)
    genesis_avatar = collection.add_avatar(
        avatar_data=avatar_data,
        is_genesis=True,
        chain=chain,
        network=network
    )
    
    return collection, genesis_avatar


def load_collection(vault_id: str, vault_number: int = 0, 
                    owner_address: str = "") -> AvatarNFTCollection:
    """Load existing collection for a vault"""
    return AvatarNFTCollection(vault_id, vault_number, owner_address)


# ============================================================================
# SMART CONTRACT ABI (for reference)
# ============================================================================

AVATAR_NFT_ABI = [
    {
        "name": "mint",
        "type": "function",
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "tokenURI", "type": "string"}
        ],
        "outputs": [{"name": "tokenId", "type": "uint256"}]
    },
    {
        "name": "transferFrom",
        "type": "function",
        "inputs": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "tokenId", "type": "uint256"}
        ]
    },
    {
        "name": "tokenURI",
        "type": "function",
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "string"}]
    },
    {
        "name": "ownerOf",
        "type": "function", 
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "address"}]
    }
]

BRIDGE_ABI = [
    {
        "name": "lockForBridge",
        "type": "function",
        "inputs": [
            {"name": "tokenId", "type": "uint256"},
            {"name": "destChainId", "type": "uint256"},
            {"name": "recipient", "type": "address"}
        ]
    },
    {
        "name": "mintFromBridge",
        "type": "function",
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "tokenURI", "type": "string"},
            {"name": "sourceChainId", "type": "uint256"},
            {"name": "sourceTokenId", "type": "uint256"}
        ],
        "outputs": [{"name": "tokenId", "type": "uint256"}]
    }
]


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  AVATAR NFT COLLECTION - Test")
    print("=" * 60)
    
    # Create test collection
    vault_id = "test_vault_" + secrets.token_hex(8)
    vault_number = 1
    owner = "0x" + secrets.token_hex(20)
    
    print(f"\n  Vault ID: {vault_id}")
    print(f"  Owner: {owner}")
    
    # Create genesis avatar
    avatar_data = {
        "avatar_id": secrets.token_hex(16),
        "dna": {
            "geometric_type": "Icosahedron",
            "complexity": 0.85,
            "symmetry": 0.92,
            "colors": {"primary": "#FF5500", "secondary": "#0055FF"}
        },
        "rarity": {
            "tier": "Legendary",
            "score": 0.95
        },
        "generation": 1,
    }
    
    collection, genesis = create_genesis_avatar(
        vault_id, vault_number, owner, avatar_data,
        chain="ethereum", network="mainnet"
    )
    
    print(f"\n  Genesis Avatar: {genesis.nft_id[:16]}...")
    print(f"  Chain: {genesis.chain}")
    print(f"  Status: {genesis.status}")
    
    # Add another avatar
    avatar_data_2 = {
        "avatar_id": secrets.token_hex(16),
        "dna": {"geometric_type": "Dodecahedron", "complexity": 0.75},
        "rarity": {"tier": "Epic", "score": 0.80},
        "generation": 1,
    }
    
    avatar2 = collection.add_avatar(avatar_data_2, chain="bsc")
    print(f"\n  Second Avatar: {avatar2.nft_id[:16]}...")
    print(f"  Chain: {avatar2.chain}")
    
    # Stats
    stats = collection.get_collection_stats()
    print(f"\n  Collection Stats:")
    print(f"    Total: {stats['total_avatars']}")
    print(f"    By chain: {stats['by_chain']}")
    print(f"    Genesis: {stats['genesis_avatar'][:16]}..." if stats['genesis_avatar'] else "    Genesis: None")
    
    print("\n  Test completed!")
