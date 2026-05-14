import hashlib
import unittest

from src.core.bitcoin_wallet import (
    BitcoinUtils,
    derive_btc_demo_signature,
    derive_btc_fallback_public_key,
    derive_btc_perpetual_salt,
    derive_btc_signed_message_hash,
)


class BitcoinWalletContractTests(unittest.TestCase):
    def test_sha256_matches_existing_contract(self):
        payload = b"bitcoin-contract-payload"
        expected = hashlib.sha256(payload).digest()

        self.assertEqual(BitcoinUtils.sha256(payload), expected)

    def test_hash256_matches_existing_double_sha256_contract(self):
        payload = b"bitcoin-double-sha256"
        expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()

        self.assertEqual(BitcoinUtils.hash256(payload), expected)

    def test_perpetual_salt_matches_existing_sha256_digest_prefix_contract(self):
        vault_key = b"bitcoin-wallet-vault-key"
        expected = hashlib.sha256(
            b"eidolon-btc-perpetual-salt:" + vault_key
        ).digest()[:16]

        self.assertEqual(derive_btc_perpetual_salt(vault_key), expected)

    def test_fallback_public_key_matches_existing_sha256_contract(self):
        private_key = b"bitcoin-private-key-fixture"
        expected = b"\x02" + hashlib.sha256(b"pubkey:" + private_key).digest()

        self.assertEqual(derive_btc_fallback_public_key(private_key), expected)

    def test_signed_message_hash_matches_existing_sha256_contract(self):
        message_bytes = b"hello bitcoin"
        expected = hashlib.sha256(
            b"\x18Bitcoin Signed Message:\n" +
            bytes([len(message_bytes)]) +
            message_bytes
        ).digest()

        self.assertEqual(derive_btc_signed_message_hash(message_bytes), expected)

    def test_demo_signature_matches_existing_sha256_contract(self):
        private_key = b"bitcoin-private-key-fixture"
        message_hash = bytes.fromhex("11" * 32)
        expected = hashlib.sha256(private_key + message_hash).hexdigest()

        self.assertEqual(derive_btc_demo_signature(private_key, message_hash), expected)


if __name__ == "__main__":
    unittest.main()
