#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    BITCOIN ASSET BRIDGE - Eidolon                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Bridge to transfer all game assets to Bitcoin blockchain:                   ║
║  - Alchemical Items                                                          ║
║  - Combat Equipment (Weapons, Armor, Accessories)                            ║
║  - Gems                                                                      ║
║  - Fragments                                                                 ║
║  - Philosopher Stones                                                        ║
║  - Artifacts                                                                 ║
║                                                                              ║
║  SUPPORTED PROTOCOLS:                                                        ║
║  - Runes (fungible/semi-fungible tokens)                                     ║
║  - Ordinals (NFT inscriptions)                                               ║
║  - OP_RETURN (on-chain metadata)                                             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import hashlib
import secrets
import struct
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ============================================================================
# CONSTANTS
# ============================================================================

PSNX_PROTOCOL_PREFIX = b'EIDL'  # Eidolon prefix
PSNX_VERSION = 2

# Magic numbers for each asset type
ASSET_MAGIC = {
    "item": 0x4954454D,       # "ITEM"
    "equipment": 0x45515549,  # "EQUI"
    "weapon": 0x5745504E,     # "WEPN"
    "armor": 0x41524D52,      # "ARMR"
    "accessory": 0x41434353,  # "ACCS"
    "gem": 0x47454D53,        # "GEMS"
    "fragment": 0x46524147,   # "FRAG"
    "stone": 0x53544F4E,      # "STON"
    "artifact": 0x41525446,   # "ARTF"
}

# Fees (in satoshis)
MIN_INSCRIPTION_FEE = 10000
MIN_TRANSFER_FEE = 5000
DUST_LIMIT = 546

# Size limits
MAX_OP_RETURN_SIZE = 80
MAX_INSCRIPTION_SIZE = 400000


# ============================================================================
# ENUMERATIONS
# ============================================================================

class AssetType(Enum):
    """Transferable asset types"""
    ITEM = ("item", "ITEM", "Alchemical Item")
    EQUIPMENT = ("equipment", "EQUI", "Combat Equipment")
    WEAPON = ("weapon", "WEPN", "Weapon")
    ARMOR = ("armor", "ARMR", "Armor")
    ACCESSORY = ("accessory", "ACCS", "Accessory")
    GEM = ("gem", "GEM", "Gem")
    FRAGMENT = ("fragment", "FRAG", "Fragment")
    STONE = ("stone", "STON", "Philosopher Stone")
    ARTIFACT = ("artifact", "ARTF", "Artifact")
    
    def __init__(self, type_id: str, code: str, display: str):
        self.type_id = type_id
        self.code = code
        self.display = display


class TransferStatus(Enum):
    """Transfer status"""
    PENDING = "pending"
    BROADCAST = "broadcast"
    CONFIRMING = "confirming"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class InscriptionType(Enum):
    """Bitcoin inscription type"""
    OP_RETURN = "op_return"
    ORDINAL = "ordinal"
    RUNE = "rune"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class AssetOnChain:
    """On-chain asset representation"""
    asset_id: str
    asset_type: str
    rune_id: str
    
    # Metadata
    name: str
    rarity: str
    power: float
    metadata: Dict = field(default_factory=dict)
    
    # Blockchain
    inscription_txid: Optional[str] = None
    inscription_type: str = "rune"
    block_height: Optional[int] = None
    confirmations: int = 0
    
    # Ownership
    owner_address: Optional[str] = None
    owner_vault: Optional[int] = None
    
    # Status
    status: str = "pending"
    created_at: str = ""
    inscribed_at: Optional[str] = None
    
    # History
    transfer_history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AssetOnChain':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TransferRequest:
    """Asset transfer request"""
    transfer_id: str
    asset_id: str
    asset_type: str
    rune_id: str
    
    from_address: str
    to_address: str
    from_vault: Optional[int] = None
    to_vault: Optional[int] = None
    
    fee_sats: int = MIN_TRANSFER_FEE
    priority: str = "normal"
    
    status: str = "pending"
    txid: Optional[str] = None
    created_at: str = ""
    broadcast_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    
    op_return_data: Optional[bytes] = None
    raw_tx: Optional[str] = None
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        if d.get('op_return_data'):
            d['op_return_data'] = d['op_return_data'].hex()
        return d


# ============================================================================
# RUNE ID GENERATOR
# ============================================================================

class RuneIdGenerator:
    """Generates unique Rune IDs for Eidolon assets"""
    
    CATEGORY_CODES = {
        "item": "ITM",
        "equipment": "EQP",
        "weapon": "WPN",
        "armor": "ARM",
        "accessory": "ACC",
        "gem": "GEM",
        "fragment": "FRG",
        "stone": "STN",
        "artifact": "ART",
    }
    
    RARITY_CODES = {
        # Combat equipment rarities
        "genesis": "G",
        "primordial": "P",
        "ascendant": "A",
        "mythic": "Y",
        "legendary": "L",
        "elite": "E",
        "superior": "S",
        "enhanced": "N",
        "common": "C",
        "fractured": "F",
        # Legacy rarities
        "divine": "D",
        "transcendent": "T",
        "mythical": "M",
        "masterwork": "W",
        "exquisite": "X",
        "refined": "R",
        "crude": "U",
    }
    
    @classmethod
    def generate(cls, asset_type: str, asset_id: str, 
                 rarity: str = "common", sub_type: str = None) -> str:
        """
        Generate unique Rune ID.
        Format: EIDL.CATEGORY.RARITY.SUBTYPE.UNIQUE
        """
        cat_code = cls.CATEGORY_CODES.get(asset_type, "UNK")
        rarity_code = cls.RARITY_CODES.get(rarity.lower(), "C")
        sub_code = (sub_type[:3].upper() if sub_type else "GEN")
        
        unique_hash = hashlib.sha256(
            f"{asset_id}{datetime.now().isoformat()}{secrets.token_hex(4)}".encode()
        ).hexdigest()[:8].upper()
        
        return f"EIDL.{cat_code}.{rarity_code}.{sub_code}.{unique_hash}"


# ============================================================================
# BITCOIN ASSET BRIDGE
# ============================================================================

class BitcoinAssetBridge:
    """
    Bridge to transfer game assets to Bitcoin blockchain.
    """
    
    def __init__(self, data_dir: str = None):
        base_path = Path(__file__).parent.parent
        self.data_dir = Path(data_dir) if data_dir else base_path / "bitcoin_assets"
        
        self.assets_dir = self.data_dir / "assets"
        self.transfers_dir = self.data_dir / "transfers"
        self.pending_dir = self.data_dir / "pending"
        
        for d in [self.assets_dir, self.transfers_dir, self.pending_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        self._assets: Dict[str, AssetOnChain] = {}
        self._load_assets()
    
    def _load_assets(self):
        """Load assets from disk."""
        for file in self.assets_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                asset = AssetOnChain.from_dict(data)
                self._assets[asset.asset_id] = asset
            except Exception as e:
                print(f"[WARN] Cannot load asset {file}: {e}")
    
    def _save_asset(self, asset: AssetOnChain):
        """Save an asset."""
        file_path = self.assets_dir / f"{asset.asset_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(asset.to_dict(), f, indent=2, ensure_ascii=False)
        self._assets[asset.asset_id] = asset
    
    def _save_transfer(self, transfer: TransferRequest):
        """Save a transfer request."""
        file_path = self.transfers_dir / f"{transfer.transfer_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(transfer.to_dict(), f, indent=2, ensure_ascii=False)
    
    # ========================================================================
    # ASSET INSCRIPTION
    # ========================================================================
    
    def inscribe_item(self, item_data: Dict, owner_address: str,
                      owner_vault: int = None) -> AssetOnChain:
        """Inscribe an alchemical item on Bitcoin."""
        return self._inscribe_asset(
            asset_type="item",
            asset_id=item_data.get('item_id', item_data.get('id', secrets.token_hex(8))),
            name=item_data.get('display_name', item_data.get('item_type', 'Unknown Item')),
            rarity=item_data.get('rarity', 'common'),
            power=item_data.get('stat_power', item_data.get('power', 0)),
            sub_type=item_data.get('category', 'misc')[:3],
            metadata=item_data,
            owner_address=owner_address,
            owner_vault=owner_vault
        )
    
    def inscribe_equipment(self, equip_data: Dict, owner_address: str,
                           owner_vault: int = None) -> AssetOnChain:
        """Inscribe combat equipment on Bitcoin."""
        # Determine equipment category
        slot = equip_data.get('slot', '')
        if slot in ['main_hand', 'off_hand', 'two_hand']:
            asset_type = "weapon"
            sub_type = equip_data.get('equipment_class', 'wpn')[:3]
        elif slot in ['head', 'chest', 'hands', 'legs', 'feet', 'back']:
            asset_type = "armor"
            sub_type = slot[:3]
        elif slot in ['neck', 'ring_1', 'ring_2', 'trinket']:
            asset_type = "accessory"
            sub_type = slot[:3]
        else:
            asset_type = "equipment"
            sub_type = "gen"
        
        # Calculate power from combat stats
        power = (
            equip_data.get('physical_damage', 0) +
            equip_data.get('magical_damage', 0) +
            equip_data.get('defense', 0) * 2 +
            equip_data.get('health', 0) / 10
        )
        
        return self._inscribe_asset(
            asset_type=asset_type,
            asset_id=equip_data.get('item_id', secrets.token_hex(8)),
            name=equip_data.get('name', 'Unknown Equipment'),
            rarity=equip_data.get('rarity', 'common'),
            power=power,
            sub_type=sub_type,
            metadata=equip_data,
            owner_address=owner_address,
            owner_vault=owner_vault
        )
    
    def inscribe_weapon(self, weapon_data: Dict, owner_address: str,
                        owner_vault: int = None) -> AssetOnChain:
        """Inscribe a weapon on Bitcoin."""
        power = (
            weapon_data.get('physical_damage', 0) +
            weapon_data.get('magical_damage', 0) +
            weapon_data.get('critical_chance', 0) * 100
        )
        return self._inscribe_asset(
            asset_type="weapon",
            asset_id=weapon_data.get('item_id', secrets.token_hex(8)),
            name=weapon_data.get('name', 'Unknown Weapon'),
            rarity=weapon_data.get('rarity', 'common'),
            power=power,
            sub_type=weapon_data.get('equipment_class', 'wpn')[:3],
            metadata=weapon_data,
            owner_address=owner_address,
            owner_vault=owner_vault
        )
    
    def inscribe_armor(self, armor_data: Dict, owner_address: str,
                       owner_vault: int = None) -> AssetOnChain:
        """Inscribe armor on Bitcoin."""
        power = (
            armor_data.get('defense', 0) * 2 +
            armor_data.get('health', 0) / 5 +
            armor_data.get('evasion', 0) * 50
        )
        return self._inscribe_asset(
            asset_type="armor",
            asset_id=armor_data.get('item_id', secrets.token_hex(8)),
            name=armor_data.get('name', 'Unknown Armor'),
            rarity=armor_data.get('rarity', 'common'),
            power=power,
            sub_type=armor_data.get('slot', 'arm')[:3],
            metadata=armor_data,
            owner_address=owner_address,
            owner_vault=owner_vault
        )
    
    def inscribe_accessory(self, acc_data: Dict, owner_address: str,
                           owner_vault: int = None) -> AssetOnChain:
        """Inscribe an accessory on Bitcoin."""
        power = sum(acc_data.get('base_stats', {}).values()) * 10
        return self._inscribe_asset(
            asset_type="accessory",
            asset_id=acc_data.get('item_id', secrets.token_hex(8)),
            name=acc_data.get('name', 'Unknown Accessory'),
            rarity=acc_data.get('rarity', 'common'),
            power=power,
            sub_type=acc_data.get('slot', 'acc')[:3],
            metadata=acc_data,
            owner_address=owner_address,
            owner_vault=owner_vault
        )
    
    def inscribe_gem(self, gem_data: Dict, owner_address: str,
                     owner_vault: int = None) -> AssetOnChain:
        """Inscribe a gem on Bitcoin."""
        return self._inscribe_asset(
            asset_type="gem",
            asset_id=gem_data.get('gem_id', secrets.token_hex(8)),
            name=gem_data.get('name', 'Unknown Gem'),
            rarity=gem_data.get('rarity', 'common'),
            power=gem_data.get('power', 0),
            sub_type=gem_data.get('gem_type', 'gen')[:3],
            metadata=gem_data,
            owner_address=owner_address,
            owner_vault=owner_vault
        )
    
    def inscribe_fragment(self, fragment_data: Dict, owner_address: str,
                          owner_vault: int = None) -> AssetOnChain:
        """Inscribe a fragment on Bitcoin."""
        return self._inscribe_asset(
            asset_type="fragment",
            asset_id=fragment_data.get('fragment_id', secrets.token_hex(8)),
            name=fragment_data.get('name', 'Unknown Fragment'),
            rarity=self._fragment_rarity(fragment_data.get('purity', 50)),
            power=fragment_data.get('mass', 0),
            sub_type=fragment_data.get('essence', 'gen')[:3],
            metadata=fragment_data,
            owner_address=owner_address,
            owner_vault=owner_vault
        )
    
    def inscribe_stone(self, stone_data: Dict, owner_address: str,
                       owner_vault: int = None) -> AssetOnChain:
        """Inscribe a Philosopher Stone on Bitcoin."""
        return self._inscribe_asset(
            asset_type="stone",
            asset_id=stone_data.get('stone_id', secrets.token_hex(8)),
            name=f"Philosopher Stone #{stone_data.get('origin_vault', 0)}",
            rarity="genesis",
            power=stone_data.get('max_energy', 1000),
            sub_type=stone_data.get('state', 'dor')[:3],
            metadata=stone_data,
            owner_address=owner_address,
            owner_vault=owner_vault
        )
    
    def inscribe_artifact(self, artifact_data: Dict, owner_address: str,
                          owner_vault: int = None) -> AssetOnChain:
        """Inscribe an artifact on Bitcoin."""
        return self._inscribe_asset(
            asset_type="artifact",
            asset_id=artifact_data.get('artifact_id', secrets.token_hex(8)),
            name=artifact_data.get('name', 'Unknown Artifact'),
            rarity=artifact_data.get('rarity', 'common'),
            power=artifact_data.get('power', 0),
            sub_type=artifact_data.get('artifact_type', 'gen')[:3],
            metadata=artifact_data,
            owner_address=owner_address,
            owner_vault=owner_vault
        )
    
    def _inscribe_asset(self, asset_type: str, asset_id: str, name: str,
                        rarity: str, power: float, sub_type: str,
                        metadata: Dict, owner_address: str,
                        owner_vault: int = None) -> AssetOnChain:
        """Internal method to inscribe an asset."""
        rune_id = RuneIdGenerator.generate(asset_type, asset_id, rarity, sub_type)
        
        asset = AssetOnChain(
            asset_id=asset_id,
            asset_type=asset_type,
            rune_id=rune_id,
            name=name,
            rarity=rarity,
            power=power,
            metadata=metadata,
            owner_address=owner_address,
            owner_vault=owner_vault,
            status="pending",
            created_at=datetime.now().isoformat()
        )
        
        self._save_asset(asset)
        return asset
    
    def confirm_inscription(self, asset_id: str, txid: str,
                           block_height: int = None) -> bool:
        """Confirm inscription after broadcast."""
        asset = self._assets.get(asset_id)
        if not asset:
            return False
        
        asset.inscription_txid = txid
        asset.block_height = block_height
        asset.status = "inscribed"
        asset.inscribed_at = datetime.now().isoformat()
        
        self._save_asset(asset)
        return True
    
    # ========================================================================
    # TRANSFERS
    # ========================================================================
    
    def transfer_asset(self, asset_id: str, 
                       from_address: str, to_address: str,
                       from_vault: int = None, to_vault: int = None,
                       priority: str = "normal") -> TransferRequest:
        """Initiate asset transfer to another Bitcoin address."""
        asset = self._assets.get(asset_id)
        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")
        
        if asset.status != "inscribed":
            raise ValueError(f"Asset not inscribed: status is {asset.status}")
        
        if asset.owner_address and asset.owner_address != from_address:
            raise ValueError("Not owner of this asset")
        
        if not self._is_valid_address(from_address):
            raise ValueError("Invalid source address")
        if not self._is_valid_address(to_address):
            raise ValueError("Invalid destination address")
        
        fee_sats = self._calculate_fee(priority)
        op_return_data = self._generate_transfer_op_return(
            asset.asset_type, asset.rune_id, to_address
        )
        
        transfer_id = secrets.token_hex(8)
        transfer = TransferRequest(
            transfer_id=transfer_id,
            asset_id=asset_id,
            asset_type=asset.asset_type,
            rune_id=asset.rune_id,
            from_address=from_address,
            from_vault=from_vault,
            to_address=to_address,
            to_vault=to_vault,
            fee_sats=fee_sats,
            priority=priority,
            status="pending",
            created_at=datetime.now().isoformat(),
            op_return_data=op_return_data
        )
        
        asset.status = "transferring"
        asset.transfer_history.append({
            "type": "transfer",
            "transfer_id": transfer_id,
            "from_address": from_address,
            "to_address": to_address,
            "initiated_at": datetime.now().isoformat(),
            "status": "pending"
        })
        
        self._save_asset(asset)
        self._save_transfer(transfer)
        
        return transfer
    
    def confirm_transfer(self, transfer_id: str, txid: str,
                        block_height: int = None) -> bool:
        """Confirm transfer after broadcast."""
        transfer_file = self.transfers_dir / f"{transfer_id}.json"
        if not transfer_file.exists():
            return False
        
        with open(transfer_file, 'r', encoding='utf-8') as f:
            transfer_data = json.load(f)
        
        transfer_data['status'] = "confirmed"
        transfer_data['txid'] = txid
        transfer_data['confirmed_at'] = datetime.now().isoformat()
        
        with open(transfer_file, 'w', encoding='utf-8') as f:
            json.dump(transfer_data, f, indent=2)
        
        asset = self._assets.get(transfer_data['asset_id'])
        if asset:
            asset.owner_address = transfer_data['to_address']
            asset.owner_vault = transfer_data.get('to_vault')
            asset.status = "inscribed"
            
            if asset.transfer_history:
                asset.transfer_history[-1]['status'] = "confirmed"
                asset.transfer_history[-1]['txid'] = txid
                asset.transfer_history[-1]['confirmed_at'] = datetime.now().isoformat()
            
            self._save_asset(asset)
        
        return True
    
    # ========================================================================
    # BATCH OPERATIONS
    # ========================================================================
    
    def inscribe_vault_items(self, vault_number: int, owner_address: str,
                             items_path: Path = None) -> List[AssetOnChain]:
        """Inscribe all items from a vault."""
        if items_path is None:
            base_path = Path(__file__).parent.parent
            items_path = base_path / "alchemical_vault" / "items"
        
        inscribed = []
        for item_file in items_path.glob("item_*.json"):
            try:
                with open(item_file, 'r', encoding='utf-8') as f:
                    item_data = json.load(f)
                
                if item_data.get('current_vault') == vault_number:
                    asset = self.inscribe_item(item_data, owner_address, vault_number)
                    inscribed.append(asset)
            except Exception as e:
                print(f"[WARN] Failed to inscribe {item_file}: {e}")
        
        return inscribed
    
    def inscribe_vault_equipment(self, vault_number: int, owner_address: str,
                                  equipment_path: Path = None) -> List[AssetOnChain]:
        """Inscribe all combat equipment from a vault."""
        if equipment_path is None:
            base_path = Path(__file__).parent.parent
            equipment_path = base_path / "alchemical_vault" / "combat_equipment"
        
        inscribed = []
        for equip_file in equipment_path.glob("combat_equip_*.json"):
            try:
                with open(equip_file, 'r', encoding='utf-8') as f:
                    equip_data = json.load(f)
                
                if equip_data.get('current_vault') == vault_number:
                    asset = self.inscribe_equipment(equip_data, owner_address, vault_number)
                    inscribed.append(asset)
            except Exception as e:
                print(f"[WARN] Failed to inscribe {equip_file}: {e}")
        
        return inscribed
    
    def inscribe_all_vault_assets(self, vault_number: int, 
                                   owner_address: str) -> Dict[str, List[AssetOnChain]]:
        """Inscribe all assets from a vault."""
        base_path = Path(__file__).parent.parent / "alchemical_vault"
        
        results = {
            "items": self.inscribe_vault_items(vault_number, owner_address),
            "equipment": self.inscribe_vault_equipment(vault_number, owner_address),
            "gems": [],
            "stones": [],
            "artifacts": [],
        }
        
        # Gems
        gems_path = base_path / "gems"
        if gems_path.exists():
            for gem_file in gems_path.glob("*.json"):
                try:
                    with open(gem_file, 'r', encoding='utf-8') as f:
                        gem_data = json.load(f)
                    if gem_data.get('vault_number') == vault_number:
                        asset = self.inscribe_gem(gem_data, owner_address, vault_number)
                        results["gems"].append(asset)
                except:
                    pass
        
        # Stones
        stones_path = base_path / "philosopher_stones"
        if stones_path.exists():
            for stone_file in stones_path.glob("*.json"):
                try:
                    with open(stone_file, 'r', encoding='utf-8') as f:
                        stone_data = json.load(f)
                    if stone_data.get('vault_number') == vault_number:
                        asset = self.inscribe_stone(stone_data, owner_address, vault_number)
                        results["stones"].append(asset)
                except:
                    pass
        
        # Artifacts
        artifacts_path = base_path / "artifacts"
        if artifacts_path.exists():
            for artifact_file in artifacts_path.glob("*.json"):
                try:
                    with open(artifact_file, 'r', encoding='utf-8') as f:
                        artifact_data = json.load(f)
                    if artifact_data.get('vault_number') == vault_number:
                        asset = self.inscribe_artifact(artifact_data, owner_address, vault_number)
                        results["artifacts"].append(asset)
                except:
                    pass
        
        return results
    
    # ========================================================================
    # QUERIES
    # ========================================================================
    
    def get_asset(self, asset_id: str) -> Optional[AssetOnChain]:
        """Get asset by ID."""
        return self._assets.get(asset_id)
    
    def get_asset_by_rune(self, rune_id: str) -> Optional[AssetOnChain]:
        """Get asset by Rune ID."""
        for asset in self._assets.values():
            if asset.rune_id == rune_id:
                return asset
        return None
    
    def get_assets_by_address(self, address: str) -> List[AssetOnChain]:
        """Get all assets owned by an address."""
        return [a for a in self._assets.values() if a.owner_address == address]
    
    def get_assets_by_vault(self, vault_number: int) -> List[AssetOnChain]:
        """Get all assets from a vault."""
        return [a for a in self._assets.values() if a.owner_vault == vault_number]
    
    def get_assets_by_type(self, asset_type: str) -> List[AssetOnChain]:
        """Get all assets of a type."""
        return [a for a in self._assets.values() if a.asset_type == asset_type]
    
    def get_equipment_by_vault(self, vault_number: int) -> List[AssetOnChain]:
        """Get all equipment from a vault."""
        equipment_types = ["equipment", "weapon", "armor", "accessory"]
        return [a for a in self._assets.values() 
                if a.owner_vault == vault_number and a.asset_type in equipment_types]
    
    def get_pending_transfers(self) -> List[Dict]:
        """Get pending transfers."""
        pending = []
        for file in self.transfers_dir.glob("*.json"):
            with open(file, 'r', encoding='utf-8') as f:
                transfer = json.load(f)
            if transfer.get('status') == 'pending':
                pending.append(transfer)
        return pending
    
    def get_statistics(self) -> Dict:
        """Global statistics."""
        assets = list(self._assets.values())
        
        by_type = {}
        for t in AssetType:
            by_type[t.type_id] = len([a for a in assets if a.asset_type == t.type_id])
        
        inscribed = len([a for a in assets if a.status == "inscribed"])
        pending = len([a for a in assets if a.status == "pending"])
        
        return {
            "total_assets": len(assets),
            "inscribed": inscribed,
            "pending": pending,
            "by_type": by_type,
            "unique_owners": len(set(a.owner_address for a in assets if a.owner_address))
        }
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def _generate_transfer_op_return(self, asset_type: str, 
                                      rune_id: str, to_address: str) -> bytes:
        """Generate OP_RETURN data for transfer."""
        data = PSNX_PROTOCOL_PREFIX
        data += struct.pack('>B', PSNX_VERSION)
        data += struct.pack('>I', ASSET_MAGIC.get(asset_type, 0))
        data += rune_id.encode('utf-8')[:32].ljust(32, b'\x00')
        data += hashlib.sha256(to_address.encode()).digest()[:20]
        return data
    
    def _is_valid_address(self, address: str) -> bool:
        """Validate Bitcoin address."""
        if not address:
            return False
        if address.startswith('1') and 26 <= len(address) <= 35:
            return True
        if address.startswith('3') and 26 <= len(address) <= 35:
            return True
        if address.startswith('bc1') and 42 <= len(address) <= 62:
            return True
        return False
    
    def _calculate_fee(self, priority: str) -> int:
        """Calculate fee based on priority."""
        if priority == "low":
            return MIN_TRANSFER_FEE
        elif priority == "high":
            return MIN_TRANSFER_FEE * 3
        return MIN_TRANSFER_FEE * 2
    
    def _fragment_rarity(self, purity: float) -> str:
        """Determine fragment rarity from purity."""
        if purity >= 99:
            return "genesis"
        elif purity >= 95:
            return "mythic"
        elif purity >= 90:
            return "legendary"
        elif purity >= 80:
            return "elite"
        elif purity >= 70:
            return "superior"
        elif purity >= 50:
            return "enhanced"
        return "common"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_rune_id(rune_id: str) -> str:
    """Format Rune ID for display."""
    parts = rune_id.split('.')
    if len(parts) >= 5:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.{parts[3]}.{parts[4][:4]}..."
    return rune_id


def parse_rune_id(rune_id: str) -> Dict:
    """Parse Rune ID components."""
    parts = rune_id.split('.')
    if len(parts) < 5:
        return {"valid": False}
    
    return {
        "valid": True,
        "prefix": parts[0],
        "category": parts[1],
        "rarity": parts[2],
        "sub_type": parts[3],
        "unique": parts[4]
    }
