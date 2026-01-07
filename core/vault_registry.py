#!/usr/bin/env python3
"""
Eidolon - Vault Registry
Manages local vault registration and authentication
"""

import os
import json
import hashlib
import secrets
import platform
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple


class VaultRegistry:
    """
    Local registry for initialized vaults.
    Stores vault metadata and password hashes for quick login.
    """
    
    REGISTRY_VERSION = "1.0"
    
    def __init__(self):
        self.registry_path = self._get_registry_path()
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry = self._load_registry()
    
    def _get_registry_path(self) -> Path:
        """Get platform-specific registry path"""
        if platform.system() == "Windows":
            base = Path(os.environ.get("APPDATA", "~"))
        else:
            base = Path.home() / ".config"
        
        return base / "Eidolon" / "vault_registry.json"
    
    def _get_device_id(self) -> str:
        """Generate unique device identifier"""
        # Combine multiple hardware identifiers
        identifiers = []
        
        # Machine ID
        try:
            if platform.system() == "Windows":
                import subprocess
                result = subprocess.run(
                    ['wmic', 'csproduct', 'get', 'uuid'],
                    capture_output=True, text=True
                )
                for line in result.stdout.strip().split('\n'):
                    if line.strip() and line.strip() != 'UUID':
                        identifiers.append(line.strip())
                        break
            else:
                machine_id_path = Path("/etc/machine-id")
                if machine_id_path.exists():
                    identifiers.append(machine_id_path.read_text().strip())
        except:
            pass
        
        # Fallback to MAC address + hostname
        identifiers.append(platform.node())
        identifiers.append(str(uuid.getnode()))
        
        # Hash all identifiers
        combined = "|".join(identifiers)
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    def _load_registry(self) -> Dict:
        """Load registry from disk"""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Verify device
                    if data.get("device_id") != self._get_device_id():
                        # Different device, start fresh
                        return self._create_empty_registry()
                    return data
            except:
                pass
        return self._create_empty_registry()
    
    def _create_empty_registry(self) -> Dict:
        """Create empty registry structure"""
        return {
            "version": self.REGISTRY_VERSION,
            "device_id": self._get_device_id(),
            "created_at": datetime.now().isoformat(),
            "vaults": {}
        }
    
    def _save_registry(self):
        """Save registry to disk"""
        self.registry["updated_at"] = datetime.now().isoformat()
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(self.registry, f, indent=2, ensure_ascii=False)
    
    def _hash_password(self, password: str, salt: bytes = None) -> Tuple[str, str]:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        # Use PBKDF2 with high iterations
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt,
            iterations=150000,
            dklen=32
        )
        
        return password_hash.hex(), salt.hex()
    
    def _verify_password(self, password: str, stored_hash: str, salt_hex: str) -> bool:
        """Verify password against stored hash"""
        salt = bytes.fromhex(salt_hex)
        computed_hash, _ = self._hash_password(password, salt)
        return secrets.compare_digest(computed_hash, stored_hash)
    
    def _derive_vault_key(self, vault_name: str, password: str, salt: bytes) -> bytes:
        """Derive vault encryption key from password"""
        # Different derivation for vault key (not the auth hash)
        key_salt = hashlib.sha256(salt + vault_name.encode()).digest()
        
        vault_key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            key_salt,
            iterations=100000,
            dklen=32
        )
        return vault_key
    
    # =========================================================================
    # Public API
    # =========================================================================
    
    def vault_exists(self, vault_name: str) -> bool:
        """Check if vault is registered"""
        return vault_name.lower() in self.registry["vaults"]
    
    def get_registered_vaults(self) -> List[Dict]:
        """Get list of registered vaults"""
        vaults = []
        for name, data in self.registry["vaults"].items():
            vaults.append({
                "name": data.get("display_name", name),
                "created_at": data.get("created_at"),
                "last_login": data.get("last_login"),
                "vault_number": data.get("vault_number"),
                "auth_method": data.get("auth_method", "password"),
                "login_count": data.get("login_count", 0)
            })
        return sorted(vaults, key=lambda x: x.get("last_login") or "", reverse=True)
    
    def register_vault(self, vault_name: str, password: str, vault_number: int = None) -> Tuple[bool, bytes, str]:
        """
        Register a new vault (Genesis).
        
        Returns:
            (success, vault_key, message)
        """
        vault_name_lower = vault_name.lower()
        
        if self.vault_exists(vault_name):
            return False, None, f"Vault '{vault_name}' already exists on this device"
        
        # Validate password strength
        if len(password) < 8:
            return False, None, "Password must be at least 8 characters"
        
        # Generate salt and hash password
        salt = secrets.token_bytes(32)
        password_hash, salt_hex = self._hash_password(password, salt)
        
        # Derive vault key
        vault_key = self._derive_vault_key(vault_name, password, salt)
        
        # Store in registry
        self.registry["vaults"][vault_name_lower] = {
            "display_name": vault_name,
            "password_hash": password_hash,
            "salt": salt_hex,
            "created_at": datetime.now().isoformat(),
            "last_login": datetime.now().isoformat(),
            "vault_number": vault_number,
            "login_count": 1
        }
        
        self._save_registry()
        
        return True, vault_key, f"Vault '{vault_name}' created successfully"
    
    def authenticate(self, vault_name: str, password: str) -> Tuple[bool, bytes, str]:
        """
        Authenticate to an existing vault.
        
        Returns:
            (success, vault_key, message)
        """
        vault_name_lower = vault_name.lower()
        
        if not self.vault_exists(vault_name):
            return False, None, f"Vault '{vault_name}' not found on this device"
        
        vault_data = self.registry["vaults"][vault_name_lower]
        
        # Verify password
        if not self._verify_password(password, vault_data["password_hash"], vault_data["salt"]):
            return False, None, "Invalid password"
        
        # Derive vault key
        salt = bytes.fromhex(vault_data["salt"])
        vault_key = self._derive_vault_key(vault_name, password, salt)
        
        # Update login stats
        vault_data["last_login"] = datetime.now().isoformat()
        vault_data["login_count"] = vault_data.get("login_count", 0) + 1
        self._save_registry()
        
        return True, vault_key, "Authentication successful"
    
    def register_vault_with_key(self, vault_name: str, password: str, 
                                 vault_key: bytes, vault_number: int = None) -> Tuple[bool, str]:
        """
        Register a vault with an externally-provided key (from key files).
        The password is used for future logins via quick connect.
        
        Args:
            vault_name: Name of the vault
            password: Password for future logins
            vault_key: The actual vault key (from .psnx/.blend_data auth)
            vault_number: Optional vault number
            
        Returns:
            (success, message)
        """
        vault_name_lower = vault_name.lower()
        
        if self.vault_exists(vault_name):
            return False, f"Vault '{vault_name}' already registered. Use Login instead."
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        
        # Generate salt and hash password
        salt = secrets.token_bytes(32)
        password_hash, salt_hex = self._hash_password(password, salt)
        
        # Store vault key hash for verification (not the key itself!)
        vault_key_verification = hashlib.sha256(vault_key + salt).hexdigest()
        
        # Store in registry
        self.registry["vaults"][vault_name_lower] = {
            "display_name": vault_name,
            "password_hash": password_hash,
            "salt": salt_hex,
            "vault_key_verification": vault_key_verification,
            "auth_method": "key_files",
            "created_at": datetime.now().isoformat(),
            "last_login": datetime.now().isoformat(),
            "vault_number": vault_number,
            "login_count": 1
        }
        
        self._save_registry()
        
        return True, f"Vault '{vault_name}' registered for quick connect"
    
    def authenticate_with_stored_key(self, vault_name: str, password: str, 
                                      vault_key: bytes) -> Tuple[bool, str]:
        """
        Authenticate using password and verify against stored vault key.
        Used for vaults registered via key files.
        
        Returns:
            (success, message)
        """
        vault_name_lower = vault_name.lower()
        
        if not self.vault_exists(vault_name):
            return False, f"Vault '{vault_name}' not found on this device"
        
        vault_data = self.registry["vaults"][vault_name_lower]
        
        # Verify password
        if not self._verify_password(password, vault_data["password_hash"], vault_data["salt"]):
            return False, "Invalid password"
        
        # Verify vault key if we have verification hash
        if "vault_key_verification" in vault_data:
            salt = bytes.fromhex(vault_data["salt"])
            expected_hash = hashlib.sha256(vault_key + salt).hexdigest()
            if expected_hash != vault_data["vault_key_verification"]:
                return False, "Vault key mismatch - use original key files"
        
        # Update login stats
        vault_data["last_login"] = datetime.now().isoformat()
        vault_data["login_count"] = vault_data.get("login_count", 0) + 1
        self._save_registry()
        
        return True, "Authentication successful"
    
    def get_vault_auth_method(self, vault_name: str) -> Optional[str]:
        """Get the authentication method used to register a vault"""
        vault_name_lower = vault_name.lower()
        if vault_name_lower in self.registry["vaults"]:
            return self.registry["vaults"][vault_name_lower].get("auth_method", "password")
        return None
    
    def delete_vault(self, vault_name: str, password: str) -> Tuple[bool, str]:
        """
        Delete a vault from registry (requires password).
        
        Returns:
            (success, message)
        """
        vault_name_lower = vault_name.lower()
        
        if not self.vault_exists(vault_name):
            return False, f"Vault '{vault_name}' not found"
        
        vault_data = self.registry["vaults"][vault_name_lower]
        
        # Verify password before deletion
        if not self._verify_password(password, vault_data["password_hash"], vault_data["salt"]):
            return False, "Invalid password - cannot delete vault"
        
        # Remove from registry
        del self.registry["vaults"][vault_name_lower]
        self._save_registry()
        
        return True, f"Vault '{vault_name}' removed from this device"
    
    def change_password(self, vault_name: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Change vault password.
        
        Returns:
            (success, message)
        """
        vault_name_lower = vault_name.lower()
        
        if not self.vault_exists(vault_name):
            return False, f"Vault '{vault_name}' not found"
        
        vault_data = self.registry["vaults"][vault_name_lower]
        
        # Verify old password
        if not self._verify_password(old_password, vault_data["password_hash"], vault_data["salt"]):
            return False, "Invalid current password"
        
        # Validate new password
        if len(new_password) < 8:
            return False, "New password must be at least 8 characters"
        
        # Generate new salt and hash
        new_salt = secrets.token_bytes(32)
        new_hash, new_salt_hex = self._hash_password(new_password, new_salt)
        
        # Update registry
        vault_data["password_hash"] = new_hash
        vault_data["salt"] = new_salt_hex
        vault_data["password_changed_at"] = datetime.now().isoformat()
        self._save_registry()
        
        return True, "Password changed successfully"
    
    def get_vault_info(self, vault_name: str) -> Optional[Dict]:
        """Get vault metadata"""
        vault_name_lower = vault_name.lower()
        if vault_name_lower in self.registry["vaults"]:
            data = self.registry["vaults"][vault_name_lower].copy()
            # Remove sensitive data
            data.pop("password_hash", None)
            data.pop("salt", None)
            return data
        return None


# =============================================================================
# Standalone test
# =============================================================================
if __name__ == "__main__":
    registry = VaultRegistry()
    
    print(f"Registry path: {registry.registry_path}")
    print(f"Device ID: {registry._get_device_id()[:16]}...")
    print(f"Registered vaults: {len(registry.get_registered_vaults())}")
    
    for vault in registry.get_registered_vaults():
        print(f"  - {vault['name']} (last login: {vault.get('last_login', 'never')})")
