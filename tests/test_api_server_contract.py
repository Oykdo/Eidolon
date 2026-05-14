import hashlib
import unittest

from src.api import server as api_server


class APIServerContractTests(unittest.TestCase):
    def test_derive_demo_vault_key_matches_historical_sha256_digest(self):
        user_id = "api-contract-user"
        expected = hashlib.sha256(user_id.encode()).digest()

        self.assertEqual(api_server.derive_demo_vault_key(user_id), expected)

    def test_demo_payload_helpers_preserve_aes_gcm_split_contract(self):
        key = api_server.derive_demo_vault_key("api-contract-user")
        nonce = bytes.fromhex("00112233445566778899aabb")
        payload = b"api-demo-payload"

        ciphertext, tag = api_server.encrypt_demo_payload(key, payload, nonce)

        expected = api_server.aes_gcm_encrypt(key, nonce, payload)
        self.assertEqual(expected[:12], nonce)
        self.assertEqual(expected[12:-16], ciphertext)
        self.assertEqual(expected[-16:], tag)
        self.assertEqual(
            api_server.decrypt_demo_payload(key, nonce, ciphertext, tag),
            payload,
        )


if __name__ == "__main__":
    unittest.main()
