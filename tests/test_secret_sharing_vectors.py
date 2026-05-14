import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.secret_sharing import (
    SecretSharingError,
    Share,
    ShamirSecretSharing,
    VaultKeySharing,
)


VECTORS_PATH = Path(__file__).resolve().parent / "vectors" / "secret_sharing_vectors.json"


def _load_vectors():
    with VECTORS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _shares_from_dicts(entries):
    return [Share.from_dict(entry) for entry in entries]


class SecretSharingVectorTests(unittest.TestCase):
    def test_small_secret_reconstructs_exactly(self):
        vectors = _load_vectors()["small_secret_case"]
        sss = ShamirSecretSharing(vectors["threshold"], vectors["total_shares"])
        shares = _shares_from_dicts(vectors["shares"])
        subset = [shares[0], shares[2], shares[4]]
        self.assertEqual(sss.reconstruct(subset).hex(), vectors["recovered_hex"])

    def test_leading_zero_secret_behavior_is_frozen(self):
        vectors = _load_vectors()["leading_zero_case"]
        sss = ShamirSecretSharing(vectors["threshold"], vectors["total_shares"])
        shares = _shares_from_dicts(vectors["shares"])
        subset = [shares[1], shares[3], shares[4]]
        self.assertEqual(sss.reconstruct(subset).hex(), vectors["recovered_hex"])

    def test_zero_secret_behavior_is_frozen(self):
        vectors = _load_vectors()["zero_secret_case"]
        sss = ShamirSecretSharing(vectors["threshold"], vectors["total_shares"])
        shares = _shares_from_dicts(vectors["shares"])
        self.assertEqual(sss.reconstruct(shares[:3]).hex(), vectors["recovered_hex"])

    def test_large_secret_reconstructs_exactly(self):
        vectors = _load_vectors()["large_secret_case"]
        sss = ShamirSecretSharing(vectors["threshold"], vectors["total_shares"])
        shares = _shares_from_dicts(vectors["shares"])
        subset = [shares[0], shares[1], shares[4]]
        self.assertEqual(sss.reconstruct(subset).hex(), vectors["recovered_hex"])

    def test_export_import_round_trip_is_stable(self):
        vectors = _load_vectors()["export_cases"]
        vks = VaultKeySharing()
        plain = vks.import_share(vectors["plain_share_json"])
        encrypted = vks.import_share(
            vectors["encrypted_share_json"],
            password=vectors["password"],
        )
        self.assertTrue(plain.verify_checksum())
        self.assertTrue(encrypted.verify_checksum())

    def test_tampered_share_is_rejected(self):
        vectors = _load_vectors()
        small = vectors["small_secret_case"]
        sss = ShamirSecretSharing(small["threshold"], small["total_shares"])
        shares = _shares_from_dicts(small["shares"])
        tampered = Share.from_dict(vectors["error_cases"]["tampered_share"])
        with self.assertRaises(SecretSharingError):
            sss.reconstruct([tampered, shares[1], shares[2]])

    def test_duplicate_share_indices_are_rejected(self):
        vectors = _load_vectors()["error_cases"]
        shares = _shares_from_dicts(vectors["duplicate_share_indices"])
        sss = ShamirSecretSharing(3, 5)
        with self.assertRaises(SecretSharingError):
            sss.reconstruct(shares)

    def test_insufficient_shares_are_rejected(self):
        vectors = _load_vectors()["error_cases"]
        shares = _shares_from_dicts(vectors["insufficient_shares"])
        sss = ShamirSecretSharing(3, 5)
        with self.assertRaises(SecretSharingError):
            sss.reconstruct(shares)


if __name__ == "__main__":
    unittest.main()
