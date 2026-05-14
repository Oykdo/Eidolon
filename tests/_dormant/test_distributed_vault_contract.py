import asyncio
import sys
import tempfile
import unittest
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.distributed_vault import DistributedStorageManager, ShamirDistributor


class DistributedVaultContractTests(unittest.TestCase):
    def test_storage_manager_encrypt_decrypt_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = DistributedStorageManager(b"\x55" * 32, data_dir=tmp)
            encrypted, nonce = manager._encrypt_data(b"distributed-payload")
            self.assertEqual(encrypted[:12], nonce)
            self.assertEqual(
                manager._decrypt_data(encrypted, nonce),
                b"distributed-payload",
            )

    def test_node_share_encrypt_decrypt_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            distributor = ShamirDistributor(b"\x66" * 32, data_dir=tmp)
            encrypted = distributor._encrypt_for_node(b"share-bytes", "node-public-key")
            self.assertEqual(
                distributor._decrypt_from_node(encrypted, "node-public-key"),
                b"share-bytes",
            )

    def test_store_persists_hash_contract(self):
        class FakeIPFS:
            async def add(self, data: bytes, pin: bool = True) -> str:
                return "QmTestCid"

        with tempfile.TemporaryDirectory() as tmp:
            manager = DistributedStorageManager(b"\x77" * 32, data_dir=tmp)
            manager.ipfs = FakeIPFS()
            stored = asyncio.run(manager.store(b"vault-data"))
            self.assertEqual(stored.content_hash, "d427bc41c9e1b2417f4a61d466e647bee40d1ac9b68943b82052b5aaff902567")
            self.assertEqual(stored.encryption_key_hash, "e29442e61ad354e5")

    def test_ipfs_simulated_cid_matches_existing_sha256_contract(self):
        client_data = b"distributed-simulation"
        expected = "Qm" + hashlib.sha256(client_data).hexdigest()[:44]

        async def _run():
            with tempfile.TemporaryDirectory() as tmp:
                manager = DistributedStorageManager(b"\x88" * 32, data_dir=tmp)
                cid = await manager.ipfs.add(client_data, pin=True)
                return cid

        cid = asyncio.run(_run())
        self.assertEqual(cid, expected)


if __name__ == "__main__":
    unittest.main()
