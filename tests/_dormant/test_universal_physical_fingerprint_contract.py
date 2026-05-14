import hashlib
import unittest

from src.core.universal_physical_fingerprint import derive_universal_component_hash


class UniversalPhysicalFingerprintContractTests(unittest.TestCase):
    def test_component_hash_matches_existing_sha256_prefix_contract(self):
        payload = b"universal-physical-component"
        expected = hashlib.sha256(payload).hexdigest()[:16]

        self.assertEqual(derive_universal_component_hash(payload), expected)


if __name__ == "__main__":
    unittest.main()
