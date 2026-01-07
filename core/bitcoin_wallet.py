"""
Module Wallet Bitcoin pour Eidolon
Support des actifs Bitcoin: BRC-20, ARC-20, Runes, Ordinals, Bitmap

Protocoles supportes:
- Bitcoin natif (BTC)
- Ordinals (inscriptions NFT)
- BRC-20 (tokens sur Bitcoin via Ordinals)
- ARC-20 (tokens Atomicals)
- Runes (protocole de tokens fongibles)
- Bitmap (metaverse sur Ordinals)
"""

import os
import sys
import json
import hashlib
import secrets
import struct
import requests
from typing import Optional, Dict, List, Tuple, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
from decimal import Decimal
from datetime import datetime

# Cryptography
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# Bitcoin-specific imports
try:
    import hashlib
    import hmac
    BITCOIN_CRYPTO_AVAILABLE = True
except ImportError:
    BITCOIN_CRYPTO_AVAILABLE = False


# ============================================================================
# CONSTANTES BITCOIN
# ============================================================================

# Prefixes des adresses Bitcoin
MAINNET_P2PKH_PREFIX = b'\x00'
MAINNET_P2SH_PREFIX = b'\x05'
MAINNET_BECH32_HRP = 'bc'
TESTNET_P2PKH_PREFIX = b'\x6f'
TESTNET_P2SH_PREFIX = b'\xc4'
TESTNET_BECH32_HRP = 'tb'

# APIs publiques
MEMPOOL_API = "https://mempool.space/api"
ORDINALS_API = "https://ordinals.com/api"
HIRO_API = "https://api.hiro.so"
ATOMICALS_API = "https://ep.atomicals.xyz/proxy"


# ============================================================================
# ENUMERATIONS
# ============================================================================

class BitcoinNetwork(Enum):
    """Reseaux Bitcoin"""
    MAINNET = ("mainnet", MAINNET_P2PKH_PREFIX, MAINNET_BECH32_HRP)
    TESTNET = ("testnet", TESTNET_P2PKH_PREFIX, TESTNET_BECH32_HRP)
    SIGNET = ("signet", TESTNET_P2PKH_PREFIX, "tb")
    
    def __init__(self, name: str, p2pkh_prefix: bytes, bech32_hrp: str):
        self._name = name
        self.p2pkh_prefix = p2pkh_prefix
        self.bech32_hrp = bech32_hrp


class BitcoinAssetType(Enum):
    """Types d'actifs Bitcoin"""
    BTC = "btc"
    ORDINAL = "ordinal"
    BRC20 = "brc20"
    ARC20 = "arc20"
    RUNE = "rune"
    BITMAP = "bitmap"
    INSCRIPTION = "inscription"


class AddressType(Enum):
    """Types d'adresses Bitcoin"""
    P2PKH = "p2pkh"      # Legacy (1...)
    P2SH = "p2sh"        # SegWit wrapped (3...)
    P2WPKH = "p2wpkh"    # Native SegWit (bc1q...)
    P2TR = "p2tr"        # Taproot (bc1p...)


# ============================================================================
# STRUCTURES DE DONNEES
# ============================================================================

@dataclass
class UTXO:
    """Unspent Transaction Output"""
    txid: str
    vout: int
    value: int  # satoshis
    script_pubkey: str
    address: str
    confirmations: int
    inscriptions: List[str] = field(default_factory=list)
    runes: Dict[str, int] = field(default_factory=dict)
    
    @property
    def is_ordinal(self) -> bool:
        return len(self.inscriptions) > 0
    
    @property
    def has_runes(self) -> bool:
        return len(self.runes) > 0


@dataclass
class Inscription:
    """Ordinal Inscription"""
    inscription_id: str
    inscription_number: int
    content_type: str
    content_length: int
    genesis_txid: str
    genesis_height: int
    genesis_fee: int
    output_value: int
    sat_ordinal: int
    sat_rarity: str
    address: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BRC20Token:
    """Token BRC-20"""
    tick: str
    balance: Decimal
    transferable_balance: Decimal
    available_balance: Decimal
    decimals: int = 18
    
    def formatted_balance(self) -> str:
        return f"{self.available_balance:.8f}"


@dataclass
class ARC20Token:
    """Token ARC-20 (Atomicals)"""
    atomical_id: str
    ticker: str
    balance: int
    confirmed_balance: int
    atomical_number: int
    type: str  # 'FT' or 'NFT'
    mint_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Rune:
    """Rune token"""
    rune_id: str
    name: str
    symbol: str
    balance: int
    divisibility: int
    spacers: int
    etching_txid: str
    
    def formatted_balance(self) -> str:
        if self.divisibility > 0:
            return str(Decimal(self.balance) / Decimal(10 ** self.divisibility))
        return str(self.balance)


@dataclass
class Bitmap:
    """Bitmap inscription"""
    inscription_id: str
    block_number: int
    district: Optional[str]
    parcel: Optional[str]
    owner: str
    genesis_height: int


@dataclass
class BitcoinBalance:
    """Balance complete d'une adresse Bitcoin"""
    address: str
    network: str
    
    # BTC natif
    btc_confirmed: int
    btc_unconfirmed: int
    
    # Ordinals
    inscriptions: List[Inscription] = field(default_factory=list)
    
    # BRC-20
    brc20_tokens: List[BRC20Token] = field(default_factory=list)
    
    # ARC-20
    arc20_tokens: List[ARC20Token] = field(default_factory=list)
    
    # Runes
    runes: List[Rune] = field(default_factory=list)
    
    # Bitmaps
    bitmaps: List[Bitmap] = field(default_factory=list)
    
    @property
    def total_btc(self) -> int:
        return self.btc_confirmed + self.btc_unconfirmed
    
    @property
    def btc_formatted(self) -> str:
        return f"{Decimal(self.total_btc) / Decimal(100_000_000):.8f} BTC"


@dataclass
class BitcoinTransaction:
    """Transaction Bitcoin"""
    txid: str
    version: int
    size: int
    vsize: int
    weight: int
    fee: int
    status: Dict[str, Any]
    inputs: List[Dict]
    outputs: List[Dict]


# ============================================================================
# UTILITAIRES BITCOIN
# ============================================================================

class BitcoinUtils:
    """Utilitaires pour Bitcoin"""
    
    @staticmethod
    def sha256(data: bytes) -> bytes:
        return hashlib.sha256(data).digest()
    
    @staticmethod
    def hash256(data: bytes) -> bytes:
        """Double SHA256"""
        return hashlib.sha256(hashlib.sha256(data).digest()).digest()
    
    @staticmethod
    def hash160(data: bytes) -> bytes:
        """RIPEMD160(SHA256(data))"""
        import hashlib
        sha = hashlib.sha256(data).digest()
        ripemd = hashlib.new('ripemd160')
        ripemd.update(sha)
        return ripemd.digest()
    
    @staticmethod
    def base58_encode(data: bytes) -> str:
        """Encodage Base58"""
        alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        
        # Convertir bytes en entier
        num = int.from_bytes(data, 'big')
        
        # Encoder
        result = ''
        while num > 0:
            num, rem = divmod(num, 58)
            result = alphabet[rem] + result
        
        # Ajouter les zeros initiaux
        for byte in data:
            if byte == 0:
                result = '1' + result
            else:
                break
        
        return result
    
    @staticmethod
    def base58check_encode(prefix: bytes, data: bytes) -> str:
        """Encodage Base58Check"""
        versioned = prefix + data
        checksum = BitcoinUtils.hash256(versioned)[:4]
        return BitcoinUtils.base58_encode(versioned + checksum)
    
    @staticmethod
    def bech32_polymod(values: List[int]) -> int:
        """Bech32 checksum"""
        generator = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
        chk = 1
        for value in values:
            top = chk >> 25
            chk = (chk & 0x1ffffff) << 5 ^ value
            for i in range(5):
                chk ^= generator[i] if ((top >> i) & 1) else 0
        return chk
    
    @staticmethod
    def bech32_hrp_expand(hrp: str) -> List[int]:
        return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]
    
    @staticmethod
    def bech32_create_checksum(hrp: str, data: List[int], spec: int = 1) -> List[int]:
        values = BitcoinUtils.bech32_hrp_expand(hrp) + data
        const = 0x2bc830a3 if spec == 2 else 1  # bech32m vs bech32
        polymod = BitcoinUtils.bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ const
        return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]
    
    @staticmethod
    def bech32_encode(hrp: str, witver: int, witprog: bytes, spec: int = 1) -> str:
        """Encodage Bech32/Bech32m"""
        alphabet = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
        
        # Convertir en base 5
        data = [witver]
        acc = 0
        bits = 0
        for byte in witprog:
            acc = (acc << 8) | byte
            bits += 8
            while bits >= 5:
                bits -= 5
                data.append((acc >> bits) & 31)
        if bits > 0:
            data.append((acc << (5 - bits)) & 31)
        
        checksum = BitcoinUtils.bech32_create_checksum(hrp, data, spec)
        return hrp + '1' + ''.join(alphabet[d] for d in data + checksum)
    
    @staticmethod
    def pubkey_to_p2pkh(pubkey: bytes, network: BitcoinNetwork = BitcoinNetwork.MAINNET) -> str:
        """Cle publique -> adresse P2PKH (Legacy)"""
        pubkey_hash = BitcoinUtils.hash160(pubkey)
        return BitcoinUtils.base58check_encode(network.p2pkh_prefix, pubkey_hash)
    
    @staticmethod
    def pubkey_to_p2wpkh(pubkey: bytes, network: BitcoinNetwork = BitcoinNetwork.MAINNET) -> str:
        """Cle publique -> adresse P2WPKH (Native SegWit)"""
        pubkey_hash = BitcoinUtils.hash160(pubkey)
        return BitcoinUtils.bech32_encode(network.bech32_hrp, 0, pubkey_hash, spec=1)
    
    @staticmethod
    def pubkey_to_p2tr(pubkey: bytes, network: BitcoinNetwork = BitcoinNetwork.MAINNET) -> str:
        """Cle publique -> adresse P2TR (Taproot)"""
        # Pour Taproot, on utilise directement la x-coordinate de la cle publique
        if len(pubkey) == 33:
            # Compressed pubkey, extraire x-coordinate
            x_coord = pubkey[1:]
        elif len(pubkey) == 32:
            x_coord = pubkey
        else:
            raise ValueError(f"Invalid pubkey length: {len(pubkey)}")
        
        return BitcoinUtils.bech32_encode(network.bech32_hrp, 1, x_coord, spec=2)


# ============================================================================
# GENERATION DE CLES BITCOIN
# ============================================================================

class BitcoinKeyDerivation:
    """Derivation de cles Bitcoin depuis la cle vault"""
    
    def __init__(self, vault_key: bytes, vault_id: str):
        self.vault_key = vault_key
        self.vault_id = vault_id
        self._private_key: Optional[bytes] = None
        self._public_key: Optional[bytes] = None
    
    def _derive_private_key(self) -> bytes:
        """
        Derive une cle privee Bitcoin depuis la cle vault.
        
        IMPORTANT: The salt is derived from vault_key itself to ensure
        the same vault_key ALWAYS generates the same address, regardless
        of vault_id changes. This makes the address PERPETUAL.
        """
        if self._private_key is None:
            # Salt derived from vault_key for perpetual address
            perpetual_salt = hashlib.sha256(b"eidolon-btc-perpetual-salt:" + self.vault_key).digest()[:16]
            
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=perpetual_salt,
                info=b'poly-spinor-bitcoin-wallet-v1'
            )
            self._private_key = hkdf.derive(self.vault_key)
        return self._private_key
    
    def _derive_public_key(self) -> bytes:
        """Derive la cle publique depuis la cle privee"""
        if self._public_key is None:
            private_key = self._derive_private_key()
            
            # Utiliser secp256k1 pour deriver la cle publique
            try:
                from cryptography.hazmat.primitives.asymmetric import ec
                from cryptography.hazmat.backends import default_backend
                
                # Creer la cle privee
                private_key_int = int.from_bytes(private_key, 'big')
                
                # Obtenir la cle publique via multiplication scalaire
                # Utilisation simplifiee - en production, utiliser une lib secp256k1
                from cryptography.hazmat.primitives.asymmetric.ec import (
                    derive_private_key, SECP256K1
                )
                
                pk = derive_private_key(private_key_int, SECP256K1(), default_backend())
                public_numbers = pk.public_key().public_numbers()
                
                # Format compressed (02/03 + x)
                x = public_numbers.x.to_bytes(32, 'big')
                prefix = b'\x02' if public_numbers.y % 2 == 0 else b'\x03'
                self._public_key = prefix + x
                
            except Exception as e:
                # Fallback: hash-based derivation (pour demo uniquement)
                self._public_key = b'\x02' + hashlib.sha256(
                    b'pubkey:' + private_key
                ).digest()
        
        return self._public_key
    
    @property
    def private_key(self) -> bytes:
        return self._derive_private_key()
    
    @property
    def private_key_wif(self) -> str:
        """Cle privee au format WIF"""
        extended = b'\x80' + self.private_key + b'\x01'  # Mainnet, compressed
        checksum = BitcoinUtils.hash256(extended)[:4]
        return BitcoinUtils.base58_encode(extended + checksum)
    
    @property
    def public_key(self) -> bytes:
        return self._derive_public_key()
    
    def get_address(self, address_type: AddressType = AddressType.P2TR,
                    network: BitcoinNetwork = BitcoinNetwork.MAINNET) -> str:
        """Genere une adresse Bitcoin"""
        pubkey = self.public_key
        
        if address_type == AddressType.P2PKH:
            return BitcoinUtils.pubkey_to_p2pkh(pubkey, network)
        elif address_type == AddressType.P2WPKH:
            return BitcoinUtils.pubkey_to_p2wpkh(pubkey, network)
        elif address_type == AddressType.P2TR:
            return BitcoinUtils.pubkey_to_p2tr(pubkey, network)
        else:
            raise ValueError(f"Unsupported address type: {address_type}")


# ============================================================================
# CLIENT API BITCOIN
# ============================================================================

class BitcoinAPIClient:
    """Client pour les APIs Bitcoin"""
    
    def __init__(self, network: BitcoinNetwork = BitcoinNetwork.MAINNET):
        self.network = network
        self.mempool_base = MEMPOOL_API if network == BitcoinNetwork.MAINNET else f"{MEMPOOL_API}/testnet"
    
    def _get(self, url: str, params: Dict = None) -> Any:
        """Requete GET"""
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API Error: {e}")
    
    # === Bitcoin Core ===
    
    def get_address_info(self, address: str) -> Dict:
        """Info sur une adresse"""
        return self._get(f"{self.mempool_base}/address/{address}")
    
    def get_address_utxos(self, address: str) -> List[UTXO]:
        """Liste des UTXOs d'une adresse"""
        data = self._get(f"{self.mempool_base}/address/{address}/utxo")
        return [
            UTXO(
                txid=u['txid'],
                vout=u['vout'],
                value=u['value'],
                script_pubkey=u.get('scriptpubkey', ''),
                address=address,
                confirmations=u.get('status', {}).get('block_height', 0)
            )
            for u in data
        ]
    
    def get_transaction(self, txid: str) -> BitcoinTransaction:
        """Details d'une transaction"""
        data = self._get(f"{self.mempool_base}/tx/{txid}")
        return BitcoinTransaction(
            txid=data['txid'],
            version=data['version'],
            size=data['size'],
            vsize=data['vsize'],
            weight=data['weight'],
            fee=data['fee'],
            status=data['status'],
            inputs=data['vin'],
            outputs=data['vout']
        )
    
    def get_fee_estimates(self) -> Dict[str, int]:
        """Estimations des frais"""
        return self._get(f"{self.mempool_base}/v1/fees/recommended")
    
    def broadcast_transaction(self, tx_hex: str) -> str:
        """Diffuse une transaction"""
        response = requests.post(
            f"{self.mempool_base}/tx",
            data=tx_hex,
            headers={'Content-Type': 'text/plain'},
            timeout=30
        )
        response.raise_for_status()
        return response.text
    
    # === Ordinals ===
    
    def get_inscription(self, inscription_id: str) -> Inscription:
        """Details d'une inscription"""
        data = self._get(f"{ORDINALS_API}/inscription/{inscription_id}")
        return Inscription(
            inscription_id=data['id'],
            inscription_number=data.get('number', 0),
            content_type=data.get('content_type', ''),
            content_length=data.get('content_length', 0),
            genesis_txid=data.get('genesis_transaction', ''),
            genesis_height=data.get('genesis_height', 0),
            genesis_fee=data.get('genesis_fee', 0),
            output_value=data.get('output_value', 0),
            sat_ordinal=data.get('sat', 0),
            sat_rarity=data.get('rarity', 'common'),
            address=data.get('address', '')
        )
    
    def get_address_inscriptions(self, address: str) -> List[Inscription]:
        """Inscriptions d'une adresse"""
        try:
            data = self._get(f"{ORDINALS_API}/inscriptions?address={address}")
            return [self.get_inscription(i['id']) for i in data.get('inscriptions', [])]
        except:
            return []
    
    # === BRC-20 ===
    
    def get_brc20_balances(self, address: str) -> List[BRC20Token]:
        """Balances BRC-20 d'une adresse"""
        try:
            data = self._get(
                f"{HIRO_API}/ordinals/v1/brc-20/balances/{address}"
            )
            return [
                BRC20Token(
                    tick=t['ticker'],
                    balance=Decimal(t.get('overall_balance', '0')),
                    transferable_balance=Decimal(t.get('transferrable_balance', '0')),
                    available_balance=Decimal(t.get('available_balance', '0'))
                )
                for t in data.get('results', [])
            ]
        except:
            return []
    
    def get_brc20_token_info(self, tick: str) -> Dict:
        """Info sur un token BRC-20"""
        return self._get(f"{HIRO_API}/ordinals/v1/brc-20/tokens/{tick}")
    
    # === Runes ===
    
    def get_runes_balances(self, address: str) -> List[Rune]:
        """Balances Runes d'une adresse"""
        try:
            data = self._get(f"{HIRO_API}/runes/v1/addresses/{address}/balances")
            return [
                Rune(
                    rune_id=r['rune']['id'],
                    name=r['rune']['name'],
                    symbol=r['rune'].get('symbol', ''),
                    balance=int(r['balance']),
                    divisibility=r['rune'].get('divisibility', 0),
                    spacers=r['rune'].get('spacers', 0),
                    etching_txid=r['rune'].get('etching', '')
                )
                for r in data.get('results', [])
            ]
        except:
            return []
    
    def get_rune_info(self, rune_id: str) -> Dict:
        """Info sur une Rune"""
        return self._get(f"{HIRO_API}/runes/v1/etchings/{rune_id}")
    
    # === ARC-20 (Atomicals) ===
    
    def get_arc20_balances(self, address: str) -> List[ARC20Token]:
        """Balances ARC-20 d'une adresse"""
        try:
            data = self._get(
                f"{ATOMICALS_API}/blockchain.atomicals.listscripthash",
                params={'params': f'["{address}"]'}
            )
            tokens = []
            for atomical_id, info in data.get('result', {}).get('atomicals', {}).items():
                if info.get('type') == 'FT':
                    tokens.append(ARC20Token(
                        atomical_id=atomical_id,
                        ticker=info.get('$ticker', ''),
                        balance=info.get('confirmed', 0),
                        confirmed_balance=info.get('confirmed', 0),
                        atomical_number=info.get('atomical_number', 0),
                        type='FT',
                        mint_info=info.get('mint_info', {})
                    ))
            return tokens
        except:
            return []
    
    # === Bitmap ===
    
    def get_bitmaps(self, address: str) -> List[Bitmap]:
        """Bitmaps d'une adresse"""
        try:
            inscriptions = self.get_address_inscriptions(address)
            bitmaps = []
            for insc in inscriptions:
                if insc.content_type == 'text/plain':
                    # Verifier si c'est un bitmap (format: block.bitmap)
                    try:
                        content = self._get(f"{ORDINALS_API}/content/{insc.inscription_id}")
                        if '.bitmap' in str(content):
                            block_num = int(str(content).split('.')[0])
                            bitmaps.append(Bitmap(
                                inscription_id=insc.inscription_id,
                                block_number=block_num,
                                district=None,
                                parcel=None,
                                owner=insc.address,
                                genesis_height=insc.genesis_height
                            ))
                    except:
                        pass
            return bitmaps
        except:
            return []


# ============================================================================
# WALLET BITCOIN COMPLET
# ============================================================================

class VaultBitcoinWallet:
    """Wallet Bitcoin complet derive du vault"""
    
    def __init__(self, vault_key: bytes, vault_id: str,
                 network: BitcoinNetwork = BitcoinNetwork.MAINNET,
                 address_type: AddressType = AddressType.P2TR):
        self.vault_key = vault_key
        self.vault_id = vault_id
        self.network = network
        self.address_type = address_type
        
        # Derivation des cles
        self._key_derivation = BitcoinKeyDerivation(vault_key, vault_id)
        
        # Client API
        self._api = BitcoinAPIClient(network)
        
        # Cache
        self._balance_cache: Optional[BitcoinBalance] = None
        self._cache_time: float = 0
    
    @property
    def private_key(self) -> bytes:
        return self._key_derivation.private_key
    
    @property
    def private_key_wif(self) -> str:
        return self._key_derivation.private_key_wif
    
    @property
    def public_key(self) -> bytes:
        return self._key_derivation.public_key
    
    @property
    def address(self) -> str:
        return self._key_derivation.get_address(self.address_type, self.network)
    
    def get_all_addresses(self) -> Dict[str, str]:
        """Retourne toutes les adresses possibles"""
        return {
            'p2pkh': self._key_derivation.get_address(AddressType.P2PKH, self.network),
            'p2wpkh': self._key_derivation.get_address(AddressType.P2WPKH, self.network),
            'p2tr': self._key_derivation.get_address(AddressType.P2TR, self.network),
        }
    
    def get_balance(self, force_refresh: bool = False) -> BitcoinBalance:
        """Obtient la balance complete"""
        import time
        
        # Cache de 60 secondes
        if not force_refresh and self._balance_cache and (time.time() - self._cache_time) < 60:
            return self._balance_cache
        
        address = self.address
        
        # BTC natif
        try:
            info = self._api.get_address_info(address)
            btc_confirmed = info.get('chain_stats', {}).get('funded_txo_sum', 0) - \
                           info.get('chain_stats', {}).get('spent_txo_sum', 0)
            btc_unconfirmed = info.get('mempool_stats', {}).get('funded_txo_sum', 0) - \
                             info.get('mempool_stats', {}).get('spent_txo_sum', 0)
        except:
            btc_confirmed = 0
            btc_unconfirmed = 0
        
        # Construire la balance
        balance = BitcoinBalance(
            address=address,
            network=self.network._name,
            btc_confirmed=btc_confirmed,
            btc_unconfirmed=btc_unconfirmed,
            inscriptions=self._api.get_address_inscriptions(address),
            brc20_tokens=self._api.get_brc20_balances(address),
            arc20_tokens=self._api.get_arc20_balances(address),
            runes=self._api.get_runes_balances(address),
            bitmaps=self._api.get_bitmaps(address)
        )
        
        self._balance_cache = balance
        self._cache_time = time.time()
        
        return balance
    
    def get_utxos(self) -> List[UTXO]:
        """Liste des UTXOs"""
        return self._api.get_address_utxos(self.address)
    
    def get_fee_estimates(self) -> Dict[str, int]:
        """Estimations des frais (sat/vB)"""
        return self._api.get_fee_estimates()
    
    # === Methodes de transfert ===
    
    def prepare_btc_transfer(self, to_address: str, amount_sats: int,
                            fee_rate: int = None) -> Dict:
        """Prepare un transfert BTC"""
        utxos = self.get_utxos()
        
        if fee_rate is None:
            fees = self.get_fee_estimates()
            fee_rate = fees.get('halfHourFee', 10)
        
        # Selectionner les UTXOs
        selected_utxos = []
        total_input = 0
        
        for utxo in sorted(utxos, key=lambda x: x.value, reverse=True):
            if utxo.is_ordinal:
                continue  # Ne pas utiliser les UTXOs avec inscriptions
            selected_utxos.append(utxo)
            total_input += utxo.value
            if total_input >= amount_sats + 1000:  # +1000 pour les frais
                break
        
        if total_input < amount_sats:
            raise ValueError(f"Insufficient funds: {total_input} < {amount_sats}")
        
        # Estimation de la taille
        estimated_size = 10 + len(selected_utxos) * 68 + 2 * 34
        estimated_fee = estimated_size * fee_rate
        
        change = total_input - amount_sats - estimated_fee
        
        return {
            'inputs': [asdict(u) for u in selected_utxos],
            'outputs': [
                {'address': to_address, 'value': amount_sats},
                {'address': self.address, 'value': change} if change > 546 else None
            ],
            'fee': estimated_fee,
            'fee_rate': fee_rate,
            'total_input': total_input,
            'amount': amount_sats,
            'change': change
        }
    
    def prepare_brc20_transfer(self, tick: str, amount: Decimal,
                               to_address: str) -> Dict:
        """Prepare un transfert BRC-20"""
        # BRC-20 utilise un processus en 2 etapes:
        # 1. Inscrire un transfer
        # 2. Envoyer l'inscription
        
        transfer_json = {
            "p": "brc-20",
            "op": "transfer",
            "tick": tick,
            "amt": str(amount)
        }
        
        return {
            'type': 'brc20_transfer',
            'inscription_content': json.dumps(transfer_json),
            'content_type': 'text/plain;charset=utf-8',
            'to_address': to_address,
            'tick': tick,
            'amount': str(amount),
            'steps': [
                '1. Inscrire le JSON de transfer',
                '2. Envoyer l\'inscription au destinataire'
            ]
        }
    
    def prepare_rune_transfer(self, rune_id: str, amount: int,
                              to_address: str) -> Dict:
        """Prepare un transfert de Rune"""
        return {
            'type': 'rune_transfer',
            'rune_id': rune_id,
            'amount': amount,
            'to_address': to_address,
            'note': 'Les Runes utilisent OP_RETURN pour les edicts de transfert'
        }
    
    def sign_message(self, message: str) -> str:
        """Signe un message avec la cle privee"""
        message_bytes = message.encode('utf-8')
        message_hash = hashlib.sha256(
            b'\x18Bitcoin Signed Message:\n' +
            bytes([len(message_bytes)]) +
            message_bytes
        ).digest()
        
        # Signature simplifiee (en production, utiliser ECDSA proper)
        signature = hashlib.sha256(
            self.private_key + message_hash
        ).hexdigest()
        
        return signature


# ============================================================================
# GESTIONNAIRE D'ACTIFS BITCOIN
# ============================================================================

class BitcoinAssetManager:
    """Gestionnaire des actifs Bitcoin dans le vault"""
    
    def __init__(self, wallet: VaultBitcoinWallet, vault_manager=None):
        self.wallet = wallet
        self.vault_manager = vault_manager
    
    def sync_assets(self) -> Dict[str, int]:
        """Synchronise tous les actifs Bitcoin avec le vault"""
        balance = self.wallet.get_balance(force_refresh=True)
        
        synced = {
            'btc': 1 if balance.total_btc > 0 else 0,
            'inscriptions': len(balance.inscriptions),
            'brc20': len(balance.brc20_tokens),
            'arc20': len(balance.arc20_tokens),
            'runes': len(balance.runes),
            'bitmaps': len(balance.bitmaps)
        }
        
        if self.vault_manager:
            # Ajouter au vault
            for insc in balance.inscriptions:
                self.vault_manager.add_asset({
                    'name': f'Inscription #{insc.inscription_number}',
                    'asset_type': 'Ordinal',
                    'chain': 'Bitcoin',
                    'inscription_id': insc.inscription_id,
                    'metadata': asdict(insc)
                })
            
            for token in balance.brc20_tokens:
                self.vault_manager.add_asset({
                    'name': f'BRC-20: {token.tick}',
                    'asset_type': 'BRC20',
                    'chain': 'Bitcoin',
                    'tick': token.tick,
                    'metadata': {
                        'balance': str(token.balance),
                        'available': str(token.available_balance)
                    }
                })
            
            for rune in balance.runes:
                self.vault_manager.add_asset({
                    'name': f'Rune: {rune.name}',
                    'asset_type': 'Rune',
                    'chain': 'Bitcoin',
                    'rune_id': rune.rune_id,
                    'metadata': asdict(rune)
                })
        
        return synced
    
    def get_portfolio_summary(self) -> Dict:
        """Resume du portfolio Bitcoin"""
        balance = self.wallet.get_balance()
        
        return {
            'address': balance.address,
            'network': balance.network,
            'btc': {
                'confirmed': balance.btc_confirmed,
                'unconfirmed': balance.btc_unconfirmed,
                'total': balance.total_btc,
                'formatted': balance.btc_formatted
            },
            'ordinals': {
                'count': len(balance.inscriptions),
                'items': [
                    {
                        'id': i.inscription_id,
                        'number': i.inscription_number,
                        'type': i.content_type,
                        'rarity': i.sat_rarity
                    }
                    for i in balance.inscriptions[:10]
                ]
            },
            'brc20': {
                'count': len(balance.brc20_tokens),
                'tokens': [
                    {
                        'tick': t.tick,
                        'balance': t.formatted_balance()
                    }
                    for t in balance.brc20_tokens
                ]
            },
            'arc20': {
                'count': len(balance.arc20_tokens),
                'tokens': [
                    {
                        'ticker': t.ticker,
                        'balance': t.balance
                    }
                    for t in balance.arc20_tokens
                ]
            },
            'runes': {
                'count': len(balance.runes),
                'tokens': [
                    {
                        'name': r.name,
                        'symbol': r.symbol,
                        'balance': r.formatted_balance()
                    }
                    for r in balance.runes
                ]
            },
            'bitmaps': {
                'count': len(balance.bitmaps),
                'blocks': [b.block_number for b in balance.bitmaps]
            }
        }


# ============================================================================
# FONCTION D'AIDE
# ============================================================================

def create_bitcoin_wallet(vault_key: bytes, vault_id: str,
                         network: BitcoinNetwork = BitcoinNetwork.MAINNET,
                         address_type: AddressType = AddressType.P2TR) -> VaultBitcoinWallet:
    """Cree un wallet Bitcoin depuis une cle vault"""
    return VaultBitcoinWallet(vault_key, vault_id, network, address_type)
