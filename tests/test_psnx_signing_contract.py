import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.psnx_signing import BlendDataSignature, PSNXSecurityManager


class PsnxSigningContractTests(unittest.TestCase):
    def test_sign_blend_data_content_hash_matches_existing_sha256_contract(self):
        manager = PSNXSecurityManager(b"\x03" * 64, "vault-contract")
        blend_data = {
            "format": "PSNX_BLEND_DATA",
            "version": 2,
            "key_id": "vault-contract",
            "scene": {"name": "ContractVault"},
            "clusters": [],
            "key_polyhedra": [],
            "materials": {},
            "crypto_properties": {},
        }

        signature = manager.sign_blend_data(blend_data, schema_version=2)
        expected_canonical = manager.signer._prepare_signable_content(blend_data, 2)
        expected = hashlib.sha256(expected_canonical).hexdigest()
        self.assertEqual(signature["crypto_properties"]["signature"]["content_hash"], expected)

    def test_verify_message_content_hash_matches_existing_sha256_contract(self):
        manager = PSNXSecurityManager(b"\x04" * 64, "vault-verify")
        signed_blend = manager.sign_blend_data(
            {
                "format": "PSNX_BLEND_DATA",
                "version": 2,
                "key_id": "vault-verify",
                "scene": {"name": "VerifyVault"},
                "clusters": [],
                "key_polyhedra": [],
                "materials": {},
                "crypto_properties": {},
            },
            schema_version=2,
        )

        signature_data = BlendDataSignature.from_dict(
            signed_blend["crypto_properties"]["signature"]
        )
        expected_canonical = manager.signer._prepare_signable_content(signed_blend, signature_data.schema_version)
        expected = hashlib.sha256(expected_canonical).hexdigest()

        verifier = manager.create_verifier()
        message = verifier._prepare_verification_message(signed_blend, signature_data)
        self.assertEqual(message[-32:].hex(), expected)


if __name__ == "__main__":
    unittest.main()
