"""
Centralized path configuration for the non-game Eidolon runtime.

This module now exposes only the storage used by:
- vault identity and security data
- avatars
- genesis eggs and incubation
- blockchain-related services
"""

import os
import sys
from pathlib import Path


def _is_frozen() -> bool:
    """Check if running from PyInstaller bundle."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_project_root() -> Path:
    """Get the absolute path to the project root directory."""
    if _is_frozen():
        # Running from PyInstaller exe - use exe directory
        return Path(sys.executable).parent.resolve()
    return Path(__file__).parent.parent.resolve()


def get_user_data_root() -> Path:
    """Get a persistent user-writable data directory.
    
    Uses %LOCALAPPDATA%\\Eidolon on Windows when running from exe.
    Falls back to project root for development.
    """
    # Allow override via environment variable
    env_dir = os.environ.get('EIDOLON_DATA_DIR')
    if env_dir:
        path = Path(env_dir).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    if _is_frozen() or sys.platform == 'win32':
        # Use %LOCALAPPDATA%\Eidolon for persistent storage
        local_app = os.environ.get('LOCALAPPDATA')
        if local_app:
            path = Path(local_app) / 'Eidolon'
            path.mkdir(parents=True, exist_ok=True)
            return path
    
    # Fallback: use project root (development mode)
    return get_project_root()


def get_data_root() -> Path:
    """Base data directory for persistent data."""
    return get_user_data_root() / "data"


def get_vaults_root() -> Path:
    """Root directory for vault-related data."""
    return get_data_root() / "vaults"


def get_keys_dir() -> Path:
    """Directory for vault key files (.psnx, .blend_data)."""
    path = get_vaults_root() / "keys"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_identities_dir() -> Path:
    """Directory for identity proofs and registry."""
    path = get_vaults_root() / "identities"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_vault_registry_path() -> Path:
    """Path to the vault registry JSON file."""
    return get_identities_dir() / "vault_registry.json"


def get_persistent_vaults_dir() -> Path:
    """Directory for persistent vault state."""
    path = get_vaults_root() / "persistent"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_security_dir() -> Path:
    """Directory for security-related data."""
    path = get_vaults_root() / "security"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_2fa_challenges_dir() -> Path:
    """Directory for 2FA challenge data."""
    path = get_security_dir() / "2fa_challenges"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_anti_spoofing_dir() -> Path:
    """Directory for anti-spoofing data."""
    path = get_security_dir() / "anti_spoofing"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_identity_history_dir() -> Path:
    """Directory for identity history."""
    path = get_security_dir() / "identity_history"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_avatars_root() -> Path:
    """Root directory for avatar NFTs."""
    return get_data_root() / "avatars"


def get_avatar_collections_dir() -> Path:
    """Directory for avatar collections."""
    path = get_avatars_root() / "collections"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_avatar_tokens_dir() -> Path:
    """Directory for avatar tokens."""
    path = get_avatars_root() / "tokens"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_avatar_viewers_dir() -> Path:
    """Directory for avatar viewers."""
    path = get_avatars_root() / "viewers"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_genesis_root() -> Path:
    """Root directory for genesis system."""
    return get_data_root() / "genesis"


def get_genesis_data_dir() -> Path:
    """Directory for genesis block data."""
    path = get_genesis_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_genesis_spheres_dir() -> Path:
    """Directory for genesis spheres (formerly eggs)."""
    path = get_genesis_root() / "spheres"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_genesis_distribution_dir() -> Path:
    """Directory for genesis distribution tracking."""
    path = get_genesis_root() / "distribution"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_blockchain_root() -> Path:
    """Root directory for blockchain data."""
    return get_data_root() / "blockchain"


def get_ordinals_dir() -> Path:
    """Directory for ordinals data."""
    path = get_blockchain_root() / "ordinals"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_runes_dir() -> Path:
    """Directory for rune data."""
    path = get_blockchain_root() / "runes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_staking_dir() -> Path:
    """Directory for staking data."""
    path = get_blockchain_root() / "staking"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_runes_exchange_dir() -> Path:
    """Directory for runes exchange data."""
    path = get_blockchain_root() / "runes_exchange"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_bitcoin_bridge_dir() -> Path:
    """Directory for Bitcoin bridge data."""
    path = get_blockchain_root() / "bitcoin_bridge"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_items_root() -> Path:
    """Root directory for game items (stones, potions, etc.)."""
    return get_data_root() / "items"


def get_rosetta_stones_dir() -> Path:
    """Directory for Rosetta Stone NFT data."""
    path = get_items_root() / "rosetta_stones"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_cipher_metrics_dir() -> Path:
    """Directory for Cipher activity metrics (use-to-earn pipeline)."""
    path = get_vaults_root() / "cipher_metrics"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_incubation_dir() -> Path:
    """Directory for incubation state."""
    path = get_vaults_root() / "incubation"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_hardware_attestation_dir() -> Path:
    """Directory for hardware attestation data."""
    path = get_security_dir() / "hardware_attestation"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_key_revocation_dir() -> Path:
    """Directory for key revocation data."""
    path = get_security_dir() / "revocation"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_timelock_recovery_dir() -> Path:
    """Directory for timelock recovery data."""
    path = get_security_dir() / "timelock_recovery"
    path.mkdir(parents=True, exist_ok=True)
    return path


def migrate_vault_storage_to_data():
    """
    Migrate data from legacy vault_storage/ to data/.

    Only non-game data is migrated.
    """
    project_root = get_project_root()
    old_root = project_root / "vault_storage"

    if not old_root.exists():
        return

    import shutil

    migrations = [
        (old_root / "keys", get_keys_dir()),
        (old_root / "identities", get_identities_dir()),
        (old_root / "persistent", get_persistent_vaults_dir()),
        (old_root / "security", get_security_dir()),
        (old_root / "avatars", get_avatars_root()),
        (old_root / "ordinals_contract", get_ordinals_dir()),
        (old_root / "rune_contract", get_runes_dir()),
        (old_root / "staking", get_staking_dir()),
        (old_root / "runes_exchange", get_runes_exchange_dir()),
        (old_root / "genesis_data", get_genesis_data_dir()),
        (old_root / "tokens", get_avatar_tokens_dir()),
    ]

    for old_path, new_path in migrations:
        if old_path.exists():
            shutil.copytree(old_path, new_path, dirs_exist_ok=True)


def get_legacy_vault_storage() -> Path:
    """
    DEPRECATED: Use get_vaults_root() instead.
    """
    import warnings

    warnings.warn(
        "get_legacy_vault_storage() is deprecated. Use get_vaults_root() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_vaults_root()
