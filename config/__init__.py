"""
Configuration module for Eidolon

Provides centralized configuration loading and management.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


# Chemin par défaut du fichier de configuration
DEFAULT_CONFIG_PATH = Path(__file__).parent / "vault_config.json"


@dataclass
class ChainConfig:
    """Configuration d'une chaîne blockchain"""
    rpc: str
    chain_id: int
    explorer: str
    symbol: str
    enabled: bool = True


class ConfigLoader:
    """Chargeur de configuration centralisé"""
    
    _instance = None
    _config: Dict[str, Any] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.reload()
    
    def reload(self, config_path: str = None):
        """Recharger la configuration depuis le fichier"""
        path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        else:
            self._config = self._default_config()
    
    def _default_config(self) -> Dict:
        """Configuration par défaut"""
        return {
            "version": "1.0",
            "vault_settings": {
                "persistence": {"auto_save_interval": 300},
                "security": {"require_dual_key": True},
                "monitoring": {"check_interval": 30},
                "transfers": {"default_delay_days": 30}
            },
            "chains": {},
            "storage": {
                "vault_directory": "data/vaults/persistent",
                "documents_directory": "data/vaults/documents",
                "keys_directory": "data/vaults/keys",
                "backups_directory": "data/vaults/backups",
                "logs_directory": "data/vaults/logs"
            },
            "ui": {"theme": "dark", "language": "fr"}
        }
    
    def get(self, *keys, default=None) -> Any:
        """
        Obtenir une valeur de configuration par chemin de clés.
        
        Exemple: config.get('vault_settings', 'security', 'max_login_attempts')
        """
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, *keys, value: Any):
        """Définir une valeur de configuration"""
        if len(keys) < 1:
            return
        
        target = self._config
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        target[keys[-1]] = value
    
    def save(self, config_path: str = None):
        """Sauvegarder la configuration"""
        path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
    
    @property
    def vault_settings(self) -> Dict:
        return self._config.get('vault_settings', {})
    
    @property
    def chains(self) -> Dict[str, ChainConfig]:
        chains_data = self._config.get('chains', {})
        return {
            name: ChainConfig(**data) 
            for name, data in chains_data.items()
        }
    
    @property
    def enabled_chains(self) -> Dict[str, ChainConfig]:
        return {
            name: chain 
            for name, chain in self.chains.items() 
            if chain.enabled
        }
    
    @property
    def storage(self) -> Dict:
        return self._config.get('storage', {})
    
    @property
    def ui(self) -> Dict:
        return self._config.get('ui', {})
    
    @property
    def monitoring(self) -> Dict:
        return self.get('vault_settings', 'monitoring', default={})
    
    @property
    def security(self) -> Dict:
        return self.get('vault_settings', 'security', default={})
    
    @property
    def transfers(self) -> Dict:
        return self.get('vault_settings', 'transfers', default={})


# Instance globale
config = ConfigLoader()


def get_config() -> ConfigLoader:
    """Obtenir l'instance de configuration"""
    return config


def get_chain_rpc(chain_name: str) -> Optional[str]:
    """Obtenir l'URL RPC d'une chaîne"""
    return config.get('chains', chain_name, 'rpc')


def get_storage_path(path_type: str = 'vault_directory') -> Path:
    """Obtenir un chemin de stockage"""
    base = Path(__file__).parent.parent
    default_paths = {
        'vault_directory': 'data/vaults/persistent',
        'documents_directory': 'data/vaults/documents',
        'keys_directory': 'data/vaults/keys',
        'backups_directory': 'data/vaults/backups',
        'logs_directory': 'data/vaults/logs',
    }
    relative_path = config.get('storage', path_type, default=default_paths.get(path_type, 'data/vaults'))
    return base / relative_path


def is_feature_enabled(feature: str) -> bool:
    """Vérifier si une fonctionnalité est activée"""
    feature_map = {
        'monitoring': ('vault_settings', 'monitoring', 'enabled'),
        'api': ('api', 'enabled'),
        'notifications': ('notifications', 'enabled'),
        'compression': ('storage', 'compression_enabled'),
        'debug': ('advanced', 'debug_mode')
    }
    
    if feature in feature_map:
        return config.get(*feature_map[feature], default=False)
    return False
