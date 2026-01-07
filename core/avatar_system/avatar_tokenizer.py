#!/usr/bin/env python3
"""
Tokenisation des avatars sur la blockchain Bitcoin via Rune Protocol
"""

import hashlib
import json
import secrets
import struct
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ============================================================================
# CONSTANTES
# ============================================================================

AVATAR_RUNE_PREFIX = "PSNX.AVT"  # Prefix pour les avatars
AVATAR_MAGIC = 0x41565452       # "AVTR" en hex

# Frais
AVATAR_INSCRIPTION_FEE = 15000  # 15k sats
AVATAR_TRANSFER_FEE = 8000      # 8k sats


# ============================================================================
# ENUMERATIONS
# ============================================================================

class TokenStatus(Enum):
    """Statut du token avatar"""
    DRAFT = "draft"
    PENDING = "pending"
    INSCRIBED = "inscribed"
    TRANSFERRING = "transferring"
    BURNED = "burned"


# ============================================================================
# STRUCTURES DE DONNEES
# ============================================================================

@dataclass
class AvatarToken:
    """Token representant un avatar sur Bitcoin"""
    token_id: str
    avatar_id: str
    vault_id: str
    rune_id: str
    
    # Metadata
    geometric_type: str
    rarity_tier: str
    rarity_score: float
    generation: int
    dna_hash: str
    
    # Blockchain
    inscription_txid: Optional[str] = None
    block_height: Optional[int] = None
    confirmations: int = 0
    
    # Ownership
    owner_address: Optional[str] = None
    owner_vault: Optional[int] = None
    
    # Status
    status: str = "draft"
    created_at: str = ""
    inscribed_at: Optional[str] = None
    
    # Transfer history
    transfer_history: List[Dict] = field(default_factory=list)
    
    # Files
    obj_ipfs: Optional[str] = None
    texture_ipfs: Optional[str] = None
    preview_ipfs: Optional[str] = None
    metadata_ipfs: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AvatarToken':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TransferRequest:
    """Requete de transfert d'avatar"""
    transfer_id: str
    token_id: str
    rune_id: str
    
    from_address: str
    to_address: str
    from_vault: Optional[int] = None
    to_vault: Optional[int] = None
    
    fee_sats: int = AVATAR_TRANSFER_FEE
    status: str = "pending"
    
    txid: Optional[str] = None
    created_at: str = ""
    confirmed_at: Optional[str] = None
    
    op_return_data: Optional[bytes] = None
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        if d.get('op_return_data'):
            d['op_return_data'] = d['op_return_data'].hex()
        return d


# ============================================================================
# GENERATEUR DE RUNE ID
# ============================================================================

class AvatarRuneGenerator:
    """Genere des Rune IDs uniques pour les avatars"""
    
    RARITY_CODES = {
        'common': 'C',
        'uncommon': 'U', 
        'rare': 'R',
        'epic': 'E',
        'legendary': 'L',
        'mythical': 'M',
        'primordial': 'P'
    }
    
    TYPE_CODES = {
        'quantum_sphere': 'QS',
        'spinor_torus': 'ST',
        'bell_polyhedron': 'BP',
        'clifford_lattice': 'CL',
        'entropy_fractal': 'EF',
        '7d_projection': '7D',
        'hybrid_form': 'HF',
        'nexus_crystal': 'NC'
    }
    
    @classmethod
    def generate(cls, avatar_id: str, geometric_type: str, 
                 rarity: str, generation: int) -> str:
        """
        Genere un Rune ID unique pour l'avatar.
        
        Format: PSNX.AVT.RARITY.TYPE.GEN.UNIQUE
        Exemple: PSNX.AVT.L.NC.G1.A1B2C3D4
        """
        rarity_code = cls.RARITY_CODES.get(rarity, 'C')
        type_code = cls.TYPE_CODES.get(geometric_type, 'XX')
        gen_code = f"G{generation}"
        
        unique_hash = hashlib.sha256(
            f"{avatar_id}{datetime.now().isoformat()}{secrets.token_hex(4)}".encode()
        ).hexdigest()[:8].upper()
        
        return f"{AVATAR_RUNE_PREFIX}.{rarity_code}.{type_code}.{gen_code}.{unique_hash}"


# ============================================================================
# TOKENIZER
# ============================================================================

class AvatarTokenizer:
    """Gere la tokenisation des avatars sur Bitcoin"""
    
    def __init__(self, data_dir: str = None):
        base_path = Path(__file__).parent.parent.parent
        self.data_dir = Path(data_dir) if data_dir else base_path / "avatar_tokens"
        
        self.tokens_dir = self.data_dir / "tokens"
        self.transfers_dir = self.data_dir / "transfers"
        
        for d in [self.tokens_dir, self.transfers_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        self._tokens: Dict[str, AvatarToken] = {}
        self._load_tokens()
    
    def _load_tokens(self):
        """Charge les tokens depuis le disque"""
        for file in self.tokens_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                token = AvatarToken.from_dict(data)
                self._tokens[token.token_id] = token
            except Exception as e:
                print(f"[WARN] Cannot load token {file}: {e}")
    
    def _save_token(self, token: AvatarToken):
        """Sauvegarde un token"""
        file_path = self.tokens_dir / f"{token.token_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(token.to_dict(), f, indent=2, ensure_ascii=False)
        self._tokens[token.token_id] = token
    
    def _save_transfer(self, transfer: TransferRequest):
        """Sauvegarde un transfert"""
        file_path = self.transfers_dir / f"{transfer.transfer_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(transfer.to_dict(), f, indent=2, ensure_ascii=False)
    
    def create_token(self, avatar_data: Dict, owner_address: str,
                     owner_vault: int = None) -> AvatarToken:
        """
        Cree un token pour un avatar.
        
        Args:
            avatar_data: Donnees de l'avatar (de QuantumAvatarGenerator)
            owner_address: Adresse Bitcoin du proprietaire
            owner_vault: Numero de vault (optionnel)
        
        Returns:
            AvatarToken
        """
        avatar_id = avatar_data.get('avatar_id', secrets.token_hex(8))
        dna = avatar_data.get('dna', {})
        
        geometric_type = dna.get('geometric_name', 'unknown')
        rarity_tier = dna.get('rarity_tier', 'common')
        rarity_score = dna.get('rarity_score', 0)
        generation = dna.get('generation', 1)
        dna_hash = dna.get('vault_hash', '')[:32]
        
        # Generer le Rune ID
        rune_id = AvatarRuneGenerator.generate(
            avatar_id, geometric_type, rarity_tier, generation
        )
        
        # Creer le token
        token_id = hashlib.sha256(
            f"{rune_id}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        token = AvatarToken(
            token_id=token_id,
            avatar_id=avatar_id,
            vault_id=avatar_data.get('vault_id', ''),
            rune_id=rune_id,
            geometric_type=geometric_type,
            rarity_tier=rarity_tier,
            rarity_score=rarity_score,
            generation=generation,
            dna_hash=dna_hash,
            owner_address=owner_address,
            owner_vault=owner_vault,
            status="draft",
            created_at=datetime.now().isoformat()
        )
        
        self._save_token(token)
        
        return token
    
    def prepare_inscription(self, token_id: str) -> Dict:
        """
        Prepare l'inscription du token sur Bitcoin.
        
        Returns:
            Donnees pour la transaction d'inscription
        """
        token = self._tokens.get(token_id)
        if not token:
            raise ValueError(f"Token not found: {token_id}")
        
        if token.status != "draft":
            raise ValueError(f"Token already inscribed: {token.status}")
        
        # Generer les donnees OP_RETURN
        op_return = self._generate_inscription_op_return(token)
        
        # Mettre a jour le statut
        token.status = "pending"
        self._save_token(token)
        
        return {
            'token_id': token.token_id,
            'rune_id': token.rune_id,
            'owner_address': token.owner_address,
            'fee_sats': AVATAR_INSCRIPTION_FEE,
            'op_return_hex': op_return.hex(),
            'op_return_size': len(op_return),
            'metadata': {
                'type': token.geometric_type,
                'rarity': token.rarity_tier,
                'score': token.rarity_score,
                'generation': token.generation
            },
            'instructions': [
                "1. Creer une transaction Bitcoin",
                "2. Ajouter OP_RETURN avec les donnees fournies",
                "3. Envoyer 546 sats (dust) a votre adresse",
                "4. Broadcaster la transaction",
                "5. Appeler confirm_inscription(token_id, txid)"
            ]
        }
    
    def confirm_inscription(self, token_id: str, txid: str,
                           block_height: int = None) -> bool:
        """Confirme l'inscription apres broadcast"""
        token = self._tokens.get(token_id)
        if not token:
            return False
        
        token.inscription_txid = txid
        token.block_height = block_height
        token.status = "inscribed"
        token.inscribed_at = datetime.now().isoformat()
        
        self._save_token(token)
        return True
    
    def transfer_avatar(self, token_id: str, 
                        from_address: str, to_address: str,
                        from_vault: int = None, to_vault: int = None) -> TransferRequest:
        """
        Initie un transfert d'avatar.
        
        Args:
            token_id: ID du token
            from_address: Adresse source
            to_address: Adresse destination
            from_vault: Vault source (optionnel)
            to_vault: Vault destination (optionnel)
        
        Returns:
            TransferRequest avec les donnees pour la transaction
        """
        token = self._tokens.get(token_id)
        if not token:
            raise ValueError(f"Token not found: {token_id}")
        
        if token.status != "inscribed":
            raise ValueError(f"Token not inscribed: {token.status}")
        
        if token.owner_address and token.owner_address != from_address:
            raise ValueError("Not owner of this token")
        
        # Valider les adresses
        if not self._is_valid_address(from_address):
            raise ValueError("Invalid source address")
        if not self._is_valid_address(to_address):
            raise ValueError("Invalid destination address")
        
        # Generer les donnees OP_RETURN
        op_return = self._generate_transfer_op_return(token, to_address)
        
        # Creer la requete de transfert
        transfer_id = secrets.token_hex(8)
        transfer = TransferRequest(
            transfer_id=transfer_id,
            token_id=token_id,
            rune_id=token.rune_id,
            from_address=from_address,
            to_address=to_address,
            from_vault=from_vault,
            to_vault=to_vault,
            fee_sats=AVATAR_TRANSFER_FEE,
            status="pending",
            created_at=datetime.now().isoformat(),
            op_return_data=op_return
        )
        
        # Marquer le token en transfert
        token.status = "transferring"
        token.transfer_history.append({
            'transfer_id': transfer_id,
            'from_address': from_address,
            'to_address': to_address,
            'initiated_at': datetime.now().isoformat(),
            'status': 'pending'
        })
        
        self._save_token(token)
        self._save_transfer(transfer)
        
        return transfer
    
    def confirm_transfer(self, transfer_id: str, txid: str) -> bool:
        """Confirme un transfert apres broadcast"""
        transfer_file = self.transfers_dir / f"{transfer_id}.json"
        if not transfer_file.exists():
            return False
        
        with open(transfer_file, 'r', encoding='utf-8') as f:
            transfer_data = json.load(f)
        
        # Mettre a jour le transfert
        transfer_data['status'] = 'confirmed'
        transfer_data['txid'] = txid
        transfer_data['confirmed_at'] = datetime.now().isoformat()
        
        with open(transfer_file, 'w', encoding='utf-8') as f:
            json.dump(transfer_data, f, indent=2)
        
        # Mettre a jour le token
        token = self._tokens.get(transfer_data['token_id'])
        if token:
            token.owner_address = transfer_data['to_address']
            token.owner_vault = transfer_data.get('to_vault')
            token.status = "inscribed"
            
            if token.transfer_history:
                token.transfer_history[-1]['status'] = 'confirmed'
                token.transfer_history[-1]['txid'] = txid
                token.transfer_history[-1]['confirmed_at'] = datetime.now().isoformat()
            
            self._save_token(token)
        
        return True
    
    def _generate_inscription_op_return(self, token: AvatarToken) -> bytes:
        """Genere les donnees OP_RETURN pour l'inscription"""
        # Format: PREFIX(4) | MAGIC(4) | VERSION(1) | RUNE_ID(32) | DNA_HASH(16) | RARITY(1) | TYPE(1)
        data = b'PSNX'
        data += struct.pack('>I', AVATAR_MAGIC)
        data += struct.pack('>B', 1)  # Version
        data += token.rune_id.encode('utf-8')[:32].ljust(32, b'\x00')
        data += bytes.fromhex(token.dna_hash[:32].ljust(32, '0'))[:16]
        
        # Rarity code
        rarity_codes = {'common': 0, 'uncommon': 1, 'rare': 2, 'epic': 3, 
                       'legendary': 4, 'mythical': 5, 'primordial': 6}
        data += struct.pack('>B', rarity_codes.get(token.rarity_tier, 0))
        
        # Type code (geometric type index)
        type_codes = {'quantum_sphere': 0, 'spinor_torus': 1, 'bell_polyhedron': 2,
                     'clifford_lattice': 3, 'entropy_fractal': 4, '7d_projection': 5,
                     'hybrid_form': 6, 'nexus_crystal': 7}
        data += struct.pack('>B', type_codes.get(token.geometric_type, 0))
        
        return data
    
    def _generate_transfer_op_return(self, token: AvatarToken, to_address: str) -> bytes:
        """Genere les donnees OP_RETURN pour un transfert"""
        # Format: PREFIX(4) | MAGIC(4) | TRANSFER_FLAG(1) | RUNE_ID(32) | ADDR_HASH(20)
        data = b'PSNX'
        data += struct.pack('>I', AVATAR_MAGIC)
        data += struct.pack('>B', 0xFF)  # Transfer flag
        data += token.rune_id.encode('utf-8')[:32].ljust(32, b'\x00')
        data += hashlib.sha256(to_address.encode()).digest()[:20]
        
        return data
    
    def _is_valid_address(self, address: str) -> bool:
        """Valide une adresse Bitcoin"""
        if not address:
            return False
        if address.startswith('1') and 26 <= len(address) <= 35:
            return True
        if address.startswith('3') and 26 <= len(address) <= 35:
            return True
        if address.startswith('bc1') and 42 <= len(address) <= 62:
            return True
        return False
    
    # ========================================================================
    # REQUETES
    # ========================================================================
    
    def get_token(self, token_id: str) -> Optional[AvatarToken]:
        """Recupere un token par ID"""
        return self._tokens.get(token_id)
    
    def get_token_by_rune(self, rune_id: str) -> Optional[AvatarToken]:
        """Recupere un token par Rune ID"""
        for token in self._tokens.values():
            if token.rune_id == rune_id:
                return token
        return None
    
    def get_tokens_by_vault(self, vault_id: str) -> List[AvatarToken]:
        """Recupere tous les tokens d'un vault"""
        return [t for t in self._tokens.values() if t.vault_id == vault_id]
    
    def get_tokens_by_address(self, address: str) -> List[AvatarToken]:
        """Recupere tous les tokens d'une adresse"""
        return [t for t in self._tokens.values() if t.owner_address == address]
    
    def get_tokens_by_owner_vault(self, vault_number: int) -> List[AvatarToken]:
        """Recupere tous les tokens par vault proprietaire"""
        return [t for t in self._tokens.values() if t.owner_vault == vault_number]
    
    def get_all_tokens(self) -> List[AvatarToken]:
        """Recupere tous les tokens"""
        return list(self._tokens.values())
    
    def get_statistics(self) -> Dict:
        """Statistiques des tokens"""
        tokens = list(self._tokens.values())
        
        by_rarity = {}
        by_type = {}
        by_status = {}
        
        for t in tokens:
            by_rarity[t.rarity_tier] = by_rarity.get(t.rarity_tier, 0) + 1
            by_type[t.geometric_type] = by_type.get(t.geometric_type, 0) + 1
            by_status[t.status] = by_status.get(t.status, 0) + 1
        
        return {
            'total_tokens': len(tokens),
            'by_rarity': by_rarity,
            'by_type': by_type,
            'by_status': by_status,
            'inscribed': by_status.get('inscribed', 0),
            'pending': by_status.get('pending', 0) + by_status.get('draft', 0)
        }


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  AVATAR TOKENIZER TEST")
    print("=" * 60)
    
    tokenizer = AvatarTokenizer()
    
    # Simuler des donnees d'avatar
    avatar_data = {
        'avatar_id': 'test_avatar_001',
        'vault_id': 'vault_001',
        'dna': {
            'vault_hash': 'a1b2c3d4e5f6789012345678901234567890abcdef',
            'geometric_name': 'nexus_crystal',
            'rarity_tier': 'legendary',
            'rarity_score': 85.5,
            'generation': 1
        }
    }
    
    print("\n1. Creating token...")
    token = tokenizer.create_token(
        avatar_data,
        owner_address="bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
        owner_vault=1
    )
    print(f"   Token ID: {token.token_id}")
    print(f"   Rune ID: {token.rune_id}")
    print(f"   Status: {token.status}")
    
    print("\n2. Preparing inscription...")
    inscription = tokenizer.prepare_inscription(token.token_id)
    print(f"   Fee: {inscription['fee_sats']} sats")
    print(f"   OP_RETURN size: {inscription['op_return_size']} bytes")
    
    print("\n3. Confirming inscription...")
    tokenizer.confirm_inscription(token.token_id, "test_txid_12345")
    token = tokenizer.get_token(token.token_id)
    print(f"   Status: {token.status}")
    print(f"   TXID: {token.inscription_txid}")
    
    print("\n4. Statistics:")
    stats = tokenizer.get_statistics()
    for k, v in stats.items():
        print(f"   {k}: {v}")
    
    print("\n" + "=" * 60)
    print("  TEST COMPLETE")
    print("=" * 60)
