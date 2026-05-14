import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.identity.secure_key_storage import (
    KeyAccessDeniedError,
    SecureKeyDerivation,
    SecureKeyStorage,
)


class SecureKeyStorageContractTests(unittest.TestCase):
    def test_derive_subkey_is_stable_and_32_bytes(self):
        master_key = bytes.fromhex("11" * 32)
        purpose = "vault_access_read"
        key1 = SecureKeyDerivation.derive_subkey(master_key, purpose)
        key2 = SecureKeyDerivation.derive_subkey(master_key, purpose)
        self.assertEqual(len(key1), 32)
        self.assertEqual(key1, key2)

    def test_derive_key_from_password_is_stable_and_32_bytes(self):
        salt = bytes.fromhex("22" * 32)
        key1 = SecureKeyDerivation.derive_key_from_password("correct horse battery staple", salt)
        key2 = SecureKeyDerivation.derive_key_from_password("correct horse battery staple", salt)
        self.assertEqual(len(key1), 32)
        self.assertEqual(key1, key2)

    def test_persisted_blob_uses_nonce_prefix_and_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage_path = str(Path(tmp, "vault_keys"))
            storage = SecureKeyStorage(
                storage_password="persist-pass",
                storage_path=storage_path,
                auto_rotate_interval=0,
            )
            metadata = storage.store_key(
                key_id="alpha",
                key_data=b"\x01" * 32,
                purpose="unit_test",
                algorithm="AES-256-GCM",
            )
            self.assertEqual(metadata.key_id, "alpha")

            raw = Path(f"{storage_path}.alpha.enc").read_bytes()
            self.assertGreater(len(raw), 12)

            loaded = SecureKeyStorage(
                storage_password="persist-pass",
                storage_path=storage_path,
                auto_rotate_interval=0,
            )
            self.assertEqual(loaded.retrieve_key("alpha"), b"\x01" * 32)

    def test_persisted_blob_is_bound_to_key_id_via_aad(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage_path = str(Path(tmp, "vault_keys"))
            storage = SecureKeyStorage(
                storage_password="persist-pass",
                storage_path=storage_path,
                auto_rotate_interval=0,
            )
            storage.store_key("alpha", b"\x02" * 32, purpose="unit_test")

            renamed = Path(f"{storage_path}.beta.enc")
            Path(f"{storage_path}.alpha.enc").replace(renamed)

            loaded = SecureKeyStorage(
                storage_password="persist-pass",
                storage_path=storage_path,
                auto_rotate_interval=0,
            )
            with self.assertRaises(KeyAccessDeniedError):
                loaded.retrieve_key("beta")

    def test_wrong_storage_password_denies_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage_path = str(Path(tmp, "vault_keys"))
            storage = SecureKeyStorage(
                storage_password="persist-pass",
                storage_path=storage_path,
                auto_rotate_interval=0,
            )
            storage.store_key("alpha", b"\x03" * 32, purpose="unit_test")

            loaded = SecureKeyStorage(
                storage_password="wrong-pass",
                storage_path=storage_path,
                auto_rotate_interval=0,
            )
            with self.assertRaises(KeyAccessDeniedError):
                loaded.retrieve_key("alpha")


if __name__ == "__main__":
    unittest.main()
