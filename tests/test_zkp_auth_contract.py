import hashlib
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.zkp_auth import (
    ChallengeResponseAuth,
    PSNX_VAULT_KEY_INFO,
    SchnorrProof,
    SchnorrZKP,
    VaultZKPAuth,
    _build_psnx_auth_message,
    compute_psnx_fingerprint,
    derive_vault_key,
    generate_psnx_auth_proof,
    scalar_from_vault_key,
    verify_psnx_auth_proof,
)


class ZkpAuthContractTests(unittest.TestCase):
    def test_from_secret_matches_documented_scalar_derivation(self):
        secret = bytes.fromhex("11" * 32)
        expected = int.from_bytes(
            hashlib.sha256(b"PSNX_ZKP_KEY_" + secret).digest(),
            "big",
        ) % SchnorrZKP.Q
        if expected == 0:
            expected = 1

        prover = SchnorrZKP.from_secret(secret)
        self.assertEqual(prover.x, expected)

    def test_fiat_shamir_uses_variable_length_big_endian_encoding(self):
        r = 0x1234
        y = 0xABCD
        message = b"contract-message"
        expected = int.from_bytes(
            hashlib.sha256(
                r.to_bytes((r.bit_length() + 7) // 8, "big")
                + y.to_bytes((y.bit_length() + 7) // 8, "big")
                + message
            ).digest(),
            "big",
        ) % SchnorrZKP.Q

        self.assertEqual(SchnorrZKP._compute_challenge(r, y, message), expected)

    def test_schnorr_proof_json_round_trip_is_stable(self):
        proof = SchnorrProof(
            commitment=0x1234,
            challenge=0x5678,
            response=0x9ABC,
            public_key=0xDEF0,
            message=b"\x01\x02test",
            timestamp=1234.5,
        )

        restored = SchnorrProof.from_json(proof.to_json())
        self.assertEqual(restored, proof)
        payload = proof.to_dict()
        self.assertEqual(payload["commitment"], hex(0x1234))
        self.assertEqual(payload["public_key"], hex(0xDEF0))
        self.assertEqual(payload["message"], "010274657374")

    def test_create_auth_proof_appends_network_order_timestamp(self):
        vault_key = bytes.fromhex("22" * 32)
        auth = VaultZKPAuth(vault_key)

        with patch("src.core.zkp_auth.time.time", return_value=1700000000.25):
            auth_data = auth.create_auth_proof("login", include_timestamp=True)

        proof = SchnorrProof.from_dict(auth_data["proof"])
        expected_suffix = struct.pack(">d", 1700000000.25)
        self.assertEqual(proof.message, b"login" + expected_suffix)
        self.assertEqual(auth_data["challenge"], "login")

    def test_psnx_auth_message_format_is_stable(self):
        message = _build_psnx_auth_message("vault-001", bytes.fromhex("a1" * 16))
        self.assertEqual(
            message,
            b"psnx-auth|v1|vault-001|" + ("a1" * 16).encode("ascii"),
        )

    def test_generate_and_verify_psnx_auth_proof_round_trip(self):
        psnx_bytes = b"psnx-contract-payload"
        vault_id = "vault-001"
        nonce = bytes.fromhex("ab" * 16)
        public_commitment = generate_psnx_auth_proof(
            psnx_bytes,
            vault_id,
            nonce,
        )["public_commitment"]

        proof = generate_psnx_auth_proof(psnx_bytes, vault_id, nonce)
        valid, reason = verify_psnx_auth_proof(
            vault_id,
            proof,
            public_commitment,
            nonce,
        )
        self.assertTrue(valid, reason)

    def test_derive_vault_key_matches_hkdf_contract(self):
        psnx_bytes = b"psnx-bytes"
        vault_id = "vault-123"
        key = derive_vault_key(psnx_bytes, vault_id)
        expected = HKDF(
            algorithm=hashes.SHA512(),
            length=32,
            salt=vault_id.encode("utf-8"),
            info=PSNX_VAULT_KEY_INFO,
        ).derive(psnx_bytes)
        self.assertEqual(key, expected)
        self.assertEqual(len(key), 32)
        self.assertEqual(derive_vault_key(psnx_bytes, vault_id), key)
        self.assertEqual(scalar_from_vault_key(key), SchnorrZKP.from_secret(key).x)
        self.assertNotEqual(compute_psnx_fingerprint(psnx_bytes, vault_id), "")
        self.assertEqual(PSNX_VAULT_KEY_INFO, b"eidolon-vault-key-v1")

    def test_challenge_response_round_trip_remains_valid(self):
        auth = ChallengeResponseAuth(b"\x77" * 32)
        challenge = bytes.fromhex("ab" * 32)

        with patch("src.core.zkp_auth.time.time", return_value=1700000000.0):
            response = auth.respond_to_challenge(challenge)

        with patch("src.core.zkp_auth.time.time", return_value=1700000005.0):
            self.assertTrue(auth.verify_response(challenge, response, max_age=60))


if __name__ == "__main__":
    unittest.main()
