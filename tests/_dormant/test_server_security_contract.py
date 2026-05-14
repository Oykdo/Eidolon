import hashlib
import hmac
import json
import unittest

from src.server import security


class ServerSecurityContractTests(unittest.TestCase):
    def test_verify_signature_accepts_matching_hmac(self):
        payload = {
            "machine_hash": "machine-beta",
            "vault_number": 12,
            "action": "verify",
        }
        message = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            security.settings.api_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        self.assertTrue(security.verify_signature(payload, signature))

    def test_verify_signature_rejects_modified_signature(self):
        payload = {
            "machine_hash": "machine-beta",
            "vault_number": 12,
            "action": "verify",
        }
        message = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            security.settings.api_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        tampered = signature[:-1] + ("0" if signature[-1] != "0" else "1")

        self.assertFalse(security.verify_signature(payload, tampered))


if __name__ == "__main__":
    unittest.main()
