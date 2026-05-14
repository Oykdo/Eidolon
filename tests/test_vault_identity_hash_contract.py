import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.identity.vault_identity import VaultIdentity, VaultIdentityManager


class VaultIdentityHashContractTests(unittest.TestCase):
    def test_derive_vault_id_matches_sha256_of_vault_key(self):
        manager = VaultIdentityManager(storage_dir=tempfile.mkdtemp())
        vault_key = bytes.fromhex("11" * 32)
        expected = hashlib.sha256(vault_key).hexdigest()
        self.assertEqual(manager._derive_vault_id(vault_key), expected)

    def test_compute_file_hash_matches_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "sample.psnx")
            payload = b"psnx-contract"
            path.write_bytes(payload)

            manager = VaultIdentityManager(storage_dir=tmp)
            self.assertEqual(
                manager._compute_file_hash(str(path)),
                hashlib.sha256(payload).hexdigest(),
            )

    def test_verify_file_hashes_detects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            psnx = Path(tmp, "sample.psnx")
            blend = Path(tmp, "sample.blend_data")
            psnx.write_bytes(b"psnx-ok")
            blend.write_bytes(b"blend-ok")

            identity = VaultIdentity(
                vault_id="deadbeef",
                vault_number=1,
                vault_name="TestVault",
                psnx_path=str(psnx),
                blend_path=str(blend),
                psnx_hash=hashlib.sha256(b"psnx-ok").hexdigest(),
                blend_hash=hashlib.sha256(b"blend-ok").hexdigest(),
                vault_key_hash="unused",
            )

            valid, _ = identity.verify_file_hashes()
            self.assertTrue(valid)

            psnx.write_bytes(b"psnx-tampered")
            valid, message = identity.verify_file_hashes()
            self.assertFalse(valid)
            self.assertIn("modified", message)


if __name__ == "__main__":
    unittest.main()
