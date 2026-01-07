#!/usr/bin/env python
"""
Eidolon - Gestionnaire de Vault Persistant
Stockage chiffré avec gestion des transfers programmés

Fonctionnalités:
- Persistance chiffrée avec Fernet (PBKDF2 + AES-128-CBC)
- Gestion des actifs, documents et tokens
- Système de transfers avec délai configurable
- Export/Import de vault complet
- Backups automatiques horodatés
"""

import json
import os
import sys
import hashlib
import zipfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


# ============================================================================
# EXCEPTIONS
# ============================================================================

class PersistentVaultError(Exception):
    """Erreur de base pour le vault persistant"""
    pass


class VaultDecryptionError(PersistentVaultError):
    """Erreur de déchiffrement"""
    pass


class VaultIntegrityError(PersistentVaultError):
    """Erreur d'intégrité des données"""
    pass


class AssetNotFoundError(PersistentVaultError):
    """Actif non trouvé"""
    pass


class TransferError(PersistentVaultError):
    """Erreur de transfer"""
    pass


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class VaultAsset:
    """Représentation d'un actif dans le vault"""
    id: str
    name: str
    asset_type: str
    contract: str = ""
    token_id: str = ""
    chain: str = "Ethereum"
    status: str = "active"
    added: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.added:
            self.added = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VaultAsset':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class VaultDocument:
    """Représentation d'un document dans le vault"""
    id: str
    name: str
    path: str
    hash: str
    size: int = 0
    mime_type: str = ""
    added: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.added:
            self.added = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VaultDocument':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class VaultToken:
    """Représentation d'un token dans le vault"""
    id: str
    symbol: str
    name: str
    contract: str
    balance: str
    decimals: int = 18
    chain: str = "Ethereum"
    added: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.added:
            self.added = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VaultToken':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class VaultTransfer:
    """Représentation d'un transfer programmé"""
    id: str
    transfer_type: str
    asset_id: str
    destination: str
    delay_days: int = 30
    status: str = "pending"
    created: str = ""
    expiry: str = ""
    executed: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.created:
            self.created = datetime.now().isoformat()
        if not self.expiry:
            self.expiry = (datetime.now() + timedelta(days=self.delay_days)).isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VaultTransfer':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ============================================================================
# GESTIONNAIRE DE VAULT PERSISTANT
# ============================================================================

class PersistentVaultManager:
    """Gestionnaire de vault persistant avec chiffrement"""
    
    VERSION = "1.0"
    KDF_ITERATIONS = 100000
    BACKUP_RETENTION_DAYS = 30
    
    def __init__(self, vault_key: bytes, vault_name: str, base_path: str = None):
        """
        Initialiser le gestionnaire de vault.
        
        Args:
            vault_key: Clé de chiffrement du vault (bytes)
            vault_name: Nom du vault
            base_path: Chemin de base (par défaut: vault_storage/persistent)
        """
        if isinstance(vault_key, str):
            vault_key = vault_key.encode()
        
        self.vault_key = vault_key
        self.vault_name = vault_name
        
        # Chemins
        if base_path:
            self.base_path = Path(base_path)
        else:
            self.base_path = Path(__file__).parent.parent / "vault_storage" / "persistent"
        
        self.vault_dir = self.base_path / vault_name
        self.state_file = self.vault_dir / "vault_state.enc"
        
        # Cache de l'état
        self._state_cache: Optional[Dict] = None
        self._cache_timestamp: Optional[datetime] = None
        
        # Initialiser le vault
        self._init_vault()
    
    def _init_vault(self):
        """Initialiser la structure du vault persistant"""
        # Créer les répertoires
        directories = [
            self.vault_dir,
            self.vault_dir / "assets",
            self.vault_dir / "documents",
            self.vault_dir / "tokens",
            self.vault_dir / "backups",
            self.vault_dir / "logs"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Créer fichier d'état si inexistant
        if not self.state_file.exists():
            initial_state = {
                'version': self.VERSION,
                'vault_name': self.vault_name,
                'created': datetime.now().isoformat(),
                'last_modified': datetime.now().isoformat(),
                'assets': [],
                'documents': [],
                'tokens': [],
                'transfers': [],
                'activity_log': []
            }
            self._save_state(initial_state)
    
    def _derive_key(self) -> bytes:
        """Dériver une clé de chiffrement Fernet à partir de la clé du vault"""
        salt = hashlib.sha256(self.vault_name.encode()).digest()[:16]
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.KDF_ITERATIONS,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.vault_key))
        return key
    
    def _encrypt_data(self, data: Union[Dict, str, bytes]) -> bytes:
        """Chiffrer les données avec Fernet"""
        key = self._derive_key()
        fernet = Fernet(key)
        
        if isinstance(data, dict):
            data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        elif isinstance(data, str):
            data = data.encode('utf-8')
        
        return fernet.encrypt(data)
    
    def _decrypt_data(self, encrypted_data: bytes, as_json: bool = True) -> Union[Dict, str, bytes]:
        """Déchiffrer les données"""
        try:
            key = self._derive_key()
            fernet = Fernet(key)
            decrypted = fernet.decrypt(encrypted_data)
            
            if as_json:
                try:
                    return json.loads(decrypted.decode('utf-8'))
                except json.JSONDecodeError:
                    return decrypted.decode('utf-8')
            return decrypted
        except InvalidToken:
            raise VaultDecryptionError("Impossible de déchiffrer les données - clé invalide")
    
    def _save_state(self, state_data: Dict, create_backup: bool = True):
        """Sauvegarder l'état du vault"""
        state_data['last_modified'] = datetime.now().isoformat()
        encrypted = self._encrypt_data(state_data)
        
        # Sauvegarder l'état principal
        with open(self.state_file, 'wb') as f:
            f.write(encrypted)
        
        # Mettre à jour le cache
        self._state_cache = state_data
        self._cache_timestamp = datetime.now()
        
        # Créer un backup horodaté
        if create_backup:
            backup_file = self.vault_dir / "backups" / f"state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.enc"
            with open(backup_file, 'wb') as f:
                f.write(encrypted)
            
            # Nettoyer les anciens backups
            self._cleanup_old_backups()
    
    def _cleanup_old_backups(self):
        """Supprimer les backups plus anciens que BACKUP_RETENTION_DAYS"""
        backup_dir = self.vault_dir / "backups"
        cutoff = datetime.now() - timedelta(days=self.BACKUP_RETENTION_DAYS)
        
        for backup_file in backup_dir.glob("state_*.enc"):
            try:
                # Extraire la date du nom de fichier
                date_str = backup_file.stem.replace("state_", "")
                file_date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
                
                if file_date < cutoff:
                    backup_file.unlink()
            except (ValueError, OSError):
                pass
    
    def load_state(self, use_cache: bool = True) -> Dict:
        """Charger l'état du vault"""
        # Utiliser le cache si valide (moins de 5 secondes)
        if use_cache and self._state_cache and self._cache_timestamp:
            if (datetime.now() - self._cache_timestamp).seconds < 5:
                return self._state_cache
        
        if self.state_file.exists():
            with open(self.state_file, 'rb') as f:
                encrypted = f.read()
            
            state = self._decrypt_data(encrypted)
            self._state_cache = state
            self._cache_timestamp = datetime.now()
            return state
        
        return None
    
    def _log_activity(self, action: str, details: str = ""):
        """Enregistrer une activité dans le journal"""
        state = self.load_state()
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'details': details
        }
        
        state['activity_log'].append(log_entry)
        
        # Garder seulement les 1000 dernières entrées
        if len(state['activity_log']) > 1000:
            state['activity_log'] = state['activity_log'][-1000:]
        
        self._save_state(state, create_backup=False)
        
        # Aussi écrire dans un fichier log
        log_file = self.vault_dir / "logs" / f"activity_{datetime.now().strftime('%Y%m')}.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{log_entry['timestamp']}] {action}: {details}\n")
    
    def _generate_id(self, data: Any) -> str:
        """Générer un ID unique basé sur les données"""
        content = f"{data}{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    # ========================================================================
    # GESTION DES ACTIFS
    # ========================================================================
    
    def add_asset(self, asset_data: Union[Dict, VaultAsset]) -> str:
        """
        Ajouter un actif au vault.
        
        Args:
            asset_data: Données de l'actif (dict ou VaultAsset)
        
        Returns:
            ID de l'actif créé
        """
        state = self.load_state()
        
        if isinstance(asset_data, VaultAsset):
            asset_dict = asset_data.to_dict()
        else:
            asset_dict = dict(asset_data)
        
        # Générer un ID si absent
        if 'id' not in asset_dict or not asset_dict['id']:
            asset_dict['id'] = self._generate_id(asset_dict)
        
        asset_dict['added'] = datetime.now().isoformat()
        asset_dict['status'] = asset_dict.get('status', 'active')
        
        state['assets'].append(asset_dict)
        self._save_state(state)
        self._log_activity("ADD_ASSET", f"Asset {asset_dict['id']} added: {asset_dict.get('name', 'N/A')}")
        
        return asset_dict['id']
    
    def get_asset(self, asset_id: str) -> Optional[Dict]:
        """Récupérer un actif par son ID"""
        state = self.load_state()
        for asset in state.get('assets', []):
            if asset.get('id') == asset_id:
                return asset
        return None
    
    def update_asset(self, asset_id: str, updates: Dict) -> bool:
        """Mettre à jour un actif"""
        state = self.load_state()
        
        for asset in state['assets']:
            if asset.get('id') == asset_id:
                asset.update(updates)
                asset['modified'] = datetime.now().isoformat()
                self._save_state(state)
                self._log_activity("UPDATE_ASSET", f"Asset {asset_id} updated")
                return True
        
        return False
    
    def remove_asset(self, asset_id: str) -> bool:
        """Supprimer un actif du vault"""
        state = self.load_state()
        
        original_count = len(state['assets'])
        state['assets'] = [a for a in state['assets'] if a.get('id') != asset_id]
        
        if len(state['assets']) < original_count:
            self._save_state(state)
            self._log_activity("REMOVE_ASSET", f"Asset {asset_id} removed")
            return True
        
        return False
    
    def list_assets(self, status: str = None, asset_type: str = None) -> List[Dict]:
        """Lister les actifs avec filtres optionnels"""
        state = self.load_state()
        assets = state.get('assets', [])
        
        if status:
            assets = [a for a in assets if a.get('status') == status]
        
        if asset_type:
            assets = [a for a in assets if a.get('asset_type') == asset_type]
        
        return assets
    
    # ========================================================================
    # GESTION DES DOCUMENTS
    # ========================================================================
    
    def add_document(self, file_path: str, metadata: Dict = None) -> str:
        """
        Ajouter un document au vault.
        
        Args:
            file_path: Chemin du fichier à ajouter
            metadata: Métadonnées optionnelles
        
        Returns:
            ID du document créé
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier non trouvé: {file_path}")
        
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Chiffrer le document
        encrypted_doc = self._encrypt_data(file_data)
        
        doc_name = os.path.basename(file_path)
        doc_hash = hashlib.sha256(file_data).hexdigest()
        doc_id = doc_hash[:16]
        
        # Déterminer le type MIME
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Sauvegarder le document chiffré
        doc_file = self.vault_dir / "documents" / f"{doc_id}.enc"
        with open(doc_file, 'wb') as f:
            f.write(encrypted_doc)
        
        # Mettre à jour l'état
        state = self.load_state()
        
        doc_entry = {
            'id': doc_id,
            'name': doc_name,
            'path': str(doc_file),
            'hash': doc_hash,
            'size': len(file_data),
            'mime_type': mime_type or 'application/octet-stream',
            'added': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        state['documents'].append(doc_entry)
        self._save_state(state)
        self._log_activity("ADD_DOCUMENT", f"Document {doc_name} added (ID: {doc_id})")
        
        return doc_id
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Récupérer les métadonnées d'un document"""
        state = self.load_state()
        for doc in state.get('documents', []):
            if doc.get('id') == doc_id:
                return doc
        return None
    
    def extract_document(self, doc_id: str, output_path: str) -> bool:
        """
        Extraire un document du vault.
        
        Args:
            doc_id: ID du document
            output_path: Chemin de sortie
        
        Returns:
            True si succès
        """
        doc_info = self.get_document(doc_id)
        if not doc_info:
            raise AssetNotFoundError(f"Document {doc_id} non trouvé")
        
        doc_file = Path(doc_info['path'])
        if not doc_file.exists():
            raise FileNotFoundError(f"Fichier chiffré non trouvé: {doc_file}")
        
        with open(doc_file, 'rb') as f:
            encrypted = f.read()
        
        decrypted = self._decrypt_data(encrypted, as_json=False)
        
        with open(output_path, 'wb') as f:
            f.write(decrypted)
        
        self._log_activity("EXTRACT_DOCUMENT", f"Document {doc_id} extracted to {output_path}")
        return True
    
    def verify_document(self, doc_id: str) -> bool:
        """Vérifier l'intégrité d'un document"""
        doc_info = self.get_document(doc_id)
        if not doc_info:
            return False
        
        doc_file = Path(doc_info['path'])
        if not doc_file.exists():
            return False
        
        try:
            with open(doc_file, 'rb') as f:
                encrypted = f.read()
            
            decrypted = self._decrypt_data(encrypted, as_json=False)
            current_hash = hashlib.sha256(decrypted).hexdigest()
            
            is_valid = current_hash == doc_info['hash']
            self._log_activity("VERIFY_DOCUMENT", f"Document {doc_id} verification: {'OK' if is_valid else 'FAILED'}")
            
            return is_valid
        except Exception:
            return False
    
    def remove_document(self, doc_id: str) -> bool:
        """Supprimer un document du vault"""
        doc_info = self.get_document(doc_id)
        if not doc_info:
            return False
        
        # Supprimer le fichier chiffré
        doc_file = Path(doc_info['path'])
        if doc_file.exists():
            doc_file.unlink()
        
        # Mettre à jour l'état
        state = self.load_state()
        state['documents'] = [d for d in state['documents'] if d.get('id') != doc_id]
        self._save_state(state)
        
        self._log_activity("REMOVE_DOCUMENT", f"Document {doc_id} removed")
        return True
    
    def list_documents(self) -> List[Dict]:
        """Lister tous les documents"""
        state = self.load_state()
        return state.get('documents', [])
    
    # ========================================================================
    # GESTION DES TOKENS
    # ========================================================================
    
    def add_token(self, token_data: Union[Dict, VaultToken]) -> str:
        """Ajouter un token au vault"""
        state = self.load_state()
        
        if isinstance(token_data, VaultToken):
            token_dict = token_data.to_dict()
        else:
            token_dict = dict(token_data)
        
        if 'id' not in token_dict or not token_dict['id']:
            token_dict['id'] = self._generate_id(token_dict)
        
        token_dict['added'] = datetime.now().isoformat()
        
        state['tokens'].append(token_dict)
        self._save_state(state)
        self._log_activity("ADD_TOKEN", f"Token {token_dict.get('symbol', 'N/A')} added")
        
        return token_dict['id']
    
    def update_token_balance(self, token_id: str, new_balance: str) -> bool:
        """Mettre à jour la balance d'un token"""
        state = self.load_state()
        
        for token in state['tokens']:
            if token.get('id') == token_id:
                token['balance'] = new_balance
                token['modified'] = datetime.now().isoformat()
                self._save_state(state)
                self._log_activity("UPDATE_TOKEN", f"Token {token_id} balance updated to {new_balance}")
                return True
        
        return False
    
    def list_tokens(self) -> List[Dict]:
        """Lister tous les tokens"""
        state = self.load_state()
        return state.get('tokens', [])
    
    # ========================================================================
    # GESTION DES TRANSFERS
    # ========================================================================
    
    def schedule_transfer(self, transfer_data: Union[Dict, VaultTransfer]) -> str:
        """
        Programmer un transfer avec délai.
        
        Args:
            transfer_data: Données du transfer
        
        Returns:
            ID du transfer créé
        """
        state = self.load_state()
        
        if isinstance(transfer_data, VaultTransfer):
            transfer_dict = transfer_data.to_dict()
        else:
            transfer_dict = dict(transfer_data)
        
        transfer_id = self._generate_id(transfer_dict)
        
        transfer_dict['id'] = transfer_id
        transfer_dict['created'] = datetime.now().isoformat()
        transfer_dict['status'] = 'pending'
        
        # Calculer la date d'expiration
        delay_days = transfer_dict.get('delay_days', 30)
        transfer_dict['expiry'] = (
            datetime.now() + timedelta(days=delay_days)
        ).isoformat()
        
        state['transfers'].append(transfer_dict)
        self._save_state(state)
        self._log_activity("SCHEDULE_TRANSFER", f"Transfer {transfer_id} scheduled for {transfer_dict['expiry']}")
        
        return transfer_id
    
    def get_pending_transfers(self) -> List[Dict]:
        """Récupérer les transfers en attente"""
        state = self.load_state()
        pending = [
            t for t in state.get('transfers', [])
            if t['status'] == 'pending'
        ]
        return pending
    
    def get_executable_transfers(self) -> List[Dict]:
        """Récupérer les transfers arrivés à échéance"""
        now = datetime.now()
        pending = self.get_pending_transfers()
        
        executable = []
        for transfer in pending:
            try:
                expiry = datetime.fromisoformat(transfer['expiry'])
                if now >= expiry:
                    executable.append(transfer)
            except (KeyError, ValueError):
                pass
        
        return executable
    
    def execute_transfer(self, transfer_id: str) -> bool:
        """Exécuter un transfer"""
        state = self.load_state()
        
        for transfer in state['transfers']:
            if transfer['id'] == transfer_id and transfer['status'] == 'pending':
                transfer['status'] = 'completed'
                transfer['executed'] = datetime.now().isoformat()
                self._save_state(state)
                self._log_activity("EXECUTE_TRANSFER", f"Transfer {transfer_id} executed")
                return True
        
        return False
    
    def cancel_transfer(self, transfer_id: str) -> bool:
        """Annuler un transfer"""
        state = self.load_state()
        
        for transfer in state['transfers']:
            if transfer['id'] == transfer_id and transfer['status'] == 'pending':
                transfer['status'] = 'cancelled'
                transfer['cancelled_at'] = datetime.now().isoformat()
                self._save_state(state)
                self._log_activity("CANCEL_TRANSFER", f"Transfer {transfer_id} cancelled")
                return True
        
        return False
    
    def process_due_transfers(self) -> List[str]:
        """Traiter automatiquement les transfers arrivés à échéance"""
        executable = self.get_executable_transfers()
        executed_ids = []
        
        for transfer in executable:
            if self.execute_transfer(transfer['id']):
                executed_ids.append(transfer['id'])
        
        return executed_ids
    
    # ========================================================================
    # EXPORT / IMPORT
    # ========================================================================
    
    def export_vault(self, output_path: str) -> str:
        """
        Exporter tout le vault (pour backup).
        
        Args:
            output_path: Répertoire de destination
        
        Returns:
            Chemin du fichier zip créé
        """
        os.makedirs(output_path, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = os.path.join(output_path, f"{self.vault_name}_backup_{timestamp}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Ajouter l'état
            zipf.write(self.state_file, 'vault_state.enc')
            
            # Ajouter les documents
            docs_dir = self.vault_dir / "documents"
            for doc_file in docs_dir.glob("*.enc"):
                zipf.write(doc_file, f"documents/{doc_file.name}")
            
            # Ajouter les métadonnées non chiffrées
            metadata = {
                'vault_name': self.vault_name,
                'exported_at': datetime.now().isoformat(),
                'version': self.VERSION
            }
            zipf.writestr('metadata.json', json.dumps(metadata, indent=2))
        
        self._log_activity("EXPORT_VAULT", f"Vault exported to {zip_path}")
        return zip_path
    
    def import_vault(self, zip_path: str, overwrite: bool = False) -> bool:
        """
        Importer un vault depuis un backup.
        
        Args:
            zip_path: Chemin du fichier zip
            overwrite: Écraser les données existantes
        
        Returns:
            True si succès
        """
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"Fichier backup non trouvé: {zip_path}")
        
        if not overwrite and self.state_file.exists():
            raise PersistentVaultError("Vault existant. Utilisez overwrite=True pour écraser.")
        
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            # Extraire l'état
            zipf.extract('vault_state.enc', self.vault_dir)
            
            # Extraire les documents
            for name in zipf.namelist():
                if name.startswith('documents/'):
                    zipf.extract(name, self.vault_dir)
        
        # Invalider le cache
        self._state_cache = None
        self._cache_timestamp = None
        
        self._log_activity("IMPORT_VAULT", f"Vault imported from {zip_path}")
        return True
    
    # ========================================================================
    # UTILITAIRES
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtenir les statistiques du vault"""
        state = self.load_state()
        
        return {
            'vault_name': self.vault_name,
            'version': state.get('version', 'unknown'),
            'created': state.get('created'),
            'last_modified': state.get('last_modified'),
            'asset_count': len(state.get('assets', [])),
            'document_count': len(state.get('documents', [])),
            'token_count': len(state.get('tokens', [])),
            'pending_transfers': len(self.get_pending_transfers()),
            'activity_log_entries': len(state.get('activity_log', []))
        }
    
    def get_activity_log(self, limit: int = 100) -> List[Dict]:
        """Récupérer le journal d'activité"""
        state = self.load_state()
        log = state.get('activity_log', [])
        return log[-limit:] if limit else log
    
    def clear_activity_log(self):
        """Effacer le journal d'activité"""
        state = self.load_state()
        state['activity_log'] = []
        self._save_state(state)
        self._log_activity("CLEAR_LOG", "Activity log cleared")


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def create_vault(vault_name: str, vault_key: bytes = None) -> PersistentVaultManager:
    """
    Créer un nouveau vault.
    
    Args:
        vault_name: Nom du vault
        vault_key: Clé de chiffrement (générée si absente)
    
    Returns:
        Instance de PersistentVaultManager
    """
    if vault_key is None:
        import secrets
        vault_key = secrets.token_bytes(32)
    
    return PersistentVaultManager(vault_key, vault_name)


def open_vault(vault_name: str, vault_key: bytes, base_path: str = None) -> PersistentVaultManager:
    """
    Ouvrir un vault existant.
    
    Args:
        vault_name: Nom du vault
        vault_key: Clé de chiffrement
        base_path: Chemin de base optionnel
    
    Returns:
        Instance de PersistentVaultManager
    """
    return PersistentVaultManager(vault_key, vault_name, base_path)


# ============================================================================
# POINT D'ENTREE CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestionnaire de Vault Persistant")
    parser.add_argument("action", choices=["create", "stats", "export", "list-assets", "list-docs"])
    parser.add_argument("--vault", "-v", required=True, help="Nom du vault")
    parser.add_argument("--key", "-k", help="Clé du vault (hex)")
    parser.add_argument("--output", "-o", help="Chemin de sortie pour export")
    
    args = parser.parse_args()
    
    # Générer ou utiliser la clé
    if args.key:
        vault_key = bytes.fromhex(args.key)
    else:
        vault_key = hashlib.sha256(args.vault.encode()).digest()
    
    manager = PersistentVaultManager(vault_key, args.vault)
    
    if args.action == "create":
        print(f"Vault '{args.vault}' créé/initialisé")
        print(f"Clé (hex): {vault_key.hex()}")
    
    elif args.action == "stats":
        stats = manager.get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    elif args.action == "export":
        output = args.output or "."
        zip_path = manager.export_vault(output)
        print(f"Vault exporté vers: {zip_path}")
    
    elif args.action == "list-assets":
        assets = manager.list_assets()
        for asset in assets:
            print(f"- {asset.get('id')}: {asset.get('name', 'N/A')} ({asset.get('status', 'unknown')})")
    
    elif args.action == "list-docs":
        docs = manager.list_documents()
        for doc in docs:
            print(f"- {doc.get('id')}: {doc.get('name', 'N/A')} ({doc.get('size', 0)} bytes)")
