import hashlib
import unittest

from src.blockchain.evm_wallet import VaultAssetManager, derive_evm_perpetual_salt


class EVMWalletContractTests(unittest.TestCase):
    def test_asset_id_matches_existing_sha256_prefix_contract(self):
        key = "ethereum:0xabc123:fungible"
        expected = hashlib.sha256(key.encode()).hexdigest()[:16]

        manager = object.__new__(VaultAssetManager)
        self.assertEqual(manager._derive_asset_id(key), expected)

    def test_perpetual_salt_matches_existing_sha256_digest_prefix_contract(self):
        vault_key = b"evm-wallet-vault-key"
        expected = hashlib.sha256(
            b"eidolon-evm-perpetual-salt:" + vault_key
        ).digest()[:16]

        self.assertEqual(derive_evm_perpetual_salt(vault_key), expected)


if __name__ == "__main__":
    unittest.main()
