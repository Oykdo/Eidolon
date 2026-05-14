import hashlib
import hmac
import unittest

from src.holo.alchemy_integration import AlchemyWebhookManager, derive_alchemy_webhook_signature


class AlchemyIntegrationContractTests(unittest.TestCase):
    def test_webhook_signature_matches_existing_hmac_sha256_contract(self):
        payload = b'{"event":"transfer","network":"eth-mainnet"}'
        signing_key = "alchemy-signing-key"
        expected = hmac.new(
            signing_key.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        self.assertEqual(derive_alchemy_webhook_signature(payload, signing_key), expected)

    def test_verify_signature_matches_existing_contract(self):
        payload = b'{"event":"transfer","network":"eth-mainnet"}'
        signing_key = "alchemy-signing-key"
        signature = hmac.new(
            signing_key.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        self.assertTrue(AlchemyWebhookManager.verify_signature(payload, signature, signing_key))
        self.assertFalse(AlchemyWebhookManager.verify_signature(payload, "00" * 32, signing_key))


if __name__ == "__main__":
    unittest.main()
