import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.psnx_signing import (
    PSNXSecurityManager,
    verify_psnx_blend_pair,
)
from src.ui.vault_gui_complete import DualKeyAuthenticator


class PsnxNativeIntegrationTests(unittest.TestCase):
    def test_verify_psnx_blend_pair_uses_native_parser_payload(self):
        master_seed = b"\x01" * 64
        manager = PSNXSecurityManager(master_seed, "vault-001")

        blend_data = {
            "format": "PSNX_BLEND_DATA",
            "version": 2,
            "key_id": "vault-001",
            "scene": {"name": "Vault"},
            "clusters": [],
            "key_polyhedra": [],
            "materials": {},
            "crypto_properties": {},
        }
        signed_blend = manager.sign_blend_data(blend_data, schema_version=2)
        signing_data = manager.get_psnx_signing_data()

        with tempfile.TemporaryDirectory() as tmp:
            blend_path = Path(tmp) / "vault.blend_data"
            blend_path.write_text(json.dumps(signed_blend), encoding="utf-8")

            with patch(
                "src.core.psnx_signing.parse_native_psnx_file",
                return_value={"key_data": {"signing_data": signing_data}},
            ) as mocked_parse:
                result = verify_psnx_blend_pair("vault.psnx", str(blend_path))

        self.assertTrue(result.valid)
        self.assertTrue(result.signature_valid)
        mocked_parse.assert_called_once_with("vault.psnx")

    def test_verify_psnx_blend_pair_accepts_legacy_signing_key(self):
        master_seed = b"\x02" * 64
        manager = PSNXSecurityManager(master_seed, "vault-legacy")

        blend_data = {
            "format": "PSNX_BLEND_DATA",
            "version": 2,
            "key_id": "vault-legacy",
            "scene": {"name": "Vault"},
            "clusters": [],
            "key_polyhedra": [],
            "materials": {},
            "crypto_properties": {},
        }
        signed_blend = manager.sign_blend_data(blend_data, schema_version=2)
        signing_data = manager.get_psnx_signing_data()

        with tempfile.TemporaryDirectory() as tmp:
            blend_path = Path(tmp) / "vault_legacy.blend_data"
            blend_path.write_text(json.dumps(signed_blend), encoding="utf-8")

            with patch(
                "src.core.psnx_signing.parse_native_psnx_file",
                return_value={"key_data": {"signing": signing_data}},
            ):
                result = verify_psnx_blend_pair("vault_legacy.psnx", str(blend_path))

        self.assertTrue(result.valid)
        self.assertTrue(result.signature_valid)

    def test_dual_key_authenticator_uses_native_parser_for_validation_and_match(self):
        auth = DualKeyAuthenticator()

        with tempfile.TemporaryDirectory() as tmp:
            psnx_path = Path(tmp) / "vault.psnx"
            blend_path = Path(tmp) / "vault.blend_data"
            psnx_path.write_bytes(b"placeholder")
            blend_path.write_text(
                json.dumps(
                    {
                        "format": "PSNX_BLEND_DATA",
                        "key_id": "vault-001",
                        "clusters": [],
                        "key_polyhedra": [],
                        "crypto_properties": {},
                    }
                ),
                encoding="utf-8",
            )

            with patch(
                "src.ui.vault_gui_complete.parse_native_psnx_file",
                return_value={"key_data": {"key_id": "vault-001"}},
            ) as mocked_parse:
                valid_psnx, psnx_msg = auth.validate_psnx_file(str(psnx_path))
                valid_match, match_msg = auth.verify_key_match(
                    str(psnx_path), str(blend_path)
                )

        self.assertTrue(valid_psnx)
        self.assertEqual(psnx_msg, "Valid PSNX file")
        self.assertTrue(valid_match)
        self.assertIn("Match verified", match_msg)
        self.assertEqual(mocked_parse.call_count, 2)


if __name__ == "__main__":
    unittest.main()
