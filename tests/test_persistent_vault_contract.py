import hashlib
import tempfile
import unittest
from pathlib import Path

from src.identity.persistent_vault import (
    PersistentVaultManager,
    derive_persistent_cli_vault_key,
    derive_persistent_document_hash,
    derive_persistent_generated_id,
)


class PersistentVaultContractTests(unittest.TestCase):
    def test_document_hash_matches_existing_sha256_contract(self):
        file_data = b"persistent-vault-document"
        expected = hashlib.sha256(file_data).hexdigest()

        self.assertEqual(derive_persistent_document_hash(file_data), expected)

    def test_cli_vault_key_matches_existing_sha256_digest_contract(self):
        vault_name = "contract_vault"
        expected = hashlib.sha256(vault_name.encode()).digest()

        self.assertEqual(derive_persistent_cli_vault_key(vault_name), expected)

    def test_generated_id_matches_existing_sha256_prefix_contract(self):
        data = {"kind": "asset", "name": "test"}
        timestamp_iso = "2026-04-03T12:34:56"
        expected = hashlib.sha256(f"{data}{timestamp_iso}".encode()).hexdigest()[:16]

        self.assertEqual(derive_persistent_generated_id(data, timestamp_iso), expected)

    def test_add_and_verify_document_preserve_existing_hash_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "vaults"
            source_file = Path(temp_dir) / "document.bin"
            source_file.write_bytes(b"vault-document-payload")

            manager = PersistentVaultManager(
                vault_key=b"0" * 32,
                vault_name="contract_vault",
                base_path=str(base_path),
            )

            doc_id = manager.add_document(str(source_file))
            doc_info = manager.get_document(doc_id)

            self.assertIsNotNone(doc_info)
            self.assertEqual(doc_info["hash"], hashlib.sha256(source_file.read_bytes()).hexdigest())
            self.assertTrue(manager.verify_document(doc_id))


if __name__ == "__main__":
    unittest.main()
