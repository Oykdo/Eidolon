import tempfile
import unittest
import os
from pathlib import Path

import re
import time
from datetime import datetime, timedelta

from src.api.auth import ZKPAuthenticator
from src.api.client import VaultAPIClient
from src.api import server as api_server
from src.api.connect_registry import ConnectAppRegistry
from src.api.user_code import ClientRateLimiter, UserCodeIndex
from src.holo.runes_vesting import RunesVestingManager
from src.identity.vault_identity import VaultIdentity, VaultIdentityManager

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
        # Isoler TOUT ce qui passe par config/paths, pas seulement le registre.
        # register_vault() construit en interne un RunesVestingManager() et un
        # RuntimeSphereManager sans argument : sans cette variable ils ecrivent
        # dans les donnees reelles de la machine. C'est ainsi que le coffre #77
        # de cette fixture a seme 80 spheres dans %LOCALAPPDATA% et une
        # allocation de 42 000 PSNX dans le grand livre a chaque passe de tests.
        self.original_data_dir = os.environ.get("EIDOLON_DATA_DIR")
        os.environ["EIDOLON_DATA_DIR"] = self.temp_dir.name
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
        if self.original_data_dir is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = self.original_data_dir
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


USER_CODE_DISPLAY_RE = re.compile(r"^[ABCDEFGHJKMNPQRSTVWXYZ0-9]{4}-[ABCDEFGHJKMNPQRSTVWXYZ0-9]{4}$")


@unittest.skipUnless(api_server.FASTAPI_AVAILABLE and TESTCLIENT_AVAILABLE, "FastAPI TestClient unavailable")
class ConnectUserCodeHTTPContractTests(unittest.TestCase):
    """Short code (XXXX-XXXX) -> Connect session / local-proof challenge, on the full API.

    Same isolation pattern as ``test_connect_http_contract.py``: every
    module-level store the Connect routes read is swapped for a fresh one and
    restored afterwards, so codes never leak between tests.
    """

    SWAPPED = (
        "connect_app_registry",
        "vault_identity_manager",
        "connect_session_store",
        "oidc_client_registry",
        "oidc_consent_registry",
        "oidc_authorization_sessions",
        "oidc_authorization_codes",
        "oidc_local_proof_challenges",
        "connect_user_code_index",
        "connect_user_code_rate_limiter",
    )

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.saved = {name: getattr(api_server, name) for name in self.SWAPPED}
        api_server.connect_app_registry = ConnectAppRegistry(storage_dir=root)
        api_server.oidc_client_registry = api_server.OIDCClientRegistry(storage_dir=root / "oidc")
        api_server.oidc_consent_registry = api_server.ConsentGrantRegistry(storage_dir=root / "consents")
        identity_manager = VaultIdentityManager(storage_dir=root / "vaults")
        identity_manager.vaults["vault-123"] = VaultIdentity(
            vault_id="vault-123",
            vault_number=7,
            vault_name="Vault Seven",
            psnx_path="C:/vaults/vault.psnx",
            blend_path="C:/vaults/vault.blend",
            psnx_hash="hash_psnx",
            blend_hash="hash_blend",
            vault_key_hash="hash_key",
        )
        api_server.vault_identity_manager = identity_manager
        api_server.connect_session_store = {}
        api_server.oidc_authorization_sessions = {}
        api_server.oidc_authorization_codes = {}
        api_server.oidc_local_proof_challenges = {}
        api_server.connect_user_code_index = UserCodeIndex()
        api_server.connect_user_code_rate_limiter = ClientRateLimiter(
            max_calls=api_server.CONNECT_CODE_RESOLVE_MAX_PER_MINUTE,
            window_seconds=60,
        )
        self.http = TestClient(api_server.app)
        self.http.post(
            "/connect/apps/register",
            json={"app_id": "cipher.desktop", "app_name": "Cipher Desktop", "scopes": ["auth", "read_public_identity"]},
        )
        approved = self.http.post("/connect/apps/cipher.desktop/approve", json={})
        self.assertEqual(approved.status_code, 200, approved.text)

    def tearDown(self):
        self.http.close()
        for name, value in self.saved.items():
            setattr(api_server, name, value)
        self.temp_dir.cleanup()

    # -- helpers -----------------------------------------------------------

    def _create_session(self) -> dict:
        response = self.http.post(
            "/connect/sessions",
            json={"app_id": "cipher.desktop", "vault_id": "vault-123", "vault_number": 7, "vault_name": "Vault Seven"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _resolve(self, code: str):
        return self.http.post("/connect/code/resolve", json={"user_code": code})

    def _create_local_proof_challenge(self) -> tuple:
        self.http.post(
            "/oidc/clients/register",
            json={
                "client_id": "amazon.web",
                "client_name": "Amazon Web",
                "redirect_uris": ["https://amazon.example/callback"],
                "allowed_scopes": ["openid", "profile", "vault.basic"],
            },
        )
        authorize = self.http.get(
            "/authorize",
            params={
                "response_type": "code",
                "client_id": "amazon.web",
                "redirect_uri": "https://amazon.example/callback",
                "scope": "openid profile vault.basic",
                "state": "state-123",
                "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                "code_challenge_method": "S256",
                "nonce": "nonce-123",
            },
        )
        self.assertEqual(authorize.status_code, 202, authorize.text)
        session = authorize.json()
        challenge = self.http.post(f"/oidc/local-proof/challenge/{session['session_id']}")
        self.assertEqual(challenge.status_code, 200, challenge.text)
        return session, challenge.json()

    @staticmethod
    def _local_proof_signature(session_id: str, challenge_id: str, challenge_token: str, vault_id: str) -> str:
        import hashlib
        import hmac

        vault = api_server.vault_identity_manager.get_vault(vault_id)
        try:
            verifier_secret = bytes.fromhex(vault.vault_key_hash)
        except ValueError:
            verifier_secret = vault.vault_key_hash.encode("utf-8")
        payload = f"{session_id}:{challenge_id}:{challenge_token}:{vault_id}".encode("utf-8")
        return hmac.new(verifier_secret, payload, hashlib.sha256).hexdigest()

    # -- sessions ----------------------------------------------------------

    def test_user_code_present_on_connect_session_create(self):
        created = self._create_session()
        self.assertRegex(created["user_code"], USER_CODE_DISPLAY_RE)
        self.assertEqual(created["user_code_expires_at"], created["expires_at"])

    def test_user_code_resolves_to_session_without_consuming_it(self):
        created = self._create_session()
        for _ in range(2):
            response = self._resolve(created["user_code"])
            self.assertEqual(response.status_code, 200, response.text)
            payload = response.json()
            self.assertEqual(payload["schema_version"], "v1")
            self.assertEqual(payload["kind"], "session")
            self.assertEqual(payload["session_id"], created["session_id"])
            self.assertIsNone(payload["challenge_id"])
            self.assertEqual(payload["expires_at"], created["expires_at"])

        exchanged = self.http.post(
            "/connect/sessions/exchange",
            json={"app_id": "cipher.desktop", "session_id": created["session_id"]},
        )
        self.assertEqual(exchanged.status_code, 200, exchanged.text)

    def test_user_code_resolve_is_lenient_on_case_separators_o_and_zero(self):
        created = self._create_session()
        raw = created["user_code"].replace("-", "")
        typed = raw.lower().replace("0", "o").replace("1", "i")
        response = self._resolve(f" {typed[:4]} - {typed[4:]} ")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["session_id"], created["session_id"])

    def test_user_code_unknown_returns_generic_404(self):
        self._create_session()
        response = self._resolve("ZZZZ-9999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Unknown or expired code")

    def test_user_code_is_invalidated_once_session_is_exchanged(self):
        created = self._create_session()
        self.http.post(
            "/connect/sessions/exchange",
            json={"app_id": "cipher.desktop", "session_id": created["session_id"]},
        )
        self.assertEqual(self._resolve(created["user_code"]).status_code, 404)

    def test_user_code_expired_returns_404(self):
        created = self._create_session()
        raw = created["user_code"].replace("-", "")
        api_server.connect_user_code_index._entries[raw].expires_at = time.time() - 1
        self.assertEqual(self._resolve(created["user_code"]).status_code, 404)

        created = self._create_session()
        record = api_server.connect_session_store[created["session_id"]]
        record.expires_at = (datetime.utcnow() - timedelta(seconds=1)).isoformat()
        self.assertEqual(self._resolve(created["user_code"]).status_code, 404)
        self.assertNotIn(created["user_code"].replace("-", ""), api_server.connect_user_code_index._entries)

    def test_user_code_resolve_is_rate_limited_per_client_ip(self):
        for _ in range(api_server.CONNECT_CODE_RESOLVE_MAX_PER_MINUTE):
            self.assertEqual(self._resolve("AAAA-AAAA").status_code, 404)
        limited = self._resolve("AAAA-AAAA")
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited.json()["detail"], "Too many requests")

    # -- local proof -------------------------------------------------------

    def test_user_code_present_on_local_proof_challenge_and_resolves_until_completed(self):
        session, challenge = self._create_local_proof_challenge()
        self.assertRegex(challenge["user_code"], USER_CODE_DISPLAY_RE)
        self.assertEqual(challenge["user_code_expires_at"], challenge["expires_at"])

        resolved = self._resolve(challenge["user_code"])
        self.assertEqual(resolved.status_code, 200, resolved.text)
        payload = resolved.json()
        self.assertEqual(payload["kind"], "local_proof")
        self.assertEqual(payload["session_id"], session["session_id"])
        self.assertEqual(payload["challenge_id"], challenge["challenge_id"])
        self.assertEqual(payload["expires_at"], challenge["expires_at"])

        completed = self.http.post(
            "/oidc/local-proof/complete",
            json={
                "session_id": session["session_id"],
                "challenge_id": challenge["challenge_id"],
                "challenge_token": challenge["challenge_token"],
                "vault_id": "vault-123",
                "proof_signature": self._local_proof_signature(
                    session["session_id"], challenge["challenge_id"], challenge["challenge_token"], "vault-123"
                ),
                "approve_consent": True,
            },
        )
        self.assertEqual(completed.status_code, 200, completed.text)
        self.assertEqual(self._resolve(challenge["user_code"]).status_code, 404)


if __name__ == "__main__":
    unittest.main()
