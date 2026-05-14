import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.rust_crypto import (
    hkdf_sha256_derive,
    scrypt_derive,
    secure_key_storage_decrypt,
    secure_key_storage_encrypt,
)


class SecureKeyStorageRustBridgeTests(unittest.TestCase):
    def test_hkdf_bridge_is_stable(self):
        key1 = hkdf_sha256_derive(
            b"\x11" * 32,
            salt=b"",
            info=b"vault_access_read",
            length=32,
        )
        key2 = hkdf_sha256_derive(
            b"\x11" * 32,
            salt=b"",
            info=b"vault_access_read",
            length=32,
        )
        self.assertEqual(len(key1), 32)
        self.assertEqual(key1, key2)

    def test_scrypt_bridge_matches_current_contract(self):
        salt = bytes.fromhex("22" * 32)
        key1 = scrypt_derive(
            "correct horse battery staple",
            salt=salt,
            length=32,
            n=2**17,
            r=8,
            p=1,
        )
        key2 = scrypt_derive(
            "correct horse battery staple",
            salt=salt,
            length=32,
            n=2**17,
            r=8,
            p=1,
        )
        self.assertEqual(len(key1), 32)
        self.assertEqual(key1, key2)

    def test_secure_key_storage_encrypt_decrypt_round_trip(self):
        key = bytes.fromhex("44" * 32)
        nonce = bytes.fromhex("55" * 12)
        plaintext = b'{"key":"aa","metadata":{"key_id":"alpha"}}'
        encrypted = secure_key_storage_encrypt(key, nonce, plaintext, key_id="alpha")
        self.assertEqual(encrypted[:12], nonce)
        self.assertEqual(
            secure_key_storage_decrypt(key, encrypted, key_id="alpha"),
            plaintext,
        )

    def test_secure_key_storage_encrypt_binds_to_key_id(self):
        key = bytes.fromhex("66" * 32)
        nonce = bytes.fromhex("77" * 12)
        plaintext = b'{"key":"bb"}'
        encrypted = secure_key_storage_encrypt(key, nonce, plaintext, key_id="alpha")
        with self.assertRaises(Exception):
            secure_key_storage_decrypt(key, encrypted, key_id="beta")


if __name__ == "__main__":
    unittest.main()
