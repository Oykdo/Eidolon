import base64
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.interoperability import BrowserPluginAPI, PSNXKeyManager, SignalAdapter


class InteroperabilityContractTests(unittest.TestCase):
    def test_identity_fingerprint_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = PSNXKeyManager(tmp)
            identity = manager.generate_identity("Alice")
            loaded = manager.get_identity(identity.identity_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.fingerprint, identity.fingerprint)
            self.assertEqual(len(identity.fingerprint.replace(" ", "")), 40)

    def test_signal_session_derivation_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = PSNXKeyManager(tmp)
            local = manager.generate_identity("Local")
            remote = manager.generate_identity("Remote")
            bundle = SignalAdapter(manager).create_signal_bundle(remote.identity_id)
            self.assertIsNotNone(bundle)

            signal = SignalAdapter(manager)
            secret1 = signal.establish_session(local.identity_id, bundle)
            secret2 = signal.establish_session(local.identity_id, bundle)
            self.assertEqual(secret1, secret2)
            self.assertEqual(len(secret1), 32)

    def test_browser_encryption_round_trip_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = PSNXKeyManager(tmp)
            identity = manager.generate_identity("Bob")
            api = BrowserPluginAPI(manager)
            session_id = api.create_session("https://example.test")
            self.assertTrue(api.request_permission(session_id, "encrypt_message"))

            payload = api.encrypt_for_recipient(
                session_id,
                identity.identity_key.public_key,
                "hello interoperable world",
            )
            self.assertIsNotNone(payload)
            self.assertEqual(sorted(payload.keys()), ["ciphertext", "ephemeral_key", "nonce"])

            nonce = base64.b64decode(payload["nonce"])
            ciphertext = base64.b64decode(payload["ciphertext"])
            ephemeral_key = base64.b64decode(payload["ephemeral_key"])
            self.assertEqual(len(nonce), 12)
            self.assertEqual(len(ephemeral_key), 32)
            self.assertGreater(len(ciphertext), len("hello interoperable world"))


if __name__ == "__main__":
    unittest.main()
