#!/usr/bin/env python3
"""
Poly-Spinor Nexus 7D - Machine Lock System
==========================================

Systeme de verrouillage par machine pour garantir UN SEUL VAULT par ordinateur.
Empeche la creation de plusieurs vaults pour beneficier des tirages plusieurs fois.

Methodes d'identification:
1. Hardware ID (CPU, carte mere, disque)
2. MAC Address
3. Machine Name + User
4. Volume Serial Number (Windows)
5. DMI/BIOS info (Linux)

Le systeme cree un fichier de verrouillage chiffre qui lie la machine au vault.
"""

import os
import sys
import json
import hashlib
import platform
import uuid
import socket
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict

# Cryptographie
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


class MachineIdentifier:
    """Generateur d'identifiant machine unique et persistant."""
    
    @staticmethod
    def get_hardware_id() -> str:
        """Obtient un ID hardware unique."""
        components = []
        
        # 1. Platform info
        components.append(platform.node())
        components.append(platform.machine())
        components.append(platform.processor())
        
        # 2. UUID de la machine (basé sur l'adresse MAC)
        try:
            machine_uuid = str(uuid.getnode())
            components.append(machine_uuid)
        except:
            pass
        
        # 3. Hostname
        try:
            components.append(socket.gethostname())
        except:
            pass
        
        # 4. Windows: Volume Serial Number
        if sys.platform == 'win32':
            try:
                import subprocess
                result = subprocess.run(
                    ['wmic', 'diskdrive', 'get', 'serialnumber'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    lines = [l.strip() for l in result.stdout.split('\n') if l.strip() and l.strip() != 'SerialNumber']
                    if lines:
                        components.append(lines[0])
            except:
                pass
            
            # Volume serial
            try:
                import subprocess
                result = subprocess.run(
                    ['vol', 'C:'],
                    capture_output=True, text=True, shell=True, timeout=5
                )
                if result.returncode == 0 and 'Volume Serial' in result.stdout:
                    for line in result.stdout.split('\n'):
                        if 'Serial' in line:
                            serial = line.split()[-1]
                            components.append(serial)
                            break
            except:
                pass
            
            # BIOS Serial
            try:
                import subprocess
                result = subprocess.run(
                    ['wmic', 'bios', 'get', 'serialnumber'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    lines = [l.strip() for l in result.stdout.split('\n') if l.strip() and l.strip() != 'SerialNumber']
                    if lines and lines[0] != 'To be filled by O.E.M.':
                        components.append(lines[0])
            except:
                pass
        
        # 5. Linux: DMI info
        elif sys.platform.startswith('linux'):
            dmi_paths = [
                '/sys/class/dmi/id/product_uuid',
                '/sys/class/dmi/id/board_serial',
                '/sys/class/dmi/id/chassis_serial',
                '/etc/machine-id',
            ]
            for path in dmi_paths:
                try:
                    with open(path, 'r') as f:
                        content = f.read().strip()
                        if content:
                            components.append(content)
                except:
                    pass
        
        # 6. macOS: Hardware UUID
        elif sys.platform == 'darwin':
            try:
                import subprocess
                result = subprocess.run(
                    ['system_profiler', 'SPHardwareDataType'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'Hardware UUID' in line:
                            hw_uuid = line.split(':')[-1].strip()
                            components.append(hw_uuid)
                            break
            except:
                pass
        
        # Combiner et hasher
        combined = "|".join(filter(None, components))
        return combined
    
    @staticmethod
    def generate_machine_hash() -> str:
        """Genere un hash unique pour cette machine."""
        hardware_id = MachineIdentifier.get_hardware_id()
        
        # Double hash avec salt
        salt = b"PSNX_MACHINE_LOCK_V1"
        h1 = hashlib.sha256(hardware_id.encode() + salt).digest()
        h2 = hashlib.sha256(h1 + b"UNIQUE_MACHINE").digest()
        
        return h2.hex()
    
    @staticmethod
    def get_short_id() -> str:
        """Retourne un ID court (16 chars) pour affichage."""
        full_hash = MachineIdentifier.generate_machine_hash()
        return full_hash[:16]


class MachineLock:
    """
    Systeme de verrouillage par machine.
    
    Garantit qu'une seule entite (vault) peut etre creee par machine physique.
    """
    
    LOCK_FILENAME = ".machine_lock.enc"
    LOCK_VERSION = 1
    
    def __init__(self, storage_dir: str = None):
        """
        Initialise le systeme de verrouillage.
        
        Args:
            storage_dir: Repertoire de stockage (defaut: vault_storage)
        """
        if storage_dir is None:
            base_path = Path(__file__).parent.parent
            storage_dir = base_path / "vault_storage"
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.lock_path = self.storage_dir / self.LOCK_FILENAME
        self.machine_hash = MachineIdentifier.generate_machine_hash()
        self._encryption_key = self._derive_key()
    
    def _derive_key(self) -> bytes:
        """Derive une cle de chiffrement basee sur la machine."""
        salt = b"PSNX_MACHINE_LOCK_KEY"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(self.machine_hash[:32].encode())
    
    def _encrypt(self, data: bytes) -> bytes:
        """Chiffre les donnees."""
        nonce = os.urandom(12)
        aesgcm = AESGCM(self._encryption_key)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext
    
    def _decrypt(self, encrypted: bytes) -> bytes:
        """Dechiffre les donnees."""
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]
        aesgcm = AESGCM(self._encryption_key)
        return aesgcm.decrypt(nonce, ciphertext, None)
    
    def is_machine_locked(self) -> Tuple[bool, Optional[Dict]]:
        """
        Verifie si cette machine a deja un vault enregistre.
        
        Returns:
            (is_locked, lock_info or None)
        """
        if not self.lock_path.exists():
            return False, None
        
        try:
            with open(self.lock_path, 'rb') as f:
                encrypted = f.read()
            
            decrypted = self._decrypt(encrypted)
            lock_data = json.loads(decrypted.decode('utf-8'))
            
            # Verifier que le hash machine correspond
            if lock_data.get('machine_hash') == self.machine_hash:
                return True, lock_data
            else:
                # Le fichier existe mais pour une autre machine (copie)
                return False, None
                
        except Exception as e:
            # Fichier corrompu ou invalide
            return False, None
    
    def can_create_vault(self) -> Tuple[bool, str]:
        """
        Verifie si un nouveau vault peut etre cree sur cette machine.
        
        Returns:
            (can_create, message)
        """
        is_locked, lock_info = self.is_machine_locked()
        
        if is_locked:
            vault_name = lock_info.get('vault_name', 'Unknown')
            created_at = lock_info.get('created_at', 'Unknown')
            vault_num = lock_info.get('vault_number', '?')
            
            return False, (
                f"Cette machine a deja un vault enregistre!\n"
                f"\n"
                f"  Vault existant: {vault_name}\n"
                f"  Numero: #{vault_num}\n"
                f"  Cree le: {created_at[:19]}\n"
                f"  Machine ID: {self.machine_hash[:16]}...\n"
                f"\n"
                f"Un seul vault est autorise par machine pour garantir\n"
                f"l'equite des tirages d'items et rewards.\n"
                f"\n"
                f"Si vous pensez qu'il s'agit d'une erreur, contactez le support."
            )
        
        return True, "OK"
    
    def register_vault(self, vault_name: str, vault_number: int, 
                       vault_key_hash: str, psnx_path: str = None) -> Tuple[bool, str]:
        """
        Enregistre un vault pour cette machine (verrouillage).
        
        Args:
            vault_name: Nom du vault
            vault_number: Numero d'inscription
            vault_key_hash: Hash de la cle vault
            psnx_path: Chemin du fichier .psnx
        
        Returns:
            (success, message)
        """
        # Verifier d'abord si deja verrouille
        can_create, error_msg = self.can_create_vault()
        if not can_create:
            return False, error_msg
        
        # Creer le lock
        lock_data = {
            'version': self.LOCK_VERSION,
            'machine_hash': self.machine_hash,
            'machine_short_id': MachineIdentifier.get_short_id(),
            'vault_name': vault_name,
            'vault_number': vault_number,
            'vault_key_hash': vault_key_hash,
            'psnx_path': str(psnx_path) if psnx_path else None,
            'created_at': datetime.utcnow().isoformat(),
            'platform': {
                'system': platform.system(),
                'node': platform.node(),
                'machine': platform.machine(),
            }
        }
        
        # Chiffrer et sauvegarder
        json_data = json.dumps(lock_data, indent=2)
        encrypted = self._encrypt(json_data.encode('utf-8'))
        
        with open(self.lock_path, 'wb') as f:
            f.write(encrypted)
        
        return True, (
            f"Machine verrouillée avec succès!\n"
            f"  Vault: {vault_name}\n"
            f"  Numero: #{vault_number}\n"
            f"  Machine ID: {self.machine_hash[:16]}..."
        )
    
    def get_registered_vault(self) -> Optional[Dict]:
        """
        Retourne les informations du vault enregistre sur cette machine.
        
        Returns:
            Lock info dict or None
        """
        is_locked, lock_info = self.is_machine_locked()
        return lock_info if is_locked else None
    
    def verify_vault_ownership(self, vault_key_hash: str) -> bool:
        """
        Verifie qu'un vault appartient bien a cette machine.
        
        Args:
            vault_key_hash: Hash de la cle vault a verifier
        
        Returns:
            True si le vault appartient a cette machine
        """
        lock_info = self.get_registered_vault()
        if not lock_info:
            return False
        
        return lock_info.get('vault_key_hash') == vault_key_hash


def check_machine_can_create_vault() -> Tuple[bool, str]:
    """
    Fonction utilitaire pour verifier rapidement si un vault peut etre cree.
    
    Returns:
        (can_create, message)
    """
    lock = MachineLock()
    return lock.can_create_vault()


def get_machine_info() -> Dict:
    """
    Retourne les informations de la machine actuelle.
    
    Returns:
        Dict avec les infos machine
    """
    return {
        'machine_hash': MachineIdentifier.generate_machine_hash(),
        'short_id': MachineIdentifier.get_short_id(),
        'hardware_id': MachineIdentifier.get_hardware_id(),
        'platform': platform.system(),
        'node': platform.node(),
    }


# Test direct
if __name__ == "__main__":
    print("=" * 60)
    print("  MACHINE LOCK SYSTEM - Diagnostic")
    print("=" * 60)
    
    # Afficher les infos machine
    info = get_machine_info()
    print(f"\n  Machine Hash: {info['machine_hash'][:32]}...")
    print(f"  Short ID: {info['short_id']}")
    print(f"  Platform: {info['platform']}")
    print(f"  Node: {info['node']}")
    
    # Verifier le statut
    lock = MachineLock()
    can_create, message = lock.can_create_vault()
    
    print(f"\n  Peut creer un vault: {'OUI' if can_create else 'NON'}")
    
    if not can_create:
        print(f"\n{message}")
    else:
        print("\n  Cette machine n'a pas encore de vault enregistre.")
    
    # Afficher le vault existant si present
    existing = lock.get_registered_vault()
    if existing:
        print(f"\n  [VAULT EXISTANT]")
        print(f"  Nom: {existing.get('vault_name')}")
        print(f"  Numero: #{existing.get('vault_number')}")
        print(f"  Cree le: {existing.get('created_at', '')[:19]}")
