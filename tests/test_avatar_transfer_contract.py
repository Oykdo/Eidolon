import hashlib
import json
import unittest

from src.blockchain.avatar_transfer import derive_avatar_id, derive_chain_hash, derive_transfer_id


class AvatarTransferContractTests(unittest.TestCase):
    def test_transfer_id_matches_existing_sha256_prefix_contract(self):
        transfer_message = {
            "avatar_id": "avatar-001",
            "from_fingerprint": "from-fp",
            "to_fingerprint": "to-fp",
            "timestamp": "2026-04-03T12:00:00+00:00",
            "reason": "gift",
            "chain_hash": "chain-abc",
        }
        message_bytes = json.dumps(transfer_message, sort_keys=True).encode()
        expected = hashlib.sha256(message_bytes).hexdigest()[:16]

        self.assertEqual(derive_transfer_id(message_bytes), expected)

    def test_chain_hash_matches_existing_sha256_contract(self):
        chain_data = {
            "avatar_id": "avatar-001",
            "genesis_fingerprint": "genesis-fp",
            "genesis_timestamp": "2026-04-03T10:00:00+00:00",
            "current_owner": "owner-fp",
            "transfers": [
                {
                    "transfer_id": "abcd1234efgh5678",
                    "timestamp": "2026-04-03T12:00:00+00:00",
                }
            ],
        }
        chain_bytes = json.dumps(chain_data, sort_keys=True).encode()
        expected = hashlib.sha256(chain_bytes).hexdigest()

        self.assertEqual(derive_chain_hash(chain_bytes), expected)

    def test_avatar_id_matches_existing_sha256_prefix_contract(self):
        blend_data = {
            "format": "PSNX_BLEND_DATA",
            "version": 2,
            "scene": {"name": "TestAvatar"},
            "clusters": [],
            "materials": {},
        }
        expected = hashlib.sha256(
            json.dumps(blend_data, sort_keys=True).encode()
        ).hexdigest()[:16]

        self.assertEqual(derive_avatar_id(blend_data), expected)


if __name__ == "__main__":
    unittest.main()
