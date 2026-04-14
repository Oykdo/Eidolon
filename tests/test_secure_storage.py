"""Test du stockage sécurisé des clés - VULN-CRYPTO-06 FIX"""

import os
import sys
import secrets
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.identity.secure_key_storage import (
    SecureKeyStorage,
    VaultKeyStorage,
    MemoryProtectedKey,
    SecureKeyDerivation,
    KeyNotFoundError,
    KeyExpiredError,
    create_secure_vault_storage
)


def test_memory_protected_key():
    """Test de la protection mémoire des clés"""
    print("\n--- Test MemoryProtectedKey ---")
    
    original_key = secrets.token_bytes(32)
    protected = MemoryProtectedKey(original_key)
    
    # Récupérer la clé
    retrieved = protected.get_key()
    assert retrieved == original_key, "Clé récupérée incorrecte!"
    print(f"Clé originale: {original_key[:8].hex()}...")
    print(f"Clé récupérée: {retrieved[:8].hex()}...")
    
    # Test rotation du masque
    protected.rotate_mask()
    retrieved_after_rotation = protected.get_key()
    assert retrieved_after_rotation == original_key, "Rotation a corrompu la clé!"
    print("[OK] Rotation du masque préserve la clé")
    
    # Test effacement sécurisé
    protected.secure_delete()
    print("[OK] Effacement sécurisé exécuté")
    
    print("[OK] MemoryProtectedKey fonctionne")
    return True


def test_key_derivation():
    """Test de la dérivation de clés"""
    print("\n--- Test SecureKeyDerivation ---")
    
    password = "mon_mot_de_passe_test"
    salt = secrets.token_bytes(32)
    
    # Dérivation
    key1 = SecureKeyDerivation.derive_key_from_password(password, salt)
    key2 = SecureKeyDerivation.derive_key_from_password(password, salt)
    
    print(f"Clé dérivée 1: {key1[:8].hex()}...")
    print(f"Clé dérivée 2: {key2[:8].hex()}...")
    
    assert key1 == key2, "Dérivation non déterministe!"
    print("[OK] Dérivation déterministe")
    
    # Différent sel = différente clé
    salt2 = secrets.token_bytes(32)
    key3 = SecureKeyDerivation.derive_key_from_password(password, salt2)
    assert key1 != key3, "Sels différents devraient produire clés différentes!"
    print("[OK] Sels différents produisent clés différentes")
    
    # Sous-clé
    subkey = SecureKeyDerivation.derive_subkey(key1, "encryption")
    print(f"Sous-clé: {subkey[:8].hex()}...")
    assert len(subkey) == 32, "Sous-clé devrait être 32 bytes!"
    
    print("[OK] SecureKeyDerivation fonctionne")
    return True


def test_secure_key_storage_memory():
    """Test du stockage en mémoire uniquement"""
    print("\n--- Test SecureKeyStorage (mémoire) ---")
    
    storage = SecureKeyStorage()
    
    # Stocker une clé
    key_data = secrets.token_bytes(32)
    metadata = storage.store_key(
        key_id="test_key_1",
        key_data=key_data,
        purpose="testing"
    )
    
    print(f"Clé stockée: {metadata.key_id}")
    print(f"Créée: {metadata.created_at}")
    print(f"Taille: {metadata.key_size_bits} bits")
    
    # Récupérer
    retrieved = storage.retrieve_key("test_key_1")
    assert retrieved == key_data, "Clé récupérée incorrecte!"
    print("[OK] Clé récupérée correctement")
    
    # Vérifier métadonnées
    meta = storage.get_metadata("test_key_1")
    assert meta.access_count == 1, "Compteur d'accès incorrect!"
    print(f"[OK] Compteur d'accès: {meta.access_count}")
    
    # Liste des clés
    keys = storage.list_keys()
    assert len(keys) == 1, "Liste des clés incorrecte!"
    print(f"[OK] Liste: {len(keys)} clé(s)")
    
    # Supprimer
    storage.delete_key("test_key_1")
    assert not storage.key_exists("test_key_1"), "Clé devrait être supprimée!"
    print("[OK] Clé supprimée")
    
    # Nettoyage
    storage.secure_clear_all()
    
    print("[OK] SecureKeyStorage (mémoire) fonctionne")
    return True


def test_key_expiration():
    """Test de l'expiration des clés"""
    print("\n--- Test Expiration ---")
    
    storage = SecureKeyStorage()
    
    # Clé qui expire dans 1 seconde
    key_data = secrets.token_bytes(32)
    storage.store_key(
        key_id="expiring_key",
        key_data=key_data,
        expires_in_seconds=1
    )
    
    # Récupérer avant expiration
    retrieved = storage.retrieve_key("expiring_key")
    assert retrieved == key_data, "Clé devrait être accessible!"
    print("[OK] Clé accessible avant expiration")
    
    # Attendre l'expiration
    print("Attente de l'expiration (2s)...")
    time.sleep(2)
    
    # Récupérer après expiration
    try:
        storage.retrieve_key("expiring_key")
        assert False, "Devrait lever KeyExpiredError!"
    except KeyExpiredError:
        print("[OK] KeyExpiredError levée correctement")
    
    storage.secure_clear_all()
    
    print("[OK] Expiration fonctionne")
    return True


def test_persistent_storage():
    """Test du stockage persistant chiffré"""
    print("\n--- Test Stockage Persistant ---")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "keys")
        password = "test_password_secure"
        
        # Créer et stocker
        storage1 = SecureKeyStorage(
            storage_password=password,
            storage_path=storage_path,
            auto_rotate_interval=0  # Désactiver rotation pour le test
        )
        
        key_data = secrets.token_bytes(32)
        storage1.store_key(
            key_id="persistent_key",
            key_data=key_data,
            purpose="persistence_test"
        )
        
        print(f"Clé stockée dans: {storage_path}")
        
        # Vérifier que le fichier existe
        key_file = f"{storage_path}.persistent_key.enc"
        assert os.path.exists(key_file), "Fichier de clé non créé!"
        print(f"[OK] Fichier créé: {os.path.basename(key_file)}")
        
        # Nettoyer la mémoire
        storage1.secure_clear_all()
        
        # Nouveau storage, recharger
        storage2 = SecureKeyStorage(
            storage_password=password,
            storage_path=storage_path,
            auto_rotate_interval=0
        )
        
        # Récupérer depuis le stockage persistant
        retrieved = storage2.retrieve_key("persistent_key")
        assert retrieved == key_data, "Clé persistée incorrecte!"
        print("[OK] Clé chargée depuis stockage persistant")
        
        storage2.secure_clear_all()
    
    print("[OK] Stockage persistant fonctionne")
    return True


def test_vault_key_storage():
    """Test du VaultKeyStorage"""
    print("\n--- Test VaultKeyStorage ---")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = create_secure_vault_storage(
            password="vault_password",
            storage_dir=tmpdir
        )
        
        # Stocker une clé vault
        vault_key = secrets.token_bytes(64)
        metadata = storage.store_vault_key(
            user_id="test_user",
            vault_key=vault_key,
            access_level="admin"
        )
        
        print(f"Vault key stockée: {metadata.key_id}")
        print(f"Purpose: {metadata.purpose}")
        
        # Récupérer
        retrieved = storage.get_vault_key("test_user")
        assert retrieved == vault_key, "Vault key incorrecte!"
        print("[OK] Vault key récupérée")
        
        # Vérifier existence
        assert storage.vault_key_exists("test_user"), "Devrait exister!"
        assert not storage.vault_key_exists("autre_user"), "Ne devrait pas exister!"
        print("[OK] Vérification d'existence")
        
        # Supprimer
        storage.delete_vault_key("test_user")
        assert not storage.vault_key_exists("test_user"), "Devrait être supprimée!"
        print("[OK] Vault key supprimée")
        
        storage.secure_clear_all()
    
    print("[OK] VaultKeyStorage fonctionne")
    return True


def test_key_not_found():
    """Test de l'erreur KeyNotFoundError"""
    print("\n--- Test KeyNotFoundError ---")
    
    storage = SecureKeyStorage()
    
    try:
        storage.retrieve_key("nonexistent_key")
        assert False, "Devrait lever KeyNotFoundError!"
    except KeyNotFoundError:
        print("[OK] KeyNotFoundError levée correctement")
    
    storage.secure_clear_all()
    return True


def main():
    print("=== TEST SECURE KEY STORAGE ===")
    print("=== VULN-CRYPTO-06 FIX VALIDATION ===")
    
    tests = [
        ("MemoryProtectedKey", test_memory_protected_key),
        ("SecureKeyDerivation", test_key_derivation),
        ("SecureKeyStorage (mémoire)", test_secure_key_storage_memory),
        ("Expiration", test_key_expiration),
        ("Stockage persistant", test_persistent_storage),
        ("VaultKeyStorage", test_vault_key_storage),
        ("KeyNotFoundError", test_key_not_found),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n=== SUMMARY ===")
    all_passed = True
    for name, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n=== VULN-CRYPTO-06 CORRIGEE ===")
    
    return all_passed


if __name__ == "__main__":
    main()
