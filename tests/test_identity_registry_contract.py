import sys
import tempfile
import unittest
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.identity.identity_registry import IdentityRegistry


class IdentityRegistryContractTests(unittest.TestCase):
    def test_registry_key_derivation_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = IdentityRegistry(storage_dir=tmp)
            key1 = registry._derive_key_from_machine_id("node|machine|processor")
            key2 = registry._derive_key_from_machine_id("node|machine|processor")
            self.assertEqual(key1, key2)
            self.assertEqual(len(key1), 32)

    def test_registry_round_trip_preserves_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = IdentityRegistry(storage_dir=tmp)
            ok, identity, error = registry.register_identity(
                name="ContractVault",
                vault_key=b"\x44" * 32,
                metadata={"source": "contract"},
            )

            self.assertTrue(ok, msg=error)
            self.assertIsNotNone(identity)

            loaded = IdentityRegistry(storage_dir=tmp)
            restored = loaded.get_identity(identity.full_id)
            self.assertIsNotNone(restored)
            self.assertEqual(restored.full_id, identity.full_id)
            self.assertEqual(restored.metadata["source"], "contract")

    def test_fingerprint_generation_matches_existing_double_sha256_contract(self):
        vault_key = b"\x55" * 32
        extra_entropy = b"extra"
        expected = hashlib.sha256(
            hashlib.sha256(vault_key + extra_entropy).digest() + b"PSNX_FINGERPRINT"
        ).digest()[:4].hex()
        self.assertEqual(
            IdentityRegistry.generate_fingerprint(vault_key, extra_entropy),
            expected,
        )

    def test_verify_identity_matches_registered_key_hash_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = IdentityRegistry(storage_dir=tmp)
            ok, identity, error = registry.register_identity(
                name="VerifyVault",
                vault_key=b"\x66" * 32,
            )

            self.assertTrue(ok, msg=error)
            valid, _ = registry.verify_identity(identity.full_id, b"\x66" * 32)
            invalid, _ = registry.verify_identity(identity.full_id, b"\x67" * 32)
            self.assertTrue(valid)
            self.assertFalse(invalid)


if __name__ == "__main__":
    unittest.main()
