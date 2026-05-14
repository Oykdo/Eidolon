import hashlib
import json
import unittest

from src.core.key_revocation import (
    derive_empty_merkle_root,
    derive_merkle_leaf,
    derive_merkle_node,
    derive_revocation_id,
)


class KeyRevocationContractTests(unittest.TestCase):
    def test_revocation_id_matches_existing_sha256_prefix_contract(self):
        revocation_message = {
            "revoked_fingerprint": "revoked-fp",
            "revoked_pubkey": "00aa11bb",
            "reason": "compromised",
            "revoked_at": "2026-04-03T12:00:00+00:00",
            "effective_at": "2026-04-04T12:00:00+00:00",
            "recovery_fingerprint": "recovery-fp",
        }
        message_bytes = json.dumps(revocation_message, sort_keys=True).encode()
        expected = hashlib.sha256(message_bytes).hexdigest()[:16]

        self.assertEqual(derive_revocation_id(message_bytes), expected)

    def test_empty_merkle_root_matches_existing_sha256_contract(self):
        self.assertEqual(derive_empty_merkle_root(), hashlib.sha256(b"empty").hexdigest())

    def test_merkle_leaf_matches_existing_sha256_contract(self):
        revocation = {
            "fingerprint": "revoked-fp",
            "effective_at": "2026-04-04T12:00:00+00:00",
            "signature": "deadbeef",
            "recovery_fingerprint": "recovery-fp",
        }
        expected = hashlib.sha256(json.dumps(revocation, sort_keys=True).encode()).digest()

        self.assertEqual(derive_merkle_leaf(revocation), expected)

    def test_merkle_node_matches_existing_sha256_contract(self):
        left = bytes.fromhex("11" * 32)
        right = bytes.fromhex("22" * 32)
        expected = hashlib.sha256(left + right).digest()

        self.assertEqual(derive_merkle_node(left, right), expected)


if __name__ == "__main__":
    unittest.main()
