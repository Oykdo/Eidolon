import tempfile
import unittest
import os
from pathlib import Path

from src.api.auth import ZKPAuthenticator
from src.api.client import VaultAPIClient
from src.api import server as api_server
from src.holo.runes_vesting import RunesVestingManager
from src.identity.vault_identity import VaultIdentityManager

try:
    from fastapi.testclient import TestClient

    TESTCLIENT_AVAILABLE = True
except ImportError:
    TESTCLIENT_AVAILABLE = False


@unittest.skipUnless(api_server.FASTAPI_AVAILABLE and TESTCLIENT_AVAILABLE, "FastAPI TestClient unavailable")
class APIHTTPContractTests(unittest.TestCase):
    def setUp(self):
        self.original_test_mode = os.environ.get("EIDOLON_TEST_MODE")
        os.environ["EIDOLON_TEST_MODE"] = "1"
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_dir = Path(self.temp_dir.name) / "identities"
        self.keys_dir = Path(self.temp_dir.name) / "keys"
        self.keys_dir.mkdir(parents=True, exist_ok=True)

        self.psnx_path = self.keys_dir / "vault.psnx"
        self.blend_path = self.keys_dir / "vault.blend_data"
        self.psnx_bytes = b"psnx-http-contract-material-v1"
        self.psnx_path.write_bytes(self.psnx_bytes)
        self.blend_path.write_bytes(b"blend-http-contract-material-v1")

        self.identity_manager = VaultIdentityManager(storage_dir=str(self.storage_dir))
        success, identity, message = self.identity_manager.register_vault(
            vault_name="http_contract_user",
            psnx_path=str(self.psnx_path),
            blend_path=str(self.blend_path),
            vault_key=b"http-contract-registration-key-32",
            vault_number=77,
        )
        self.assertTrue(success, message)
        self.assertIsNotNone(identity)
        self.identity = identity

        self.original_authenticator = api_server.authenticator
        self.original_identity_manager = api_server.vault_identity_manager
        self.original_get_vesting_manager = api_server._get_vesting_manager
        api_server.vault_identity_manager = self.identity_manager
        api_server.authenticator = ZKPAuthenticator(api_server.auth_config, identity_manager=self.identity_manager)
        self.vesting_storage = Path(self.temp_dir.name) / "runes_vesting"
        self.vesting_manager = RunesVestingManager(storage_path=self.vesting_storage)
        self.vesting_manager.create_vesting_schedule(
            self.identity.vault_id,
            self.identity.vault_number,
        )
        api_server._get_vesting_manager = lambda: RunesVestingManager(storage_path=self.vesting_storage)

        self.http = TestClient(api_server.app)
        self.client = VaultAPIClient(
            "http://testserver",
            psnx_path=str(self.psnx_path),
            vault_id=self.identity.vault_id,
        )
        self.client._client = self.http

    def tearDown(self):
        self.client.close()
        self.http.close()
        api_server.authenticator = self.original_authenticator
        api_server.vault_identity_manager = self.original_identity_manager
        api_server._get_vesting_manager = self.original_get_vesting_manager
        if self.original_test_mode is None:
            os.environ.pop("EIDOLON_TEST_MODE", None)
        else:
            os.environ["EIDOLON_TEST_MODE"] = self.original_test_mode
        self.temp_dir.cleanup()

    def test_http_psnx_enroll_and_login_flow(self):
        enroll_payload = self.client.enroll(vault_number=self.identity.vault_number)
        self.assertEqual(enroll_payload["schema_version"], "v1")
        self.assertEqual(enroll_payload["vault_id"], self.identity.vault_id)
        self.assertEqual(enroll_payload["vault_number"], self.identity.vault_number)
        self.assertEqual(enroll_payload["zkp_scheme"], "psnx_schnorr_v1")

        challenge_response = self.http.post(
            "/auth/challenge",
            json={"vault_id": self.identity.vault_id},
        )
        self.assertEqual(challenge_response.status_code, 200)
        challenge_payload = challenge_response.json()
        self.assertEqual(challenge_payload["schema_version"], "v1")
        self.assertEqual(challenge_payload["auth_mode"], "zkp_psnx")
        self.assertEqual(challenge_payload["vault_id"], self.identity.vault_id)
        self.assertIn("nonce", challenge_payload)

        session = self.client.login(cipher_account_id="cipher-acc-001")
        self.assertEqual(session.vault_id, self.identity.vault_id)
        self.assertEqual(session.vault_number, self.identity.vault_number)
        self.assertEqual(session.auth_strength, "zkp_psnx")
        self.assertEqual(session.cipher_account_id, "cipher-acc-001")

        vault_info_response = self.http.get(
            "/vault/info",
            headers={"Authorization": f"Bearer {session.access_token}"},
        )
        self.assertEqual(vault_info_response.status_code, 200)

        refresh_response = self.http.post(
            "/auth/refresh",
            json={"refresh_token": session.refresh_token},
        )
        self.assertEqual(refresh_response.status_code, 200)
        refresh_payload = refresh_response.json()
        self.assertEqual(refresh_payload["schema_version"], "v1")
        self.assertEqual(refresh_payload["token_type"], "bearer")
        self.assertIn("access_token", refresh_payload)

    def test_http_psnx_login_rejects_nonce_replay(self):
        self.client.enroll(vault_number=self.identity.vault_number)

        challenge_payload = self.http.post(
            "/auth/challenge",
            json={"vault_id": self.identity.vault_id},
        ).json()
        proof = self.client._psnx_auth.create_proof(challenge_payload["nonce"])

        first_login = self.http.post(
            "/auth/login",
            json={"vault_id": self.identity.vault_id, "proof": proof},
        )
        self.assertEqual(first_login.status_code, 200)

        second_login = self.http.post(
            "/auth/login",
            json={"vault_id": self.identity.vault_id, "proof": proof},
        )
        self.assertEqual(second_login.status_code, 401)
        self.assertIn("nonce", second_login.json()["detail"].lower())

    def test_http_psnx_claim_ledger_endpoints(self):
        self.client.enroll(vault_number=self.identity.vault_number)
        session = self.client.login(cipher_account_id="cipher-acc-claims")
        headers = {"Authorization": f"Bearer {session.access_token}"}

        get_response = self.http.get("/vault/psnx/claims", headers=headers)
        self.assertEqual(get_response.status_code, 200)
        get_payload = get_response.json()
        self.assertEqual(get_payload["schema_version"], "v1")
        self.assertEqual(get_payload["vault_id"], self.identity.vault_id)
        self.assertEqual(get_payload["claim_summary"]["claim_count"], 0)

        post_response = self.http.post(
            "/vault/psnx/claims",
            json={"record_now": True, "destination_btc_address": "bc1ptestclaim"},
            headers=headers,
        )
        self.assertEqual(post_response.status_code, 200)
        post_payload = post_response.json()
        self.assertEqual(post_payload["schema_version"], "v1")
        self.assertGreater(post_payload["amount_recorded"], 0)
        self.assertEqual(post_payload["claim"]["destination_btc_address"], "bc1ptestclaim")
        self.assertEqual(post_payload["claim_summary"]["claim_count"], 1)
        self.assertGreater(post_payload["claim_summary"]["recorded_offchain_amount"], 0)

    def test_http_protected_endpoint_requires_bearer_token(self):
        response = self.http.get("/vault/info")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Missing authorization header")


if __name__ == "__main__":
    unittest.main()
