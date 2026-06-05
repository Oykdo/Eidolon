import json
import sys
import time
import unittest
import base64
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.authenticated_files import AuthenticatedFileFormat
from src.crypto.constant_time import constant_time_compare, constant_time_select
from src.crypto.rust_crypto import (
    aes_gcm_decrypt,
    aes_gcm_encrypt,
    authenticated_file_build,
    authenticated_file_parse,
    hkdf_sha256_derive,
    hkdf_sha256_derive_no_salt,
    hkdf_sha512_derive,
    hmac_sha256,
    is_rust_crypto_available,
    psnx_legacy_prism_bool,
    psnx_normalize_legacy_prism_payload_json,
    secret_share_checksum,
    shamir_reconstruct_large_v2,
    shamir_reconstruct_v1,
    shamir_split_large_v2,
    shamir_split_v1,
    verify_secret_share_checksum,
    sha256_digest,
)


VECTORS_PATH = Path(__file__).parent / "vectors" / "rust_crypto_vectors.json"


def _load_vectors():
    with VECTORS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class RustCryptoBridgeTests(unittest.TestCase):
    def test_sha256_vectors_match_python_behavior(self):
        vectors = _load_vectors()
        for case in vectors["sha256_cases"]:
            data = bytes.fromhex(case["data_hex"])
            self.assertEqual(sha256_digest(data).hex(), case["digest_hex"])

    def test_hmac_vectors_match_python_behavior(self):
        vectors = _load_vectors()
        for case in vectors["hmac_cases"]:
            key = bytes.fromhex(case["key_hex"])
            data = bytes.fromhex(case["data_hex"])
            self.assertEqual(hmac_sha256(key, data).hex(), case["digest_hex"])

    def test_hkdf_vectors_match_python_behavior(self):
        vectors = _load_vectors()
        for case in vectors["hkdf_cases"]:
            okm = hkdf_sha256_derive(
                bytes.fromhex(case["ikm_hex"]),
                salt=bytes.fromhex(case["salt_hex"]),
                info=bytes.fromhex(case["info_hex"]),
                length=case["length"],
            )
            self.assertEqual(okm.hex(), case["okm_hex"])

    def test_hkdf_without_salt_is_stable(self):
        okm1 = hkdf_sha256_derive_no_salt(b"ikm-no-salt", info=b"interop", length=32)
        okm2 = hkdf_sha256_derive_no_salt(b"ikm-no-salt", info=b"interop", length=32)
        self.assertEqual(okm1, okm2)
        self.assertEqual(len(okm1), 32)

    def test_hkdf_sha512_is_stable(self):
        okm1 = hkdf_sha512_derive(
            b"ikm-sha512",
            salt=b"vault-001",
            info=b"eidolon-vault-key-v1",
            length=32,
        )
        okm2 = hkdf_sha512_derive(
            b"ikm-sha512",
            salt=b"vault-001",
            info=b"eidolon-vault-key-v1",
            length=32,
        )
        self.assertEqual(okm1, okm2)
        self.assertEqual(len(okm1), 32)

    def test_generic_aes_gcm_bridge_round_trip(self):
        encrypted = aes_gcm_encrypt(
            b"\x44" * 32,
            b"\x55" * 12,
            b"bridge-payload",
            aad=b"assoc-data",
        )
        self.assertEqual(
            aes_gcm_decrypt(b"\x44" * 32, encrypted, aad=b"assoc-data"),
            b"bridge-payload",
        )
        with self.assertRaises(Exception):
            aes_gcm_decrypt(b"\x44" * 32, encrypted, aad=b"wrong-aad")

    def test_constant_time_vectors_match_python_behavior(self):
        vectors = _load_vectors()
        for case in vectors["constant_time_cases"]:
            left = bytes.fromhex(case["compare_left_hex"])
            right = bytes.fromhex(case["compare_right_hex"])
            select_left = bytes.fromhex(case["select_left_hex"])
            select_right = bytes.fromhex(case["select_right_hex"])
            self.assertEqual(
                constant_time_compare(left, right),
                case["expected_equal"],
            )
            self.assertEqual(
                constant_time_select(True, select_left, select_right).hex(),
                case["selected_true_hex"],
            )
            self.assertEqual(
                constant_time_select(False, select_left, select_right).hex(),
                case["selected_false_hex"],
            )

    def test_authenticated_file_vectors_remain_stable(self):
        vectors = _load_vectors()
        for case in vectors["authenticated_file_cases"]:
            aff = AuthenticatedFileFormat(bytes.fromhex(case["auth_key_hex"]))
            with patch.object(time, "time", return_value=case["created_at"]):
                file_bytes = aff.create_file(
                    bytes.fromhex(case["data_hex"]),
                    case["file_type"],
                    case["key_id"],
                    compress=case["compress"],
                )
            self.assertEqual(file_bytes.hex(), case["file_hex"])

    def test_authenticated_file_build_bridge_matches_vectors(self):
        vectors = _load_vectors()
        for case in vectors["authenticated_file_cases"]:
            expected = bytes.fromhex(case["file_hex"])
            metadata_hex = expected[6:10]
            metadata_len = int.from_bytes(metadata_hex, "big")
            metadata_bytes = expected[10 : 10 + metadata_len]
            data_len_offset = 10 + metadata_len
            data_len = int.from_bytes(expected[data_len_offset : data_len_offset + 4], "big")
            data = expected[data_len_offset + 4 : data_len_offset + 4 + data_len]

            built = authenticated_file_build(
                bytes.fromhex(case["auth_key_hex"]),
                version=4,
                flags=1 if case["compress"] else 0,
                metadata_bytes=metadata_bytes,
                data=data,
            )
            self.assertEqual(built, expected)

    def test_authenticated_file_round_trip_vectors(self):
        vectors = _load_vectors()
        for case in vectors["authenticated_file_cases"]:
            aff = AuthenticatedFileFormat(bytes.fromhex(case["auth_key_hex"]))
            metadata, data = aff.parse_file(bytes.fromhex(case["file_hex"]))
            self.assertEqual(data, bytes.fromhex(case["data_hex"]))
            self.assertEqual(metadata.key_id, case["key_id"])
            self.assertEqual(metadata.file_type, case["file_type"])

    def test_authenticated_file_parse_bridge_returns_raw_sections(self):
        case = _load_vectors()["authenticated_file_cases"][0]
        parsed = authenticated_file_parse(
            bytes.fromhex(case["auth_key_hex"]),
            bytes.fromhex(case["file_hex"]),
        )
        self.assertEqual(parsed["version"], 4)
        expected_flags = 1 if case.get("compress", False) else 0
        self.assertEqual(parsed["flags"], expected_flags)
        self.assertIsInstance(parsed["metadata_bytes"], bytes)
        self.assertIsInstance(parsed["data"], bytes)

    def test_rust_bridge_is_optional(self):
        self.assertIsInstance(is_rust_crypto_available(), bool)

    def test_secret_share_checksum_bridge_matches_vectors(self):
        from src.crypto.secret_sharing import Share

        vectors_path = Path(__file__).parent / "vectors" / "secret_sharing_vectors.json"
        with vectors_path.open("r", encoding="utf-8") as handle:
            vectors = json.load(handle)

        for case_name in ["small_secret_case", "large_secret_case"]:
            share = Share.from_dict(vectors[case_name]["shares"][0])
            checksum = secret_share_checksum(
                share.data,
                index=share.index,
                threshold=share.threshold,
                version=share.version,
            )
            self.assertEqual(checksum, share.checksum)
            self.assertTrue(
                verify_secret_share_checksum(
                    share.data,
                    index=share.index,
                    threshold=share.threshold,
                    checksum=share.checksum,
                    version=share.version,
                )
            )

    def test_shamir_reconstruct_v1_matches_vectors(self):
        vectors_path = Path(__file__).parent / "vectors" / "secret_sharing_vectors.json"
        with vectors_path.open("r", encoding="utf-8") as handle:
            vectors = json.load(handle)

        for case_name in ["small_secret_case", "leading_zero_case", "zero_secret_case"]:
            case = vectors[case_name]
            shares = case["shares"]
            subset = [shares[i - 1] for i in case["recover_subset_indices"]]
            recovered = shamir_reconstruct_v1(
                [base64.b64decode(entry["data"]) for entry in subset],
                share_indices=[entry["index"] for entry in subset],
                threshold=case["threshold"],
            )
            self.assertEqual(recovered.hex(), case["recovered_hex"])

    def test_shamir_split_v1_generates_valid_reconstructable_shares(self):
        secret = bytes.fromhex(
            "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"
        )
        shares = shamir_split_v1(secret, threshold=3, total_shares=5)
        self.assertEqual(len(shares), 5)
        self.assertTrue(all(len(entry["data"]) == 32 for entry in shares))
        self.assertTrue(all(entry["version"] == 1 for entry in shares))

        recovered = shamir_reconstruct_v1(
            [shares[0]["data"], shares[2]["data"], shares[4]["data"]],
            share_indices=[shares[0]["index"], shares[2]["index"], shares[4]["index"]],
            threshold=3,
        )
        expected = secret.lstrip(b"\x00") or b"\x00"
        self.assertEqual(recovered, expected)

    def test_shamir_reconstruct_large_v2_matches_vectors(self):
        vectors_path = Path(__file__).parent / "vectors" / "secret_sharing_vectors.json"
        with vectors_path.open("r", encoding="utf-8") as handle:
            vectors = json.load(handle)

        case = vectors["large_secret_case"]
        subset = [case["shares"][i - 1] for i in case["recover_subset_indices"]]
        recovered = shamir_reconstruct_large_v2(
            [base64.b64decode(entry["data"]) for entry in subset],
            share_indices=[entry["index"] for entry in subset],
            threshold=case["threshold"],
        )
        self.assertEqual(recovered.hex(), case["recovered_hex"])

    def test_shamir_split_large_v2_round_trip(self):
        secret = (
            b"Eidolon large secret payload for migration validation. "
            b"This exceeds thirty-two bytes."
        )
        key_material = bytes.fromhex(
            "10f0e0d0c0b0a09080706050403020100102030405060708090a0b0c0d0e0f10"
        )
        nonce = bytes.fromhex("a1a2a3a4a5a6a7a8a9aaabac")

        shares = shamir_split_large_v2(
            secret,
            threshold=3,
            total_shares=5,
            key_material=key_material,
            nonce=nonce,
        )
        self.assertEqual(len(shares), 5)
        self.assertTrue(all(entry["version"] == 2 for entry in shares))
        self.assertTrue(all(len(entry["data"]) > 44 for entry in shares))

        recovered = shamir_reconstruct_large_v2(
            [shares[0]["data"], shares[1]["data"], shares[4]["data"]],
            share_indices=[shares[0]["index"], shares[1]["index"], shares[4]["index"]],
            threshold=3,
        )
        self.assertEqual(recovered, secret)

    def test_legacy_prism_payload_normalization_is_scoped(self):
        payload = json.dumps(
            {
                "crypto_properties": {
                    "psnx_is_quantum": "True",
                    "label": "True",
                }
            }
        )

        normalized = json.loads(psnx_normalize_legacy_prism_payload_json(payload))

        self.assertIs(normalized["crypto_properties"]["psnx_is_quantum"], True)
        self.assertEqual(normalized["crypto_properties"]["label"], "True")
        self.assertIs(psnx_legacy_prism_bool("True"), True)
        self.assertIs(psnx_legacy_prism_bool("False"), False)
        self.assertIsNone(psnx_legacy_prism_bool("true"))


if __name__ == "__main__":
    unittest.main()
