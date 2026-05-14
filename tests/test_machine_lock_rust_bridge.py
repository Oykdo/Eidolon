import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.rust_crypto import (
    machine_lock_decrypt,
    machine_lock_derive_key,
    machine_lock_encrypt,
    machine_lock_hash,
    pbkdf2_sha256_derive,
)


class MachineLockRustBridgeTests(unittest.TestCase):
    def test_machine_lock_hash_matches_python_behavior(self):
        hardware_id = "node|machine|processor|uuid"
        h1 = hashlib.sha256(hardware_id.encode() + b"EIDOLON_MACHINE_LOCK_V2").digest()
        expected = hashlib.sha256(h1 + b"UNIQUE_MACHINE").hexdigest()
        self.assertEqual(machine_lock_hash(hardware_id), expected)

    def test_machine_lock_derive_key_is_stable(self):
        machine_hash = "abcd1234abcd1234abcd1234abcd1234ffffeeeeffffeeeeffffeeeeffffeeee"
        key1 = machine_lock_derive_key(machine_hash)
        key2 = machine_lock_derive_key(machine_hash)
        self.assertEqual(len(key1), 32)
        self.assertEqual(key1, key2)

    def test_machine_lock_encrypt_decrypt_round_trip(self):
        machine_hash = "abcd1234abcd1234abcd1234abcd1234ffffeeeeffffeeeeffffeeeeffffeeee"
        key = machine_lock_derive_key(machine_hash)
        nonce = bytes.fromhex("11" * 12)
        plaintext = b'{"vault":1}'
        encrypted = machine_lock_encrypt(key, nonce, plaintext)
        self.assertEqual(encrypted[:12], nonce)
        self.assertEqual(machine_lock_decrypt(key, encrypted), plaintext)

    def test_pbkdf2_bridge_is_stable(self):
        key1 = pbkdf2_sha256_derive(
            b"vault-password",
            salt=b"vault_config_salt_v1",
            length=32,
            iterations=100000,
        )
        key2 = pbkdf2_sha256_derive(
            b"vault-password",
            salt=b"vault_config_salt_v1",
            length=32,
            iterations=100000,
        )
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 32)


if __name__ == "__main__":
    unittest.main()
