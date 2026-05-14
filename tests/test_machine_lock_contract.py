import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.identity.machine_lock import MachineIdentifier, MachineLock


class MachineLockContractTests(unittest.TestCase):
    def test_generate_machine_hash_matches_documented_double_hash(self):
        hardware_id = "node|machine|processor|uuid"
        expected = hashlib.sha256(
            hashlib.sha256(
                hardware_id.encode() + b"EIDOLON_MACHINE_LOCK_V2"
            ).digest()
            + b"UNIQUE_MACHINE"
        ).hexdigest()

        with patch.object(MachineIdentifier, "get_hardware_id", return_value=hardware_id):
            self.assertEqual(MachineIdentifier.generate_machine_hash(), expected)

    def test_derive_key_is_stable_and_32_bytes(self):
        hardware_id = "node|machine|processor|uuid"
        with patch.object(MachineIdentifier, "get_hardware_id", return_value=hardware_id):
            lock = MachineLock(storage_dir=tempfile.mkdtemp())

        self.assertEqual(len(lock._derive_key()), 32)
        self.assertEqual(lock._derive_key(), lock._encryption_key)

    def test_encrypt_decrypt_round_trip_uses_nonce_prefix(self):
        hardware_id = "node|machine|processor|uuid"
        with patch.object(MachineIdentifier, "get_hardware_id", return_value=hardware_id):
            lock = MachineLock(storage_dir=tempfile.mkdtemp())

        plaintext = b'{"hello":"world"}'
        encrypted = lock._encrypt(plaintext)
        self.assertGreater(len(encrypted), 12)
        self.assertEqual(lock._decrypt(encrypted), plaintext)

    def test_save_and_load_local_lock_round_trip(self):
        hardware_id = "node|machine|processor|uuid"
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(MachineIdentifier, "get_hardware_id", return_value=hardware_id):
                lock = MachineLock(storage_dir=tmp)
                lock._save_local_lock(
                    {
                        "vault_name": "VectorVault",
                        "vault_number": 7,
                        "vault_key_hash": "deadbeef",
                    }
                )
                loaded = lock._get_local_lock()

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["vault_name"], "VectorVault")
            self.assertEqual(loaded["vault_number"], 7)
            self.assertEqual(loaded["vault_key_hash"], "deadbeef")
            self.assertEqual(loaded["version"], MachineLock.LOCK_VERSION)
            self.assertIn("updated_at", loaded)

            raw = Path(tmp, MachineLock.LOCK_FILENAME).read_bytes()
            self.assertGreater(len(raw), 12)

    def test_local_lock_rejects_wrong_machine_hash(self):
        hardware_id = "node|machine|processor|uuid"
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(MachineIdentifier, "get_hardware_id", return_value=hardware_id):
                lock = MachineLock(storage_dir=tmp)
                lock._save_local_lock({"vault_name": "VectorVault"})

            with patch.object(MachineIdentifier, "get_hardware_id", return_value="other-machine"):
                other_lock = MachineLock(storage_dir=tmp)
                self.assertIsNone(other_lock._get_local_lock())


if __name__ == "__main__":
    unittest.main()
