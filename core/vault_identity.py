#!/usr/bin/env python3
"""
Eidolon - Vault Identity System
================================

Links vaults to their cryptographic key files (.psnx + .blend_data).
A vault only exists if it has valid key files.

The vault identity is derived from:
1. The .psnx file (encrypted key data)
2. The .blend_data file (3D entropy data)
3. Together they produce the vault_key

Vault data (items, equipment, avatars) is tied to the vault_id,
which is a hash of the vault_key.
"""

import os
import sys
import json
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ============================================================================
# CONSTANTS
# ============================================================================

VAULT_REGISTRY_FILE = "vault_registry.json"
VAULT_DATA_DIR = "vault_data"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class VaultIdentity:
    """Represents a vault linked to its key files"""
    
    # Core identity
    vault_id: str               # Hash of vault_key (unique identifier)
    vault_number: int           # Registration number (pioneer order)
    vault_name: str             # User-chosen name
    
    # Key files (paths)
    psnx_path: str              # Path to .psnx file
    blend_path: str             # Path to .blend_data file
    
    # Verification
    psnx_hash: str              # SHA-256 of .psnx file
    blend_hash: str             # SHA-256 of .blend_data file
    vault_key_hash: str         # Hash of derived vault_key (for verification)
    
    # Metadata
    created_at: str = ""
    last_accessed: str = ""
    pioneer_tier: str = "standard"
    genesis_block: Optional[int] = None
    
    # Status
    is_active: bool = True
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        self.last_accessed = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VaultIdentity':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def get_short_id(self) -> str:
        """Get short vault ID for display"""
        return self.vault_id[:16]
    
    def verify_files_exist(self) -> Tuple[bool, str]:
        """Check if key files still exist"""
        if not os.path.exists(self.psnx_path):
            return False, f"PSNX file not found: {self.psnx_path}"
        if not os.path.exists(self.blend_path):
            return False, f"Blend file not found: {self.blend_path}"
        return True, "OK"
    
    def verify_file_hashes(self) -> Tuple[bool, str]:
        """Verify key files haven't been modified"""
        exists, msg = self.verify_files_exist()
        if not exists:
            return False, msg
        
        # Check PSNX hash
        with open(self.psnx_path, 'rb') as f:
            current_psnx_hash = hashlib.sha256(f.read()).hexdigest()
        if current_psnx_hash != self.psnx_hash:
            return False, "PSNX file has been modified"
        
        # Check Blend hash
        with open(self.blend_path, 'rb') as f:
            current_blend_hash = hashlib.sha256(f.read()).hexdigest()
        if current_blend_hash != self.blend_hash:
            return False, "Blend file has been modified"
        
        return True, "OK"


# ============================================================================
# VAULT IDENTITY MANAGER
# ============================================================================

class VaultIdentityManager:
    """
    Manages vault identities linked to key files.
    
    A vault is only valid if:
    1. It has .psnx and .blend_data files
    2. The files can derive the correct vault_key
    3. The vault_id matches the vault_key hash
    """
    
    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            base_path = Path(__file__).parent.parent
            storage_dir = base_path / "vault_storage" / "identities"
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.registry_file = self.storage_dir / VAULT_REGISTRY_FILE
        self._load_registry()
    
    def _load_registry(self):
        """Load vault registry from disk"""
        if self.registry_file.exists():
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.vaults: Dict[str, VaultIdentity] = {
                k: VaultIdentity.from_dict(v) for k, v in data.get("vaults", {}).items()
            }
            self.next_vault_number = data.get("next_vault_number", 1)
        else:
            self.vaults = {}
            self.next_vault_number = 1
    
    def _save_registry(self):
        """Save vault registry to disk"""
        data = {
            "vaults": {k: v.to_dict() for k, v in self.vaults.items()},
            "next_vault_number": self.next_vault_number,
            "updated_at": datetime.utcnow().isoformat(),
        }
        with open(self.registry_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of a file"""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def _derive_vault_id(self, vault_key: bytes) -> str:
        """Derive vault ID from vault key"""
        return hashlib.sha256(vault_key).hexdigest()
    
    def _get_pioneer_tier(self, vault_number: int) -> str:
        """Get pioneer tier based on vault number"""
        if vault_number <= 10:
            return "genesis"
        elif vault_number <= 33:
            return "primordial"
        elif vault_number <= 100:
            return "supreme"
        elif vault_number <= 333:
            return "elite"
        elif vault_number <= 1000:
            return "veteran"
        elif vault_number <= 3333:
            return "early"
        elif vault_number <= 10000:
            return "pioneer"
        else:
            return "standard"
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def register_vault(self, vault_name: str, psnx_path: str, blend_path: str,
                       vault_key: bytes, genesis_block: int = None) -> Tuple[bool, VaultIdentity, str]:
        """
        Register a new vault from key files.
        
        Args:
            vault_name: User-chosen name
            psnx_path: Path to .psnx file
            blend_path: Path to .blend_data file
            vault_key: Derived vault key (from authentication)
            genesis_block: Genesis block number (if applicable)
        
        Returns:
            (success, vault_identity, message)
        """
        # Verify files exist
        if not os.path.exists(psnx_path):
            return False, None, f"PSNX file not found: {psnx_path}"
        if not os.path.exists(blend_path):
            return False, None, f"Blend file not found: {blend_path}"
        
        # Compute vault ID
        vault_id = self._derive_vault_id(vault_key)
        
        # Check if already registered
        if vault_id in self.vaults:
            existing = self.vaults[vault_id]
            return False, existing, f"Vault already registered as '{existing.vault_name}' (#{existing.vault_number})"
        
        # Compute file hashes
        psnx_hash = self._compute_file_hash(psnx_path)
        blend_hash = self._compute_file_hash(blend_path)
        vault_key_hash = hashlib.sha256(vault_key + b"EIDOLON_VERIFY").hexdigest()
        
        # Assign vault number
        vault_number = self.next_vault_number
        self.next_vault_number += 1
        
        # Get pioneer tier
        pioneer_tier = self._get_pioneer_tier(vault_number)
        
        # Create identity
        identity = VaultIdentity(
            vault_id=vault_id,
            vault_number=vault_number,
            vault_name=vault_name,
            psnx_path=os.path.abspath(psnx_path),
            blend_path=os.path.abspath(blend_path),
            psnx_hash=psnx_hash,
            blend_hash=blend_hash,
            vault_key_hash=vault_key_hash,
            pioneer_tier=pioneer_tier,
            genesis_block=genesis_block,
        )
        
        # Store
        self.vaults[vault_id] = identity
        self._save_registry()
        
        # Create vault data directory
        vault_data_dir = self.storage_dir / VAULT_DATA_DIR / vault_id[:16]
        vault_data_dir.mkdir(parents=True, exist_ok=True)
        
        return True, identity, f"Vault '{vault_name}' registered as #{vault_number} ({pioneer_tier})"
    
    def get_vault(self, vault_id: str) -> Optional[VaultIdentity]:
        """Get vault by ID"""
        return self.vaults.get(vault_id)
    
    def get_vault_by_number(self, vault_number: int) -> Optional[VaultIdentity]:
        """Get vault by registration number"""
        for vault in self.vaults.values():
            if vault.vault_number == vault_number:
                return vault
        return None
    
    def get_vault_by_name(self, vault_name: str) -> Optional[VaultIdentity]:
        """Get vault by name (case-insensitive)"""
        vault_name_lower = vault_name.lower()
        for vault in self.vaults.values():
            if vault.vault_name.lower() == vault_name_lower:
                return vault
        return None
    
    def get_vault_by_key(self, vault_key: bytes) -> Optional[VaultIdentity]:
        """Get vault by vault key"""
        # First try direct vault_id match
        vault_id = self._derive_vault_id(vault_key)
        if vault_id in self.vaults:
            return self.vaults.get(vault_id)
        
        # Fallback: search by vault_key_hash
        vault_key_hash = hashlib.sha256(vault_key).hexdigest()
        for vault in self.vaults.values():
            if vault.vault_key_hash == vault_key_hash:
                return vault
        
        return None
    
    def list_vaults(self, active_only: bool = True) -> List[VaultIdentity]:
        """List all registered vaults"""
        vaults = list(self.vaults.values())
        if active_only:
            vaults = [v for v in vaults if v.is_active]
        return sorted(vaults, key=lambda v: v.vault_number)
    
    def verify_vault(self, vault_id: str, vault_key: bytes) -> Tuple[bool, str]:
        """
        Verify a vault's integrity.
        
        Checks:
        1. Vault exists in registry
        2. Key files exist
        3. Key files haven't been modified
        4. Vault key matches
        """
        vault = self.vaults.get(vault_id)
        if not vault:
            return False, "Vault not found in registry"
        
        # Check files exist
        exists, msg = vault.verify_files_exist()
        if not exists:
            return False, msg
        
        # Check file hashes
        valid, msg = vault.verify_file_hashes()
        if not valid:
            return False, msg
        
        # Verify vault key
        expected_hash = hashlib.sha256(vault_key + b"EIDOLON_VERIFY").hexdigest()
        if expected_hash != vault.vault_key_hash:
            return False, "Vault key mismatch"
        
        # Update last accessed
        vault.last_accessed = datetime.utcnow().isoformat()
        self._save_registry()
        
        return True, "Vault verified successfully"
    
    def update_vault_access(self, vault_id: str):
        """Update last access time"""
        if vault_id in self.vaults:
            self.vaults[vault_id].last_accessed = datetime.utcnow().isoformat()
            self._save_registry()
    
    def deactivate_vault(self, vault_id: str) -> Tuple[bool, str]:
        """Deactivate a vault (doesn't delete data)"""
        if vault_id not in self.vaults:
            return False, "Vault not found"
        
        self.vaults[vault_id].is_active = False
        self._save_registry()
        return True, "Vault deactivated"
    
    def get_vault_data_path(self, vault_id: str) -> Optional[Path]:
        """Get path to vault's data directory"""
        if vault_id not in self.vaults:
            return None
        return self.storage_dir / VAULT_DATA_DIR / vault_id[:16]
    
    def get_statistics(self) -> Dict:
        """Get vault statistics"""
        vaults = list(self.vaults.values())
        active = [v for v in vaults if v.is_active]
        
        tiers = {}
        for v in active:
            tiers[v.pioneer_tier] = tiers.get(v.pioneer_tier, 0) + 1
        
        return {
            "total_vaults": len(vaults),
            "active_vaults": len(active),
            "next_vault_number": self.next_vault_number,
            "by_tier": tiers,
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def authenticate_and_register(psnx_path: str, blend_path: str, 
                               vault_name: str = None) -> Tuple[bool, VaultIdentity, bytes, str]:
    """
    Authenticate with key files and register vault if new.
    
    Returns:
        (success, vault_identity, vault_key, message)
    """
    from ui.vault_gui_complete import DualKeyAuthenticator
    
    # Authenticate
    auth = DualKeyAuthenticator()
    success, msg = auth.authenticate(psnx_path, blend_path)
    
    if not success:
        return False, None, None, f"Authentication failed: {msg}"
    
    vault_key = auth.vault_key
    
    # Get or create vault identity
    manager = VaultIdentityManager()
    existing = manager.get_vault_by_key(vault_key)
    
    if existing:
        # Verify and update access
        valid, verify_msg = manager.verify_vault(existing.vault_id, vault_key)
        if not valid:
            return False, None, None, f"Vault verification failed: {verify_msg}"
        return True, existing, vault_key, f"Welcome back, {existing.vault_name} (#{existing.vault_number})"
    
    # Register new vault
    if not vault_name:
        vault_name = Path(psnx_path).stem.replace("vault_key_", "").split("_")[0]
    
    success, identity, msg = manager.register_vault(
        vault_name=vault_name,
        psnx_path=psnx_path,
        blend_path=blend_path,
        vault_key=vault_key
    )
    
    if not success:
        return False, identity, vault_key, msg
    
    return True, identity, vault_key, msg


def get_vault_for_key(vault_key: bytes) -> Optional[VaultIdentity]:
    """Get vault identity for a vault key"""
    manager = VaultIdentityManager()
    return manager.get_vault_by_key(vault_key)


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  VAULT IDENTITY SYSTEM - Test")
    print("=" * 60)
    
    manager = VaultIdentityManager()
    
    # Show statistics
    stats = manager.get_statistics()
    print(f"\n  Total vaults: {stats['total_vaults']}")
    print(f"  Active vaults: {stats['active_vaults']}")
    print(f"  Next vault number: {stats['next_vault_number']}")
    
    if stats['by_tier']:
        print(f"\n  By tier:")
        for tier, count in sorted(stats['by_tier'].items()):
            print(f"    {tier}: {count}")
    
    # List vaults
    vaults = manager.list_vaults()
    if vaults:
        print(f"\n  Registered vaults:")
        for v in vaults:
            print(f"    #{v.vault_number} {v.vault_name} ({v.pioneer_tier}) - {v.get_short_id()}")
    else:
        print(f"\n  No vaults registered yet.")
    
    print()
