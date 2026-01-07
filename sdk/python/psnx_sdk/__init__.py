"""
Eidolon - Python SDK

SDK officiel pour interagir avec l'API Eidolon.

Installation:
    pip install psnx-sdk

Usage:
    from psnx_sdk import PSNXClient, Vault, KeyGenerator
    
    # Generer une cle
    key_gen = KeyGenerator()
    vault_key = key_gen.generate()
    
    # Creer un vault
    vault = Vault(vault_key)
    encrypted = vault.encrypt(b"secret")
    decrypted = vault.decrypt(encrypted)
    
    # Client API
    client = PSNXClient("http://api.example.com", vault_key)
    client.login("user_id")
    info = client.vault_info()
"""

__version__ = "1.0.0"
__author__ = "Poly-Spinor Team"

from .client import PSNXClient
from .vault import Vault, EncryptedData
from .keygen import KeyGenerator, KeyPair
from .sharing import SecretSharing, Share
from .zkp import ZKPProver, ZKPVerifier
from .web3 import (
    VaultWeb3Wallet,
    IPFSClient,
    BackupRegistry,
    DecentralizedBackupManager,
    EVMChain,
    ChainConfig,
    BackupRecord,
    BackupRegistration,
    is_valid_address,
    format_ether,
    parse_ether,
    shorten_address,
    get_chain_by_id,
    get_chain_by_name,
)
from .exceptions import (
    PSNXError,
    AuthenticationError,
    EncryptionError,
    DecryptionError,
    NetworkError,
    ValidationError
)

__all__ = [
    # Core
    "PSNXClient",
    "Vault",
    "EncryptedData",
    "KeyGenerator",
    "KeyPair",
    "SecretSharing",
    "Share",
    "ZKPProver",
    "ZKPVerifier",
    # Web3
    "VaultWeb3Wallet",
    "IPFSClient",
    "BackupRegistry",
    "DecentralizedBackupManager",
    "EVMChain",
    "ChainConfig",
    "BackupRecord",
    "BackupRegistration",
    "is_valid_address",
    "format_ether",
    "parse_ether",
    "shorten_address",
    "get_chain_by_id",
    "get_chain_by_name",
    # Exceptions
    "PSNXError",
    "AuthenticationError",
    "EncryptionError",
    "DecryptionError",
    "NetworkError",
    "ValidationError",
]
