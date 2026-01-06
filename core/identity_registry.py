#!/usr/bin/env python3
"""
Poly-Spinor Nexus 7D - Registre d'Identité Décentralisé
========================================================

Système de gestion d'identité locale qui garantit l'unicité des noms
tout en maintenant une architecture 100% décentralisée.

Principes:
- Aucun serveur central
- Stockage local chiffré
- Fingerprint cryptographique pour unicité globale
- Vérification au moment de la création

Format d'identité: NOM_fingerprint
Exemple: MonVault_7a3f2b1c
"""

import os
import json
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass, asdict
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


@dataclass
class VaultIdentity:
    """Représente une identité de vault unique"""
    name: str                    # Nom choisi par l'utilisateur
    fingerprint: str             # Fingerprint cryptographique (8 chars)
    full_id: str                 # Identité complète: name_fingerprint
    key_hash: str                # Hash de la clé vault (pour vérification)
    created_at: str              # Date de création ISO
    psnx_path: Optional[str]     # Chemin du fichier .psnx
    blend_path: Optional[str]    # Chemin du fichier .blend_data
    metadata: Dict               # Métadonnées additionnelles


class IdentityRegistry:
    """
    Registre local d'identités de vault.
    
    Stocke les identités de manière chiffrée pour:
    - Vérifier l'unicité des noms localement
    - Associer noms <-> clés cryptographiques
    - Retrouver facilement ses vaults
    """
    
    REGISTRY_VERSION = 1
    REGISTRY_FILENAME = ".vault_identities.enc"
    
    def __init__(self, storage_dir: str = None):
        """
        Initialise le registre d'identités.
        
        Args:
            storage_dir: Répertoire de stockage (défaut: vault_storage)
        """
        if storage_dir is None:
            base_path = Path(__file__).parent.parent
            storage_dir = base_path / "vault_storage"
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.registry_path = self.storage_dir / self.REGISTRY_FILENAME
        self._registry_key = self._derive_registry_key()
        self._identities: Dict[str, VaultIdentity] = {}
        
        self._load_registry()
    
    def _derive_registry_key(self) -> bytes:
        """
        Dérive une clé de chiffrement pour le registre.
        Basée sur des informations machine pour rester local.
        """
        # Utiliser des informations stables de la machine
        machine_id = self._get_machine_identifier()
        
        salt = b"PSNX_IDENTITY_REGISTRY_v1"
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        return kdf.derive(machine_id.encode())
    
    def _get_machine_identifier(self) -> str:
        """Obtient un identifiant stable de la machine."""
        import platform
        
        components = [
            platform.node(),
            platform.machine(),
            platform.processor(),
            str(self.storage_dir.absolute()),
        ]
        
        return "|".join(components)
    
    def _encrypt_data(self, data: bytes) -> bytes:
        """Chiffre les données avec AES-GCM."""
        nonce = os.urandom(12)
        aesgcm = AESGCM(self._registry_key)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext
    
    def _decrypt_data(self, encrypted: bytes) -> bytes:
        """Déchiffre les données AES-GCM."""
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]
        aesgcm = AESGCM(self._registry_key)
        return aesgcm.decrypt(nonce, ciphertext, None)
    
    def _load_registry(self):
        """Charge le registre depuis le fichier chiffré."""
        if not self.registry_path.exists():
            self._identities = {}
            return
        
        try:
            with open(self.registry_path, 'rb') as f:
                encrypted = f.read()
            
            decrypted = self._decrypt_data(encrypted)
            data = json.loads(decrypted.decode('utf-8'))
            
            if data.get('version') != self.REGISTRY_VERSION:
                print(f"[WARN] Version du registre différente, migration possible")
            
            # Reconstruire les identités
            self._identities = {}
            for full_id, identity_data in data.get('identities', {}).items():
                self._identities[full_id] = VaultIdentity(**identity_data)
                
        except Exception as e:
            print(f"[WARN] Impossible de charger le registre: {e}")
            self._identities = {}
    
    def _save_registry(self):
        """Sauvegarde le registre de manière chiffrée."""
        data = {
            'version': self.REGISTRY_VERSION,
            'updated_at': datetime.utcnow().isoformat(),
            'identities': {
                full_id: asdict(identity) 
                for full_id, identity in self._identities.items()
            }
        }
        
        json_data = json.dumps(data, indent=2, ensure_ascii=False)
        encrypted = self._encrypt_data(json_data.encode('utf-8'))
        
        with open(self.registry_path, 'wb') as f:
            f.write(encrypted)
    
    @staticmethod
    def generate_fingerprint(vault_key: bytes, extra_entropy: bytes = None) -> str:
        """
        Génère un fingerprint cryptographique unique.
        
        Args:
            vault_key: Clé du vault
            extra_entropy: Entropie additionnelle optionnelle
        
        Returns:
            Fingerprint de 8 caractères hexadécimaux
        """
        data = vault_key
        if extra_entropy:
            data += extra_entropy
        
        # Double hash pour plus de sécurité
        h1 = hashlib.sha256(data).digest()
        h2 = hashlib.sha256(h1 + b"PSNX_FINGERPRINT").digest()
        
        return h2[:4].hex()  # 8 caractères
    
    def check_name_available(self, name: str) -> Tuple[bool, Optional[str]]:
        """
        Vérifie si un nom est disponible.
        
        Args:
            name: Nom à vérifier
        
        Returns:
            (disponible, message)
        """
        name_lower = name.lower().strip()
        
        # Validation du format
        if not name_lower:
            return False, "Le nom ne peut pas être vide"
        
        if len(name_lower) < 3:
            return False, "Le nom doit contenir au moins 3 caractères"
        
        if len(name_lower) > 32:
            return False, "Le nom ne peut pas dépasser 32 caractères"
        
        # Caractères autorisés
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-")
        if not all(c in allowed for c in name_lower.replace(' ', '_')):
            return False, "Le nom ne peut contenir que des lettres, chiffres, _ et -"
        
        # Vérifier unicité locale
        for identity in self._identities.values():
            if identity.name.lower() == name_lower:
                return False, f"Le nom '{name}' est déjà utilisé (ID: {identity.full_id})"
        
        return True, None
    
    def register_identity(
        self,
        name: str,
        vault_key: bytes,
        psnx_path: str = None,
        blend_path: str = None,
        metadata: Dict = None
    ) -> Tuple[bool, Optional[VaultIdentity], Optional[str]]:
        """
        Enregistre une nouvelle identité de vault.
        
        Args:
            name: Nom choisi par l'utilisateur
            vault_key: Clé du vault
            psnx_path: Chemin du fichier .psnx
            blend_path: Chemin du fichier .blend_data
            metadata: Métadonnées additionnelles
        
        Returns:
            (success, identity, error_message)
        """
        # Vérifier disponibilité
        available, error = self.check_name_available(name)
        if not available:
            return False, None, error
        
        # Générer le fingerprint
        fingerprint = self.generate_fingerprint(vault_key)
        
        # Créer l'identité complète
        safe_name = name.lower().replace(' ', '_')
        full_id = f"{safe_name}_{fingerprint}"
        
        # Vérifier que le full_id n'existe pas (collision quasi-impossible)
        if full_id in self._identities:
            # Régénérer avec entropie supplémentaire
            extra = secrets.token_bytes(16)
            fingerprint = self.generate_fingerprint(vault_key, extra)
            full_id = f"{safe_name}_{fingerprint}"
        
        # Hash de la clé pour vérification future
        key_hash = hashlib.sha256(vault_key).hexdigest()
        
        identity = VaultIdentity(
            name=name,
            fingerprint=fingerprint,
            full_id=full_id,
            key_hash=key_hash,
            created_at=datetime.utcnow().isoformat(),
            psnx_path=str(psnx_path) if psnx_path else None,
            blend_path=str(blend_path) if blend_path else None,
            metadata=metadata or {}
        )
        
        # Enregistrer
        self._identities[full_id] = identity
        self._save_registry()
        
        return True, identity, None
    
    def get_identity(self, full_id: str) -> Optional[VaultIdentity]:
        """Récupère une identité par son ID complet."""
        return self._identities.get(full_id)
    
    def get_identity_by_name(self, name: str) -> Optional[VaultIdentity]:
        """Récupère une identité par son nom."""
        name_lower = name.lower()
        for identity in self._identities.values():
            if identity.name.lower() == name_lower:
                return identity
        return None
    
    def verify_identity(self, full_id: str, vault_key: bytes) -> Tuple[bool, str]:
        """
        Vérifie qu'une clé correspond à une identité.
        
        Args:
            full_id: ID complet de l'identité
            vault_key: Clé à vérifier
        
        Returns:
            (valid, message)
        """
        identity = self.get_identity(full_id)
        if not identity:
            return False, f"Identité '{full_id}' non trouvée"
        
        key_hash = hashlib.sha256(vault_key).hexdigest()
        
        if key_hash == identity.key_hash:
            return True, "Identité vérifiée avec succès"
        else:
            return False, "La clé ne correspond pas à cette identité"
    
    def list_identities(self) -> List[VaultIdentity]:
        """Liste toutes les identités enregistrées."""
        return list(self._identities.values())
    
    def update_paths(
        self, 
        full_id: str, 
        psnx_path: str = None, 
        blend_path: str = None
    ) -> bool:
        """Met à jour les chemins des fichiers pour une identité."""
        identity = self.get_identity(full_id)
        if not identity:
            return False
        
        if psnx_path:
            identity.psnx_path = str(psnx_path)
        if blend_path:
            identity.blend_path = str(blend_path)
        
        self._save_registry()
        return True
    
    def delete_identity(self, full_id: str, vault_key: bytes) -> Tuple[bool, str]:
        """
        Supprime une identité (nécessite la clé pour confirmer).
        
        Args:
            full_id: ID de l'identité à supprimer
            vault_key: Clé pour confirmer la propriété
        
        Returns:
            (success, message)
        """
        valid, msg = self.verify_identity(full_id, vault_key)
        if not valid:
            return False, f"Impossible de supprimer: {msg}"
        
        del self._identities[full_id]
        self._save_registry()
        
        return True, f"Identité '{full_id}' supprimée"
    
    def export_identity_card(self, full_id: str) -> Optional[str]:
        """
        Exporte une carte d'identité lisible pour l'utilisateur.
        
        Returns:
            Texte formaté de la carte d'identité
        """
        identity = self.get_identity(full_id)
        if not identity:
            return None
        
        card = f"""
╔══════════════════════════════════════════════════════════════╗
║            POLY-SPINOR NEXUS 7D - IDENTITY CARD              ║
╠══════════════════════════════════════════════════════════════╣
║  NAME:        {identity.name:<46} ║
║  FINGERPRINT: {identity.fingerprint:<46} ║
║  FULL ID:     {identity.full_id:<46} ║
║  CREATED:     {identity.created_at[:19]:<46} ║
╠══════════════════════════════════════════════════════════════╣
║  KEY FILES:                                                  ║
║  PSNX:  {(identity.psnx_path or 'N/A')[:52]:<52} ║
║  BLEND: {(identity.blend_path or 'N/A')[:52]:<52} ║
╚══════════════════════════════════════════════════════════════╝
"""
        return card


def interactive_name_selection(registry: IdentityRegistry) -> str:
    """
    Interface interactive pour choisir un nom unique.
    
    Args:
        registry: Instance du registre d'identités
    
    Returns:
        Nom validé et disponible
    """
    print("\n" + "="*60)
    print("  SELECTION DU NOM DE VAULT")
    print("="*60)
    print("\n  Règles:")
    print("  - 3 à 32 caractères")
    print("  - Lettres, chiffres, _ et - uniquement")
    print("  - Le nom doit être unique sur cette machine")
    print()
    
    while True:
        name = input("  Nom du vault: ").strip()
        
        if not name:
            print("  [!] Veuillez entrer un nom\n")
            continue
        
        available, error = registry.check_name_available(name)
        
        if available:
            # Aperçu de l'identité
            preview_fp = secrets.token_hex(4)[:8]
            safe_name = name.lower().replace(' ', '_')
            print(f"\n  [OK] Nom disponible!")
            print(f"  [PREVIEW] Votre identité sera: {safe_name}_{preview_fp}")
            print(f"            (fingerprint final généré avec votre clé)")
            
            confirm = input("\n  Confirmer ce nom? [O/n]: ").strip().lower()
            if confirm in ('', 'o', 'oui', 'y', 'yes'):
                return name
            else:
                print("  Choisissez un autre nom.\n")
        else:
            print(f"  [X] {error}\n")


# Point d'entrée pour tests
if __name__ == "__main__":
    print("Test du registre d'identités...")
    
    registry = IdentityRegistry()
    
    # Lister les identités existantes
    identities = registry.list_identities()
    print(f"\nIdentités enregistrées: {len(identities)}")
    
    for identity in identities:
        print(f"  - {identity.full_id} (créé: {identity.created_at[:10]})")
    
    # Test interactif
    if input("\nTester la création? [o/N]: ").lower() == 'o':
        name = interactive_name_selection(registry)
        test_key = secrets.token_bytes(32)
        
        success, identity, error = registry.register_identity(
            name=name,
            vault_key=test_key,
            metadata={"test": True}
        )
        
        if success:
            print(registry.export_identity_card(identity.full_id))
        else:
            print(f"Erreur: {error}")
