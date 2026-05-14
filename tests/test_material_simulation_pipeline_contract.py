import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.holo.material_fingerprint import MaterialFingerprint
from src.holo.material_simulation_pipeline import CompleteMaterialSimulationPipeline


class MaterialSimulationPipelineContractTests(unittest.TestCase):
    def test_validation_token_matches_existing_sha256_contract(self):
        pipeline = object.__new__(CompleteMaterialSimulationPipeline)
        fingerprint = MaterialFingerprint(
            static_hash="static-hash",
            interaction_hash="interaction-hash",
            dynamic_signature="dynamic-signature",
            composite_fingerprint="composite-fingerprint-001",
            timestamp="2026-04-03T12:00:00",
            metadata={},
        )
        crypto_vertex = "crypto-vertex-001"
        simulation_results = [{"final_face": 1}, {"final_face": 4}, {"final_face": 6}]

        result = pipeline._validate_results(
            simulation_results=simulation_results,
            fingerprint=fingerprint,
            crypto_vertex=crypto_vertex,
        )

        expected_seed = "composite-fingerprint-001crypto-vertex-0013"
        expected = hashlib.sha256(expected_seed.encode()).hexdigest()
        self.assertTrue(result["valid"])
        self.assertEqual(result["token"], expected)


if __name__ == "__main__":
    unittest.main()
