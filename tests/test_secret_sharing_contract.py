import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.secret_sharing import ShamirSecretSharing, VaultKeySharing


class SecretSharingContractTests(unittest.TestCase):
    def test_large_secret_split_and_reconstruct_round_trip(self):
        secret = (
            b"Eidolon migration contract payload for large secret handling. "
            b"This must exceed thirty-two bytes."
        )
        sss = ShamirSecretSharing(3, 5)
        shares = sss.split(secret)
        recovered = sss.reconstruct([shares[0], shares[2], shares[4]])
        self.assertEqual(recovered, secret)

    def test_export_import_encrypted_share_round_trip(self):
        sss = ShamirSecretSharing(3, 5)
        valid_share = sss.split(bytes.fromhex("01" * 32))[0]
        exported = VaultKeySharing().export_share(valid_share, password="strong-password")
        payload = json.loads(exported)

        self.assertTrue(payload["encrypted"])
        imported = VaultKeySharing().import_share(exported, password="strong-password")
        self.assertEqual(imported.to_dict(), valid_share.to_dict())


if __name__ == "__main__":
    unittest.main()
