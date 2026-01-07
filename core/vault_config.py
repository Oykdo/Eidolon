#!/usr/bin/env python
"""
Eidolon - Configuration du Vault
Gestion centralisée des paramètres et configurations

Fonctionnalités:
- Configuration persistante en JSON chiffré
- Profils de configuration multiples
- Validation des paramètres
- Migration de versions
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64


# ============================================================================
# ENUMS DE CONFIGURATION
# ============================================================================

class SecurityLevel(Enum):
    """Niveaux de sécurité"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PARANOID = "paranoid"


class BackupFrequency(Enum):
    """Fréquence des backups"""
    NEVER = "never"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


class Theme(Enum):
    """Thèmes de l'interface"""
    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"


# ============================================================================
# DATACLASSES DE CONFIGURATION
# ============================================================================

@dataclass
class SecurityConfig:
    """Configuration de sécurité"""
    level: str = "high"
    kdf_iterations: int = 100000
    auto_lock_minutes: int = 15
    require_confirmation: bool = True
    max_failed_attempts: int = 5
    enable_audit_log: bool = True
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SecurityConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class BackupConfig:
    """Configuration des backups"""
    enabled: bool = True
    frequency: str = "daily"
    retention_days: int = 30
    compress: bool = True
    encrypt: bool = True
    backup_path: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BackupConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class NetworkConfig:
    """Configuration réseau"""
    default_chain: str = "ethereum"
    rpc_endpoints: Dict[str, str] = field(default_factory=lambda: {
        "ethereum": "https://eth-mainnet.g.alchemy.com/v2/demo",
        "polygon": "https://polygon-rpc.com",
        "arbitrum": "https://arb1.arbitrum.io/rpc",
        "optimism": "https://mainnet.optimism.io",
        "bsc": "https://bsc-dataseed.binance.org"
    })
    timeout_seconds: int = 30
    retry_attempts: int = 3
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'NetworkConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class UIConfig:
    """Configuration de l'interface utilisateur"""
    theme: str = "dark"
    language: str = "fr"
    window_width: int = 1400
    window_height: int = 900
    show_notifications: bool = True
    confirm_actions: bool = True
    auto_refresh_seconds: int = 30
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UIConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TransferConfig:
    """Configuration des transfers"""
    default_delay_days: int = 30
    min_delay_days: int = 1
    max_delay_days: int = 365
    auto_execute: bool = True
    require_confirmation: bool = True
    notification_before_days: int = 3
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TransferConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class VaultConfiguration:
    """Configuration complète du vault"""
    version: str = "1.0"
    vault_name: str = ""
    created_at: str = ""
    modified_at: str = ""
    security: SecurityConfig = field(default_factory=SecurityConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    transfer: TransferConfig = field(default_factory=TransferConfig)
    custom: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.modified_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            'version': self.version,
            'vault_name': self.vault_name,
            'created_at': self.created_at,
            'modified_at': self.modified_at,
            'security': self.security.to_dict() if isinstance(self.security, SecurityConfig) else self.security,
            'backup': self.backup.to_dict() if isinstance(self.backup, BackupConfig) else self.backup,
            'network': self.network.to_dict() if isinstance(self.network, NetworkConfig) else self.network,
            'ui': self.ui.to_dict() if isinstance(self.ui, UIConfig) else self.ui,
            'transfer': self.transfer.to_dict() if isinstance(self.transfer, TransferConfig) else self.transfer,
            'custom': self.custom
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VaultConfiguration':
        return cls(
            version=data.get('version', '1.0'),
            vault_name=data.get('vault_name', ''),
            created_at=data.get('created_at', ''),
            modified_at=data.get('modified_at', ''),
            security=SecurityConfig.from_dict(data.get('security', {})),
            backup=BackupConfig.from_dict(data.get('backup', {})),
            network=NetworkConfig.from_dict(data.get('network', {})),
            ui=UIConfig.from_dict(data.get('ui', {})),
            transfer=TransferConfig.from_dict(data.get('transfer', {})),
            custom=data.get('custom', {})
        )


# ============================================================================
# GESTIONNAIRE DE CONFIGURATION
# ============================================================================

class VaultConfigManager:
    """Gestionnaire de configuration du vault"""
    
    CONFIG_FILENAME = "vault_config.enc"
    PROFILES_DIR = "profiles"
    
    def __init__(self, vault_key: bytes, vault_path: str):
        """
        Initialiser le gestionnaire de configuration.
        
        Args:
            vault_key: Clé de chiffrement
            vault_path: Chemin du répertoire du vault
        """
        if isinstance(vault_key, str):
            vault_key = vault_key.encode()
        
        self.vault_key = vault_key
        self.vault_path = Path(vault_path)
        self.config_file = self.vault_path / self.CONFIG_FILENAME
        self.profiles_path = self.vault_path / self.PROFILES_DIR
        
        # Configuration actuelle
        self._config: Optional[VaultConfiguration] = None
        
        # Initialiser
        self._init_config()
    
    def _derive_key(self) -> bytes:
        """Dériver une clé Fernet"""
        salt = b'vault_config_salt_v1'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.vault_key))
    
    def _encrypt(self, data: Dict) -> bytes:
        """Chiffrer les données"""
        key = self._derive_key()
        fernet = Fernet(key)
        json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        return fernet.encrypt(json_data)
    
    def _decrypt(self, encrypted: bytes) -> Dict:
        """Déchiffrer les données"""
        key = self._derive_key()
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted)
        return json.loads(decrypted.decode('utf-8'))
    
    def _init_config(self):
        """Initialiser la configuration"""
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self.profiles_path.mkdir(parents=True, exist_ok=True)
        
        if self.config_file.exists():
            self._load()
        else:
            self._config = VaultConfiguration(vault_name=self.vault_path.name)
            self._save()
    
    def _load(self):
        """Charger la configuration depuis le fichier"""
        with open(self.config_file, 'rb') as f:
            encrypted = f.read()
        
        data = self._decrypt(encrypted)
        self._config = VaultConfiguration.from_dict(data)
    
    def _save(self):
        """Sauvegarder la configuration"""
        self._config.modified_at = datetime.now().isoformat()
        encrypted = self._encrypt(self._config.to_dict())
        
        with open(self.config_file, 'wb') as f:
            f.write(encrypted)
    
    @property
    def config(self) -> VaultConfiguration:
        """Accéder à la configuration"""
        if self._config is None:
            self._load()
        return self._config
    
    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        """
        Obtenir une valeur de configuration.
        
        Args:
            section: Section (security, backup, network, ui, transfer, custom)
            key: Clé optionnelle dans la section
            default: Valeur par défaut
        
        Returns:
            Valeur de configuration
        """
        config_dict = self.config.to_dict()
        
        if section not in config_dict:
            return default
        
        section_data = config_dict[section]
        
        if key is None:
            return section_data
        
        if isinstance(section_data, dict):
            return section_data.get(key, default)
        
        return getattr(section_data, key, default)
    
    def set(self, section: str, key: str, value: Any):
        """
        Définir une valeur de configuration.
        
        Args:
            section: Section
            key: Clé
            value: Nouvelle valeur
        """
        if section == 'security':
            setattr(self._config.security, key, value)
        elif section == 'backup':
            setattr(self._config.backup, key, value)
        elif section == 'network':
            if key == 'rpc_endpoints' and isinstance(value, dict):
                self._config.network.rpc_endpoints.update(value)
            else:
                setattr(self._config.network, key, value)
        elif section == 'ui':
            setattr(self._config.ui, key, value)
        elif section == 'transfer':
            setattr(self._config.transfer, key, value)
        elif section == 'custom':
            self._config.custom[key] = value
        
        self._save()
    
    def update_section(self, section: str, data: Dict):
        """
        Mettre à jour une section entière.
        
        Args:
            section: Section à mettre à jour
            data: Nouvelles données
        """
        if section == 'security':
            self._config.security = SecurityConfig.from_dict(data)
        elif section == 'backup':
            self._config.backup = BackupConfig.from_dict(data)
        elif section == 'network':
            self._config.network = NetworkConfig.from_dict(data)
        elif section == 'ui':
            self._config.ui = UIConfig.from_dict(data)
        elif section == 'transfer':
            self._config.transfer = TransferConfig.from_dict(data)
        elif section == 'custom':
            self._config.custom.update(data)
        
        self._save()
    
    def reset_section(self, section: str):
        """Réinitialiser une section aux valeurs par défaut"""
        if section == 'security':
            self._config.security = SecurityConfig()
        elif section == 'backup':
            self._config.backup = BackupConfig()
        elif section == 'network':
            self._config.network = NetworkConfig()
        elif section == 'ui':
            self._config.ui = UIConfig()
        elif section == 'transfer':
            self._config.transfer = TransferConfig()
        elif section == 'custom':
            self._config.custom = {}
        
        self._save()
    
    def reset_all(self):
        """Réinitialiser toute la configuration"""
        vault_name = self._config.vault_name
        created_at = self._config.created_at
        
        self._config = VaultConfiguration(
            vault_name=vault_name,
            created_at=created_at
        )
        self._save()
    
    # ========================================================================
    # PROFILS
    # ========================================================================
    
    def save_profile(self, profile_name: str) -> str:
        """
        Sauvegarder la configuration actuelle comme profil.
        
        Args:
            profile_name: Nom du profil
        
        Returns:
            Chemin du fichier de profil
        """
        profile_file = self.profiles_path / f"{profile_name}.enc"
        
        profile_data = {
            'name': profile_name,
            'created_at': datetime.now().isoformat(),
            'config': self._config.to_dict()
        }
        
        encrypted = self._encrypt(profile_data)
        with open(profile_file, 'wb') as f:
            f.write(encrypted)
        
        return str(profile_file)
    
    def load_profile(self, profile_name: str) -> bool:
        """
        Charger un profil de configuration.
        
        Args:
            profile_name: Nom du profil
        
        Returns:
            True si succès
        """
        profile_file = self.profiles_path / f"{profile_name}.enc"
        
        if not profile_file.exists():
            return False
        
        with open(profile_file, 'rb') as f:
            encrypted = f.read()
        
        profile_data = self._decrypt(encrypted)
        self._config = VaultConfiguration.from_dict(profile_data['config'])
        self._save()
        
        return True
    
    def list_profiles(self) -> List[str]:
        """Lister les profils disponibles"""
        profiles = []
        for f in self.profiles_path.glob("*.enc"):
            profiles.append(f.stem)
        return profiles
    
    def delete_profile(self, profile_name: str) -> bool:
        """Supprimer un profil"""
        profile_file = self.profiles_path / f"{profile_name}.enc"
        
        if profile_file.exists():
            profile_file.unlink()
            return True
        return False
    
    # ========================================================================
    # EXPORT / IMPORT
    # ========================================================================
    
    def export_config(self, output_path: str, include_sensitive: bool = False) -> str:
        """
        Exporter la configuration en JSON lisible.
        
        Args:
            output_path: Chemin de sortie
            include_sensitive: Inclure les données sensibles
        
        Returns:
            Chemin du fichier exporté
        """
        config_data = self._config.to_dict()
        
        if not include_sensitive:
            # Masquer les données sensibles
            if 'network' in config_data and 'rpc_endpoints' in config_data['network']:
                for chain in config_data['network']['rpc_endpoints']:
                    endpoint = config_data['network']['rpc_endpoints'][chain]
                    if 'api' in endpoint.lower() or 'key' in endpoint.lower():
                        config_data['network']['rpc_endpoints'][chain] = "[MASKED]"
        
        output_file = Path(output_path)
        if output_file.is_dir():
            output_file = output_file / f"vault_config_{datetime.now().strftime('%Y%m%d')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        return str(output_file)
    
    def import_config(self, input_path: str, merge: bool = False):
        """
        Importer une configuration depuis un fichier JSON.
        
        Args:
            input_path: Chemin du fichier
            merge: Fusionner avec la config existante au lieu de remplacer
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            imported_data = json.load(f)
        
        if merge:
            current_data = self._config.to_dict()
            self._deep_merge(current_data, imported_data)
            self._config = VaultConfiguration.from_dict(current_data)
        else:
            # Préserver certaines valeurs
            vault_name = self._config.vault_name
            created_at = self._config.created_at
            
            self._config = VaultConfiguration.from_dict(imported_data)
            self._config.vault_name = vault_name
            self._config.created_at = created_at
        
        self._save()
    
    def _deep_merge(self, base: Dict, override: Dict):
        """Fusionner deux dictionnaires récursivement"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    def validate(self) -> List[str]:
        """
        Valider la configuration.
        
        Returns:
            Liste des erreurs de validation (vide si OK)
        """
        errors = []
        
        # Validation sécurité
        if self._config.security.kdf_iterations < 10000:
            errors.append("security.kdf_iterations doit être >= 10000")
        
        if self._config.security.auto_lock_minutes < 1:
            errors.append("security.auto_lock_minutes doit être >= 1")
        
        # Validation backup
        if self._config.backup.retention_days < 1:
            errors.append("backup.retention_days doit être >= 1")
        
        # Validation transfer
        if self._config.transfer.min_delay_days < 0:
            errors.append("transfer.min_delay_days doit être >= 0")
        
        if self._config.transfer.max_delay_days < self._config.transfer.min_delay_days:
            errors.append("transfer.max_delay_days doit être >= min_delay_days")
        
        # Validation UI
        if self._config.ui.window_width < 800:
            errors.append("ui.window_width doit être >= 800")
        
        if self._config.ui.window_height < 600:
            errors.append("ui.window_height doit être >= 600")
        
        return errors


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def get_default_config() -> VaultConfiguration:
    """Obtenir une configuration par défaut"""
    return VaultConfiguration()


def create_config_manager(vault_key: bytes, vault_path: str) -> VaultConfigManager:
    """Créer un gestionnaire de configuration"""
    return VaultConfigManager(vault_key, vault_path)


# ============================================================================
# POINT D'ENTRÉE CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestionnaire de Configuration Vault")
    parser.add_argument("action", choices=["show", "set", "reset", "export", "validate"])
    parser.add_argument("--vault-path", "-p", required=True, help="Chemin du vault")
    parser.add_argument("--key", "-k", help="Clé du vault (hex)")
    parser.add_argument("--section", "-s", help="Section de configuration")
    parser.add_argument("--name", "-n", help="Nom de la clé")
    parser.add_argument("--value", "-v", help="Valeur")
    parser.add_argument("--output", "-o", help="Fichier de sortie")
    
    args = parser.parse_args()
    
    # Générer la clé si non fournie
    if args.key:
        vault_key = bytes.fromhex(args.key)
    else:
        vault_key = hashlib.sha256(args.vault_path.encode()).digest()
    
    manager = VaultConfigManager(vault_key, args.vault_path)
    
    if args.action == "show":
        if args.section:
            data = manager.get(args.section)
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(manager.config.to_dict(), indent=2, ensure_ascii=False))
    
    elif args.action == "set":
        if not args.section or not args.name or args.value is None:
            print("--section, --name et --value requis")
        else:
            # Essayer de parser la valeur comme JSON
            try:
                value = json.loads(args.value)
            except:
                value = args.value
            
            manager.set(args.section, args.name, value)
            print(f"Configuration mise à jour: {args.section}.{args.name} = {value}")
    
    elif args.action == "reset":
        if args.section:
            manager.reset_section(args.section)
            print(f"Section {args.section} réinitialisée")
        else:
            manager.reset_all()
            print("Configuration réinitialisée")
    
    elif args.action == "export":
        output = args.output or "."
        path = manager.export_config(output)
        print(f"Configuration exportée vers: {path}")
    
    elif args.action == "validate":
        errors = manager.validate()
        if errors:
            print("Erreurs de validation:")
            for e in errors:
                print(f"  - {e}")
        else:
            print("Configuration valide")
