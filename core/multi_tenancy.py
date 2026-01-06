"""
Multi-Tenancy System pour Poly-Spinor Nexus 7D
Isolation des vaults par organisation avec roles et permissions

Features:
- Isolation complete des donnees par tenant
- Roles hierarchiques (Owner, Admin, Manager, Member, Viewer)
- Permissions granulaires sur les ressources
- Audit logs immutables avec signature cryptographique
- Quotas et limites par organisation
"""

import os
import json
import hashlib
import secrets
import time
from datetime import datetime
from typing import Optional, Dict, List, Any, Set
from dataclasses import dataclass, asdict, field
from enum import Enum, auto
from abc import ABC, abstractmethod

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.fernet import Fernet


# ============================================================================
# ENUMERATIONS
# ============================================================================

class Role(Enum):
    """Roles hierarchiques dans une organisation"""
    OWNER = 5       # Proprietaire - tous les droits
    ADMIN = 4       # Administrateur - gestion complete
    MANAGER = 3     # Manager - gestion des membres et ressources
    MEMBER = 2      # Membre - acces aux ressources partagees
    VIEWER = 1      # Viewer - lecture seule
    GUEST = 0       # Invite - acces limite


class Permission(Enum):
    """Permissions granulaires"""
    # Vault permissions
    VAULT_CREATE = auto()
    VAULT_READ = auto()
    VAULT_UPDATE = auto()
    VAULT_DELETE = auto()
    VAULT_SHARE = auto()
    VAULT_EXPORT = auto()
    
    # Asset permissions
    ASSET_CREATE = auto()
    ASSET_READ = auto()
    ASSET_UPDATE = auto()
    ASSET_DELETE = auto()
    ASSET_TRANSFER = auto()
    
    # Document permissions
    DOC_CREATE = auto()
    DOC_READ = auto()
    DOC_UPDATE = auto()
    DOC_DELETE = auto()
    DOC_ENCRYPT = auto()
    DOC_DECRYPT = auto()
    
    # Organization permissions
    ORG_MANAGE = auto()
    ORG_INVITE = auto()
    ORG_REMOVE = auto()
    ORG_SETTINGS = auto()
    
    # Admin permissions
    ADMIN_AUDIT = auto()
    ADMIN_KEYS = auto()
    ADMIN_BILLING = auto()
    ADMIN_API = auto()


class AuditAction(Enum):
    """Types d'actions pour l'audit"""
    # Auth
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    LOGIN_FAILED = "auth.login_failed"
    PASSWORD_CHANGE = "auth.password_change"
    MFA_ENABLE = "auth.mfa_enable"
    
    # Vault
    VAULT_CREATE = "vault.create"
    VAULT_ACCESS = "vault.access"
    VAULT_UPDATE = "vault.update"
    VAULT_DELETE = "vault.delete"
    VAULT_SHARE = "vault.share"
    VAULT_EXPORT = "vault.export"
    
    # Asset
    ASSET_ADD = "asset.add"
    ASSET_VIEW = "asset.view"
    ASSET_UPDATE = "asset.update"
    ASSET_DELETE = "asset.delete"
    ASSET_TRANSFER = "asset.transfer"
    
    # Document
    DOC_UPLOAD = "doc.upload"
    DOC_DOWNLOAD = "doc.download"
    DOC_DELETE = "doc.delete"
    DOC_DECRYPT = "doc.decrypt"
    
    # Org
    ORG_CREATE = "org.create"
    ORG_UPDATE = "org.update"
    ORG_MEMBER_ADD = "org.member_add"
    ORG_MEMBER_REMOVE = "org.member_remove"
    ORG_ROLE_CHANGE = "org.role_change"
    
    # Admin
    ADMIN_SETTINGS = "admin.settings"
    ADMIN_KEY_ROTATE = "admin.key_rotate"
    ADMIN_EXPORT = "admin.export"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Organization:
    """Organisation/Tenant"""
    org_id: str
    name: str
    created_at: str
    owner_id: str
    
    # Settings
    settings: Dict[str, Any] = field(default_factory=dict)
    
    # Quotas
    max_vaults: int = 100
    max_members: int = 50
    max_storage_mb: int = 10240  # 10 GB
    
    # Encryption key (derived from master key)
    encryption_key_id: str = ""
    
    # Status
    is_active: bool = True
    suspended_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Member:
    """Membre d'une organisation"""
    user_id: str
    org_id: str
    role: Role
    joined_at: str
    
    # Custom permissions (override role defaults)
    custom_permissions: Set[Permission] = field(default_factory=set)
    denied_permissions: Set[Permission] = field(default_factory=set)
    
    # Status
    is_active: bool = True
    last_access: Optional[str] = None
    
    # MFA
    mfa_enabled: bool = False
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['role'] = self.role.name
        d['custom_permissions'] = [p.name for p in self.custom_permissions]
        d['denied_permissions'] = [p.name for p in self.denied_permissions]
        return d


@dataclass
class AuditLog:
    """Log d'audit immutable"""
    log_id: str
    timestamp: str
    org_id: str
    user_id: str
    action: AuditAction
    resource_type: str
    resource_id: str
    details: Dict[str, Any]
    ip_address: str
    user_agent: str
    
    # Integrity
    previous_hash: str
    log_hash: str
    signature: str
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['action'] = self.action.value
        return d


@dataclass
class TenantVault:
    """Vault isole pour un tenant"""
    vault_id: str
    org_id: str
    name: str
    created_at: str
    created_by: str
    
    # Encryption (tenant-specific key)
    encryption_key_hash: str = ""
    
    # Access control
    shared_with: List[str] = field(default_factory=list)  # user_ids
    
    # Stats
    asset_count: int = 0
    doc_count: int = 0
    size_bytes: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================================
# ROLE PERMISSIONS MAPPING
# ============================================================================

ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.OWNER: set(Permission),  # All permissions
    
    Role.ADMIN: {
        Permission.VAULT_CREATE, Permission.VAULT_READ, Permission.VAULT_UPDATE,
        Permission.VAULT_DELETE, Permission.VAULT_SHARE, Permission.VAULT_EXPORT,
        Permission.ASSET_CREATE, Permission.ASSET_READ, Permission.ASSET_UPDATE,
        Permission.ASSET_DELETE, Permission.ASSET_TRANSFER,
        Permission.DOC_CREATE, Permission.DOC_READ, Permission.DOC_UPDATE,
        Permission.DOC_DELETE, Permission.DOC_ENCRYPT, Permission.DOC_DECRYPT,
        Permission.ORG_MANAGE, Permission.ORG_INVITE, Permission.ORG_REMOVE,
        Permission.ORG_SETTINGS,
        Permission.ADMIN_AUDIT,
    },
    
    Role.MANAGER: {
        Permission.VAULT_CREATE, Permission.VAULT_READ, Permission.VAULT_UPDATE,
        Permission.VAULT_SHARE,
        Permission.ASSET_CREATE, Permission.ASSET_READ, Permission.ASSET_UPDATE,
        Permission.ASSET_DELETE,
        Permission.DOC_CREATE, Permission.DOC_READ, Permission.DOC_UPDATE,
        Permission.DOC_DELETE, Permission.DOC_ENCRYPT, Permission.DOC_DECRYPT,
        Permission.ORG_INVITE,
    },
    
    Role.MEMBER: {
        Permission.VAULT_READ, Permission.VAULT_UPDATE,
        Permission.ASSET_CREATE, Permission.ASSET_READ, Permission.ASSET_UPDATE,
        Permission.DOC_CREATE, Permission.DOC_READ, Permission.DOC_UPDATE,
        Permission.DOC_ENCRYPT, Permission.DOC_DECRYPT,
    },
    
    Role.VIEWER: {
        Permission.VAULT_READ,
        Permission.ASSET_READ,
        Permission.DOC_READ,
    },
    
    Role.GUEST: {
        Permission.VAULT_READ,
        Permission.ASSET_READ,
    },
}


# ============================================================================
# TENANT ISOLATION MANAGER
# ============================================================================

class TenantIsolationManager:
    """Gestionnaire d'isolation des tenants"""
    
    def __init__(self, master_key: bytes, data_dir: str = "./tenant_data"):
        self.master_key = master_key
        self.data_dir = data_dir
        
        # Create directories
        self.orgs_dir = f"{data_dir}/organizations"
        self.vaults_dir = f"{data_dir}/vaults"
        self.audit_dir = f"{data_dir}/audit"
        
        for d in [self.orgs_dir, self.vaults_dir, self.audit_dir]:
            os.makedirs(d, exist_ok=True)
        
        # Cache
        self._org_keys: Dict[str, bytes] = {}
    
    def _derive_org_key(self, org_id: str) -> bytes:
        """Derive une cle unique pour une organisation"""
        if org_id in self._org_keys:
            return self._org_keys[org_id]
        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=org_id.encode('utf-8'),
            info=b'poly-spinor-tenant-isolation-v1'
        )
        key = hkdf.derive(self.master_key)
        self._org_keys[org_id] = key
        return key
    
    def _encrypt_data(self, org_id: str, data: bytes) -> bytes:
        """Chiffre des donnees avec la cle du tenant"""
        key = self._derive_org_key(org_id)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data, org_id.encode())
        return nonce + ciphertext
    
    def _decrypt_data(self, org_id: str, encrypted: bytes) -> bytes:
        """Dechiffre des donnees avec la cle du tenant"""
        key = self._derive_org_key(org_id)
        aesgcm = AESGCM(key)
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]
        return aesgcm.decrypt(nonce, ciphertext, org_id.encode())
    
    def create_organization(self, name: str, owner_id: str) -> Organization:
        """Cree une nouvelle organisation"""
        org_id = secrets.token_hex(16)
        
        org = Organization(
            org_id=org_id,
            name=name,
            created_at=datetime.now().isoformat(),
            owner_id=owner_id,
            encryption_key_id=hashlib.sha256(self._derive_org_key(org_id)).hexdigest()[:16]
        )
        
        # Create org directory
        org_path = f"{self.orgs_dir}/{org_id}"
        os.makedirs(org_path, exist_ok=True)
        os.makedirs(f"{org_path}/members", exist_ok=True)
        
        # Save org data (encrypted)
        self._save_org(org)
        
        # Add owner as member
        self.add_member(org_id, owner_id, Role.OWNER)
        
        return org
    
    def _save_org(self, org: Organization):
        """Sauvegarde une organisation"""
        org_path = f"{self.orgs_dir}/{org.org_id}/org.enc"
        data = json.dumps(org.to_dict()).encode()
        encrypted = self._encrypt_data(org.org_id, data)
        
        with open(org_path, 'wb') as f:
            f.write(encrypted)
    
    def load_organization(self, org_id: str) -> Optional[Organization]:
        """Charge une organisation"""
        org_path = f"{self.orgs_dir}/{org_id}/org.enc"
        
        if not os.path.exists(org_path):
            return None
        
        with open(org_path, 'rb') as f:
            encrypted = f.read()
        
        data = self._decrypt_data(org_id, encrypted)
        d = json.loads(data.decode())
        return Organization(**d)
    
    def add_member(self, org_id: str, user_id: str, role: Role) -> Member:
        """Ajoute un membre a une organisation"""
        member = Member(
            user_id=user_id,
            org_id=org_id,
            role=role,
            joined_at=datetime.now().isoformat()
        )
        
        # Save member
        member_path = f"{self.orgs_dir}/{org_id}/members/{user_id}.enc"
        data = json.dumps(member.to_dict()).encode()
        encrypted = self._encrypt_data(org_id, data)
        
        with open(member_path, 'wb') as f:
            f.write(encrypted)
        
        return member
    
    def get_member(self, org_id: str, user_id: str) -> Optional[Member]:
        """Recupere un membre"""
        member_path = f"{self.orgs_dir}/{org_id}/members/{user_id}.enc"
        
        if not os.path.exists(member_path):
            return None
        
        with open(member_path, 'rb') as f:
            encrypted = f.read()
        
        data = self._decrypt_data(org_id, encrypted)
        d = json.loads(data.decode())
        d['role'] = Role[d['role']]
        d['custom_permissions'] = {Permission[p] for p in d.get('custom_permissions', [])}
        d['denied_permissions'] = {Permission[p] for p in d.get('denied_permissions', [])}
        return Member(**d)
    
    def update_member_role(self, org_id: str, user_id: str, new_role: Role) -> bool:
        """Met a jour le role d'un membre"""
        member = self.get_member(org_id, user_id)
        if not member:
            return False
        
        member.role = new_role
        
        # Save
        member_path = f"{self.orgs_dir}/{org_id}/members/{user_id}.enc"
        data = json.dumps(member.to_dict()).encode()
        encrypted = self._encrypt_data(org_id, data)
        
        with open(member_path, 'wb') as f:
            f.write(encrypted)
        
        return True
    
    def remove_member(self, org_id: str, user_id: str) -> bool:
        """Retire un membre d'une organisation"""
        member_path = f"{self.orgs_dir}/{org_id}/members/{user_id}.enc"
        
        if os.path.exists(member_path):
            os.remove(member_path)
            return True
        return False
    
    def list_members(self, org_id: str) -> List[Member]:
        """Liste les membres d'une organisation"""
        members_dir = f"{self.orgs_dir}/{org_id}/members"
        members = []
        
        if not os.path.exists(members_dir):
            return members
        
        for filename in os.listdir(members_dir):
            if filename.endswith('.enc'):
                user_id = filename[:-4]
                member = self.get_member(org_id, user_id)
                if member:
                    members.append(member)
        
        return members


# ============================================================================
# PERMISSION CHECKER
# ============================================================================

class PermissionChecker:
    """Verificateur de permissions"""
    
    def __init__(self, tenant_manager: TenantIsolationManager):
        self.tenant_manager = tenant_manager
    
    def get_effective_permissions(self, org_id: str, user_id: str) -> Set[Permission]:
        """Obtient les permissions effectives d'un utilisateur"""
        member = self.tenant_manager.get_member(org_id, user_id)
        
        if not member or not member.is_active:
            return set()
        
        # Start with role permissions
        permissions = ROLE_PERMISSIONS.get(member.role, set()).copy()
        
        # Add custom permissions
        permissions |= member.custom_permissions
        
        # Remove denied permissions
        permissions -= member.denied_permissions
        
        return permissions
    
    def has_permission(self, org_id: str, user_id: str, permission: Permission) -> bool:
        """Verifie si un utilisateur a une permission"""
        permissions = self.get_effective_permissions(org_id, user_id)
        return permission in permissions
    
    def require_permission(self, org_id: str, user_id: str, permission: Permission):
        """Exige une permission (leve une exception si absente)"""
        if not self.has_permission(org_id, user_id, permission):
            raise PermissionError(
                f"User {user_id} lacks permission {permission.name} in org {org_id}"
            )
    
    def can_access_vault(self, org_id: str, user_id: str, vault_id: str) -> bool:
        """Verifie si un utilisateur peut acceder a un vault"""
        if not self.has_permission(org_id, user_id, Permission.VAULT_READ):
            return False
        
        # Check vault ownership or sharing
        # (simplified - in production, check vault.shared_with)
        return True


# ============================================================================
# AUDIT LOGGER
# ============================================================================

class ImmutableAuditLogger:
    """Logger d'audit immutable avec chaine de hachage"""
    
    def __init__(self, tenant_manager: TenantIsolationManager, signing_key: bytes):
        self.tenant_manager = tenant_manager
        self.signing_key = signing_key
        self._last_hashes: Dict[str, str] = {}
    
    def _compute_hash(self, log: AuditLog) -> str:
        """Calcule le hash d'un log"""
        data = f"{log.timestamp}:{log.org_id}:{log.user_id}:{log.action.value}:" \
               f"{log.resource_type}:{log.resource_id}:{json.dumps(log.details)}:" \
               f"{log.previous_hash}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _sign_log(self, log_hash: str) -> str:
        """Signe un log"""
        import hmac
        signature = hmac.new(
            self.signing_key,
            log_hash.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_last_hash(self, org_id: str) -> str:
        """Obtient le dernier hash pour une org"""
        if org_id in self._last_hashes:
            return self._last_hashes[org_id]
        
        # Try to load from file
        last_hash_file = f"{self.tenant_manager.audit_dir}/{org_id}/last_hash"
        if os.path.exists(last_hash_file):
            with open(last_hash_file, 'r') as f:
                return f.read().strip()
        
        return "0" * 64  # Genesis hash
    
    def _save_last_hash(self, org_id: str, log_hash: str):
        """Sauvegarde le dernier hash"""
        self._last_hashes[org_id] = log_hash
        
        audit_dir = f"{self.tenant_manager.audit_dir}/{org_id}"
        os.makedirs(audit_dir, exist_ok=True)
        
        with open(f"{audit_dir}/last_hash", 'w') as f:
            f.write(log_hash)
    
    def log(self, org_id: str, user_id: str, action: AuditAction,
            resource_type: str, resource_id: str, details: Dict[str, Any] = None,
            ip_address: str = "0.0.0.0", user_agent: str = "unknown") -> AuditLog:
        """Enregistre un evenement d'audit"""
        
        log_id = secrets.token_hex(16)
        timestamp = datetime.now().isoformat()
        previous_hash = self._get_last_hash(org_id)
        
        log = AuditLog(
            log_id=log_id,
            timestamp=timestamp,
            org_id=org_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            previous_hash=previous_hash,
            log_hash="",
            signature=""
        )
        
        # Compute hash and signature
        log.log_hash = self._compute_hash(log)
        log.signature = self._sign_log(log.log_hash)
        
        # Save log
        self._save_log(org_id, log)
        
        # Update last hash
        self._save_last_hash(org_id, log.log_hash)
        
        return log
    
    def _save_log(self, org_id: str, log: AuditLog):
        """Sauvegarde un log d'audit"""
        audit_dir = f"{self.tenant_manager.audit_dir}/{org_id}"
        os.makedirs(audit_dir, exist_ok=True)
        
        # Daily log file
        date_str = log.timestamp[:10]
        log_file = f"{audit_dir}/audit_{date_str}.jsonl"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log.to_dict()) + '\n')
    
    def verify_chain(self, org_id: str) -> bool:
        """Verifie l'integrite de la chaine d'audit"""
        audit_dir = f"{self.tenant_manager.audit_dir}/{org_id}"
        
        if not os.path.exists(audit_dir):
            return True
        
        all_logs = []
        
        # Load all logs
        for filename in sorted(os.listdir(audit_dir)):
            if filename.startswith("audit_") and filename.endswith(".jsonl"):
                with open(f"{audit_dir}/{filename}", 'r') as f:
                    for line in f:
                        d = json.loads(line)
                        d['action'] = AuditAction(d['action'])
                        all_logs.append(AuditLog(**d))
        
        # Verify chain
        expected_previous = "0" * 64
        
        for log in all_logs:
            # Verify previous hash
            if log.previous_hash != expected_previous:
                return False
            
            # Verify log hash
            computed_hash = self._compute_hash(log)
            if computed_hash != log.log_hash:
                return False
            
            # Verify signature
            expected_sig = self._sign_log(log.log_hash)
            if expected_sig != log.signature:
                return False
            
            expected_previous = log.log_hash
        
        return True
    
    def get_logs(self, org_id: str, start_date: str = None, end_date: str = None,
                 user_id: str = None, action: AuditAction = None,
                 limit: int = 100) -> List[AuditLog]:
        """Recupere les logs d'audit filtres"""
        audit_dir = f"{self.tenant_manager.audit_dir}/{org_id}"
        
        if not os.path.exists(audit_dir):
            return []
        
        logs = []
        
        for filename in sorted(os.listdir(audit_dir), reverse=True):
            if not filename.startswith("audit_"):
                continue
            
            file_date = filename[6:16]  # audit_YYYY-MM-DD.jsonl
            
            if start_date and file_date < start_date:
                continue
            if end_date and file_date > end_date:
                continue
            
            with open(f"{audit_dir}/{filename}", 'r') as f:
                for line in f:
                    if len(logs) >= limit:
                        break
                    
                    d = json.loads(line)
                    
                    # Apply filters
                    if user_id and d.get('user_id') != user_id:
                        continue
                    if action and d.get('action') != action.value:
                        continue
                    
                    d['action'] = AuditAction(d['action'])
                    logs.append(AuditLog(**d))
            
            if len(logs) >= limit:
                break
        
        return logs


# ============================================================================
# MULTI-TENANT VAULT MANAGER
# ============================================================================

class MultiTenantVaultManager:
    """Gestionnaire de vaults multi-tenant"""
    
    def __init__(self, master_key: bytes, data_dir: str = "./tenant_data"):
        self.tenant_manager = TenantIsolationManager(master_key, data_dir)
        self.permission_checker = PermissionChecker(self.tenant_manager)
        self.audit_logger = ImmutableAuditLogger(self.tenant_manager, master_key)
        self.vaults_dir = f"{data_dir}/vaults"
    
    def create_vault(self, org_id: str, user_id: str, name: str,
                    ip_address: str = "0.0.0.0") -> TenantVault:
        """Cree un vault pour un tenant"""
        # Check permission
        self.permission_checker.require_permission(org_id, user_id, Permission.VAULT_CREATE)
        
        # Check quota
        org = self.tenant_manager.load_organization(org_id)
        if not org:
            raise ValueError(f"Organization {org_id} not found")
        
        existing_vaults = self.list_vaults(org_id, user_id)
        if len(existing_vaults) >= org.max_vaults:
            raise ValueError(f"Vault quota exceeded ({org.max_vaults})")
        
        # Create vault
        vault_id = secrets.token_hex(16)
        vault = TenantVault(
            vault_id=vault_id,
            org_id=org_id,
            name=name,
            created_at=datetime.now().isoformat(),
            created_by=user_id,
            encryption_key_hash=hashlib.sha256(
                self.tenant_manager._derive_org_key(org_id) + vault_id.encode()
            ).hexdigest()[:16]
        )
        
        # Save vault
        self._save_vault(vault)
        
        # Audit log
        self.audit_logger.log(
            org_id=org_id,
            user_id=user_id,
            action=AuditAction.VAULT_CREATE,
            resource_type="vault",
            resource_id=vault_id,
            details={"name": name},
            ip_address=ip_address
        )
        
        return vault
    
    def _save_vault(self, vault: TenantVault):
        """Sauvegarde un vault"""
        vault_dir = f"{self.vaults_dir}/{vault.org_id}"
        os.makedirs(vault_dir, exist_ok=True)
        
        vault_path = f"{vault_dir}/{vault.vault_id}.enc"
        data = json.dumps(vault.to_dict()).encode()
        encrypted = self.tenant_manager._encrypt_data(vault.org_id, data)
        
        with open(vault_path, 'wb') as f:
            f.write(encrypted)
    
    def get_vault(self, org_id: str, user_id: str, vault_id: str) -> Optional[TenantVault]:
        """Recupere un vault"""
        # Check permission
        self.permission_checker.require_permission(org_id, user_id, Permission.VAULT_READ)
        
        vault_path = f"{self.vaults_dir}/{org_id}/{vault_id}.enc"
        
        if not os.path.exists(vault_path):
            return None
        
        with open(vault_path, 'rb') as f:
            encrypted = f.read()
        
        data = self.tenant_manager._decrypt_data(org_id, encrypted)
        d = json.loads(data.decode())
        
        # Log access
        self.audit_logger.log(
            org_id=org_id,
            user_id=user_id,
            action=AuditAction.VAULT_ACCESS,
            resource_type="vault",
            resource_id=vault_id
        )
        
        return TenantVault(**d)
    
    def list_vaults(self, org_id: str, user_id: str) -> List[TenantVault]:
        """Liste les vaults d'une organisation"""
        self.permission_checker.require_permission(org_id, user_id, Permission.VAULT_READ)
        
        vault_dir = f"{self.vaults_dir}/{org_id}"
        vaults = []
        
        if not os.path.exists(vault_dir):
            return vaults
        
        for filename in os.listdir(vault_dir):
            if filename.endswith('.enc'):
                vault_id = filename[:-4]
                vault = self.get_vault(org_id, user_id, vault_id)
                if vault:
                    vaults.append(vault)
        
        return vaults
    
    def delete_vault(self, org_id: str, user_id: str, vault_id: str,
                    ip_address: str = "0.0.0.0") -> bool:
        """Supprime un vault"""
        self.permission_checker.require_permission(org_id, user_id, Permission.VAULT_DELETE)
        
        vault_path = f"{self.vaults_dir}/{org_id}/{vault_id}.enc"
        
        if os.path.exists(vault_path):
            os.remove(vault_path)
            
            # Audit log
            self.audit_logger.log(
                org_id=org_id,
                user_id=user_id,
                action=AuditAction.VAULT_DELETE,
                resource_type="vault",
                resource_id=vault_id,
                ip_address=ip_address
            )
            
            return True
        
        return False
    
    def share_vault(self, org_id: str, user_id: str, vault_id: str,
                   share_with_user_id: str, ip_address: str = "0.0.0.0") -> bool:
        """Partage un vault avec un autre membre"""
        self.permission_checker.require_permission(org_id, user_id, Permission.VAULT_SHARE)
        
        vault = self.get_vault(org_id, user_id, vault_id)
        if not vault:
            return False
        
        if share_with_user_id not in vault.shared_with:
            vault.shared_with.append(share_with_user_id)
            self._save_vault(vault)
            
            # Audit log
            self.audit_logger.log(
                org_id=org_id,
                user_id=user_id,
                action=AuditAction.VAULT_SHARE,
                resource_type="vault",
                resource_id=vault_id,
                details={"shared_with": share_with_user_id},
                ip_address=ip_address
            )
        
        return True


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_multi_tenant_system(master_key: bytes, data_dir: str = "./tenant_data") -> MultiTenantVaultManager:
    """Cree un systeme multi-tenant complet"""
    return MultiTenantVaultManager(master_key, data_dir)
