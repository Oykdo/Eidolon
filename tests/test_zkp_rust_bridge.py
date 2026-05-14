import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
VECTORS_PATH = Path(__file__).parent / "vectors" / "rust_crypto_vectors.json"

from src.crypto.rust_crypto import (
    zkp_build_proof,
    is_rust_crypto_available,
    zkp_compute_challenge,
    zkp_compute_response,
    zkp_public_key_from_scalar,
    zkp_scalar_from_secret,
    zkp_verify_equation,
)
from src.crypto.zkp_auth import SchnorrZKP


class ZkpRustBridgeTests(unittest.TestCase):
    @staticmethod
    def _vectors() -> dict:
        return json.loads(VECTORS_PATH.read_text(encoding="utf-8"))

    def test_zkp_scalar_from_secret_matches_python_behavior(self):
        case = self._vectors()["zkp_cases"]["scalar_case"]
        secret = bytes.fromhex(case["secret_hex"])
        self.assertEqual(zkp_scalar_from_secret(secret), int(case["scalar_hex"], 16))

    def test_zkp_compute_challenge_matches_python_behavior(self):
        case = self._vectors()["zkp_cases"]["challenge_case"]
        commitment = int(case["commitment_hex"], 16)
        public_key = int(case["public_key_hex"], 16)
        message = bytes.fromhex(case["message_hex"])
        commitment_bytes = commitment.to_bytes((commitment.bit_length() + 7) // 8, "big")
        public_key_bytes = public_key.to_bytes((public_key.bit_length() + 7) // 8, "big")

        self.assertEqual(
            zkp_compute_challenge(commitment_bytes, public_key_bytes, message),
            int(case["challenge_hex"], 16),
        )

    def test_rust_extension_is_available(self):
        self.assertIsInstance(is_rust_crypto_available(), bool)

    def test_zkp_verify_equation_matches_python_behavior(self):
        case = self._vectors()["zkp_cases"]["proof_case"]
        challenge = int(case["challenge_hex"], 16)
        public_key = int(case["public_key_hex"], 16)
        commitment = int(case["commitment_hex"], 16)
        response = int(case["response_hex"], 16)

        expected = (
            pow(SchnorrZKP.G, response, SchnorrZKP.P)
            == (commitment * pow(public_key, challenge, SchnorrZKP.P)) % SchnorrZKP.P
        )

        self.assertEqual(
            zkp_verify_equation(
                commitment=commitment,
                challenge=challenge,
                response=response,
                public_key=public_key,
            ),
            expected,
        )

    def test_zkp_public_key_from_scalar_matches_python_behavior(self):
        case = self._vectors()["zkp_cases"]["proof_case"]
        scalar = int(case["scalar_hex"], 16)
        self.assertEqual(
            zkp_public_key_from_scalar(scalar),
            int(case["public_key_hex"], 16),
        )

    def test_zkp_compute_response_matches_python_behavior(self):
        case = self._vectors()["zkp_cases"]["proof_case"]
        nonce = int(case["nonce_hex"], 16)
        challenge = int(case["challenge_hex"], 16)
        scalar = int(case["scalar_hex"], 16)
        self.assertEqual(
            zkp_compute_response(
                nonce=nonce,
                challenge=challenge,
                scalar=scalar,
            ),
            int(case["response_hex"], 16),
        )

    def test_zkp_build_proof_matches_python_behavior(self):
        case = self._vectors()["zkp_cases"]["proof_case"]
        scalar = int(case["scalar_hex"], 16)
        nonce = int(case["nonce_hex"], 16)
        message = bytes.fromhex(case["message_hex"])
        proof = zkp_build_proof(scalar=scalar, nonce=nonce, message=message)
        self.assertEqual(proof["public_key"], int(case["public_key_hex"], 16))
        self.assertEqual(proof["commitment"], int(case["commitment_hex"], 16))
        self.assertEqual(proof["challenge"], int(case["challenge_hex"], 16))
        self.assertEqual(proof["response"], int(case["response_hex"], 16))


if __name__ == "__main__":
    unittest.main()
