#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         ITEM RUNES EXCHANGE - Poly-Spinor Nexus 7D                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Systeme d'echange d'items via le protocole RUNES sur Bitcoin.              ║
║                                                                              ║
║  FONCTIONNALITES:                                                            ║
║  - Inscription d'items comme Runes sur Bitcoin                               ║
║  - Generation de Rune ID unique par item                                     ║
║  - Transfert d'items entre vaults via transactions Bitcoin                   ║
║  - Marche P2P pour l'echange d'items                                         ║
║  - Historique des transactions on-chain                                      ║
║                                                                              ║
║  PROTOCOLE RUNES:                                                            ║
║  - Runes permet des tokens fongibles sur Bitcoin                             ║
║  - Chaque item devient un Rune unique (NFT-like)                             ║
║  - Transfert atomique via OP_RETURN                                          ║
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


# ============================================================================
# CONSTANTES
# ============================================================================

# Prefixe pour les Runes d'items PSNX
PSNX_RUNE_PREFIX = "PSNX"
RUNE_MAGIC_NUMBER = 0x52554E45  # "RUNE" en hex

# Frais de transaction (en sats)
MIN_INSCRIPTION_FEE = 10000  # 10k sats
MIN_TRANSFER_FEE = 5000      # 5k sats

# Limites
MAX_ITEMS_PER_TX = 10
INSCRIPTION_COOLDOWN = 600  # 10 minutes entre inscriptions


# ============================================================================
# ENUMERATIONS
# ============================================================================

class RuneItemStatus(Enum):
    """Statut d'un item sur la blockchain"""
    PENDING = "pending"           # En attente d'inscription
    INSCRIBED = "inscribed"       # Inscrit sur Bitcoin
    TRANSFERRING = "transferring" # Transfert en cours
    CONFIRMED = "confirmed"       # Transfert confirme
    BURNED = "burned"             # Detruit (item consomme)


class ListingStatus(Enum):
    """Statut d'une annonce de vente"""
    ACTIVE = "active"
    SOLD = "sold"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


# ============================================================================
# STRUCTURES DE DONNEES
# ============================================================================

@dataclass
class RuneItemInscription:
    """Inscription d'un item comme Rune"""
    inscription_id: str          # ID unique d'inscription
    item_id: str                 # ID de l'item original
    rune_id: str                 # ID du Rune sur Bitcoin (format: PSNX.XXXXX)
    
    # Metadonnees de l'item
    item_type: str
    category: str
    rarity: str
    stat_power: float
    
    # Blockchain
    txid: Optional[str] = None   # Transaction d'inscription
    block_height: Optional[int] = None
    confirmations: int = 0
    
    # Ownership
    owner_vault: int = 0
    owner_address: Optional[str] = None
    
    # Status
    status: str = "pending"
    inscribed_at: Optional[str] = None
    
    # Historique
    transfer_history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RuneItemInscription':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ItemListing:
    """Annonce de vente d'un item"""
    listing_id: str
    inscription_id: str
    item_id: str
    rune_id: str
    
    # Prix
    price_sats: int              # Prix en satoshis
    price_btc: float             # Prix en BTC
    price_runes: int = 0         # Prix en PSNX Runes (alternatif)
    
    # Vendeur
    seller_vault: int = 0
    seller_address: Optional[str] = None
    
    # Item info
    item_type: str = ""
    rarity: str = ""
    stat_power: float = 0.0
    
    # Status
    status: str = "active"
    created_at: str = ""
    expires_at: Optional[str] = None
    
    # Acheteur (si vendu)
    buyer_vault: Optional[int] = None
    buyer_address: Optional[str] = None
    sold_at: Optional[str] = None
    sale_txid: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ItemListing':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TradeOffer:
    """Offre d'echange entre items"""
    offer_id: str
    
    # Offrant
    offerer_vault: int
    offered_items: List[str]     # Liste des inscription_ids offerts
    
    # Demande
    target_vault: int
    requested_items: List[str]   # Liste des inscription_ids demandes
    
    # Compensation optionnelle en sats
    sats_offered: int = 0
    sats_requested: int = 0
    
    # Status
    status: str = "pending"      # pending, accepted, rejected, expired
    created_at: str = ""
    expires_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# GENERATEUR DE RUNE ID
# ============================================================================

class RuneIdGenerator:
    """Generateur d'identifiants Rune uniques pour les items"""
    
    @staticmethod
    def generate_rune_id(item_id: str, item_type: str, rarity: str, 
                         vault_number: int) -> str:
        """
        Genere un Rune ID unique pour un item.
        Format: PSNX.CATEGORY.RARITY.XXXXX
        
        Args:
            item_id: ID de l'item
            item_type: Type d'item
            rarity: Rarete
            vault_number: Numero du vault d'origine
        
        Returns:
            Rune ID unique
        """
        # Creer un hash unique
        data = f"{item_id}{item_type}{rarity}{vault_number}{secrets.token_hex(8)}"
        hash_bytes = hashlib.sha256(data.encode()).digest()
        
        # Extraire les composants
        category_code = item_type[:3].upper()
        rarity_code = rarity[0].upper()
        unique_id = hash_bytes[:4].hex().upper()
        
        return f"{PSNX_RUNE_PREFIX}.{category_code}.{rarity_code}.{unique_id}"
    
    @staticmethod
    def parse_rune_id(rune_id: str) -> Dict[str, str]:
        """Parse un Rune ID en ses composants."""
        parts = rune_id.split('.')
        if len(parts) != 4 or parts[0] != PSNX_RUNE_PREFIX:
            return {}
        
        return {
            'prefix': parts[0],
            'category': parts[1],
            'rarity': parts[2],
            'unique': parts[3]
        }
    
    @staticmethod
    def validate_rune_id(rune_id: str) -> bool:
        """Valide le format d'un Rune ID."""
        parts = rune_id.split('.')
        return (len(parts) == 4 and 
                parts[0] == PSNX_RUNE_PREFIX and
                len(parts[1]) == 3 and
                len(parts[2]) == 1 and
                len(parts[3]) == 8)


# ============================================================================
# GESTIONNAIRE D'ECHANGE
# ============================================================================

class ItemRunesExchange:
    """
    Gestionnaire d'echange d'items via le protocole Runes.
    
    Permet:
    - Inscription d'items comme Runes
    - Transfert entre vaults
    - Marche P2P
    - Echanges directs
    """
    
    def __init__(self, data_dir: str = None):
        """
        Initialise le gestionnaire d'echange.
        
        Args:
            data_dir: Repertoire de donnees
        """
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            base_path = Path(__file__).parent.parent
            self.data_dir = base_path / "runes_exchange"
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Sous-repertoires
        self.inscriptions_dir = self.data_dir / "inscriptions"
        self.listings_dir = self.data_dir / "listings"
        self.offers_dir = self.data_dir / "offers"
        self.history_dir = self.data_dir / "history"
        
        for d in [self.inscriptions_dir, self.listings_dir, 
                  self.offers_dir, self.history_dir]:
            d.mkdir(exist_ok=True)
        
        self.rune_generator = RuneIdGenerator()
    
    # ========================================================================
    # INSCRIPTION D'ITEMS
    # ========================================================================
    
    def inscribe_item(self, item_data: Dict, vault_number: int,
                      owner_address: str = None) -> RuneItemInscription:
        """
        Inscrit un item comme Rune sur Bitcoin.
        
        Args:
            item_data: Donnees de l'item a inscrire
            vault_number: Numero du vault proprietaire
            owner_address: Adresse Bitcoin du proprietaire
        
        Returns:
            RuneItemInscription
        """
        item_id = item_data.get('item_id', '')
        item_type = item_data.get('item_type', 'unknown')
        category = item_data.get('category', 'misc')
        rarity = item_data.get('rarity', 'common')
        stat_power = item_data.get('stat_power', 0)
        
        # Generer le Rune ID
        rune_id = self.rune_generator.generate_rune_id(
            item_id, item_type, rarity, vault_number
        )
        
        # Creer l'inscription
        inscription_id = hashlib.sha256(
            f"{rune_id}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        inscription = RuneItemInscription(
            inscription_id=inscription_id,
            item_id=item_id,
            rune_id=rune_id,
            item_type=item_type,
            category=category,
            rarity=rarity,
            stat_power=stat_power,
            owner_vault=vault_number,
            owner_address=owner_address,
            status="pending",
            inscribed_at=datetime.now().isoformat()
        )
        
        # Sauvegarder
        self._save_inscription(inscription)
        
        return inscription
    
    def confirm_inscription(self, inscription_id: str, txid: str,
                           block_height: int = None) -> bool:
        """
        Confirme une inscription apres broadcast sur Bitcoin.
        
        Args:
            inscription_id: ID de l'inscription
            txid: Transaction ID
            block_height: Hauteur du bloc (optionnel)
        
        Returns:
            True si succes
        """
        inscription = self.get_inscription(inscription_id)
        if not inscription:
            return False
        
        inscription.txid = txid
        inscription.block_height = block_height
        inscription.status = "inscribed"
        inscription.confirmations = 0
        
        self._save_inscription(inscription)
        return True
    
    def get_inscription(self, inscription_id: str) -> Optional[RuneItemInscription]:
        """Recupere une inscription par ID."""
        file_path = self.inscriptions_dir / f"{inscription_id}.json"
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return RuneItemInscription.from_dict(data)
    
    def get_inscription_by_item(self, item_id: str) -> Optional[RuneItemInscription]:
        """Recupere l'inscription d'un item specifique."""
        for file in self.inscriptions_dir.glob("*.json"):
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('item_id') == item_id:
                return RuneItemInscription.from_dict(data)
        return None
    
    def get_vault_inscriptions(self, vault_number: int) -> List[RuneItemInscription]:
        """Recupere toutes les inscriptions d'un vault."""
        inscriptions = []
        for file in self.inscriptions_dir.glob("*.json"):
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('owner_vault') == vault_number:
                inscriptions.append(RuneItemInscription.from_dict(data))
        return inscriptions
    
    # ========================================================================
    # TRANSFERTS
    # ========================================================================
    
    def initiate_transfer(self, inscription_id: str, 
                         from_vault: int, to_vault: int,
                         to_address: str = None) -> Dict:
        """
        Initie un transfert d'item entre vaults.
        
        Args:
            inscription_id: ID de l'inscription a transferer
            from_vault: Vault source
            to_vault: Vault destination
            to_address: Adresse Bitcoin destination
        
        Returns:
            Donnees du transfert
        """
        inscription = self.get_inscription(inscription_id)
        if not inscription:
            return {"error": "Inscription not found"}
        
        if inscription.owner_vault != from_vault:
            return {"error": "Not owner of this item"}
        
        if inscription.status != "inscribed":
            return {"error": f"Cannot transfer: status is {inscription.status}"}
        
        # Marquer en transfert
        inscription.status = "transferring"
        
        # Ajouter a l'historique
        transfer_record = {
            "type": "transfer",
            "from_vault": from_vault,
            "to_vault": to_vault,
            "to_address": to_address,
            "initiated_at": datetime.now().isoformat(),
            "status": "pending"
        }
        inscription.transfer_history.append(transfer_record)
        
        self._save_inscription(inscription)
        
        # Generer les donnees pour la transaction Bitcoin
        transfer_data = {
            "inscription_id": inscription_id,
            "rune_id": inscription.rune_id,
            "from_vault": from_vault,
            "to_vault": to_vault,
            "to_address": to_address,
            "op_return_data": self._generate_transfer_op_return(
                inscription.rune_id, to_vault
            ),
            "estimated_fee": MIN_TRANSFER_FEE
        }
        
        return transfer_data
    
    def confirm_transfer(self, inscription_id: str, txid: str,
                        new_owner_vault: int, new_owner_address: str = None) -> bool:
        """
        Confirme un transfert apres broadcast sur Bitcoin.
        """
        inscription = self.get_inscription(inscription_id)
        if not inscription:
            return False
        
        # Mettre a jour le proprietaire
        inscription.owner_vault = new_owner_vault
        inscription.owner_address = new_owner_address
        inscription.status = "inscribed"
        
        # Mettre a jour l'historique
        if inscription.transfer_history:
            inscription.transfer_history[-1]["status"] = "confirmed"
            inscription.transfer_history[-1]["txid"] = txid
            inscription.transfer_history[-1]["confirmed_at"] = datetime.now().isoformat()
        
        self._save_inscription(inscription)
        return True
    
    def _generate_transfer_op_return(self, rune_id: str, to_vault: int) -> bytes:
        """Genere les donnees OP_RETURN pour un transfert Rune."""
        # Format: RUNE_MAGIC | RUNE_ID | TO_VAULT
        data = struct.pack('>I', RUNE_MAGIC_NUMBER)  # Magic number
        data += rune_id.encode('utf-8')[:32].ljust(32, b'\x00')  # Rune ID (32 bytes)
        data += struct.pack('>I', to_vault)  # Vault destination
        return data
    
    # ========================================================================
    # MARCHE P2P
    # ========================================================================
    
    def create_listing(self, inscription_id: str, price_sats: int,
                      seller_vault: int, expires_hours: int = 168) -> ItemListing:
        """
        Cree une annonce de vente pour un item.
        
        Args:
            inscription_id: ID de l'inscription a vendre
            price_sats: Prix en satoshis
            seller_vault: Vault du vendeur
            expires_hours: Duree de validite en heures
        
        Returns:
            ItemListing
        """
        inscription = self.get_inscription(inscription_id)
        if not inscription:
            raise ValueError("Inscription not found")
        
        if inscription.owner_vault != seller_vault:
            raise ValueError("Not owner of this item")
        
        listing_id = secrets.token_hex(8)
        
        listing = ItemListing(
            listing_id=listing_id,
            inscription_id=inscription_id,
            item_id=inscription.item_id,
            rune_id=inscription.rune_id,
            price_sats=price_sats,
            price_btc=price_sats / 100_000_000,
            seller_vault=seller_vault,
            seller_address=inscription.owner_address,
            item_type=inscription.item_type,
            rarity=inscription.rarity,
            stat_power=inscription.stat_power,
            status="active",
            created_at=datetime.now().isoformat()
        )
        
        if expires_hours:
            from datetime import timedelta
            expires = datetime.now() + timedelta(hours=expires_hours)
            listing.expires_at = expires.isoformat()
        
        self._save_listing(listing)
        return listing
    
    def buy_listing(self, listing_id: str, buyer_vault: int,
                   buyer_address: str = None) -> Dict:
        """
        Achete un item en vente.
        
        Args:
            listing_id: ID de l'annonce
            buyer_vault: Vault de l'acheteur
            buyer_address: Adresse Bitcoin de l'acheteur
        
        Returns:
            Donnees de la transaction
        """
        listing = self.get_listing(listing_id)
        if not listing:
            return {"error": "Listing not found"}
        
        if listing.status != "active":
            return {"error": f"Listing is {listing.status}"}
        
        if listing.seller_vault == buyer_vault:
            return {"error": "Cannot buy your own listing"}
        
        # Verifier expiration
        if listing.expires_at:
            expires = datetime.fromisoformat(listing.expires_at)
            if datetime.now() > expires:
                listing.status = "expired"
                self._save_listing(listing)
                return {"error": "Listing has expired"}
        
        # Preparer la transaction
        purchase_data = {
            "listing_id": listing_id,
            "inscription_id": listing.inscription_id,
            "rune_id": listing.rune_id,
            "price_sats": listing.price_sats,
            "seller_address": listing.seller_address,
            "buyer_vault": buyer_vault,
            "buyer_address": buyer_address,
            "total_sats": listing.price_sats + MIN_TRANSFER_FEE
        }
        
        return purchase_data
    
    def confirm_purchase(self, listing_id: str, txid: str,
                        buyer_vault: int, buyer_address: str = None) -> bool:
        """Confirme un achat apres paiement."""
        listing = self.get_listing(listing_id)
        if not listing:
            return False
        
        # Marquer comme vendu
        listing.status = "sold"
        listing.buyer_vault = buyer_vault
        listing.buyer_address = buyer_address
        listing.sold_at = datetime.now().isoformat()
        listing.sale_txid = txid
        
        self._save_listing(listing)
        
        # Transferer la propriete de l'inscription
        self.confirm_transfer(
            listing.inscription_id, txid, buyer_vault, buyer_address
        )
        
        # Enregistrer dans l'historique
        self._record_sale(listing, txid)
        
        return True
    
    def cancel_listing(self, listing_id: str, seller_vault: int) -> bool:
        """Annule une annonce de vente."""
        listing = self.get_listing(listing_id)
        if not listing:
            return False
        
        if listing.seller_vault != seller_vault:
            return False
        
        if listing.status != "active":
            return False
        
        listing.status = "cancelled"
        self._save_listing(listing)
        return True
    
    def get_listing(self, listing_id: str) -> Optional[ItemListing]:
        """Recupere une annonce par ID."""
        file_path = self.listings_dir / f"{listing_id}.json"
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return ItemListing.from_dict(data)
    
    def get_active_listings(self, 
                           rarity_filter: str = None,
                           category_filter: str = None,
                           max_price_sats: int = None,
                           sort_by: str = "price") -> List[ItemListing]:
        """Recupere les annonces actives avec filtres."""
        listings = []
        
        for file in self.listings_dir.glob("*.json"):
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('status') != 'active':
                continue
            
            # Verifier expiration
            if data.get('expires_at'):
                expires = datetime.fromisoformat(data['expires_at'])
                if datetime.now() > expires:
                    continue
            
            # Appliquer filtres
            if rarity_filter and data.get('rarity') != rarity_filter:
                continue
            if max_price_sats and data.get('price_sats', 0) > max_price_sats:
                continue
            
            listings.append(ItemListing.from_dict(data))
        
        # Trier
        if sort_by == "price":
            listings.sort(key=lambda x: x.price_sats)
        elif sort_by == "power":
            listings.sort(key=lambda x: x.stat_power, reverse=True)
        elif sort_by == "recent":
            listings.sort(key=lambda x: x.created_at, reverse=True)
        
        return listings
    
    # ========================================================================
    # ECHANGES DIRECTS (TRADES)
    # ========================================================================
    
    def create_trade_offer(self, offerer_vault: int, offered_items: List[str],
                          target_vault: int, requested_items: List[str],
                          sats_offered: int = 0, sats_requested: int = 0,
                          expires_hours: int = 24) -> TradeOffer:
        """
        Cree une offre d'echange direct entre vaults.
        
        Args:
            offerer_vault: Vault qui propose
            offered_items: Items offerts (inscription IDs)
            target_vault: Vault cible
            requested_items: Items demandes (inscription IDs)
            sats_offered: Sats offerts en plus
            sats_requested: Sats demandes en plus
            expires_hours: Duree de validite
        
        Returns:
            TradeOffer
        """
        # Verifier que l'offrant possede les items offerts
        for insc_id in offered_items:
            inscription = self.get_inscription(insc_id)
            if not inscription or inscription.owner_vault != offerer_vault:
                raise ValueError(f"Cannot offer item {insc_id}: not owned")
        
        # Verifier que la cible possede les items demandes
        for insc_id in requested_items:
            inscription = self.get_inscription(insc_id)
            if not inscription or inscription.owner_vault != target_vault:
                raise ValueError(f"Cannot request item {insc_id}: not owned by target")
        
        offer_id = secrets.token_hex(8)
        
        from datetime import timedelta
        expires = datetime.now() + timedelta(hours=expires_hours)
        
        offer = TradeOffer(
            offer_id=offer_id,
            offerer_vault=offerer_vault,
            offered_items=offered_items,
            target_vault=target_vault,
            requested_items=requested_items,
            sats_offered=sats_offered,
            sats_requested=sats_requested,
            status="pending",
            created_at=datetime.now().isoformat(),
            expires_at=expires.isoformat()
        )
        
        self._save_offer(offer)
        return offer
    
    def accept_trade_offer(self, offer_id: str, accepter_vault: int) -> Dict:
        """
        Accepte une offre d'echange.
        
        Returns:
            Donnees pour la transaction atomique
        """
        offer = self.get_offer(offer_id)
        if not offer:
            return {"error": "Offer not found"}
        
        if offer.target_vault != accepter_vault:
            return {"error": "This offer is not for you"}
        
        if offer.status != "pending":
            return {"error": f"Offer is {offer.status}"}
        
        # Verifier expiration
        if offer.expires_at:
            expires = datetime.fromisoformat(offer.expires_at)
            if datetime.now() > expires:
                offer.status = "expired"
                self._save_offer(offer)
                return {"error": "Offer has expired"}
        
        # Preparer l'echange atomique
        trade_data = {
            "offer_id": offer_id,
            "offerer_vault": offer.offerer_vault,
            "accepter_vault": accepter_vault,
            "items_to_offerer": offer.requested_items,
            "items_to_accepter": offer.offered_items,
            "sats_to_offerer": offer.sats_requested,
            "sats_to_accepter": offer.sats_offered,
            "total_transfers": len(offer.offered_items) + len(offer.requested_items)
        }
        
        return trade_data
    
    def confirm_trade(self, offer_id: str, txid: str) -> bool:
        """Confirme un echange apres execution."""
        offer = self.get_offer(offer_id)
        if not offer:
            return False
        
        # Transferer les items offerts vers la cible
        for insc_id in offer.offered_items:
            self.confirm_transfer(insc_id, txid, offer.target_vault)
        
        # Transferer les items demandes vers l'offrant
        for insc_id in offer.requested_items:
            self.confirm_transfer(insc_id, txid, offer.offerer_vault)
        
        offer.status = "accepted"
        self._save_offer(offer)
        
        return True
    
    def reject_trade_offer(self, offer_id: str, rejector_vault: int) -> bool:
        """Rejette une offre d'echange."""
        offer = self.get_offer(offer_id)
        if not offer:
            return False
        
        if offer.target_vault != rejector_vault:
            return False
        
        offer.status = "rejected"
        self._save_offer(offer)
        return True
    
    def get_offer(self, offer_id: str) -> Optional[TradeOffer]:
        """Recupere une offre par ID."""
        file_path = self.offers_dir / f"{offer_id}.json"
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return TradeOffer(**data)
    
    def get_pending_offers_for_vault(self, vault_number: int) -> List[TradeOffer]:
        """Recupere les offres en attente pour un vault."""
        offers = []
        for file in self.offers_dir.glob("*.json"):
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if (data.get('status') == 'pending' and 
                data.get('target_vault') == vault_number):
                offers.append(TradeOffer(**data))
        return offers
    
    # ========================================================================
    # UTILITAIRES
    # ========================================================================
    
    def _save_inscription(self, inscription: RuneItemInscription):
        """Sauvegarde une inscription."""
        file_path = self.inscriptions_dir / f"{inscription.inscription_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(inscription.to_dict(), f, indent=2, ensure_ascii=False)
    
    def _save_listing(self, listing: ItemListing):
        """Sauvegarde une annonce."""
        file_path = self.listings_dir / f"{listing.listing_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(listing.to_dict(), f, indent=2, ensure_ascii=False)
    
    def _save_offer(self, offer: TradeOffer):
        """Sauvegarde une offre."""
        file_path = self.offers_dir / f"{offer.offer_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(offer.to_dict(), f, indent=2, ensure_ascii=False)
    
    def _record_sale(self, listing: ItemListing, txid: str):
        """Enregistre une vente dans l'historique."""
        record = {
            "type": "sale",
            "listing_id": listing.listing_id,
            "rune_id": listing.rune_id,
            "item_type": listing.item_type,
            "rarity": listing.rarity,
            "price_sats": listing.price_sats,
            "seller_vault": listing.seller_vault,
            "buyer_vault": listing.buyer_vault,
            "txid": txid,
            "timestamp": datetime.now().isoformat()
        }
        
        history_file = self.history_dir / f"sales_{datetime.now().strftime('%Y%m')}.json"
        
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
        
        history.append(record)
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    
    def get_market_stats(self) -> Dict:
        """Calcule les statistiques du marche."""
        total_listings = 0
        active_listings = 0
        total_volume_sats = 0
        avg_price_sats = 0
        
        # Compter les annonces
        for file in self.listings_dir.glob("*.json"):
            total_listings += 1
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('status') == 'active':
                active_listings += 1
            if data.get('status') == 'sold':
                total_volume_sats += data.get('price_sats', 0)
        
        # Calculer moyenne si ventes
        sold_count = total_listings - active_listings
        if sold_count > 0:
            avg_price_sats = total_volume_sats // sold_count
        
        return {
            "total_listings": total_listings,
            "active_listings": active_listings,
            "sold_count": sold_count,
            "total_volume_sats": total_volume_sats,
            "total_volume_btc": total_volume_sats / 100_000_000,
            "avg_price_sats": avg_price_sats
        }


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  TEST ITEM RUNES EXCHANGE")
    print("=" * 60)
    
    # Creer le gestionnaire
    exchange = ItemRunesExchange()
    
    # Simuler un item
    test_item = {
        "item_id": "test123456",
        "item_type": "potion_power",
        "category": "potion",
        "rarity": "legendary",
        "stat_power": 4500
    }
    
    # Inscrire l'item
    print("\n1. Inscription d'un item...")
    inscription = exchange.inscribe_item(test_item, vault_number=1)
    print(f"   Inscription ID: {inscription.inscription_id}")
    print(f"   Rune ID: {inscription.rune_id}")
    print(f"   Status: {inscription.status}")
    
    # Confirmer l'inscription
    print("\n2. Confirmation d'inscription...")
    exchange.confirm_inscription(
        inscription.inscription_id, 
        txid="abc123def456"
    )
    inscription = exchange.get_inscription(inscription.inscription_id)
    print(f"   Status: {inscription.status}")
    
    # Creer une annonce
    print("\n3. Creation d'une annonce de vente...")
    listing = exchange.create_listing(
        inscription.inscription_id,
        price_sats=100000,  # 0.001 BTC
        seller_vault=1
    )
    print(f"   Listing ID: {listing.listing_id}")
    print(f"   Price: {listing.price_sats} sats ({listing.price_btc} BTC)")
    
    # Afficher les annonces actives
    print("\n4. Annonces actives:")
    listings = exchange.get_active_listings()
    for l in listings:
        print(f"   - {l.rune_id}: {l.price_sats} sats [{l.rarity}]")
    
    # Stats du marche
    print("\n5. Stats du marche:")
    stats = exchange.get_market_stats()
    for k, v in stats.items():
        print(f"   {k}: {v}")
    
    print("\n" + "=" * 60)
    print("  TEST TERMINE")
    print("=" * 60)
