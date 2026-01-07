#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         BITCOIN ASSET BRIDGE - Poly-Spinor Nexus 7D                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Pont unifie pour transferer tous les actifs du jeu sur Bitcoin:            ║
║  - Items alchimiques                                                         ║
║  - Gemmes                                                                    ║
║  - Fragments                                                                 ║
║  - Pierres Philosophales                                                     ║
║  - Artefacts                                                                 ║
║                                                                              ║
║  PROTOCOLES SUPPORTES:                                                       ║
║  - Runes (tokens fongibles/semi-fongibles)                                   ║
║  - Ordinals (inscriptions NFT)                                               ║
║  - OP_RETURN (metadata on-chain)                                             ║
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
from typing import Optional, Dict, List, Any, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ============================================================================
# CONSTANTES
# ============================================================================

# Prefixe pour tous les actifs PSNX sur Bitcoin
PSNX_PROTOCOL_PREFIX = b'PSNX'
PSNX_VERSION = 1

# Magic numbers pour chaque type d'actif
ASSET_MAGIC = {
    "item": 0x4954454D,      # "ITEM"
    "gem": 0x47454D53,       # "GEMS"
    "fragment": 0x46524147,  # "FRAG"
    "stone": 0x53544F4E,     # "STON"
    "artifact": 0x41525446,  # "ARTF"
}

# Frais minimums (en satoshis)
MIN_INSCRIPTION_FEE = 10000   # 10k sats pour inscription
MIN_TRANSFER_FEE = 5000       # 5k sats pour transfert
DUST_LIMIT = 546              # Output minimum

# Tailles max
MAX_OP_RETURN_SIZE = 80       # Limite OP_RETURN standard
MAX_INSCRIPTION_SIZE = 400000 # ~400KB pour Ordinals


# ============================================================================
# ENUMERATIONS
# ============================================================================

class AssetType(Enum):
    """Types d'actifs transferables"""
    ITEM = ("item", "ITEM", "Alchemical Item")
    GEM = ("gem", "GEM", "Gem")
    FRAGMENT = ("fragment", "FRAG", "Fragment")
    STONE = ("stone", "STON", "Philosopher Stone")
    ARTIFACT = ("artifact", "ARTF", "Artifact")
    
    def __init__(self, type_id: str, code: str, display: str):
        self.type_id = type_id
        self.code = code
        self.display = display


class TransferStatus(Enum):
    """Statut d'un transfert"""
    PENDING = "pending"
    BROADCAST = "broadcast"
    CONFIRMING = "confirming"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class InscriptionType(Enum):
    """Type d'inscription sur Bitcoin"""
    OP_RETURN = "op_return"      # Metadata simple
    ORDINAL = "ordinal"          # NFT complet
    RUNE = "rune"                # Token Rune


# ============================================================================
# STRUCTURES DE DONNEES
# ============================================================================

@dataclass
class AssetOnChain:
    """Representation d'un actif inscrit sur Bitcoin"""
    asset_id: str               # ID unique de l'actif
    asset_type: str             # Type d'actif (item, gem, etc.)
    rune_id: str                # ID Rune sur Bitcoin
    
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
    """Requete de transfert d'actif"""
    transfer_id: str
    asset_id: str
    asset_type: str
    rune_id: str
    
    # Source
    from_address: str
    
    # Destination
    to_address: str
    
    # Optional
    from_vault: Optional[int] = None
    to_vault: Optional[int] = None
    
    # Transaction
    fee_sats: int = MIN_TRANSFER_FEE
    priority: str = "normal"  # low, normal, high
    
    # Status
    status: str = "pending"
    txid: Optional[str] = None
    created_at: str = ""
    broadcast_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    
    # Data
    op_return_data: Optional[bytes] = None
    raw_tx: Optional[str] = None
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        if d.get('op_return_data'):
            d['op_return_data'] = d['op_return_data'].hex()
        return d


# ============================================================================
# GENERATEUR DE RUNE ID
# ============================================================================

class RuneIdGenerator:
    """Genere des IDs Rune uniques pour les actifs PSNX"""
    
    # Codes de categories
    CATEGORY_CODES = {
        "item": "ITM",
        "gem": "GEM",
        "fragment": "FRG",
        "stone": "STN",
        "artifact": "ART",
    }
    
    # Codes de rarete
    RARITY_CODES = {
        "primordial": "P",
        "divine": "D",
        "transcendent": "T",
        "mythical": "M",
        "legendary": "L",
        "masterwork": "W",
        "exquisite": "X",
        "superior": "S",
        "refined": "R",
        "common": "C",
        "crude": "U",
    }
    
    @classmethod
    def generate(cls, asset_type: str, asset_id: str, 
                 rarity: str = "common", sub_type: str = None) -> str:
        """
        Genere un Rune ID unique.
        
        Format: PSNX.CATEGORY.RARITY.SUBTYPE.UNIQUE
        Exemple: PSNX.ITM.L.POT.A1B2C3D4
        """
        cat_code = cls.CATEGORY_CODES.get(asset_type, "UNK")
        rarity_code = cls.RARITY_CODES.get(rarity.lower(), "C")
        
        # Sous-type (3 chars max)
        if sub_type:
            sub_code = sub_type[:3].upper()
        else:
            sub_code = "GEN"
        
        # Hash unique (8 hex chars)
        unique_hash = hashlib.sha256(
            f"{asset_id}{datetime.now().isoformat()}{secrets.token_hex(4)}".encode()
        ).hexdigest()[:8].upper()
        
        return f"PSNX.{cat_code}.{rarity_code}.{sub_code}.{unique_hash}"


# ============================================================================
# BITCOIN ASSET BRIDGE
# ============================================================================

class BitcoinAssetBridge:
    """
    Pont pour transferer les actifs du jeu sur la blockchain Bitcoin.
    
    Permet d'inscrire et transferer:
    - Items alchimiques
    - Gemmes
    - Fragments
    - Pierres Philosophales
    - Artefacts
    """
    
    def __init__(self, data_dir: str = None):
        base_path = Path(__file__).parent.parent
        self.data_dir = Path(data_dir) if data_dir else base_path / "bitcoin_assets"
        
        # Creer les repertoires
        self.assets_dir = self.data_dir / "assets"
        self.transfers_dir = self.data_dir / "transfers"
        self.pending_dir = self.data_dir / "pending"
        
        for d in [self.assets_dir, self.transfers_dir, self.pending_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Cache des actifs
        self._assets: Dict[str, AssetOnChain] = {}
        self._load_assets()
    
    def _load_assets(self):
        """Charge les actifs depuis le disque."""
        for file in self.assets_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                asset = AssetOnChain.from_dict(data)
                self._assets[asset.asset_id] = asset
            except Exception as e:
                print(f"[WARN] Cannot load asset {file}: {e}")
    
    def _save_asset(self, asset: AssetOnChain):
        """Sauvegarde un actif."""
        file_path = self.assets_dir / f"{asset.asset_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(asset.to_dict(), f, indent=2, ensure_ascii=False)
        self._assets[asset.asset_id] = asset
    
    def _save_transfer(self, transfer: TransferRequest):
        """Sauvegarde une requete de transfert."""
        file_path = self.transfers_dir / f"{transfer.transfer_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(transfer.to_dict(), f, indent=2, ensure_ascii=False)
    
    # ========================================================================
    # INSCRIPTION D'ACTIFS
    # ========================================================================
    
    def inscribe_item(self, item_data: Dict, owner_address: str,
                      owner_vault: int = None) -> AssetOnChain:
        """Inscrit un item alchimique sur Bitcoin."""
        return self._inscribe_asset(
            asset_type="item",
            asset_id=item_data.get('item_id', secrets.token_hex(8)),
            name=item_data.get('display_name', item_data.get('item_type', 'Unknown Item')),
            rarity=item_data.get('rarity', 'common'),
            power=item_data.get('stat_power', 0),
            sub_type=item_data.get('category', 'misc')[:3],
            metadata=item_data,
            owner_address=owner_address,
            owner_vault=owner_vault
        )
    
    def inscribe_gem(self, gem_data: Dict, owner_address: str,
                     owner_vault: int = None) -> AssetOnChain:
        """Inscrit une gemme sur Bitcoin."""
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
        """Inscrit un fragment sur Bitcoin."""
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
        """Inscrit une Pierre Philosophale sur Bitcoin."""
        return self._inscribe_asset(
            asset_type="stone",
            asset_id=stone_data.get('stone_id', secrets.token_hex(8)),
            name=f"Philosopher Stone #{stone_data.get('origin_vault', 0)}",
            rarity="primordial",  # Toutes les pierres sont Primordiales
            power=stone_data.get('max_energy', 1000),
            sub_type=stone_data.get('state', 'dor')[:3],
            metadata=stone_data,
            owner_address=owner_address,
            owner_vault=owner_vault
        )
    
    def inscribe_artifact(self, artifact_data: Dict, owner_address: str,
                          owner_vault: int = None) -> AssetOnChain:
        """Inscrit un artefact sur Bitcoin."""
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
        """Methode interne pour inscrire un actif."""
        
        # Generer le Rune ID
        rune_id = RuneIdGenerator.generate(
            asset_type, asset_id, rarity, sub_type
        )
        
        # Creer l'actif on-chain
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
        """Confirme une inscription apres broadcast."""
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
    # TRANSFERTS
    # ========================================================================
    
    def transfer_asset(self, asset_id: str, 
                       from_address: str, to_address: str,
                       from_vault: int = None, to_vault: int = None,
                       priority: str = "normal") -> TransferRequest:
        """
        Initie un transfert d'actif vers une autre adresse Bitcoin.
        
        Args:
            asset_id: ID de l'actif a transferer
            from_address: Adresse Bitcoin source
            to_address: Adresse Bitcoin destination
            from_vault: Vault source (optionnel)
            to_vault: Vault destination (optionnel)
            priority: Priorite de frais (low, normal, high)
        
        Returns:
            TransferRequest avec les donnees pour la transaction
        """
        asset = self._assets.get(asset_id)
        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")
        
        if asset.status != "inscribed":
            raise ValueError(f"Asset not inscribed: status is {asset.status}")
        
        # Verifier la propriete
        if asset.owner_address and asset.owner_address != from_address:
            raise ValueError("Not owner of this asset")
        
        # Valider les adresses
        if not self._is_valid_address(from_address):
            raise ValueError("Invalid source address")
        if not self._is_valid_address(to_address):
            raise ValueError("Invalid destination address")
        
        # Calculer les frais
        fee_sats = self._calculate_fee(priority)
        
        # Generer les donnees OP_RETURN
        op_return_data = self._generate_transfer_op_return(
            asset.asset_type, asset.rune_id, to_address
        )
        
        # Creer la requete de transfert
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
        
        # Marquer l'actif en transfert
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
        """Confirme un transfert apres broadcast."""
        # Charger le transfert
        transfer_file = self.transfers_dir / f"{transfer_id}.json"
        if not transfer_file.exists():
            return False
        
        with open(transfer_file, 'r', encoding='utf-8') as f:
            transfer_data = json.load(f)
        
        # Mettre a jour le transfert
        transfer_data['status'] = "confirmed"
        transfer_data['txid'] = txid
        transfer_data['confirmed_at'] = datetime.now().isoformat()
        
        with open(transfer_file, 'w', encoding='utf-8') as f:
            json.dump(transfer_data, f, indent=2)
        
        # Mettre a jour l'actif
        asset = self._assets.get(transfer_data['asset_id'])
        if asset:
            asset.owner_address = transfer_data['to_address']
            asset.owner_vault = transfer_data.get('to_vault')
            asset.status = "inscribed"
            
            # Mettre a jour l'historique
            if asset.transfer_history:
                asset.transfer_history[-1]['status'] = "confirmed"
                asset.transfer_history[-1]['txid'] = txid
                asset.transfer_history[-1]['confirmed_at'] = datetime.now().isoformat()
            
            self._save_asset(asset)
        
        return True
    
    def get_transfer_data(self, transfer_id: str) -> Optional[Dict]:
        """Retourne les donnees pour construire la transaction Bitcoin."""
        transfer_file = self.transfers_dir / f"{transfer_id}.json"
        if not transfer_file.exists():
            return None
        
        with open(transfer_file, 'r', encoding='utf-8') as f:
            transfer = json.load(f)
        
        return {
            "transfer_id": transfer['transfer_id'],
            "rune_id": transfer['rune_id'],
            "asset_type": transfer['asset_type'],
            "from_address": transfer['from_address'],
            "to_address": transfer['to_address'],
            "fee_sats": transfer['fee_sats'],
            "op_return_hex": transfer.get('op_return_data', ''),
            "instructions": [
                "1. Creer une transaction depuis from_address",
                "2. Ajouter un output OP_RETURN avec op_return_hex",
                "3. Ajouter un output de 546 sats vers to_address",
                "4. Ajouter le change vers from_address",
                "5. Signer et broadcaster la transaction",
                "6. Appeler confirm_transfer(transfer_id, txid)"
            ]
        }
    
    # ========================================================================
    # REQUETES
    # ========================================================================
    
    def get_asset(self, asset_id: str) -> Optional[AssetOnChain]:
        """Recupere un actif par ID."""
        return self._assets.get(asset_id)
    
    def get_asset_by_rune(self, rune_id: str) -> Optional[AssetOnChain]:
        """Recupere un actif par Rune ID."""
        for asset in self._assets.values():
            if asset.rune_id == rune_id:
                return asset
        return None
    
    def get_assets_by_address(self, address: str) -> List[AssetOnChain]:
        """Recupere tous les actifs d'une adresse."""
        return [a for a in self._assets.values() if a.owner_address == address]
    
    def get_assets_by_vault(self, vault_number: int) -> List[AssetOnChain]:
        """Recupere tous les actifs d'un vault."""
        return [a for a in self._assets.values() if a.owner_vault == vault_number]
    
    def get_assets_by_type(self, asset_type: str) -> List[AssetOnChain]:
        """Recupere tous les actifs d'un type."""
        return [a for a in self._assets.values() if a.asset_type == asset_type]
    
    def get_pending_transfers(self) -> List[Dict]:
        """Recupere les transferts en attente."""
        pending = []
        for file in self.transfers_dir.glob("*.json"):
            with open(file, 'r', encoding='utf-8') as f:
                transfer = json.load(f)
            if transfer.get('status') == 'pending':
                pending.append(transfer)
        return pending
    
    def get_statistics(self) -> Dict:
        """Statistiques globales."""
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
    # UTILITAIRES
    # ========================================================================
    
    def _generate_transfer_op_return(self, asset_type: str, 
                                      rune_id: str, to_address: str) -> bytes:
        """Genere les donnees OP_RETURN pour un transfert."""
        # Format: PREFIX | VERSION | MAGIC | RUNE_ID | ADDR_HASH
        data = PSNX_PROTOCOL_PREFIX
        data += struct.pack('>B', PSNX_VERSION)
        data += struct.pack('>I', ASSET_MAGIC.get(asset_type, 0))
        data += rune_id.encode('utf-8')[:32].ljust(32, b'\x00')
        data += hashlib.sha256(to_address.encode()).digest()[:20]
        
        return data
    
    def _is_valid_address(self, address: str) -> bool:
        """Valide une adresse Bitcoin."""
        if not address:
            return False
        # P2PKH (Legacy)
        if address.startswith('1') and 26 <= len(address) <= 35:
            return True
        # P2SH
        if address.startswith('3') and 26 <= len(address) <= 35:
            return True
        # Bech32 (SegWit)
        if address.startswith('bc1') and 42 <= len(address) <= 62:
            return True
        return False
    
    def _calculate_fee(self, priority: str) -> int:
        """Calcule les frais selon la priorite."""
        base_fee = MIN_TRANSFER_FEE
        if priority == "low":
            return base_fee
        elif priority == "high":
            return base_fee * 3
        return base_fee * 2  # normal
    
    def _fragment_rarity(self, purity: float) -> str:
        """Determine la rarete d'un fragment selon sa purete."""
        if purity >= 99:
            return "primordial"
        elif purity >= 95:
            return "mythical"
        elif purity >= 90:
            return "legendary"
        elif purity >= 80:
            return "masterwork"
        elif purity >= 70:
            return "exquisite"
        elif purity >= 50:
            return "superior"
        else:
            return "common"


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def format_rune_id(rune_id: str) -> str:
    """Formate un Rune ID pour affichage."""
    parts = rune_id.split('.')
    if len(parts) >= 5:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.{parts[3]}.{parts[4][:4]}..."
    return rune_id


def parse_rune_id(rune_id: str) -> Dict:
    """Parse un Rune ID en ses composants."""
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


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  TEST BITCOIN ASSET BRIDGE")
    print("=" * 60)
    
    bridge = BitcoinAssetBridge()
    
    # Test inscription d'un item
    print("\n1. Inscription d'un item...")
    item = bridge.inscribe_item(
        {
            "item_id": "test_item_001",
            "item_type": "potion_power",
            "category": "potion",
            "rarity": "legendary",
            "stat_power": 5000,
            "display_name": "Potion de Puissance Legendaire"
        },
        owner_address="bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
        owner_vault=1
    )
    print(f"   Asset ID: {item.asset_id}")
    print(f"   Rune ID: {item.rune_id}")
    print(f"   Status: {item.status}")
    
    # Confirmer l'inscription
    print("\n2. Confirmation inscription...")
    bridge.confirm_inscription(item.asset_id, "abc123def456789")
    item = bridge.get_asset(item.asset_id)
    print(f"   Status: {item.status}")
    print(f"   TXID: {item.inscription_txid}")
    
    # Test inscription d'une gemme
    print("\n3. Inscription d'une gemme...")
    gem = bridge.inscribe_gem(
        {
            "gem_id": "test_gem_001",
            "gem_type": "quantum_crystal",
            "rarity": "mythical",
            "power": 8000,
            "name": "Cristal Quantique"
        },
        owner_address="bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
        owner_vault=1
    )
    print(f"   Rune ID: {gem.rune_id}")
    
    # Test inscription d'une pierre
    print("\n4. Inscription d'une Pierre Philosophale...")
    stone = bridge.inscribe_stone(
        {
            "stone_id": "supreme_stone_001",
            "origin_vault": 1,
            "max_energy": 3333,
            "state": "transcendent"
        },
        owner_address="bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
        owner_vault=1
    )
    print(f"   Rune ID: {stone.rune_id}")
    
    # Test transfert
    print("\n5. Test transfert...")
    bridge.confirm_inscription(gem.asset_id, "gem_txid_123")
    
    try:
        transfer = bridge.transfer_asset(
            gem.asset_id,
            from_address="bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
            to_address="bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
        )
        print(f"   Transfer ID: {transfer.transfer_id}")
        print(f"   Fee: {transfer.fee_sats} sats")
        print(f"   OP_RETURN: {len(transfer.op_return_data)} bytes")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Statistiques
    print("\n6. Statistiques:")
    stats = bridge.get_statistics()
    print(f"   Total assets: {stats['total_assets']}")
    print(f"   Inscribed: {stats['inscribed']}")
    print(f"   Pending: {stats['pending']}")
    print(f"   By type: {stats['by_type']}")
    
    print("\n" + "=" * 60)
    print("  TEST TERMINE")
    print("=" * 60)
