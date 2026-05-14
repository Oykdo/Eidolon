import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.holo.material_fingerprint import MaterialFingerprintExtractor


class MaterialFingerprintContractTests(unittest.TestCase):
    def test_dynamic_signature_matches_existing_sha256_contract(self):
        extractor = object.__new__(MaterialFingerprintExtractor)
        simulation_results = [
            {"final_face": 4, "material_specific_data": {"energy_loss_profile": 1.25}},
            {"final_face": 7, "material_specific_data": {"energy_loss_profile": 0.5}},
        ]

        expected = hashlib.sha256(b"4:1.2500|7:0.5000").hexdigest()
        self.assertEqual(extractor._extract_dynamic_signature(simulation_results), expected)


if __name__ == "__main__":
    unittest.main()
