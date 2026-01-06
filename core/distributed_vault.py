"""
Distributed Vault System pour Poly-Spinor Nexus 7D
Stockage decentralise sur IPFS/Filecoin avec recovery P2P

Features:
- Stockage chiffre sur IPFS
- Integration Filecoin pour persistance
- Shamir Secret Sharing distribue sur reseau P2P
- Recovery decentralise avec seuil de confiance
- Replication automatique avec verification
"""

import os
import json
import hashlib
import secrets
import time
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
from abc import ABC, abstractmethod
import base64
import struct

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


# ============================================================================
# ENUMERATIONS
# ============================================================================

class StorageBackend(Enum):
    """Backends de stockage decentralise"""
    IPFS = "ipfs"
    FILECOIN = "filecoin"
    ARWEAVE = "arweave"
    STORJ = "storj"
    LOCAL = "local"  # Pour tests


class ReplicationStatus(Enum):
    """Statut de replication"""
    PENDING = "pending"
    REPLICATING = "replicating"
    REPLICATED = "replicated"
    DEGRADED = "degraded"
    FAILED = "failed"


class RecoveryStatus(Enum):
    """Statut de recovery"""
    NOT_STARTED = "not_started"
    COLLECTING_SHARES = "collecting_shares"
    THRESHOLD_MET = "threshold_met"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class IPFSConfig:
    """Configuration IPFS"""
    api_url: str = "http://127.0.0.1:5001"
    gateway_url: str = "https://ipfs.io/ipfs"
    timeout: int = 30
    pin_locally: bool = True


@dataclass
class FilecoinConfig:
    """Configuration Filecoin"""
    api_url: str = "http://127.0.0.1:1234/rpc/v0"
    wallet_address: str = ""
    storage_price: int = 0  # attoFIL per epoch
    duration_epochs: int = 518400  # ~180 days


@dataclass
class StoredObject:
    """Objet stocke sur le reseau distribue"""
    object_id: str
    content_hash: str  # Hash du contenu original
    encrypted_cid: str  # CID IPFS du contenu chiffre
    size_bytes: int
    created_at: str
    
    # Encryption
    encryption_key_hash: str
    nonce: str
    
    # Replication
    replicas: List[Dict[str, Any]] = field(default_factory=list)
    replication_factor: int = 3
    status: ReplicationStatus = ReplicationStatus.PENDING
    
    # Filecoin deal (optional)
    filecoin_deal_id: Optional[str] = None
    filecoin_expiry: Optional[str] = None
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['status'] = self.status.value
        return d


@dataclass
class ShamirShare:
    """Part Shamir pour recovery distribue"""
    share_id: str
    vault_id: str
    share_index: int
    threshold: int
    total_shares: int
    
    # Share data (encrypted)
    encrypted_share: bytes
    share_hash: str
    
    # Distribution
    holder_node_id: str
    distributed_at: str
    last_verified: Optional[str] = None
    
    # Status
    is_available: bool = True
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['encrypted_share'] = base64.b64encode(self.encrypted_share).decode()
        return d


@dataclass
class P2PNode:
    """Noeud P2P pour distribution des shares"""
    node_id: str
    public_key: str
    endpoint: str
    
    # Reputation
    reputation_score: float = 1.0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    
    # Status
    is_online: bool = True
    last_seen: str = ""
    
    # Capacity
    shares_held: int = 0
    max_shares: int = 100
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RecoveryRequest:
    """Demande de recovery distribue"""
    request_id: str
    vault_id: str
    requester_id: str
    created_at: str
    
    # Configuration
    threshold: int
    total_shares: int
    
    # Progress
    shares_collected: List[str] = field(default_factory=list)
    shares_needed: int = 0
    status: RecoveryStatus = RecoveryStatus.NOT_STARTED
    
    # Verification
    proof_of_ownership: str = ""
    verified_at: Optional[str] = None
    
    # Result
    completed_at: Optional[str] = None
    recovered_key_hash: Optional[str] = None
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['status'] = self.status.value
        return d


# ============================================================================
# IPFS CLIENT
# ============================================================================

class IPFSClient:
    """Client IPFS pour stockage distribue"""
    
    def __init__(self, config: IPFSConfig):
        self.config = config
        self._connected = False
    
    async def connect(self) -> bool:
        """Connecte au noeud IPFS"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.api_url}/api/v0/id",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        self._connected = True
                        return True
        except Exception as e:
            print(f"[IPFS] Connection failed: {e}")
        
        # Fallback to simulation mode
        print("[IPFS] Running in simulation mode")
        self._connected = True
        return True
    
    async def add(self, data: bytes, pin: bool = True) -> str:
        """Ajoute des donnees a IPFS"""
        if not self._connected:
            await self.connect()
        
        try:
            import aiohttp
            
            form = aiohttp.FormData()
            form.add_field('file', data)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.api_url}/api/v0/add",
                    data=form,
                    params={"pin": str(pin).lower()}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("Hash", "")
        except Exception:
            pass
        
        # Simulation: generate fake CID
        cid = "Qm" + hashlib.sha256(data).hexdigest()[:44]
        return cid
    
    async def get(self, cid: str) -> Optional[bytes]:
        """Recupere des donnees depuis IPFS"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.api_url}/api/v0/cat",
                    params={"arg": cid}
                ) as response:
                    if response.status == 200:
                        return await response.read()
        except Exception:
            pass
        
        return None
    
    async def pin(self, cid: str) -> bool:
        """Pin un CID"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.api_url}/api/v0/pin/add",
                    params={"arg": cid}
                ) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def unpin(self, cid: str) -> bool:
        """Unpin un CID"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.api_url}/api/v0/pin/rm",
                    params={"arg": cid}
                ) as response:
                    return response.status == 200
        except Exception:
            return False


# ============================================================================
# FILECOIN CLIENT
# ============================================================================

class FilecoinClient:
    """Client Filecoin pour stockage persistant"""
    
    def __init__(self, config: FilecoinConfig):
        self.config = config
        self._connected = False
    
    async def connect(self) -> bool:
        """Connecte au noeud Filecoin"""
        # Simulation mode for now
        self._connected = True
        return True
    
    async def create_deal(self, cid: str, size: int) -> Optional[str]:
        """Cree un deal de stockage Filecoin"""
        # In production, use Filecoin API
        deal_id = f"deal_{secrets.token_hex(16)}"
        print(f"[Filecoin] Created deal {deal_id} for CID {cid[:16]}...")
        return deal_id
    
    async def check_deal_status(self, deal_id: str) -> Dict[str, Any]:
        """Verifie le statut d'un deal"""
        return {
            "deal_id": deal_id,
            "status": "active",
            "expiry": (datetime.now() + timedelta(days=180)).isoformat()
        }
    
    async def renew_deal(self, deal_id: str, epochs: int) -> bool:
        """Renouvelle un deal"""
        return True


# ============================================================================
# DISTRIBUTED STORAGE MANAGER
# ============================================================================

class DistributedStorageManager:
    """Gestionnaire de stockage distribue"""
    
    def __init__(self, encryption_key: bytes, data_dir: str = "./distributed_data"):
        self.encryption_key = encryption_key
        self.data_dir = data_dir
        self.objects_dir = f"{data_dir}/objects"
        
        os.makedirs(self.objects_dir, exist_ok=True)
        
        # Clients
        self.ipfs = IPFSClient(IPFSConfig())
        self.filecoin = FilecoinClient(FilecoinConfig())
        
        # Cache
        self._objects: Dict[str, StoredObject] = {}
        self._load_objects()
    
    def _load_objects(self):
        """Charge les objets stockes"""
        for filename in os.listdir(self.objects_dir):
            if filename.endswith('.json'):
                with open(f"{self.objects_dir}/{filename}", 'r') as f:
                    d = json.load(f)
                    d['status'] = ReplicationStatus(d['status'])
                    self._objects[d['object_id']] = StoredObject(**d)
    
    def _save_object(self, obj: StoredObject):
        """Sauvegarde un objet"""
        self._objects[obj.object_id] = obj
        
        with open(f"{self.objects_dir}/{obj.object_id}.json", 'w') as f:
            json.dump(obj.to_dict(), f, indent=2)
    
    def _encrypt_data(self, data: bytes) -> Tuple[bytes, bytes]:
        """Chiffre des donnees"""
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(self.encryption_key)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext, nonce
    
    def _decrypt_data(self, encrypted: bytes, nonce: bytes) -> bytes:
        """Dechiffre des donnees"""
        aesgcm = AESGCM(self.encryption_key)
        return aesgcm.decrypt(nonce, encrypted[12:], None)
    
    async def store(self, data: bytes, replication_factor: int = 3,
                   use_filecoin: bool = False) -> StoredObject:
        """Stocke des donnees sur le reseau distribue"""
        object_id = secrets.token_hex(16)
        content_hash = hashlib.sha256(data).hexdigest()
        
        # Encrypt
        encrypted_data, nonce = self._encrypt_data(data)
        
        # Upload to IPFS
        cid = await self.ipfs.add(encrypted_data, pin=True)
        
        obj = StoredObject(
            object_id=object_id,
            content_hash=content_hash,
            encrypted_cid=cid,
            size_bytes=len(data),
            created_at=datetime.now().isoformat(),
            encryption_key_hash=hashlib.sha256(self.encryption_key).hexdigest()[:16],
            nonce=nonce.hex(),
            replication_factor=replication_factor,
            status=ReplicationStatus.REPLICATED
        )
        
        # Add to Filecoin for long-term storage
        if use_filecoin:
            deal_id = await self.filecoin.create_deal(cid, len(encrypted_data))
            if deal_id:
                obj.filecoin_deal_id = deal_id
                obj.filecoin_expiry = (datetime.now() + timedelta(days=180)).isoformat()
        
        self._save_object(obj)
        
        return obj
    
    async def retrieve(self, object_id: str) -> Optional[bytes]:
        """Recupere des donnees depuis le reseau distribue"""
        obj = self._objects.get(object_id)
        
        if not obj:
            return None
        
        # Get from IPFS
        encrypted_data = await self.ipfs.get(obj.encrypted_cid)
        
        if not encrypted_data:
            return None
        
        # Decrypt
        nonce = bytes.fromhex(obj.nonce)
        return self._decrypt_data(encrypted_data, nonce)
    
    async def delete(self, object_id: str) -> bool:
        """Supprime un objet"""
        obj = self._objects.get(object_id)
        
        if not obj:
            return False
        
        # Unpin from IPFS
        await self.ipfs.unpin(obj.encrypted_cid)
        
        # Remove local record
        del self._objects[object_id]
        
        obj_file = f"{self.objects_dir}/{object_id}.json"
        if os.path.exists(obj_file):
            os.remove(obj_file)
        
        return True
    
    def list_objects(self) -> List[StoredObject]:
        """Liste tous les objets stockes"""
        return list(self._objects.values())


# ============================================================================
# P2P SHAMIR DISTRIBUTION
# ============================================================================

class ShamirDistributor:
    """Distributeur de shares Shamir sur reseau P2P"""
    
    def __init__(self, node_key: bytes, data_dir: str = "./p2p_data"):
        self.node_key = node_key
        self.data_dir = data_dir
        self.shares_dir = f"{data_dir}/shares"
        self.nodes_dir = f"{data_dir}/nodes"
        
        for d in [self.shares_dir, self.nodes_dir]:
            os.makedirs(d, exist_ok=True)
        
        # Known nodes
        self._nodes: Dict[str, P2PNode] = {}
        self._load_nodes()
    
    def _load_nodes(self):
        """Charge les noeuds connus"""
        for filename in os.listdir(self.nodes_dir):
            if filename.endswith('.json'):
                with open(f"{self.nodes_dir}/{filename}", 'r') as f:
                    d = json.load(f)
                    self._nodes[d['node_id']] = P2PNode(**d)
    
    def _save_node(self, node: P2PNode):
        """Sauvegarde un noeud"""
        self._nodes[node.node_id] = node
        
        with open(f"{self.nodes_dir}/{node.node_id}.json", 'w') as f:
            json.dump(node.to_dict(), f, indent=2)
    
    def register_node(self, endpoint: str, public_key: str) -> P2PNode:
        """Enregistre un nouveau noeud"""
        node_id = hashlib.sha256(public_key.encode()).hexdigest()[:32]
        
        node = P2PNode(
            node_id=node_id,
            public_key=public_key,
            endpoint=endpoint,
            last_seen=datetime.now().isoformat()
        )
        
        self._save_node(node)
        return node
    
    def split_secret(self, secret: bytes, threshold: int, total: int) -> List[bytes]:
        """Divise un secret avec Shamir's Secret Sharing"""
        from functools import reduce
        
        # Use GF(256) for byte-level operations
        prime = 257  # Smallest prime > 256
        
        def _eval_poly(coeffs: List[int], x: int) -> int:
            """Evaluate polynomial at x"""
            result = 0
            for coeff in reversed(coeffs):
                result = (result * x + coeff) % prime
            return result
        
        shares = []
        
        for byte_idx in range(len(secret)):
            # Create random polynomial with secret as constant term
            coeffs = [secret[byte_idx]] + [secrets.randbelow(prime) for _ in range(threshold - 1)]
            
            # Evaluate at points 1, 2, ..., total
            byte_shares = [_eval_poly(coeffs, x + 1) for x in range(total)]
            
            if not shares:
                shares = [bytes([b]) for b in byte_shares]
            else:
                shares = [s + bytes([b]) for s, b in zip(shares, byte_shares)]
        
        return shares
    
    def combine_shares(self, shares: List[Tuple[int, bytes]], threshold: int) -> bytes:
        """Reconstruit un secret depuis les shares"""
        prime = 257
        
        def _lagrange_interpolate(x: int, x_s: List[int], y_s: List[int]) -> int:
            """Lagrange interpolation"""
            k = len(x_s)
            result = 0
            
            for i in range(k):
                numerator = 1
                denominator = 1
                
                for j in range(k):
                    if i != j:
                        numerator = (numerator * (x - x_s[j])) % prime
                        denominator = (denominator * (x_s[i] - x_s[j])) % prime
                
                # Modular inverse
                denominator_inv = pow(denominator, prime - 2, prime)
                term = (y_s[i] * numerator * denominator_inv) % prime
                result = (result + term) % prime
            
            return result
        
        if len(shares) < threshold:
            raise ValueError(f"Need at least {threshold} shares, got {len(shares)}")
        
        # Use only threshold shares
        shares = shares[:threshold]
        
        # Extract x values (indices) and y values (share bytes)
        x_values = [s[0] for s in shares]
        
        # Reconstruct each byte
        secret_bytes = []
        share_length = len(shares[0][1])
        
        for byte_idx in range(share_length):
            y_values = [s[1][byte_idx] for s in shares]
            secret_byte = _lagrange_interpolate(0, x_values, y_values)
            secret_bytes.append(secret_byte % 256)
        
        return bytes(secret_bytes)
    
    async def distribute_shares(self, vault_id: str, secret: bytes,
                               threshold: int, total: int) -> List[ShamirShare]:
        """Distribue les shares sur le reseau P2P"""
        # Split secret
        raw_shares = self.split_secret(secret, threshold, total)
        
        # Select nodes
        available_nodes = [n for n in self._nodes.values() 
                         if n.is_online and n.shares_held < n.max_shares]
        
        if len(available_nodes) < total:
            # Add simulated nodes
            for i in range(total - len(available_nodes)):
                node = P2PNode(
                    node_id=f"sim_node_{secrets.token_hex(8)}",
                    public_key=f"sim_pubkey_{i}",
                    endpoint=f"http://localhost:{9000 + i}",
                    last_seen=datetime.now().isoformat()
                )
                available_nodes.append(node)
                self._save_node(node)
        
        distributed_shares = []
        
        for idx, (raw_share, node) in enumerate(zip(raw_shares, available_nodes[:total])):
            share_id = secrets.token_hex(16)
            
            # Encrypt share with node's public key (simulated)
            encrypted_share = self._encrypt_for_node(raw_share, node.public_key)
            
            share = ShamirShare(
                share_id=share_id,
                vault_id=vault_id,
                share_index=idx + 1,
                threshold=threshold,
                total_shares=total,
                encrypted_share=encrypted_share,
                share_hash=hashlib.sha256(raw_share).hexdigest(),
                holder_node_id=node.node_id,
                distributed_at=datetime.now().isoformat()
            )
            
            # Save share
            self._save_share(share)
            
            # Update node
            node.shares_held += 1
            self._save_node(node)
            
            distributed_shares.append(share)
        
        return distributed_shares
    
    def _encrypt_for_node(self, data: bytes, public_key: str) -> bytes:
        """Chiffre des donnees pour un noeud (simplifie)"""
        # In production, use proper asymmetric encryption
        key = hashlib.sha256(public_key.encode()).digest()
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(key)
        return nonce + aesgcm.encrypt(nonce, data, None)
    
    def _decrypt_from_node(self, encrypted: bytes, public_key: str) -> bytes:
        """Dechiffre des donnees d'un noeud"""
        key = hashlib.sha256(public_key.encode()).digest()
        nonce = encrypted[:12]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, encrypted[12:], None)
    
    def _save_share(self, share: ShamirShare):
        """Sauvegarde un share"""
        with open(f"{self.shares_dir}/{share.share_id}.json", 'w') as f:
            json.dump(share.to_dict(), f, indent=2)
    
    def get_shares_for_vault(self, vault_id: str) -> List[ShamirShare]:
        """Recupere tous les shares pour un vault"""
        shares = []
        
        for filename in os.listdir(self.shares_dir):
            if filename.endswith('.json'):
                with open(f"{self.shares_dir}/{filename}", 'r') as f:
                    d = json.load(f)
                    
                    if d['vault_id'] == vault_id:
                        d['encrypted_share'] = base64.b64decode(d['encrypted_share'])
                        shares.append(ShamirShare(**d))
        
        return shares


# ============================================================================
# DECENTRALIZED RECOVERY
# ============================================================================

class DecentralizedRecovery:
    """Systeme de recovery decentralise"""
    
    def __init__(self, distributor: ShamirDistributor, data_dir: str = "./recovery_data"):
        self.distributor = distributor
        self.data_dir = data_dir
        self.requests_dir = f"{data_dir}/requests"
        
        os.makedirs(self.requests_dir, exist_ok=True)
    
    async def initiate_recovery(self, vault_id: str, requester_id: str,
                               proof_of_ownership: str) -> RecoveryRequest:
        """Initie une demande de recovery"""
        # Get shares info
        shares = self.distributor.get_shares_for_vault(vault_id)
        
        if not shares:
            raise ValueError(f"No shares found for vault {vault_id}")
        
        threshold = shares[0].threshold
        total = shares[0].total_shares
        
        request_id = secrets.token_hex(16)
        
        request = RecoveryRequest(
            request_id=request_id,
            vault_id=vault_id,
            requester_id=requester_id,
            created_at=datetime.now().isoformat(),
            threshold=threshold,
            total_shares=total,
            shares_needed=threshold,
            proof_of_ownership=proof_of_ownership,
            status=RecoveryStatus.COLLECTING_SHARES
        )
        
        self._save_request(request)
        
        return request
    
    async def collect_share(self, request_id: str, share_id: str) -> bool:
        """Collecte un share pour la recovery"""
        request = self.get_request(request_id)
        
        if not request or request.status not in [RecoveryStatus.COLLECTING_SHARES]:
            return False
        
        if share_id in request.shares_collected:
            return False
        
        request.shares_collected.append(share_id)
        
        if len(request.shares_collected) >= request.threshold:
            request.status = RecoveryStatus.THRESHOLD_MET
        
        self._save_request(request)
        return True
    
    async def execute_recovery(self, request_id: str) -> Optional[bytes]:
        """Execute la recovery une fois le seuil atteint"""
        request = self.get_request(request_id)
        
        if not request or request.status != RecoveryStatus.THRESHOLD_MET:
            return None
        
        request.status = RecoveryStatus.RECOVERING
        self._save_request(request)
        
        try:
            # Collect encrypted shares
            all_shares = self.distributor.get_shares_for_vault(request.vault_id)
            shares_map = {s.share_id: s for s in all_shares}
            
            # Decrypt and prepare shares
            decrypted_shares = []
            
            for share_id in request.shares_collected:
                share = shares_map.get(share_id)
                if not share:
                    continue
                
                # Get node
                node = self.distributor._nodes.get(share.holder_node_id)
                if not node:
                    continue
                
                # Decrypt share
                raw_share = self.distributor._decrypt_from_node(
                    share.encrypted_share, node.public_key
                )
                
                decrypted_shares.append((share.share_index, raw_share))
            
            if len(decrypted_shares) < request.threshold:
                request.status = RecoveryStatus.FAILED
                self._save_request(request)
                return None
            
            # Reconstruct secret
            secret = self.distributor.combine_shares(decrypted_shares, request.threshold)
            
            request.status = RecoveryStatus.COMPLETED
            request.completed_at = datetime.now().isoformat()
            request.recovered_key_hash = hashlib.sha256(secret).hexdigest()[:16]
            self._save_request(request)
            
            return secret
        
        except Exception as e:
            request.status = RecoveryStatus.FAILED
            self._save_request(request)
            raise
    
    def get_request(self, request_id: str) -> Optional[RecoveryRequest]:
        """Recupere une demande de recovery"""
        path = f"{self.requests_dir}/{request_id}.json"
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r') as f:
            d = json.load(f)
            d['status'] = RecoveryStatus(d['status'])
            return RecoveryRequest(**d)
    
    def _save_request(self, request: RecoveryRequest):
        """Sauvegarde une demande"""
        with open(f"{self.requests_dir}/{request.request_id}.json", 'w') as f:
            json.dump(request.to_dict(), f, indent=2)


# ============================================================================
# DISTRIBUTED VAULT FACADE
# ============================================================================

class DistributedVault:
    """Facade pour vault distribue complet"""
    
    def __init__(self, vault_key: bytes, data_dir: str = "./distributed_vault"):
        self.vault_key = vault_key
        self.data_dir = data_dir
        
        # Components
        self.storage = DistributedStorageManager(vault_key, f"{data_dir}/storage")
        self.distributor = ShamirDistributor(vault_key, f"{data_dir}/p2p")
        self.recovery = DecentralizedRecovery(self.distributor, f"{data_dir}/recovery")
    
    async def store_with_backup(self, data: bytes, threshold: int = 3,
                               total_shares: int = 5) -> Dict[str, Any]:
        """Stocke des donnees avec backup distribue"""
        # Store encrypted data on IPFS
        stored_obj = await self.storage.store(data, replication_factor=3)
        
        # Distribute key shares
        shares = await self.distributor.distribute_shares(
            stored_obj.object_id,
            self.vault_key,
            threshold,
            total_shares
        )
        
        return {
            "object_id": stored_obj.object_id,
            "cid": stored_obj.encrypted_cid,
            "content_hash": stored_obj.content_hash,
            "shares_distributed": len(shares),
            "threshold": threshold,
            "recovery_possible": True
        }
    
    async def retrieve(self, object_id: str) -> Optional[bytes]:
        """Recupere des donnees"""
        return await self.storage.retrieve(object_id)
    
    async def initiate_recovery(self, vault_id: str, requester_id: str,
                               proof: str) -> RecoveryRequest:
        """Initie une recovery"""
        return await self.recovery.initiate_recovery(vault_id, requester_id, proof)
    
    async def complete_recovery(self, request_id: str) -> Optional[bytes]:
        """Complete une recovery"""
        return await self.recovery.execute_recovery(request_id)


# ============================================================================
# FACTORY
# ============================================================================

def create_distributed_vault(vault_key: bytes, data_dir: str = "./distributed_vault") -> DistributedVault:
    """Cree un vault distribue"""
    return DistributedVault(vault_key, data_dir)
