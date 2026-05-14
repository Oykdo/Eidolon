import base64
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.identity.vault_config import VaultConfigManager
from src.crypto.rust_crypto import sha256_digest


class VaultConfigContractTests(unittest.TestCase):
    def test_derive_key_is_stable_and_fernet_sized(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = VaultConfigManager(b"\x11" * 32, tmp)
            key1 = manager._derive_key()
            key2 = manager._derive_key()
            self.assertEqual(key1, key2)
            self.assertEqual(len(base64.urlsafe_b64decode(key1)), 32)

    def test_config_round_trip_remains_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = VaultConfigManager(b"\x22" * 32, tmp)
            manager.set("ui", "language", "en")
            manager.set("security", "kdf_iterations", 150000)

            loaded = VaultConfigManager(b"\x22" * 32, tmp)
            self.assertEqual(loaded.get("ui", "language"), "en")
            self.assertEqual(loaded.get("security", "kdf_iterations"), 150000)

    def test_cli_default_vault_key_hash_contract_remains_stable(self):
        vault_path = "/tmp/eidolon-vault-contract"
        self.assertEqual(
            sha256_digest(vault_path.encode()),
            hashlib.sha256(vault_path.encode()).digest(),
        )


if __name__ == "__main__":
    unittest.main()
