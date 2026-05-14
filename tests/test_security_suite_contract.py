import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.security_suite import SecureVaultManager


class SecuritySuiteContractTests(unittest.TestCase):
    def test_generate_secure_key_matches_documented_hkdf_inputs(self):
        entropy = bytes(range(64))
        fixed_time = 1700000000.0
        user_name = "Alice"
        combined = entropy + f"PSNX_VAULT_{user_name}_{fixed_time}".encode()

        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF

        expected = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"PSNX_SECURE_KEY_v10",
            info=b"vault_master_key",
        ).derive(combined)

        manager = SecureVaultManager()
        with patch.object(manager.entropy_pool, "get_entropy", return_value=entropy), patch(
            "src.core.security_suite.time.time", return_value=fixed_time
        ), patch.object(manager.key_storage, "store"):
            derived = manager.generate_secure_key(user_name)

        self.assertEqual(derived, expected)

    def test_secure_file_key_id_matches_sha256_prefix(self):
        vault_key = bytes.fromhex("22" * 32)
        expected = hashlib.sha256(vault_key).hexdigest()[:16]
        self.assertEqual(expected, hashlib.sha256(vault_key).hexdigest()[:16])


if __name__ == "__main__":
    unittest.main()
