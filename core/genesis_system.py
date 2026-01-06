"""
Systeme de Genesis Block avec Easter Egg pour les 100,000 premiers utilisateurs
Integration avec Rune Protocol Bitcoin
"""

import hashlib
import json
import time
import os
import secrets
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List
from enum import Enum

from cryptography.fernet import Fernet


class GenesisTier(Enum):
    """Niveaux d'easter eggs selon le rang d'inscription"""
    FOUNDER_1 = 1        # 1-100
    FOUNDER_10 = 2       # 101-1,000
    FOUNDER_100 = 3      # 1,001-10,000
    FOUNDER_1000 = 4     # 10,001-100,000
    STANDARD = 5         # Apres 100,000


@dataclass
class GenesisBlock:
    """Bloc de genesis d'un utilisateur"""
    version: int = 1
    user_id: str = ""
    timestamp: int = 0
    block_hash: str = ""
    previous_hash: str = "0" * 64
    nonce: int = 0
    difficulty: int = 20
    merkleroot: str = ""
    
    # Easter egg data
    easter_egg_type: str = ""
    easter_egg_data: Dict[str, Any] = field(default_factory=dict)
    inscription_number: int = 0
    tier: str = ""
    
    # Rune Protocol data
    rune_symbol: str = ""
    rune_amount: int = 0
    rune_divisibility: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
    
    def compute_hash(self) -> str:
        """Calculer le hash SHA-256 du bloc"""
        block_string = json.dumps({
            "version": self.version,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "merkleroot": self.merkleroot,
            "nonce": self.nonce,
            "difficulty": self.difficulty,
            "easter_egg_type": self.easter_egg_type,
            "inscription_number": self.inscription_number
        }, sort_keys=True)
        
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty: int = 20) -> str:
        """Miner le bloc genesis (PoW leger)"""
        self.difficulty = difficulty
        prefix = "0" * difficulty
        
        while not self.block_hash.startswith(prefix):
            self.nonce += 1
            self.timestamp = int(time.time())
            self.block_hash = self.compute_hash()
        
        return self.block_hash


class EasterEggGenerator:
    """Generateur d'easter eggs pour les early adopters"""
    
    EASTER_EGGS = {
        GenesisTier.FOUNDER_1: {
            "name": "Quantum Pioneer",
            "description": "Genesis Founder #1-100",
            "attributes": {
                "rarity": "Mythic",
                "color": "#FFD700",
                "glow": True,
                "animation": "quantum_flare"
            },
            "rewards": {
                "rune_multiplier": 10.0,
                "future_airdrop": True,
                "governance_power": 100
            }
        },
        GenesisTier.FOUNDER_10: {
            "name": "Spinor Visionary",
            "description": "Genesis Founder #101-1,000",
            "attributes": {
                "rarity": "Legendary",
                "color": "#C0C0C0",
                "glow": True,
                "animation": "spinor_pulse"
            },
            "rewards": {
                "rune_multiplier": 5.0,
                "future_airdrop": True,
                "governance_power": 50
            }
        },
        GenesisTier.FOUNDER_100: {
            "name": "Bell Verifier",
            "description": "Genesis Founder #1,001-10,000",
            "attributes": {
                "rarity": "Epic",
                "color": "#A335EE",
                "glow": False,
                "animation": "bell_oscillation"
            },
            "rewards": {
                "rune_multiplier": 2.5,
                "future_airdrop": True,
                "governance_power": 25
            }
        },
        GenesisTier.FOUNDER_1000: {
            "name": "Post-Quantum Guardian",
            "description": "Genesis Founder #10,001-100,000",
            "attributes": {
                "rarity": "Rare",
                "color": "#0070DD",
                "glow": False,
                "animation": "lattice_shield"
            },
            "rewards": {
                "rune_multiplier": 1.5,
                "future_airdrop": False,
                "governance_power": 10
            }
        }
    }
    
    @staticmethod
    def get_tier(inscription_number: int) -> GenesisTier:
        """Obtenir le tier selon le numero d'inscription"""
        if inscription_number <= 100:
            return GenesisTier.FOUNDER_1
        elif inscription_number <= 1000:
            return GenesisTier.FOUNDER_10
        elif inscription_number <= 10000:
            return GenesisTier.FOUNDER_100
        elif inscription_number <= 100000:
            return GenesisTier.FOUNDER_1000
        else:
            return GenesisTier.STANDARD
    
    @staticmethod
    def get_easter_egg(inscription_number: int) -> Optional[Dict[str, Any]]:
        """Obtenir l'easter egg selon le numero d'inscription"""
        tier = EasterEggGenerator.get_tier(inscription_number)
        
        if tier == GenesisTier.STANDARD:
            return None
        
        egg = EasterEggGenerator.EASTER_EGGS[tier].copy()
        egg["inscription_number"] = inscription_number
        egg["tier"] = tier.name
        egg["mint_date"] = datetime.now().isoformat()
        
        # Generer un hash unique pour cet easter egg
        unique_seed = f"{inscription_number}:{time.time()}:{secrets.token_hex(8)}"
        egg["unique_hash"] = hashlib.sha256(unique_seed.encode()).hexdigest()[:16]
        
        return egg


class RuneSymbolGenerator:
    """Generateur de symboles runiques"""
    
    # Alphabet runique Elder Futhark
    RUNIC_ALPHABET = "ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈᛉᛊᛏᛒᛖᛗᛚᛜᛟᛞ"
    
    # Prefixes par tier
    TIER_PREFIXES = {
        GenesisTier.FOUNDER_1: "ᛏᚨᛚ",    # TAL (Tres Ancien Legacy)
        GenesisTier.FOUNDER_10: "ᚨᚾᚲ",   # ANK (Ancien)
        GenesisTier.FOUNDER_100: "ᚠᛟᚱ",  # FOR (Fondateur)
        GenesisTier.FOUNDER_1000: "ᛖᚨᚱ", # EAR (Early)
        GenesisTier.STANDARD: "ᛊᛏᛞ"      # STD (Standard)
    }
    
    @classmethod
    def generate_symbol(cls, inscription_number: int) -> str:
        """Generer un symbole rune unique"""
        # Convertir le numero en base runique
        num = inscription_number
        runic_symbol = ""
        
        while num > 0:
            num, remainder = divmod(num, len(cls.RUNIC_ALPHABET))
            runic_symbol = cls.RUNIC_ALPHABET[remainder] + runic_symbol
        
        if not runic_symbol:
            runic_symbol = cls.RUNIC_ALPHABET[0]
        
        # Obtenir le prefixe selon le tier
        tier = EasterEggGenerator.get_tier(inscription_number)
        prefix = cls.TIER_PREFIXES.get(tier, cls.TIER_PREFIXES[GenesisTier.STANDARD])
        
        return f"{prefix}•{runic_symbol}"
    
    @classmethod
    def calculate_amount(cls, inscription_number: int) -> int:
        """Calculer le montant de rune selon le tier"""
        base_amount = 1_000_000  # 1 million d'unites
        
        if inscription_number <= 100:
            return base_amount * 1000  # 1 milliard
        elif inscription_number <= 1000:
            return base_amount * 100   # 100 millions
        elif inscription_number <= 10000:
            return base_amount * 10    # 10 millions
        elif inscription_number <= 100000:
            return base_amount * 1     # 1 million
        else:
            return base_amount // 10   # 100,000


class GenesisManager:
    """Gestionnaire du systeme Genesis"""
    
    def __init__(self, data_dir: str = "./genesis_data"):
        self.data_dir = data_dir
        self.blocks_dir = f"{data_dir}/blocks"
        self.encrypted_dir = f"{data_dir}/blocks/encrypted"
        self.keys_dir = f"{data_dir}/blocks/keys"
        self.inscriptions_dir = f"{data_dir}/inscriptions"
        self.counter_file = f"{data_dir}/inscription_counter.json"
        
        # Initialiser les dossiers
        for dir_path in [self.blocks_dir, self.encrypted_dir, self.keys_dir, self.inscriptions_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Initialiser le compteur
        self.counter = self._load_counter()
    
    def _load_counter(self) -> dict:
        """Charger le compteur d'inscriptions"""
        if os.path.exists(self.counter_file):
            with open(self.counter_file, 'r') as f:
                return json.load(f)
        
        # Fichier initial
        initial = {
            "total_inscriptions": 0,
            "last_inscription_time": 0,
            "genesis_hash": hashlib.sha256(b"Poly-Spinor-Nexus-7D-Genesis").hexdigest(),
            "founders": {
                "tier_1": 0,    # 1-100
                "tier_2": 0,    # 101-1,000
                "tier_3": 0,    # 1,001-10,000
                "tier_4": 0     # 10,001-100,000
            }
        }
        
        with open(self.counter_file, 'w') as f:
            json.dump(initial, f, indent=2)
        
        return initial
    
    def _save_counter(self):
        """Sauvegarder le compteur"""
        self.counter["last_inscription_time"] = int(time.time())
        
        with open(self.counter_file, 'w') as f:
            json.dump(self.counter, f, indent=2)
    
    def get_next_inscription_number(self) -> int:
        """Obtenir le prochain numero d'inscription"""
        self.counter["total_inscriptions"] += 1
        inscription_num = self.counter["total_inscriptions"]
        
        # Mettre a jour les compteurs par tier
        if inscription_num <= 100:
            self.counter["founders"]["tier_1"] += 1
        elif inscription_num <= 1000:
            self.counter["founders"]["tier_2"] += 1
        elif inscription_num <= 10000:
            self.counter["founders"]["tier_3"] += 1
        elif inscription_num <= 100000:
            self.counter["founders"]["tier_4"] += 1
        
        self._save_counter()
        return inscription_num
    
    def create_genesis_block(self, user_data: dict, difficulty: int = 16) -> GenesisBlock:
        """Creer un bloc de genesis pour un nouvel utilisateur"""
        # Generer l'ID utilisateur unique
        user_id_seed = f"{user_data.get('wallet_address', '')}:{time.time()}:{secrets.token_hex(16)}"
        user_id = hashlib.sha256(user_id_seed.encode()).hexdigest()[:32]
        
        # Obtenir le numero d'inscription
        inscription_num = self.get_next_inscription_number()
        
        # Creer le merkle root
        merkle_data = f"{user_id}:{inscription_num}:{user_data}"
        merkleroot = hashlib.sha256(merkle_data.encode()).hexdigest()
        
        # Creer le bloc genesis
        genesis = GenesisBlock(
            user_id=user_id,
            timestamp=int(time.time()),
            inscription_number=inscription_num,
            merkleroot=merkleroot,
            previous_hash=self.counter.get("genesis_hash", "0" * 64)
        )
        
        # Ajouter l'easter egg si applicable
        if inscription_num <= 100000:
            egg_data = EasterEggGenerator.get_easter_egg(inscription_num)
            if egg_data:
                genesis.easter_egg_type = egg_data["name"]
                genesis.easter_egg_data = egg_data
                genesis.tier = egg_data["tier"]
        
        # Miner le bloc (PoW leger)
        print(f"[*] Mining genesis block #{inscription_num}...")
        genesis.mine_block(difficulty=difficulty)
        print(f"[+] Block mined! Hash: {genesis.block_hash[:16]}...")
        
        # Generer la rune associee
        genesis.rune_symbol = RuneSymbolGenerator.generate_symbol(inscription_num)
        genesis.rune_amount = RuneSymbolGenerator.calculate_amount(inscription_num)
        genesis.rune_divisibility = 8
        
        # Sauvegarder le bloc
        self._save_genesis_block(genesis)
        
        # Generer une inscription Bitcoin (format simplifie)
        if inscription_num <= 100000:
            self._create_bitcoin_inscription(genesis)
        
        return genesis
    
    def _save_genesis_block(self, genesis: GenesisBlock):
        """Sauvegarder le bloc genesis"""
        block_filename = f"{self.blocks_dir}/genesis_{genesis.inscription_number:06d}.json"
        
        with open(block_filename, 'w') as f:
            json.dump(genesis.to_dict(), f, indent=2)
        
        # Creer egalement une version chiffree
        self._save_encrypted_block(genesis)
    
    def _save_encrypted_block(self, genesis: GenesisBlock):
        """Sauvegarder une version chiffree du bloc"""
        # Generer une cle de chiffrement
        key = Fernet.generate_key()
        cipher = Fernet(key)
        
        # Chiffrer les donnees
        encrypted_data = cipher.encrypt(json.dumps(genesis.to_dict()).encode())
        
        # Sauvegarder
        enc_filename = f"{self.encrypted_dir}/genesis_{genesis.inscription_number:06d}.enc"
        key_filename = f"{self.keys_dir}/genesis_{genesis.inscription_number:06d}.key"
        
        with open(enc_filename, 'wb') as f:
            f.write(encrypted_data)
        
        with open(key_filename, 'wb') as f:
            f.write(key)
    
    def _create_bitcoin_inscription(self, genesis: GenesisBlock):
        """Creer une inscription Bitcoin (format ord)"""
        inscription_data = {
            "p": "rune",  # Protocol: rune
            "op": "deploy",
            "sym": genesis.rune_symbol,
            "amt": str(genesis.rune_amount),
            "dec": str(genesis.rune_divisibility),
            "genesis": genesis.block_hash,
            "user": genesis.user_id,
            "inscription": genesis.inscription_number,
            "tier": genesis.tier,
            "timestamp": genesis.timestamp
        }
        
        if genesis.easter_egg_data:
            inscription_data["easter_egg"] = genesis.easter_egg_data.get("unique_hash", "")
            inscription_data["rarity"] = genesis.easter_egg_data.get("attributes", {}).get("rarity", "")
        
        # Sauvegarder l'inscription
        inscription_file = f"{self.inscriptions_dir}/{genesis.inscription_number:06d}.json"
        
        with open(inscription_file, 'w') as f:
            json.dump(inscription_data, f, indent=2)
        
        print(f"[+] Inscription Bitcoin generee: #{genesis.inscription_number}")
        print(f"    Rune: {genesis.rune_symbol}")
        print(f"    Montant: {genesis.rune_amount:,}")
        print(f"    Tier: {genesis.tier or 'STANDARD'}")
    
    def load_genesis_block(self, inscription_number: int) -> Optional[GenesisBlock]:
        """Charger un bloc genesis existant"""
        block_filename = f"{self.blocks_dir}/genesis_{inscription_number:06d}.json"
        
        if not os.path.exists(block_filename):
            return None
        
        with open(block_filename, 'r') as f:
            data = json.load(f)
        
        return GenesisBlock(**data)
    
    def load_encrypted_block(self, inscription_number: int) -> Optional[GenesisBlock]:
        """Charger et dechiffrer un bloc genesis"""
        enc_filename = f"{self.encrypted_dir}/genesis_{inscription_number:06d}.enc"
        key_filename = f"{self.keys_dir}/genesis_{inscription_number:06d}.key"
        
        if not os.path.exists(enc_filename) or not os.path.exists(key_filename):
            return None
        
        with open(key_filename, 'rb') as f:
            key = f.read()
        
        with open(enc_filename, 'rb') as f:
            encrypted_data = f.read()
        
        cipher = Fernet(key)
        decrypted_data = cipher.decrypt(encrypted_data)
        data = json.loads(decrypted_data.decode())
        
        return GenesisBlock(**data)
    
    def get_genesis_stats(self) -> dict:
        """Obtenir les statistiques du systeme genesis"""
        block_files = [f for f in os.listdir(self.blocks_dir) 
                       if f.startswith("genesis_") and f.endswith(".json")]
        
        remaining_founders = max(0, 100000 - self.counter["total_inscriptions"])
        
        # Calculer les places restantes par tier
        remaining_by_tier = {
            "tier_1_remaining": max(0, 100 - self.counter["founders"]["tier_1"]),
            "tier_2_remaining": max(0, 900 - self.counter["founders"]["tier_2"]),
            "tier_3_remaining": max(0, 9000 - self.counter["founders"]["tier_3"]),
            "tier_4_remaining": max(0, 90000 - self.counter["founders"]["tier_4"])
        }
        
        return {
            "total_inscriptions": self.counter["total_inscriptions"],
            "total_blocks": len(block_files),
            "remaining_founder_slots": remaining_founders,
            "founders_by_tier": self.counter["founders"],
            "remaining_by_tier": remaining_by_tier,
            "next_inscription_number": self.counter["total_inscriptions"] + 1,
            "genesis_hash": self.counter.get("genesis_hash", ""),
            "last_inscription_time": self.counter.get("last_inscription_time", 0)
        }
    
    def get_tier_info(self, inscription_number: int) -> dict:
        """Obtenir les informations du tier pour un numero d'inscription"""
        tier = EasterEggGenerator.get_tier(inscription_number)
        
        tier_ranges = {
            GenesisTier.FOUNDER_1: (1, 100, "Quantum Pioneer"),
            GenesisTier.FOUNDER_10: (101, 1000, "Spinor Visionary"),
            GenesisTier.FOUNDER_100: (1001, 10000, "Bell Verifier"),
            GenesisTier.FOUNDER_1000: (10001, 100000, "Post-Quantum Guardian"),
            GenesisTier.STANDARD: (100001, float('inf'), "Standard User")
        }
        
        start, end, name = tier_ranges[tier]
        
        return {
            "tier": tier.name,
            "tier_value": tier.value,
            "name": name,
            "range_start": start,
            "range_end": end if end != float('inf') else "unlimited",
            "rune_symbol": RuneSymbolGenerator.generate_symbol(inscription_number),
            "rune_amount": RuneSymbolGenerator.calculate_amount(inscription_number),
            "is_founder": inscription_number <= 100000
        }


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def create_user_genesis(wallet_address: str, data_dir: str = "./genesis_data") -> GenesisBlock:
    """Fonction simplifiee pour creer un genesis block pour un utilisateur"""
    manager = GenesisManager(data_dir)
    
    user_data = {
        "wallet_address": wallet_address,
        "created_at": datetime.now().isoformat()
    }
    
    return manager.create_genesis_block(user_data)


def get_genesis_info(data_dir: str = "./genesis_data") -> dict:
    """Obtenir les informations du systeme genesis"""
    manager = GenesisManager(data_dir)
    return manager.get_genesis_stats()


def preview_next_inscription(data_dir: str = "./genesis_data") -> dict:
    """Previsualiser la prochaine inscription sans la creer"""
    manager = GenesisManager(data_dir)
    next_num = manager.counter["total_inscriptions"] + 1
    
    return {
        "next_inscription_number": next_num,
        "tier_info": manager.get_tier_info(next_num),
        "easter_egg": EasterEggGenerator.get_easter_egg(next_num) if next_num <= 100000 else None
    }
