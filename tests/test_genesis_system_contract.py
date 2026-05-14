import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.holo.genesis_system import AvatarRuneGenerator, FounderRewardGenerator, GenesisTier, RuneSymbolGenerator


class GenesisSystemContractTests(unittest.TestCase):
    def test_founder_reward_unique_hash_matches_existing_sha256_contract(self):
        with patch("src.holo.genesis_system.time.time", return_value=1712145600.0), \
             patch("src.holo.genesis_system.secrets.token_hex", return_value="0011223344556677"):
            reward = FounderRewardGenerator.get_founder_reward(12)

        expected_seed = "12:1712145600.0:0011223344556677"
        expected = hashlib.sha256(expected_seed.encode()).hexdigest()[:16]
        self.assertIsNotNone(reward)
        self.assertEqual(reward["unique_hash"], expected)

    def test_avatar_rune_inscription_id_matches_existing_sha256_contract(self):
        fingerprint = {
            "hash": "blend-hash-001122334455",
            "merkle_root": "merkle-root-001122334455",
            "entropy_signature": "entropy-signature",
            "metadata": {},
            "file_size": 123,
            "chunks": 1,
        }

        with patch.object(AvatarRuneGenerator, "compute_blend_fingerprint", return_value=fingerprint):
            inscription = AvatarRuneGenerator.generate_avatar_rune(
                avatar_id="avatar-xyz",
                vault_number=42,
                blend_data_path="ignored.blend",
                vault_key=None,
            )

        expected_seed = "avatar-xyz:42:blend-hash-001122334455"
        expected = hashlib.sha256(expected_seed.encode()).hexdigest()[:16]
        self.assertEqual(inscription.inscription_id, expected)

    def test_avatar_rune_symbol_suffix_matches_existing_sha256_contract(self):
        fingerprint = {
            "hash": "blend-hash-001122334455",
            "merkle_root": "merkle-root-001122334455",
            "entropy_signature": "entropy-signature",
            "metadata": {},
            "file_size": 123,
            "chunks": 1,
        }

        with patch.object(AvatarRuneGenerator, "compute_blend_fingerprint", return_value=fingerprint):
            inscription = AvatarRuneGenerator.generate_avatar_rune(
                avatar_id="avatar-xyz",
                vault_number=42,
                blend_data_path="ignored.blend",
                vault_key=None,
            )

        avatar_hash = hashlib.sha256(b"avatar-xyz").hexdigest()[:8]
        expected_suffix = ""
        for char in avatar_hash[:4]:
            idx = int(char, 16) % len(RuneSymbolGenerator.RUNIC_ALPHABET)
            expected_suffix += RuneSymbolGenerator.RUNIC_ALPHABET[idx]

        prefix = AvatarRuneGenerator.AVATAR_RUNE_PREFIXES[GenesisTier.FOUNDER]
        self.assertEqual(inscription.rune_symbol, f"{prefix}•{expected_suffix}")

    def test_avatar_rune_inscription_witness_matches_existing_sha256_contract(self):
        fingerprint = {
            "hash": "blend-hash-001122334455",
            "merkle_root": "merkle-root-001122334455",
            "entropy_signature": "entropy-signature",
            "metadata": {},
            "file_size": 123,
            "chunks": 1,
        }

        with patch.object(AvatarRuneGenerator, "compute_blend_fingerprint", return_value=fingerprint):
            inscription = AvatarRuneGenerator.generate_avatar_rune(
                avatar_id="avatar-xyz",
                vault_number=42,
                blend_data_path="ignored.blend",
                vault_key=None,
            )

        witness_data = json.dumps(inscription.inscription_content, sort_keys=True)
        expected = hashlib.sha256(witness_data.encode()).hexdigest()
        self.assertEqual(inscription.inscription_witness, expected)


if __name__ == "__main__":
    unittest.main()
