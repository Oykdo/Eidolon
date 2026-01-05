"""
Backup System Module for Quantum Cryptographic System

This module provides secure backup and recovery capabilities for quantum keys,
escrowed documents, and system state, including encryption, distributed storage,
and integrity verification.
"""

import numpy as np
import hashlib
import os
import json
from typing import Dict, List, Tuple, Optional, Union, Any
from datetime import datetime
from ..core.spinor_crypto import SpinorCryptographicEngine

# ============================================================================
# Encryption Utilities
# ============================================================================

class BackupEncryption:
    """
    Encryption utilities for secure backups.
    """

    def __init__(self):
        self.crypto_engine = SpinorCryptographicEngine()

    def encrypt_data(self, data: bytes, key: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Encrypt data for backup.

        :param data: Data to encrypt
        :param key: Optional encryption key
        :return: Tuple of (encrypted_data, key)
        """
        if key is None:
            key = os.urandom(32)  # Generate random key

        encrypted_data, _ = self.crypto_engine.encrypt(data, key)
        return encrypted_data, key

    def decrypt_data(self, encrypted_data: bytes, key: bytes) -> bytes:
        """
        Decrypt backup data.

        :param encrypted_data: Encrypted data
        :param key: Decryption key
        :return: Decrypted data
        """
        return self.crypto_engine.decrypt(encrypted_data, key, key)

# ============================================================================
# Integrity Verification
# ============================================================================

class IntegrityVerifier:
    """
    Integrity verification using cryptographic hashes.
    """

    @staticmethod
    def compute_hash(data: bytes) -> str:
        """
        Compute SHA256 hash of data.

        :param data: Data to hash
        :return: Hex string hash
        """
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def verify_integrity(data: bytes, expected_hash: str) -> bool:
        """
        Verify data integrity against expected hash.

        :param data: Data to verify
        :param expected_hash: Expected hash
        :return: True if matches
        """
        return IntegrityVerifier.compute_hash(data) == expected_hash

# ============================================================================
# Distributed Storage
# ============================================================================

class DistributedStorage:
    """
    Simulated distributed storage across multiple locations.
    """

    def __init__(self, num_locations: int = 3):
        self.num_locations = num_locations
        self.storage_locations = [{} for _ in range(num_locations)]  # In-memory simulation

    def store_fragment(self, backup_id: str, fragment_id: int, data: bytes) -> bool:
        """
        Store a data fragment in a specific location.

        :param backup_id: Unique backup identifier
        :param fragment_id: Fragment index
        :param data: Fragment data
        :return: Success status
        """
        if fragment_id < self.num_locations:
            self.storage_locations[fragment_id][backup_id] = data
            return True
        return False

    def retrieve_fragment(self, backup_id: str, fragment_id: int) -> Optional[bytes]:
        """
        Retrieve a data fragment from storage.

        :param backup_id: Backup identifier
        :param fragment_id: Fragment index
        :return: Fragment data or None
        """
        if fragment_id < self.num_locations:
            return self.storage_locations[fragment_id].get(backup_id)
        return None

    def store_backup(self, backup_id: str, data: bytes) -> bool:
        """
        Store backup data across distributed locations.

        :param backup_id: Backup identifier
        :param data: Backup data
        :return: Success status
        """
        # Split data into fragments (simple split for simulation)
        fragment_size = len(data) // self.num_locations + 1
        fragments = [data[i:i + fragment_size] for i in range(0, len(data), fragment_size)]

        success = True
        for i, fragment in enumerate(fragments):
            if i < self.num_locations:
                success &= self.store_fragment(backup_id, i, fragment)

        return success

    def retrieve_backup(self, backup_id: str) -> Optional[bytes]:
        """
        Retrieve and reconstruct backup data from distributed locations.

        :param backup_id: Backup identifier
        :return: Reconstructed data or None
        """
        fragments = []
        for i in range(self.num_locations):
            fragment = self.retrieve_fragment(backup_id, i)
            if fragment is None:
                return None
            fragments.append(fragment)

        return b''.join(fragments)

# ============================================================================
# Quantum Key Backup
# ============================================================================

class QuantumKeyBackup:
    """
    Backup and recovery for quantum cryptographic keys.
    """

    def __init__(self):
        self.encryption = BackupEncryption()
        self.integrity = IntegrityVerifier()
        self.storage = DistributedStorage()

    def backup_key(self, key: bytes, key_id: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create secure backup of quantum key.

        :param key: Key bytes to backup
        :param key_id: Unique key identifier
        :param metadata: Optional metadata
        :return: Backup information
        """
        # Serialize metadata
        backup_metadata = {
            'key_id': key_id,
            'timestamp': datetime.now().isoformat(),
            'key_size': len(key),
            'type': 'quantum_key'
        }
        if metadata:
            backup_metadata.update(metadata)

        metadata_json = json.dumps(backup_metadata).encode('utf-8')

        # Combine key and metadata
        data_to_backup = key + b'|' + metadata_json

        # Encrypt
        encrypted_data, encryption_key = self.encryption.encrypt_data(data_to_backup)

        # Compute integrity hash
        integrity_hash = self.integrity.compute_hash(encrypted_data)

        # Store in distributed storage
        backup_id = f"key_{key_id}_{int(datetime.now().timestamp())}"
        success = self.storage.store_backup(backup_id, encrypted_data)

        if not success:
            raise RuntimeError("Failed to store backup in distributed storage")

        return {
            'backup_id': backup_id,
            'encryption_key': encryption_key.hex(),
            'integrity_hash': integrity_hash,
            'metadata': backup_metadata
        }

    def recover_key(self, backup_info: Dict[str, Any]) -> Tuple[bytes, Dict]:
        """
        Recover quantum key from backup.

        :param backup_info: Backup information from backup_key
        :return: Tuple of (key_bytes, metadata)
        """
        backup_id = backup_info['backup_id']
        encryption_key = bytes.fromhex(backup_info['encryption_key'])
        expected_hash = backup_info['integrity_hash']

        # Retrieve from storage
        encrypted_data = self.storage.retrieve_backup(backup_id)
        if encrypted_data is None:
            raise RuntimeError(f"Backup {backup_id} not found")

        # Verify integrity
        if not self.integrity.verify_integrity(encrypted_data, expected_hash):
            raise RuntimeError("Integrity verification failed")

        # Decrypt
        decrypted_data = self.encryption.decrypt_data(encrypted_data, encryption_key)

        # Parse key and metadata
        parts = decrypted_data.split(b'|', 1)
        if len(parts) != 2:
            raise RuntimeError("Invalid backup format")

        key = parts[0]
        metadata = json.loads(parts[1].decode('utf-8'))

        return key, metadata

# ============================================================================
# Document Backup
# ============================================================================

class DocumentBackup:
    """
    Backup and recovery for escrowed documents.
    """

    def __init__(self):
        self.encryption = BackupEncryption()
        self.integrity = IntegrityVerifier()
        self.storage = DistributedStorage()

    def backup_document(self, document: bytes, doc_id: str, escrow_info: Dict,
                       metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create secure backup of escrowed document.

        :param document: Document bytes
        :param doc_id: Document identifier
        :param escrow_info: Escrow information
        :param metadata: Optional metadata
        :return: Backup information
        """
        # Serialize metadata
        backup_metadata = {
            'doc_id': doc_id,
            'timestamp': datetime.now().isoformat(),
            'doc_size': len(document),
            'type': 'escrowed_document',
            'escrow_info': escrow_info
        }
        if metadata:
            backup_metadata.update(metadata)

        metadata_json = json.dumps(backup_metadata).encode('utf-8')

        # Combine document and metadata
        data_to_backup = document + b'|' + metadata_json

        # Encrypt
        encrypted_data, encryption_key = self.encryption.encrypt_data(data_to_backup)

        # Compute integrity hash
        integrity_hash = self.integrity.compute_hash(encrypted_data)

        # Store in distributed storage
        backup_id = f"doc_{doc_id}_{int(datetime.now().timestamp())}"
        success = self.storage.store_backup(backup_id, encrypted_data)

        if not success:
            raise RuntimeError("Failed to store backup in distributed storage")

        return {
            'backup_id': backup_id,
            'encryption_key': encryption_key.hex(),
            'integrity_hash': integrity_hash,
            'metadata': backup_metadata
        }

    def recover_document(self, backup_info: Dict[str, Any]) -> Tuple[bytes, Dict]:
        """
        Recover escrowed document from backup.

        :param backup_info: Backup information
        :return: Tuple of (document_bytes, metadata)
        """
        backup_id = backup_info['backup_id']
        encryption_key = bytes.fromhex(backup_info['encryption_key'])
        expected_hash = backup_info['integrity_hash']

        # Retrieve from storage
        encrypted_data = self.storage.retrieve_backup(backup_id)
        if encrypted_data is None:
            raise RuntimeError(f"Backup {backup_id} not found")

        # Verify integrity
        if not self.integrity.verify_integrity(encrypted_data, expected_hash):
            raise RuntimeError("Integrity verification failed")

        # Decrypt
        decrypted_data = self.encryption.decrypt_data(encrypted_data, encryption_key)

        # Parse document and metadata
        parts = decrypted_data.split(b'|', 1)
        if len(parts) != 2:
            raise RuntimeError("Invalid backup format")

        document = parts[0]
        metadata = json.loads(parts[1].decode('utf-8'))

        return document, metadata

# ============================================================================
# System State Backup
# ============================================================================

class SystemStateBackup:
    """
    Backup and recovery for system state.
    """

    def __init__(self):
        self.encryption = BackupEncryption()
        self.integrity = IntegrityVerifier()
        self.storage = DistributedStorage()

    def backup_system_state(self, state_data: Dict[str, Any], state_id: str,
                           metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create secure backup of system state.

        :param state_data: System state dictionary
        :param state_id: State identifier
        :param metadata: Optional metadata
        :return: Backup information
        """
        # Serialize state data
        state_json = json.dumps(state_data, default=str).encode('utf-8')

        # Serialize metadata
        backup_metadata = {
            'state_id': state_id,
            'timestamp': datetime.now().isoformat(),
            'state_size': len(state_json),
            'type': 'system_state'
        }
        if metadata:
            backup_metadata.update(metadata)

        metadata_json = json.dumps(backup_metadata).encode('utf-8')

        # Combine state and metadata
        data_to_backup = state_json + b'|' + metadata_json

        # Encrypt
        encrypted_data, encryption_key = self.encryption.encrypt_data(data_to_backup)

        # Compute integrity hash
        integrity_hash = self.integrity.compute_hash(encrypted_data)

        # Store in distributed storage
        backup_id = f"state_{state_id}_{int(datetime.now().timestamp())}"
        success = self.storage.store_backup(backup_id, encrypted_data)

        if not success:
            raise RuntimeError("Failed to store backup in distributed storage")

        return {
            'backup_id': backup_id,
            'encryption_key': encryption_key.hex(),
            'integrity_hash': integrity_hash,
            'metadata': backup_metadata
        }

    def recover_system_state(self, backup_info: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict]:
        """
        Recover system state from backup.

        :param backup_info: Backup information
        :return: Tuple of (state_data, metadata)
        """
        backup_id = backup_info['backup_id']
        encryption_key = bytes.fromhex(backup_info['encryption_key'])
        expected_hash = backup_info['integrity_hash']

        # Retrieve from storage
        encrypted_data = self.storage.retrieve_backup(backup_id)
        if encrypted_data is None:
            raise RuntimeError(f"Backup {backup_id} not found")

        # Verify integrity
        if not self.integrity.verify_integrity(encrypted_data, expected_hash):
            raise RuntimeError("Integrity verification failed")

        # Decrypt
        decrypted_data = self.encryption.decrypt_data(encrypted_data, encryption_key)

        # Parse state and metadata
        parts = decrypted_data.split(b'|', 1)
        if len(parts) != 2:
            raise RuntimeError("Invalid backup format")

        state_json = parts[0]
        metadata = json.loads(parts[1].decode('utf-8'))

        # Deserialize state data
        state_data = json.loads(state_json.decode('utf-8'))

        return state_data, metadata

# ============================================================================
# Main Backup System
# ============================================================================

class BackupSystem:
    """
    Main backup system orchestrating all backup operations.
    """

    def __init__(self):
        self.key_backup = QuantumKeyBackup()
        self.document_backup = DocumentBackup()
        self.system_backup = SystemStateBackup()
        self.backup_registry = {}  # Registry of all backups

    def backup_quantum_key(self, key: bytes, key_id: str, **kwargs) -> str:
        """
        Backup a quantum key.

        :param key: Key bytes
        :param key_id: Key identifier
        :return: Backup ID
        """
        backup_info = self.key_backup.backup_key(key, key_id, **kwargs)
        self.backup_registry[backup_info['backup_id']] = backup_info
        return backup_info['backup_id']

    def backup_document(self, document: bytes, doc_id: str, escrow_info: Dict, **kwargs) -> str:
        """
        Backup an escrowed document.

        :param document: Document bytes
        :param doc_id: Document ID
        :param escrow_info: Escrow information
        :return: Backup ID
        """
        backup_info = self.document_backup.backup_document(document, doc_id, escrow_info, **kwargs)
        self.backup_registry[backup_info['backup_id']] = backup_info
        return backup_info['backup_id']

    def backup_system_state(self, state_data: Dict[str, Any], state_id: str, **kwargs) -> str:
        """
        Backup system state.

        :param state_data: State data
        :param state_id: State ID
        :return: Backup ID
        """
        backup_info = self.system_backup.backup_system_state(state_data, state_id, **kwargs)
        self.backup_registry[backup_info['backup_id']] = backup_info
        return backup_info['backup_id']

    def recover_backup(self, backup_id: str) -> Tuple[Any, Dict]:
        """
        Recover data from backup.

        :param backup_id: Backup identifier
        :return: Tuple of (recovered_data, metadata)
        """
        if backup_id not in self.backup_registry:
            raise ValueError(f"Backup {backup_id} not found in registry")

        backup_info = self.backup_registry[backup_id]

        if backup_info['metadata']['type'] == 'quantum_key':
            return self.key_backup.recover_key(backup_info)
        elif backup_info['metadata']['type'] == 'escrowed_document':
            return self.document_backup.recover_document(backup_info)
        elif backup_info['metadata']['type'] == 'system_state':
            return self.system_backup.recover_system_state(backup_info)
        else:
            raise ValueError(f"Unknown backup type: {backup_info['metadata']['type']}")

    def list_backups(self, backup_type: Optional[str] = None) -> List[Dict]:
        """
        List all backups or backups of specific type.

        :param backup_type: Optional type filter
        :return: List of backup metadata
        """
        backups = []
        for backup_id, info in self.backup_registry.items():
            if backup_type is None or info['metadata']['type'] == backup_type:
                backups.append({
                    'backup_id': backup_id,
                    'type': info['metadata']['type'],
                    'timestamp': info['metadata']['timestamp'],
                    'size': info['metadata'].get('key_size') or info['metadata'].get('doc_size') or info['metadata'].get('state_size')
                })
        return backups

# ============================================================================
# Convenience Functions
# ============================================================================

def create_backup_system() -> BackupSystem:
    """Create a new backup system instance."""
    return BackupSystem()

def backup_quantum_key(key: bytes, key_id: str) -> str:
    """Convenience function to backup a quantum key."""
    system = BackupSystem()
    return system.backup_quantum_key(key, key_id)

def recover_quantum_key(backup_id: str) -> bytes:
    """Convenience function to recover a quantum key."""
    system = BackupSystem()
    data, _ = system.recover_backup(backup_id)
    return data