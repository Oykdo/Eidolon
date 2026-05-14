import hashlib
import unittest

from src.blockchain.avatar_visualization import (
    derive_avatar_blend_digest,
    derive_avatar_psnx_digest,
    derive_avatar_visualization_vault_id,
)


class AvatarVisualizationContractTests(unittest.TestCase):
    def test_vault_id_matches_existing_sha256_contract(self):
        vault_key = b"avatar-visualization-vault-key"
        expected = hashlib.sha256(vault_key).hexdigest()

        self.assertEqual(derive_avatar_visualization_vault_id(vault_key), expected)

    def test_psnx_digest_matches_existing_sha256_contract(self):
        psnx_bytes = b"psnx-avatar-seed-material"
        expected = hashlib.sha256(psnx_bytes).digest()

        self.assertEqual(derive_avatar_psnx_digest(psnx_bytes), expected)

    def test_blend_digest_matches_existing_sha256_contract(self):
        blend_bytes = b"{\"blend\":\"avatar-seed-material\"}"
        expected = hashlib.sha256(blend_bytes).digest()

        self.assertEqual(derive_avatar_blend_digest(blend_bytes), expected)


if __name__ == "__main__":
    unittest.main()
