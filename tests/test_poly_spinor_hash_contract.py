import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.poly_spinor_hash import generate_ntru_parameters


class PolySpinorHashContractTests(unittest.TestCase):
    def test_ntru_seed_hash_matches_existing_sha256_contract(self):
        spinor_seed = bytes(range(256)) * 16
        public_key = generate_ntru_parameters(spinor_seed)

        expected = hashlib.sha256(spinor_seed).hexdigest()
        self.assertEqual(public_key["seed_hash"], expected)


if __name__ == "__main__":
    unittest.main()
