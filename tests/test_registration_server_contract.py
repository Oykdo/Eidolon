import hashlib
import hmac
import json
import time
import unittest

from src.api import registration_server


@unittest.skipUnless(
    registration_server.FASTAPI_AVAILABLE and hasattr(registration_server, "verify_signature"),
    "registration server signature helper unavailable",
)
class RegistrationServerContractTests(unittest.TestCase):
    def test_verify_signature_accepts_matching_hmac(self):
        payload = {
            "machine_hash": "machine-alpha",
            "vault_number": 7,
            "vault_id": "vault-007",
            "action": "register",
        }
        timestamp = str(int(time.time()))
        message = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            registration_server.API_SECRET.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        self.assertTrue(
            registration_server.verify_signature(payload, signature, timestamp, "nonce-1")
        )

    def test_verify_signature_rejects_modified_signature(self):
        payload = {
            "machine_hash": "machine-alpha",
            "vault_number": 7,
            "vault_id": "vault-007",
            "action": "register",
        }
        timestamp = str(int(time.time()))
        message = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            registration_server.API_SECRET.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        tampered = ("0" if signature[0] != "0" else "1") + signature[1:]

        self.assertFalse(
            registration_server.verify_signature(payload, tampered, timestamp, "nonce-1")
        )

    def test_verify_signature_rejects_stale_timestamp(self):
        payload = {
            "machine_hash": "machine-alpha",
            "vault_number": 7,
            "vault_id": "vault-007",
            "action": "register",
        }
        stale_timestamp = str(int(time.time()) - 301)
        message = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            registration_server.API_SECRET.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        self.assertFalse(
            registration_server.verify_signature(payload, signature, stale_timestamp, "nonce-1")
        )

    def test_derive_transfer_code_matches_historical_sha256_prefix(self):
        frozen_now = 1712345678.25
        expected = hashlib.sha256(f"7{frozen_now}".encode()).hexdigest()[:16]

        self.assertEqual(
            registration_server.derive_transfer_code(7, frozen_now),
            expected,
        )


if __name__ == "__main__":
    unittest.main()
