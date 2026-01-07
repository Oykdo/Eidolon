#!/usr/bin/env python3
"""
Gestionnaire d'avatars - Liaison et detachement des vaults
L'avatar est LIE au vault de creation mais peut etre DETACHE et transfere
"""

import hashlib
import json
import secrets
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from .avatar_generator import QuantumAvatarGenerator, AvatarDNA, Avatar3D
from .avatar_tokenizer import AvatarTokenizer, AvatarToken


# ============================================================================
# CONSTANTES
# ============================================================================

# Frais de detachement (en sats) - operation irreversible
DETACH_FEE = 50000  # 50k sats

# Bonus/Malus
ATTACHED_POWER_BONUS = 1.5      # +50% puissance quand attache
DETACHED_POWER_MULTIPLIER = 1.0  # Puissance normale quand detache
ORIGIN_VAULT_BONUS = 1.1        # +10% si possede par le vault d'origine


# ============================================================================
# ENUMERATIONS
# ============================================================================

class AvatarState(Enum):
    """Etat de liaison de l'avatar"""
    ATTACHED = "attached"      # Lie au vault, ne peut pas etre transfere
    DETACHED = "detached"      # Detache, peut etre transfere librement
    SOUL_BOUND = "soul_bound"  # Lie a l'ame du vault (jamais detachable)


class OwnershipType(Enum):
    """Type de propriete"""
    ORIGIN = "origin"          # Vault d'origine (createur)
    TRANSFERRED = "transferred" # Transfere depuis un autre vault
    PURCHASED = "purchased"     # Achete sur le marche


# ============================================================================
# STRUCTURES DE DONNEES
# ============================================================================

@dataclass
class AvatarBinding:
    """Informations de liaison avatar-vault"""
    avatar_id: str
    
    # Vault d'origine (immutable)
    origin_vault_id: str
    origin_vault_number: int
    origin_address: str
    created_at: str
    
    # Etat de liaison
    state: str = "attached"  # attached, detached, soul_bound
    
    # Proprietaire actuel (peut changer si detache)
    current_owner_address: Optional[str] = None
    current_owner_vault: Optional[int] = None
    ownership_type: str = "origin"
    
    # Detachement
    detached_at: Optional[str] = None
    detach_txid: Optional[str] = None
    detach_reason: Optional[str] = None
    
    # Stats affectees par la liaison
    power_multiplier: float = 1.5  # Bonus quand attache
    
    # Historique
    ownership_history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AvatarBinding':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass 
class ManagedAvatar:
    """Avatar complet avec gestion de liaison"""
    # Identifiants
    avatar_id: str
    vault_id: str
    
    # Donnees 3D
    dna: Dict
    geometry_type: str
    rarity_tier: str
    rarity_score: float
    
    # Fichiers
    obj_path: Optional[str] = None
    texture_path: Optional[str] = None
    preview_path: Optional[str] = None
    
    # Liaison
    binding: Optional[AvatarBinding] = None
    
    # Token Bitcoin
    token: Optional[AvatarToken] = None
    is_tokenized: bool = False
    
    # Stats effectives (affectees par la liaison)
    effective_power: float = 0
    attributes: Dict = field(default_factory=dict)
    
    # Metadata
    created_at: str = ""
    last_updated: str = ""
    version: int = 1
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        if self.binding:
            d['binding'] = self.binding.to_dict()
        if self.token:
            d['token'] = self.token.to_dict()
        return d
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ManagedAvatar':
        binding_data = data.pop('binding', None)
        token_data = data.pop('token', None)
        
        avatar = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        
        if binding_data:
            avatar.binding = AvatarBinding.from_dict(binding_data)
        if token_data:
            avatar.token = AvatarToken.from_dict(token_data)
        
        return avatar


# ============================================================================
# GESTIONNAIRE D'AVATARS
# ============================================================================

class AvatarManager:
    """
    Gestionnaire principal des avatars.
    
    Gere:
    - Creation d'avatars lies aux vaults
    - Detachement (liberation) des avatars
    - Transfert des avatars detaches
    - Tokenisation sur Bitcoin
    - Calcul des stats avec bonus de liaison
    """
    
    def __init__(self, data_dir: str = None):
        base_path = Path(__file__).parent.parent.parent
        self.data_dir = Path(data_dir) if data_dir else base_path / "avatars"
        
        self.avatars_dir = self.data_dir / "managed"
        self.models_dir = self.data_dir / "models"
        self.textures_dir = self.data_dir / "textures"
        self.previews_dir = self.data_dir / "previews"
        
        for d in [self.avatars_dir, self.models_dir, self.textures_dir, self.previews_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Tokenizer pour Bitcoin
        self.tokenizer = AvatarTokenizer(str(self.data_dir / "tokens"))
        
        # Cache
        self._avatars: Dict[str, ManagedAvatar] = {}
        self._load_avatars()
    
    def _load_avatars(self):
        """Charge les avatars depuis le disque"""
        for file in self.avatars_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                avatar = ManagedAvatar.from_dict(data)
                self._avatars[avatar.avatar_id] = avatar
            except Exception as e:
                print(f"[WARN] Cannot load avatar {file}: {e}")
    
    def _save_avatar(self, avatar: ManagedAvatar):
        """Sauvegarde un avatar"""
        avatar.last_updated = datetime.now().isoformat()
        file_path = self.avatars_dir / f"{avatar.avatar_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(avatar.to_dict(), f, indent=2, ensure_ascii=False)
        self._avatars[avatar.avatar_id] = avatar
    
    # ========================================================================
    # CREATION
    # ========================================================================
    
    def create_avatar(self, vault_data: bytes, vault_id: str, 
                      vault_number: int, owner_address: str,
                      generation: int = 1,
                      soul_bound: bool = False) -> ManagedAvatar:
        """
        Cree un nouvel avatar LIE au vault.
        
        L'avatar est automatiquement attache au vault de creation.
        Il peut etre detache plus tard (sauf si soul_bound=True).
        
        Args:
            vault_data: Donnees brutes du vault pour generer l'ADN
            vault_id: ID du vault
            vault_number: Numero du vault
            owner_address: Adresse Bitcoin du proprietaire
            generation: Generation de l'avatar
            soul_bound: Si True, l'avatar ne pourra JAMAIS etre detache
        
        Returns:
            ManagedAvatar lie au vault
        """
        # Generer l'avatar 3D
        generator = QuantumAvatarGenerator(
            vault_data=vault_data,
            vault_id=vault_id,
            generation=generation
        )
        
        avatar_3d = generator.generate_avatar()
        
        # Exporter les fichiers
        obj_path = self.models_dir / f"avatar_{avatar_3d.avatar_id}.obj"
        generator.export_obj(str(obj_path))
        
        texture_path = None
        preview_path = None
        
        try:
            texture_path = self.textures_dir / f"texture_{avatar_3d.avatar_id}.png"
            generator.generate_texture(str(texture_path))
            
            preview_path = self.previews_dir / f"preview_{avatar_3d.avatar_id}.png"
            generator.generate_preview(str(preview_path))
        except Exception as e:
            print(f"[WARN] Could not generate texture/preview: {e}")
        
        # Creer la liaison
        initial_state = "soul_bound" if soul_bound else "attached"
        
        binding = AvatarBinding(
            avatar_id=avatar_3d.avatar_id,
            origin_vault_id=vault_id,
            origin_vault_number=vault_number,
            origin_address=owner_address,
            created_at=datetime.now().isoformat(),
            state=initial_state,
            current_owner_address=owner_address,
            current_owner_vault=vault_number,
            ownership_type="origin",
            power_multiplier=ATTACHED_POWER_BONUS,
            ownership_history=[{
                "type": "creation",
                "vault_id": vault_id,
                "vault_number": vault_number,
                "address": owner_address,
                "timestamp": datetime.now().isoformat(),
                "state": initial_state
            }]
        )
        
        # Calculer la puissance effective
        base_power = generator.dna.rarity_score * 100
        effective_power = base_power * ATTACHED_POWER_BONUS
        
        # Creer l'avatar gere
        managed = ManagedAvatar(
            avatar_id=avatar_3d.avatar_id,
            vault_id=vault_id,
            dna=generator.dna.to_dict(),
            geometry_type=generator.dna.geometric_name,
            rarity_tier=generator.dna.rarity_tier,
            rarity_score=generator.dna.rarity_score,
            obj_path=str(obj_path),
            texture_path=str(texture_path) if texture_path else None,
            preview_path=str(preview_path) if preview_path else None,
            binding=binding,
            effective_power=effective_power,
            attributes=generator.dna.attributes,
            created_at=datetime.now().isoformat()
        )
        
        self._save_avatar(managed)
        
        return managed
    
    # ========================================================================
    # DETACHEMENT
    # ========================================================================
    
    def can_detach(self, avatar_id: str, requester_vault: int = None,
                   requester_address: str = None) -> Tuple[bool, str]:
        """
        Verifie si un avatar peut etre detache.
        
        Returns:
            (can_detach, reason)
        """
        avatar = self._avatars.get(avatar_id)
        if not avatar:
            return False, "Avatar not found"
        
        if not avatar.binding:
            return False, "Avatar has no binding information"
        
        binding = avatar.binding
        
        # Verifier l'etat
        if binding.state == "soul_bound":
            return False, "Avatar is soul-bound and can never be detached"
        
        if binding.state == "detached":
            return False, "Avatar is already detached"
        
        # Verifier la propriete
        is_owner = False
        if requester_vault and binding.current_owner_vault == requester_vault:
            is_owner = True
        if requester_address and binding.current_owner_address == requester_address:
            is_owner = True
        
        if not is_owner:
            return False, "Only the owner can detach the avatar"
        
        return True, "Avatar can be detached"
    
    def detach_avatar(self, avatar_id: str, 
                      requester_address: str,
                      requester_vault: int = None,
                      reason: str = None) -> Dict:
        """
        Detache un avatar de son vault.
        
        Une fois detache:
        - L'avatar perd son bonus de puissance (+50% -> 0%)
        - L'avatar peut etre transfere librement
        - L'avatar garde son lien d'ORIGINE (pour l'historique)
        - Le detachement est IRREVERSIBLE
        
        Args:
            avatar_id: ID de l'avatar
            requester_address: Adresse du demandeur
            requester_vault: Vault du demandeur
            reason: Raison du detachement
        
        Returns:
            Donnees pour la transaction Bitcoin de detachement
        """
        can, msg = self.can_detach(avatar_id, requester_vault, requester_address)
        if not can:
            raise ValueError(msg)
        
        avatar = self._avatars[avatar_id]
        binding = avatar.binding
        
        # Marquer comme detache
        binding.state = "detached"
        binding.detached_at = datetime.now().isoformat()
        binding.detach_reason = reason or "Owner requested detachment"
        binding.power_multiplier = DETACHED_POWER_MULTIPLIER
        
        # Ajouter a l'historique
        binding.ownership_history.append({
            "type": "detachment",
            "from_vault": binding.current_owner_vault,
            "address": requester_address,
            "timestamp": datetime.now().isoformat(),
            "reason": reason
        })
        
        # Recalculer la puissance
        base_power = avatar.rarity_score * 100
        avatar.effective_power = base_power * DETACHED_POWER_MULTIPLIER
        
        self._save_avatar(avatar)
        
        # Generer les donnees pour la transaction
        return {
            "avatar_id": avatar_id,
            "status": "detached",
            "fee_sats": DETACH_FEE,
            "power_before": base_power * ATTACHED_POWER_BONUS,
            "power_after": base_power * DETACHED_POWER_MULTIPLIER,
            "power_loss": f"-{int((ATTACHED_POWER_BONUS - 1) * 100)}%",
            "warning": "DETACHMENT IS IRREVERSIBLE. Avatar loses attachment bonus permanently.",
            "origin_vault": binding.origin_vault_number,
            "can_transfer": True
        }
    
    # ========================================================================
    # TRANSFERT
    # ========================================================================
    
    def can_transfer(self, avatar_id: str, from_address: str = None,
                     from_vault: int = None) -> Tuple[bool, str]:
        """Verifie si un avatar peut etre transfere"""
        avatar = self._avatars.get(avatar_id)
        if not avatar:
            return False, "Avatar not found"
        
        if not avatar.binding:
            return False, "Avatar has no binding information"
        
        binding = avatar.binding
        
        # Seuls les avatars detaches peuvent etre transferes
        if binding.state == "attached":
            return False, "Avatar is still attached to vault. Detach first."
        
        if binding.state == "soul_bound":
            return False, "Soul-bound avatars cannot be transferred"
        
        # Verifier la propriete
        is_owner = False
        if from_vault and binding.current_owner_vault == from_vault:
            is_owner = True
        if from_address and binding.current_owner_address == from_address:
            is_owner = True
        
        if not is_owner:
            return False, "Only the owner can transfer the avatar"
        
        return True, "Avatar can be transferred"
    
    def transfer_avatar(self, avatar_id: str,
                        from_address: str, to_address: str,
                        from_vault: int = None, to_vault: int = None) -> Dict:
        """
        Transfere un avatar DETACHE vers une nouvelle adresse.
        
        Args:
            avatar_id: ID de l'avatar
            from_address: Adresse source
            to_address: Adresse destination
            from_vault: Vault source (optionnel)
            to_vault: Vault destination (optionnel)
        
        Returns:
            Donnees pour la transaction
        """
        can, msg = self.can_transfer(avatar_id, from_address, from_vault)
        if not can:
            raise ValueError(msg)
        
        avatar = self._avatars[avatar_id]
        binding = avatar.binding
        
        # Si tokenise, utiliser le tokenizer
        if avatar.is_tokenized and avatar.token:
            transfer = self.tokenizer.transfer_avatar(
                avatar.token.token_id,
                from_address, to_address,
                from_vault, to_vault
            )
            return {
                "transfer_id": transfer.transfer_id,
                "token_transfer": True,
                "rune_id": transfer.rune_id,
                "fee_sats": transfer.fee_sats,
                "op_return_hex": transfer.op_return_data.hex() if transfer.op_return_data else None
            }
        
        # Transfert off-chain (mise a jour locale)
        old_owner = binding.current_owner_address
        old_vault = binding.current_owner_vault
        
        binding.current_owner_address = to_address
        binding.current_owner_vault = to_vault
        binding.ownership_type = "transferred"
        
        # Bonus si transfere au vault d'origine
        if to_vault == binding.origin_vault_number:
            binding.power_multiplier = ORIGIN_VAULT_BONUS
            avatar.effective_power = avatar.rarity_score * 100 * ORIGIN_VAULT_BONUS
        
        # Historique
        binding.ownership_history.append({
            "type": "transfer",
            "from_address": old_owner,
            "from_vault": old_vault,
            "to_address": to_address,
            "to_vault": to_vault,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_avatar(avatar)
        
        return {
            "avatar_id": avatar_id,
            "transferred": True,
            "from": {"address": old_owner, "vault": old_vault},
            "to": {"address": to_address, "vault": to_vault},
            "is_origin_vault": to_vault == binding.origin_vault_number,
            "power_multiplier": binding.power_multiplier
        }
    
    def confirm_transfer(self, avatar_id: str, txid: str = None) -> bool:
        """Confirme un transfert"""
        avatar = self._avatars.get(avatar_id)
        if not avatar:
            return False
        
        if avatar.binding and avatar.binding.ownership_history:
            avatar.binding.ownership_history[-1]['confirmed'] = True
            avatar.binding.ownership_history[-1]['txid'] = txid
            avatar.binding.ownership_history[-1]['confirmed_at'] = datetime.now().isoformat()
        
        self._save_avatar(avatar)
        return True
    
    # ========================================================================
    # TOKENISATION
    # ========================================================================
    
    def tokenize_avatar(self, avatar_id: str, owner_address: str) -> AvatarToken:
        """
        Tokenise un avatar sur Bitcoin.
        
        L'avatar DOIT etre DETACHE pour etre tokenise.
        Une fois tokenise, les transferts passent par la blockchain.
        """
        avatar = self._avatars.get(avatar_id)
        if not avatar:
            raise ValueError("Avatar not found")
        
        if avatar.binding and avatar.binding.state == "attached":
            raise ValueError("Avatar must be detached before tokenization")
        
        if avatar.is_tokenized:
            raise ValueError("Avatar is already tokenized")
        
        # Creer le token
        avatar_data = {
            'avatar_id': avatar.avatar_id,
            'vault_id': avatar.vault_id,
            'dna': avatar.dna
        }
        
        token = self.tokenizer.create_token(
            avatar_data,
            owner_address,
            avatar.binding.current_owner_vault if avatar.binding else None
        )
        
        avatar.token = token
        avatar.is_tokenized = True
        
        self._save_avatar(avatar)
        
        return token
    
    # ========================================================================
    # REQUETES
    # ========================================================================
    
    def get_avatar(self, avatar_id: str) -> Optional[ManagedAvatar]:
        """Recupere un avatar par ID"""
        return self._avatars.get(avatar_id)
    
    def get_avatars_by_vault(self, vault_id: str) -> List[ManagedAvatar]:
        """Recupere les avatars crees par un vault (origine)"""
        return [a for a in self._avatars.values() if a.vault_id == vault_id]
    
    def get_avatars_owned_by_vault(self, vault_number: int) -> List[ManagedAvatar]:
        """Recupere les avatars actuellement possedes par un vault"""
        return [a for a in self._avatars.values() 
                if a.binding and a.binding.current_owner_vault == vault_number]
    
    def get_avatars_by_address(self, address: str) -> List[ManagedAvatar]:
        """Recupere les avatars possedes par une adresse"""
        return [a for a in self._avatars.values()
                if a.binding and a.binding.current_owner_address == address]
    
    def get_attached_avatars(self, vault_number: int = None) -> List[ManagedAvatar]:
        """Recupere les avatars encore attaches"""
        avatars = [a for a in self._avatars.values()
                   if a.binding and a.binding.state == "attached"]
        if vault_number:
            avatars = [a for a in avatars 
                      if a.binding.current_owner_vault == vault_number]
        return avatars
    
    def get_detached_avatars(self, owner_address: str = None) -> List[ManagedAvatar]:
        """Recupere les avatars detaches"""
        avatars = [a for a in self._avatars.values()
                   if a.binding and a.binding.state == "detached"]
        if owner_address:
            avatars = [a for a in avatars
                      if a.binding.current_owner_address == owner_address]
        return avatars
    
    def get_transferable_avatars(self, owner_address: str = None,
                                  owner_vault: int = None) -> List[ManagedAvatar]:
        """Recupere les avatars qui peuvent etre transferes"""
        result = []
        for avatar in self._avatars.values():
            can, _ = self.can_transfer(avatar.avatar_id, owner_address, owner_vault)
            if can:
                result.append(avatar)
        return result
    
    def get_statistics(self) -> Dict:
        """Statistiques globales"""
        avatars = list(self._avatars.values())
        
        attached = sum(1 for a in avatars if a.binding and a.binding.state == "attached")
        detached = sum(1 for a in avatars if a.binding and a.binding.state == "detached")
        soul_bound = sum(1 for a in avatars if a.binding and a.binding.state == "soul_bound")
        tokenized = sum(1 for a in avatars if a.is_tokenized)
        
        by_rarity = {}
        for a in avatars:
            by_rarity[a.rarity_tier] = by_rarity.get(a.rarity_tier, 0) + 1
        
        by_type = {}
        for a in avatars:
            by_type[a.geometry_type] = by_type.get(a.geometry_type, 0) + 1
        
        return {
            "total_avatars": len(avatars),
            "attached": attached,
            "detached": detached,
            "soul_bound": soul_bound,
            "tokenized": tokenized,
            "by_rarity": by_rarity,
            "by_type": by_type
        }
    
    def get_avatar_info(self, avatar_id: str) -> Optional[Dict]:
        """Informations detaillees sur un avatar"""
        avatar = self._avatars.get(avatar_id)
        if not avatar:
            return None
        
        binding = avatar.binding
        
        return {
            "avatar_id": avatar.avatar_id,
            "vault_id": avatar.vault_id,
            "geometry_type": avatar.geometry_type,
            "rarity": {
                "tier": avatar.rarity_tier,
                "score": avatar.rarity_score
            },
            "power": {
                "base": avatar.rarity_score * 100,
                "multiplier": binding.power_multiplier if binding else 1.0,
                "effective": avatar.effective_power
            },
            "binding": {
                "state": binding.state if binding else "unknown",
                "origin_vault": binding.origin_vault_number if binding else None,
                "current_owner": binding.current_owner_address if binding else None,
                "current_vault": binding.current_owner_vault if binding else None,
                "can_detach": binding.state == "attached" if binding else False,
                "can_transfer": binding.state == "detached" if binding else False
            },
            "tokenized": avatar.is_tokenized,
            "token_id": avatar.token.token_id if avatar.token else None,
            "rune_id": avatar.token.rune_id if avatar.token else None,
            "files": {
                "model": avatar.obj_path,
                "texture": avatar.texture_path,
                "preview": avatar.preview_path
            },
            "created_at": avatar.created_at
        }


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  AVATAR MANAGER TEST")
    print("=" * 60)
    
    manager = AvatarManager()
    
    # Creer un avatar lie
    print("\n1. Creating ATTACHED avatar...")
    vault_data = b"test_vault_data_for_avatar_generation"
    
    avatar = manager.create_avatar(
        vault_data=vault_data,
        vault_id="vault_test_001",
        vault_number=1,
        owner_address="bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
        generation=1,
        soul_bound=False
    )
    
    print(f"   Avatar ID: {avatar.avatar_id}")
    print(f"   Type: {avatar.geometry_type}")
    print(f"   Rarity: {avatar.rarity_tier} ({avatar.rarity_score:.1f})")
    print(f"   State: {avatar.binding.state}")
    print(f"   Power: {avatar.effective_power:.0f} (with +50% bonus)")
    
    # Verifier le detachement
    print("\n2. Checking detachment...")
    can, msg = manager.can_detach(
        avatar.avatar_id,
        requester_vault=1,
        requester_address="bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
    )
    print(f"   Can detach: {can} - {msg}")
    
    # Detacher
    print("\n3. Detaching avatar...")
    detach_result = manager.detach_avatar(
        avatar.avatar_id,
        requester_address="bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
        requester_vault=1,
        reason="Test detachment"
    )
    print(f"   Status: {detach_result['status']}")
    print(f"   Power before: {detach_result['power_before']:.0f}")
    print(f"   Power after: {detach_result['power_after']:.0f}")
    print(f"   Power loss: {detach_result['power_loss']}")
    
    # Verifier le transfert
    print("\n4. Checking transfer...")
    can, msg = manager.can_transfer(
        avatar.avatar_id,
        from_address="bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
    )
    print(f"   Can transfer: {can} - {msg}")
    
    # Transferer
    print("\n5. Transferring avatar...")
    transfer_result = manager.transfer_avatar(
        avatar.avatar_id,
        from_address="bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
        to_address="bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
        from_vault=1,
        to_vault=2
    )
    print(f"   Transferred: {transfer_result['transferred']}")
    print(f"   From: Vault #{transfer_result['from']['vault']}")
    print(f"   To: Vault #{transfer_result['to']['vault']}")
    
    # Stats
    print("\n6. Statistics:")
    stats = manager.get_statistics()
    for k, v in stats.items():
        print(f"   {k}: {v}")
    
    # Info complete
    print("\n7. Avatar info:")
    info = manager.get_avatar_info(avatar.avatar_id)
    print(f"   State: {info['binding']['state']}")
    print(f"   Current owner vault: {info['binding']['current_vault']}")
    print(f"   Can detach: {info['binding']['can_detach']}")
    print(f"   Can transfer: {info['binding']['can_transfer']}")
    
    print("\n" + "=" * 60)
    print("  TEST COMPLETE")
    print("=" * 60)
