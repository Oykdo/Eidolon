import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.identity.vault_registry import VaultRegistry


class VaultRegistryContractTests(unittest.TestCase):
    def test_hash_password_matches_pbkdf2_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(VaultRegistry, "_get_registry_path", return_value=Path(tmp) / "vault_registry.json"):
                registry = VaultRegistry()
                salt = bytes.fromhex("11" * 32)
                password_hash, salt_hex = registry._hash_password("correct horse battery staple", salt)

        expected = hashlib.pbkdf2_hmac(
            "sha256",
            b"correct horse battery staple",
            salt,
            150000,
            32,
        ).hex()
        self.assertEqual(password_hash, expected)
        self.assertEqual(salt_hex, salt.hex())

    def test_derive_vault_key_matches_existing_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(VaultRegistry, "_get_registry_path", return_value=Path(tmp) / "vault_registry.json"):
                registry = VaultRegistry()
                salt = bytes.fromhex("22" * 32)
                vault_key = registry._derive_vault_key("AlphaVault", "hunter2-password", salt)

        key_salt = hashlib.sha256(salt + b"AlphaVault").digest()
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            b"hunter2-password",
            key_salt,
            100000,
            32,
        )
        self.assertEqual(vault_key, expected)

    def test_register_and_authenticate_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(VaultRegistry, "_get_registry_path", return_value=Path(tmp) / "vault_registry.json"):
                registry = VaultRegistry()
                ok, vault_key, _ = registry.register_vault("Alpha", "strong-pass-01")
                self.assertTrue(ok)
                self.assertEqual(len(vault_key), 32)

                auth_ok, auth_key, _ = registry.authenticate("Alpha", "strong-pass-01")
                self.assertTrue(auth_ok)
                self.assertEqual(auth_key, vault_key)

    def test_stored_key_verification_hash_matches_existing_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(VaultRegistry, "_get_registry_path", return_value=Path(tmp) / "vault_registry.json"):
                registry = VaultRegistry()
                vault_key = bytes.fromhex("33" * 32)
                ok, _ = registry.register_vault_with_key(
                    "Beta",
                    "strong-pass-02",
                    vault_key,
                    key_id="key-123",
                )
                self.assertTrue(ok)

                vault_data = registry.registry["vaults"]["beta"]
                salt = bytes.fromhex(vault_data["salt"])
                expected = hashlib.sha256(vault_key + salt).hexdigest()
                self.assertEqual(vault_data["vault_key_verification"], expected)


if __name__ == "__main__":
    unittest.main()
