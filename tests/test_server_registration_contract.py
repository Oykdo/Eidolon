import hashlib
import hmac
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.identity.server_registration import MachineIdentifier, ServerRegistrationClient


class ServerRegistrationContractTests(unittest.TestCase):
    def test_sign_request_matches_existing_hmac_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            with patch.object(ServerRegistrationClient, "_get_cache_dir", return_value=cache_dir):
                with patch.object(MachineIdentifier, "get_machine_id", return_value="node|user"):
                    client = ServerRegistrationClient(
                        server_url="http://unit.test",
                        api_secret="secret-key-001",
                    )

            payload = {"machine_hash": "abc123", "vault_number": 7, "action": "verify"}
            with patch("src.core.server_registration.time.time", return_value=1700000000):
                with patch("src.core.server_registration.secrets.token_hex", return_value="0011223344556677"):
                    signature = client._sign_request(payload)

        expected_payload = {
            "machine_hash": "abc123",
            "vault_number": 7,
            "action": "verify",
            "timestamp": 1700000000,
            "nonce": "0011223344556677",
        }
        expected_message = __import__("json").dumps(expected_payload, sort_keys=True).encode()
        expected_signature = hmac.new(
            b"secret-key-001",
            expected_message,
            hashlib.sha256,
        ).hexdigest()

        self.assertEqual(payload, expected_payload)
        self.assertEqual(signature, expected_signature)

    def test_client_uses_machine_lock_hash_contract(self):
        machine_id = "node|user|uuid"
        expected = MachineIdentifier.get_machine_hash(machine_id)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(ServerRegistrationClient, "_get_cache_dir", return_value=Path(tmp)):
                with patch.object(MachineIdentifier, "get_machine_id", return_value=machine_id):
                    client = ServerRegistrationClient(
                        server_url="http://unit.test",
                        api_secret="secret-key-001",
                    )
        self.assertEqual(client.get_machine_hash(), expected)


if __name__ == "__main__":
    unittest.main()
