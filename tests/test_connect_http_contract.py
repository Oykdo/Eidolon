import tempfile
import unittest
import hashlib
import hmac
from pathlib import Path
from unittest.mock import patch

from src.api import server as api_server
from src.api.connect_registry import ConnectAppRegistry
from src.identity.vault_identity import VaultIdentity, VaultIdentityManager

try:
    from fastapi.testclient import TestClient

    TESTCLIENT_AVAILABLE = True
except ImportError:
    TESTCLIENT_AVAILABLE = False


@unittest.skipUnless(api_server.FASTAPI_AVAILABLE and TESTCLIENT_AVAILABLE, "FastAPI TestClient unavailable")
class ConnectHTTPContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_registry = api_server.connect_app_registry
        self.original_identity_manager = api_server.vault_identity_manager
        self.original_session_store = api_server.connect_session_store
        self.original_oidc_client_registry = api_server.oidc_client_registry
        self.original_oidc_consent_registry = api_server.oidc_consent_registry
        self.original_oidc_partner_onboarding_registry = api_server.oidc_partner_onboarding_registry
        self.original_oidc_hosted_account_registry = api_server.oidc_hosted_account_registry
        self.original_oidc_hosted_login_session_registry = api_server.oidc_hosted_login_session_registry
        self.original_oidc_authorization_sessions = api_server.oidc_authorization_sessions
        self.original_oidc_authorization_codes = api_server.oidc_authorization_codes
        self.original_oidc_local_proof_challenges = api_server.oidc_local_proof_challenges
        self.original_admin_secret = api_server.runtime_config.admin_secret
        self.original_connect_secret = api_server.runtime_config.connect_session_secret
        api_server.connect_app_registry = ConnectAppRegistry(storage_dir=Path(self.temp_dir.name))
        api_server.oidc_client_registry = api_server.OIDCClientRegistry(storage_dir=Path(self.temp_dir.name) / "oidc")
        api_server.oidc_consent_registry = api_server.ConsentGrantRegistry(storage_dir=Path(self.temp_dir.name) / "consents")
        api_server.oidc_partner_onboarding_registry = api_server.PartnerOnboardingRegistry(storage_dir=Path(self.temp_dir.name) / "onboarding")
        api_server.oidc_hosted_account_registry = api_server.HostedAccountRegistry(storage_dir=Path(self.temp_dir.name) / "hosted-accounts")
        api_server.oidc_hosted_login_session_registry = api_server.HostedLoginSessionRegistry(storage_dir=Path(self.temp_dir.name) / "hosted-sessions")
        identity_manager = VaultIdentityManager(storage_dir=Path(self.temp_dir.name) / "vaults")
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
        self.http = TestClient(api_server.app)

    def tearDown(self):
        self.http.close()
        api_server.connect_app_registry = self.original_registry
        api_server.vault_identity_manager = self.original_identity_manager
        api_server.connect_session_store = self.original_session_store
        api_server.oidc_client_registry = self.original_oidc_client_registry
        api_server.oidc_consent_registry = self.original_oidc_consent_registry
        api_server.oidc_partner_onboarding_registry = self.original_oidc_partner_onboarding_registry
        api_server.oidc_hosted_account_registry = self.original_oidc_hosted_account_registry
        api_server.oidc_hosted_login_session_registry = self.original_oidc_hosted_login_session_registry
        api_server.oidc_authorization_sessions = self.original_oidc_authorization_sessions
        api_server.oidc_authorization_codes = self.original_oidc_authorization_codes
        api_server.oidc_local_proof_challenges = self.original_oidc_local_proof_challenges
        api_server.runtime_config.admin_secret = self.original_admin_secret
        api_server.runtime_config.connect_session_secret = self.original_connect_secret
        self.temp_dir.cleanup()

    def _build_local_proof_signature(self, session_id: str, challenge_id: str, challenge_token: str, vault_id: str) -> str:
        vault = api_server.vault_identity_manager.get_vault(vault_id)
        self.assertIsNotNone(vault)
        try:
            verifier_secret = bytes.fromhex(vault.vault_key_hash)
        except ValueError:
            verifier_secret = vault.vault_key_hash.encode("utf-8")
        payload = f"{session_id}:{challenge_id}:{challenge_token}:{vault_id}".encode("utf-8")
        return hmac.new(verifier_secret, payload, hashlib.sha256).hexdigest()

    def _build_hosted_password_verifier(self, salt: str, password: str) -> str:
        return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()

    def test_register_connect_app_returns_pending_consent_contract(self):
        response = self.http.post(
            "/connect/apps/register",
            json={
                "app_id": "cipher.desktop",
                "app_name": "Cipher Desktop",
                "scopes": ["encrypt", "auth"],
                "display_origin": "cipher://desktop",
                "redirect_uri": "cipher://callback",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["schema_version"], "v1")
        self.assertEqual(payload["app_id"], "cipher.desktop")
        self.assertEqual(payload["requested_scopes"], ["auth", "encrypt"])
        self.assertEqual(payload["granted_scopes"], [])
        self.assertTrue(payload["consent_required"])
        self.assertEqual(payload["status"], "pending_consent")

    def test_register_connect_app_rejects_unknown_scope(self):
        response = self.http.post(
            "/connect/apps/register",
            json={
                "app_id": "cipher.desktop",
                "app_name": "Cipher Desktop",
                "scopes": ["auth", "root"],
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported Eidolon Connect scopes", response.json()["detail"])

    def test_get_connect_capabilities_returns_stable_contract(self):
        response = self.http.get("/connect/capabilities")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["schema_version"], "v1")
        self.assertEqual(
            payload["capabilities"],
            ["auth", "encrypt", "decrypt", "sign", "derive_key", "read_public_identity"],
        )
        self.assertTrue(payload["consent_required"])
        self.assertTrue(payload["app_scoped_keys"])
        self.assertFalse(payload["raw_vault_key_export"])

    def test_get_connect_app_status_returns_registration_state(self):
        self.http.post(
            "/connect/apps/register",
            json={
                "app_id": "cipher.desktop",
                "app_name": "Cipher Desktop",
                "scopes": ["encrypt", "auth"],
            },
        )
        response = self.http.get("/connect/apps/cipher.desktop")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["app_id"], "cipher.desktop")
        self.assertEqual(payload["requested_scopes"], ["auth", "encrypt"])
        self.assertEqual(payload["status"], "pending_consent")

    def test_get_connect_app_status_returns_404_for_unknown_app(self):
        response = self.http.get("/connect/apps/unknown.app")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Connect app not found")

    def test_create_and_exchange_connect_session_contract(self):
        self.http.post(
            "/connect/apps/register",
            json={
                "app_id": "cipher.desktop",
                "app_name": "Cipher Desktop",
                "scopes": ["auth", "read_public_identity"],
            },
        )
        self.http.post(
            "/connect/apps/cipher.desktop/approve",
            json={},
        )

        create_response = self.http.post(
            "/connect/sessions",
            json={
                "app_id": "cipher.desktop",
                "vault_id": "vault-123",
                "vault_number": 7,
                "vault_name": "Vault Seven",
                "source": "cipher-desktop",
            },
        )
        self.assertEqual(create_response.status_code, 200)
        created = create_response.json()
        self.assertEqual(created["schema_version"], "v1")
        self.assertEqual(created["app_id"], "cipher.desktop")
        self.assertEqual(created["vault_id"], "vault-123")
        self.assertEqual(created["vault_number"], 7)
        self.assertEqual(created["vault_name"], "Vault Seven")
        self.assertEqual(created["status"], "approved")
        self.assertTrue(created["session_id"])

        exchange_response = self.http.post(
            "/connect/sessions/exchange",
            json={
                "app_id": "cipher.desktop",
                "session_id": created["session_id"],
            },
        )
        self.assertEqual(exchange_response.status_code, 200)
        exchanged = exchange_response.json()
        self.assertEqual(exchanged["schema_version"], "v1")
        self.assertEqual(exchanged["app_id"], "cipher.desktop")
        self.assertEqual(exchanged["vault_id"], "vault-123")
        self.assertEqual(exchanged["vault_number"], 7)
        self.assertEqual(exchanged["vault_name"], "Vault Seven")
        self.assertEqual(exchanged["auth_context"], "eidolon_connect_session")

    def test_connect_session_exchange_is_one_time(self):
        self.http.post(
            "/connect/apps/register",
            json={
                "app_id": "cipher.desktop",
                "app_name": "Cipher Desktop",
                "scopes": ["auth"],
            },
        )
        self.http.post(
            "/connect/apps/cipher.desktop/approve",
            json={},
        )
        created = self.http.post(
            "/connect/sessions",
            json={
                "app_id": "cipher.desktop",
                "vault_id": "vault-123",
            },
        ).json()

        first_exchange = self.http.post(
            "/connect/sessions/exchange",
            json={"app_id": "cipher.desktop", "session_id": created["session_id"]},
        )
        self.assertEqual(first_exchange.status_code, 200)

        second_exchange = self.http.post(
            "/connect/sessions/exchange",
            json={"app_id": "cipher.desktop", "session_id": created["session_id"]},
        )
        self.assertEqual(second_exchange.status_code, 404)
        self.assertEqual(second_exchange.json()["detail"], "Connect session not found")

    def test_create_connect_session_requires_approved_app(self):
        self.http.post(
            "/connect/apps/register",
            json={
                "app_id": "cipher.desktop",
                "app_name": "Cipher Desktop",
                "scopes": ["auth"],
            },
        )

        response = self.http.post(
            "/connect/sessions",
            json={
                "app_id": "cipher.desktop",
                "vault_id": "vault-123",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("requires explicit approval", response.json()["detail"])

    def test_approve_and_revoke_connect_app(self):
        self.http.post(
            "/connect/apps/register",
            json={
                "app_id": "cipher.desktop",
                "app_name": "Cipher Desktop",
                "scopes": ["auth", "read_public_identity"],
            },
        )

        approve_response = self.http.post(
            "/connect/apps/cipher.desktop/approve",
            json={"granted_scopes": ["auth"]},
        )
        self.assertEqual(approve_response.status_code, 200)
        approved = approve_response.json()
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["granted_scopes"], ["auth"])

        revoke_response = self.http.post("/connect/apps/cipher.desktop/revoke")
        self.assertEqual(revoke_response.status_code, 200)
        revoked = revoke_response.json()
        self.assertEqual(revoked["status"], "pending_consent")
        self.assertEqual(revoked["granted_scopes"], [])

    def test_approve_requires_local_operator_or_admin_secret(self):
        self.http.post(
            "/connect/apps/register",
            json={
                "app_id": "cipher.desktop",
                "app_name": "Cipher Desktop",
                "scopes": ["auth"],
            },
        )
        api_server.runtime_config.admin_secret = "admin-secret"

        with patch.object(api_server, "is_loopback_client", return_value=False):
            forbidden = self.http.post(
                "/connect/apps/cipher.desktop/approve",
                json={},
            )
            self.assertEqual(forbidden.status_code, 403)

            allowed = self.http.post(
                "/connect/apps/cipher.desktop/approve",
                json={},
                headers={"X-Eidolon-Admin-Secret": "admin-secret"},
            )
            self.assertEqual(allowed.status_code, 200)
            self.assertEqual(allowed.json()["status"], "approved")

    def test_create_connect_session_requires_local_host_or_shared_secret(self):
        self.http.post(
            "/connect/apps/register",
            json={
                "app_id": "cipher.desktop",
                "app_name": "Cipher Desktop",
                "scopes": ["auth"],
            },
        )
        self.http.post("/connect/apps/cipher.desktop/approve", json={})
        api_server.runtime_config.connect_session_secret = "connect-secret"

        with patch.object(api_server, "is_loopback_client", return_value=False):
            forbidden = self.http.post(
                "/connect/sessions",
                json={
                    "app_id": "cipher.desktop",
                    "vault_id": "vault-123",
                },
            )
            self.assertEqual(forbidden.status_code, 403)

            allowed = self.http.post(
                "/connect/sessions",
                json={
                    "app_id": "cipher.desktop",
                    "vault_id": "vault-123",
                },
                headers={"X-Eidolon-Connect-Secret": "connect-secret"},
            )
            self.assertEqual(allowed.status_code, 200)
            self.assertEqual(allowed.json()["app_id"], "cipher.desktop")

    def test_partner_onboarding_flow_returns_pending_review_contract(self):
        response = self.http.post(
            "/oidc/partners/onboarding",
            json={
                "partner_name": "Amazon Web",
                "contact_email": "dev@amazon.example",
                "requested_client_id": "amazon.web",
                "redirect_uris": ["https://amazon.example/callback"],
                "requested_scopes": ["openid", "profile", "vault.basic"],
                "integration_notes": "Need Sign in with Eidolon for account linking.",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["request_id"], "por_amazon.web")
        self.assertEqual(payload["status"], "pending_review")
        self.assertEqual(payload["requested_client_id"], "amazon.web")
        self.assertEqual(payload["requested_scopes"], ["openid", "profile", "vault.basic"])
        self.assertIn("display_name", payload["claims_supported"])
        self.assertTrue(payload["next_steps"])

        fetched = self.http.get("/oidc/partners/onboarding/por_amazon.web")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["contact_email"], "dev@amazon.example")

        audit = self.http.get("/oidc/audit/events")
        self.assertEqual(audit.status_code, 200)
        self.assertEqual(audit.json()[0]["event_type"], "oidc.partner.onboarding_submitted")

    def test_partner_onboarding_rejects_unknown_scope(self):
        response = self.http.post(
            "/oidc/partners/onboarding",
            json={
                "partner_name": "Amazon Web",
                "contact_email": "dev@amazon.example",
                "requested_client_id": "amazon.web",
                "redirect_uris": ["https://amazon.example/callback"],
                "requested_scopes": ["openid", "admin.root"],
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported Eidolon OIDC scopes", response.json()["detail"])

    def test_oidc_client_admin_endpoints_list_get_and_update_clients(self):
        registered = self.http.post(
            "/oidc/clients/register",
            json={
                "client_id": "amazon.web",
                "client_name": "Amazon Web",
                "redirect_uris": ["https://amazon.example/callback"],
                "allowed_scopes": ["openid", "profile"],
                "environment": "sandbox",
                "branding_name": "Amazon Login",
                "consent_text": "Share your Eidolon profile with Amazon.",
            },
        )
        self.assertEqual(registered.status_code, 200)
        self.assertIsNotNone(registered.json()["created_at"])
        self.assertEqual(registered.json()["environment"], "sandbox")

        listed = self.http.get("/oidc/clients")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)
        self.assertEqual(listed.json()[0]["client_id"], "amazon.web")

        fetched = self.http.get("/oidc/clients/amazon.web")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["client_name"], "Amazon Web")

        updated = self.http.put(
            "/oidc/clients/amazon.web",
            json={
                "client_name": "Amazon Marketplace",
                "redirect_uris": ["https://amazon.example/oidc/callback"],
                "allowed_scopes": ["openid", "vault.basic"],
                "client_type": "public",
                "token_endpoint_auth_method": "none",
                "logo_uri": "https://amazon.example/logo.png",
                "policy_uri": "https://amazon.example/privacy",
                "environment": "production",
                "branding_name": "Amazon Identity",
                "consent_text": "Share your Eidolon profile with Amazon Identity.",
                "status": "active",
            },
        )
        self.assertEqual(updated.status_code, 200)
        body = updated.json()
        self.assertEqual(body["client_name"], "Amazon Marketplace")
        self.assertEqual(body["redirect_uris"], ["https://amazon.example/oidc/callback"])
        self.assertEqual(body["allowed_scopes"], ["openid", "vault.basic"])
        self.assertEqual(body["logo_uri"], "https://amazon.example/logo.png")
        self.assertEqual(body["environment"], "production")
        self.assertEqual(body["branding_name"], "Amazon Identity")
        self.assertIsNotNone(body["updated_at"])

    def test_oidc_client_admin_endpoints_require_admin_access(self):
        self.http.post(
            "/oidc/clients/register",
            json={
                "client_id": "amazon.web",
                "client_name": "Amazon Web",
                "redirect_uris": ["https://amazon.example/callback"],
                "allowed_scopes": ["openid"],
            },
        )
        api_server.runtime_config.admin_secret = "admin-secret"

        with patch.object(api_server, "is_loopback_client", return_value=False):
            forbidden_list = self.http.get("/oidc/clients")
            self.assertEqual(forbidden_list.status_code, 403)

            allowed_list = self.http.get(
                "/oidc/clients",
                headers={"X-Eidolon-Admin-Secret": "admin-secret"},
            )
            self.assertEqual(allowed_list.status_code, 200)

            forbidden_update = self.http.put(
                "/oidc/clients/amazon.web",
                json={
                    "client_name": "Amazon Marketplace",
                    "redirect_uris": ["https://amazon.example/oidc/callback"],
                    "allowed_scopes": ["openid"],
                    "client_type": "public",
                    "token_endpoint_auth_method": "none",
                    "status": "active",
                },
            )
            self.assertEqual(forbidden_update.status_code, 403)

    def test_confidential_client_token_flow_requires_client_secret(self):
        registered = self.http.post(
            "/oidc/clients/register",
            json={
                "client_id": "amazon.server",
                "client_name": "Amazon Server",
                "redirect_uris": ["https://amazon.example/callback"],
                "allowed_scopes": ["openid", "profile"],
                "client_type": "confidential",
                "token_endpoint_auth_method": "client_secret_post",
            },
        )
        self.assertEqual(registered.status_code, 200)
        self.assertTrue(registered.json()["client_secret_issued"])

        secret_response = self.http.post("/oidc/clients/amazon.server/rotate-secret")
        self.assertEqual(secret_response.status_code, 200)
        client_secret = secret_response.json()["client_secret"]

        with patch.dict("os.environ", {"EIDOLON_TEST_MODE": "1"}, clear=False):
            authorize = self.http.get(
                "/authorize",
                params={
                    "response_type": "code",
                    "client_id": "amazon.server",
                    "redirect_uri": "https://amazon.example/callback",
                    "scope": "openid profile",
                    "state": "state-123",
                    "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                    "code_challenge_method": "S256",
                    "login_hint": "vault:vault-123",
                },
                follow_redirects=False,
            )
        code = authorize.headers["location"].split("code=", 1)[1].split("&", 1)[0]

        missing_secret = self.http.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "https://amazon.example/callback",
                "client_id": "amazon.server",
                "code_verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
            },
        )
        self.assertEqual(missing_secret.status_code, 401)
        self.assertEqual(missing_secret.json()["detail"], "client_secret is required for confidential clients")

        with patch.dict("os.environ", {"EIDOLON_TEST_MODE": "1"}, clear=False):
            authorize2 = self.http.get(
                "/authorize",
                params={
                    "response_type": "code",
                    "client_id": "amazon.server",
                    "redirect_uri": "https://amazon.example/callback",
                    "scope": "openid profile",
                    "state": "state-124",
                    "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                    "code_challenge_method": "S256",
                    "login_hint": "vault:vault-123",
                },
                follow_redirects=False,
            )
        code2 = authorize2.headers["location"].split("code=", 1)[1].split("&", 1)[0]
        token = self.http.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": code2,
                "redirect_uri": "https://amazon.example/callback",
                "client_id": "amazon.server",
                "client_secret": client_secret,
                "code_verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
            },
        )
        self.assertEqual(token.status_code, 200)

        audit = self.http.get("/oidc/audit/events")
        self.assertEqual(audit.status_code, 200)
        event_types = [event["event_type"] for event in audit.json()]
        self.assertIn("oidc.client.secret_rotated", event_types)
        self.assertIn("oidc.token.exchanged", event_types)

    def test_discovery_exposes_eidolon_environment(self):
        discovery = self.http.get("/.well-known/openid-configuration")
        self.assertEqual(discovery.status_code, 200)
        self.assertEqual(discovery.json()["eidolon_environment"], "sandbox")

    def test_public_client_must_not_send_client_secret(self):
        self.http.post(
            "/oidc/clients/register",
            json={
                "client_id": "amazon.web",
                "client_name": "Amazon Web",
                "redirect_uris": ["https://amazon.example/callback"],
                "allowed_scopes": ["openid", "profile"],
            },
        )
        with patch.dict("os.environ", {"EIDOLON_TEST_MODE": "1"}, clear=False):
            authorize = self.http.get(
                "/authorize",
                params={
                    "response_type": "code",
                    "client_id": "amazon.web",
                    "redirect_uri": "https://amazon.example/callback",
                    "scope": "openid profile",
                    "state": "state-123",
                    "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                    "code_challenge_method": "S256",
                    "login_hint": "vault:vault-123",
                },
                follow_redirects=False,
            )
        code = authorize.headers["location"].split("code=", 1)[1].split("&", 1)[0]
        token = self.http.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "https://amazon.example/callback",
                "client_id": "amazon.web",
                "client_secret": "should-not-be-sent",
                "code_verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
            },
        )
        self.assertEqual(token.status_code, 400)
        self.assertEqual(token.json()["detail"], "Public clients must not send client_secret")

    def test_oidc_discovery_authorize_token_and_userinfo_contract(self):
        response = self.http.post(
            "/oidc/clients/register",
            json={
                "client_id": "amazon.web",
                "client_name": "Amazon Web",
                "redirect_uris": ["https://amazon.example/callback"],
                "allowed_scopes": ["openid", "profile", "vault.basic"],
            },
        )
        self.assertEqual(response.status_code, 200)
        registered = response.json()
        self.assertEqual(registered["client_id"], "amazon.web")
        self.assertEqual(registered["allowed_scopes"], ["openid", "profile", "vault.basic"])

        discovery = self.http.get("/.well-known/openid-configuration")
        self.assertEqual(discovery.status_code, 200)
        discovery_payload = discovery.json()
        self.assertEqual(discovery_payload["response_types_supported"], ["code"])
        self.assertIn("vault.basic", discovery_payload["scopes_supported"])

        jwks = self.http.get("/jwks.json")
        self.assertEqual(jwks.status_code, 200)
        self.assertEqual(jwks.json()["keys"][0]["alg"], "RS256")

        with patch.dict("os.environ", {"EIDOLON_TEST_MODE": "1"}, clear=False):
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
                    "login_hint": "vault:vault-123",
                },
                follow_redirects=False,
            )
        self.assertEqual(authorize.status_code, 302)
        location = authorize.headers["location"]
        self.assertIn("https://amazon.example/callback", location)
        self.assertIn("code=", location)
        self.assertIn("state=state-123", location)
        code = location.split("code=", 1)[1].split("&", 1)[0]

        token = self.http.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "https://amazon.example/callback",
                "client_id": "amazon.web",
                "code_verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
            },
        )
        self.assertEqual(token.status_code, 200)
        token_payload = token.json()
        self.assertEqual(token_payload["token_type"], "Bearer")
        self.assertIn("access_token", token_payload)
        self.assertIn("id_token", token_payload)

        userinfo = self.http.get(
            "/userinfo",
            headers={"Authorization": f"Bearer {token_payload['access_token']}"},
        )
        self.assertEqual(userinfo.status_code, 200)
        profile = userinfo.json()
        self.assertEqual(profile["vault_id"], "vault-123")
        self.assertEqual(profile["vault_number"], 7)
        self.assertEqual(profile["display_name"], "Vault Seven")
        self.assertEqual(profile["auth_strength"], "local_vault_verified")

    def test_authorize_returns_pending_consent_before_grant(self):
        self.http.post(
            "/oidc/clients/register",
            json={
                "client_id": "amazon.web",
                "client_name": "Amazon Web",
                "redirect_uris": ["https://amazon.example/callback"],
                "allowed_scopes": ["openid", "profile", "vault.basic"],
            },
        )

        response = self.http.get(
            "/authorize",
            params={
                "response_type": "code",
                "client_id": "amazon.web",
                "redirect_uri": "https://amazon.example/callback",
                "scope": "openid profile",
                "state": "state-123",
                "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                "code_challenge_method": "S256",
                "nonce": "nonce-123",
                "login_hint": "vault:vault-123",
            },
        )
        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertEqual(payload["status"], "pending_consent")
        self.assertEqual(payload["next_step"], "grant_consent")
        self.assertEqual(payload["policy_mode"], "local_only")
        self.assertEqual(payload["available_login_methods"], ["local_proof"])
        self.assertEqual(payload["active_login_method"], "local_proof")
        self.assertIsNone(payload["authorization_code"])

    def test_oidc_consent_endpoints_record_and_return_grant(self):
        self.http.post(
            "/oidc/clients/register",
            json={
                "client_id": "amazon.web",
                "client_name": "Amazon Web",
                "redirect_uris": ["https://amazon.example/callback"],
                "allowed_scopes": ["openid", "profile", "vault.basic"],
            },
        )
        grant = self.http.post(
            "/oidc/consents",
            json={
                "client_id": "amazon.web",
                "subject_id": "subject-12345678",
                "granted_scopes": ["profile", "openid"],
            },
        )
        self.assertEqual(grant.status_code, 200)
        granted = grant.json()
        self.assertEqual(granted["granted_scopes"], ["openid", "profile"])
        self.assertIn("display_name", granted["claims_granted"])

        fetched = self.http.get("/oidc/consents/amazon.web/subject-12345678")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["subject_id"], "subject-12345678")

    def test_oidc_local_proof_challenge_and_complete_contract(self):
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
        self.assertEqual(authorize.status_code, 202)
        session = authorize.json()
        self.assertEqual(session["status"], "pending_authentication")
        self.assertEqual(session["policy_mode"], "flexible")
        self.assertEqual(session["available_login_methods"], ["local_proof", "hosted_account"])
        self.assertIsNone(session["active_login_method"])

        challenge = self.http.post(f"/oidc/local-proof/challenge/{session['session_id']}")
        self.assertEqual(challenge.status_code, 200)
        challenge_payload = challenge.json()
        self.assertEqual(challenge_payload["status"], "pending_local_proof")
        self.assertIn("eidolon://connect/local-proof?", challenge_payload["launcher_protocol_url"])

        completed = self.http.post(
            "/oidc/local-proof/complete",
            json={
                "session_id": session["session_id"],
                "challenge_id": challenge_payload["challenge_id"],
                "challenge_token": challenge_payload["challenge_token"],
                "vault_id": "vault-123",
                "proof_signature": self._build_local_proof_signature(
                    session["session_id"],
                    challenge_payload["challenge_id"],
                    challenge_payload["challenge_token"],
                    "vault-123",
                ),
                "approve_consent": True,
            },
        )
        self.assertEqual(completed.status_code, 200)
        completed_payload = completed.json()
        self.assertEqual(completed_payload["status"], "ready")
        self.assertEqual(completed_payload["next_step"], "exchange_code")
        self.assertEqual(completed_payload["policy_mode"], "local_only")
        self.assertEqual(completed_payload["available_login_methods"], ["local_proof"])
        self.assertEqual(completed_payload["active_login_method"], "local_proof")
        self.assertTrue(completed_payload["authorization_code"])

        token = self.http.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": completed_payload["authorization_code"],
                "redirect_uri": "https://amazon.example/callback",
                "client_id": "amazon.web",
                "code_verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
            },
        )
        self.assertEqual(token.status_code, 200)

    def test_oidc_authorization_session_status_exposes_redirect_location(self):
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
                "scope": "openid profile",
                "state": "state-123",
                "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                "code_challenge_method": "S256",
                "login_hint": "vault:vault-123",
            },
        )
        session = authorize.json()
        challenge = self.http.post(f"/oidc/local-proof/challenge/{session['session_id']}").json()
        completed = self.http.post(
            "/oidc/local-proof/complete",
            json={
                "session_id": session["session_id"],
                "challenge_id": challenge["challenge_id"],
                "challenge_token": challenge["challenge_token"],
                "vault_id": "vault-123",
                "proof_signature": self._build_local_proof_signature(
                    session["session_id"],
                    challenge["challenge_id"],
                    challenge["challenge_token"],
                    "vault-123",
                ),
                "approve_consent": True,
            },
        )
        self.assertEqual(completed.status_code, 200)

        status = self.http.get(f"/oidc/authorization-sessions/{session['session_id']}")
        self.assertEqual(status.status_code, 200)
        payload = status.json()
        self.assertEqual(payload["status"], "ready")
        self.assertIn("code=", payload["redirect_location"])
        self.assertIn("state=state-123", payload["redirect_location"])

    def test_oidc_hosted_login_ui_renders_authorization_context(self):
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
                "scope": "openid profile",
                "state": "state-123",
                "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                "code_challenge_method": "S256",
            },
        )
        self.assertEqual(authorize.status_code, 202)
        session = authorize.json()

        hosted_ui = self.http.get(f"/oidc/hosted-login/{session['session_id']}")
        self.assertEqual(hosted_ui.status_code, 200)
        self.assertIn("text/html", hosted_ui.headers["content-type"])
        body = hosted_ui.text
        self.assertIn("Hosted Eidolon Login", body)
        self.assertIn("Amazon Web", body)
        self.assertIn(session["session_id"], body)
        self.assertIn("openid profile", body)
        self.assertIn("flexible", body)
        self.assertIn('name="login_handle"', body)
        self.assertIn('name="password"', body)
        self.assertIn(f"/oidc/local-proof/challenge/{session['session_id']}", body)

    def test_oidc_hosted_login_ui_returns_404_for_unknown_session(self):
        hosted_ui = self.http.get("/oidc/hosted-login/missing-session")
        self.assertEqual(hosted_ui.status_code, 404)
        self.assertEqual(hosted_ui.json()["detail"], "Authorization session not found")

    def test_oidc_hosted_consent_ui_renders_requested_claims(self):
        self.http.post(
            "/oidc/clients/register",
            json={
                "client_id": "amazon.web",
                "client_name": "Amazon Web",
                "redirect_uris": ["https://amazon.example/callback"],
                "allowed_scopes": ["openid", "profile", "vault.basic"],
                "branding_name": "Amazon Identity",
                "consent_text": "Share your Eidolon profile with Amazon Identity.",
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
                "login_hint": "vault:vault-123",
            },
        )
        self.assertEqual(authorize.status_code, 202)
        session = authorize.json()

        hosted_ui = self.http.get(f"/oidc/hosted-consent/{session['session_id']}")
        self.assertEqual(hosted_ui.status_code, 200)
        self.assertIn("text/html", hosted_ui.headers["content-type"])
        body = hosted_ui.text
        self.assertIn("Hosted Consent Review", body)
        self.assertIn("Amazon Identity", body)
        self.assertIn("openid profile vault.basic", body)
        self.assertIn("display_name", body)
        self.assertIn("vault_id", body)
        self.assertIn("local_vault_verified", body)
        self.assertIn("Share your Eidolon profile with Amazon Identity.", body)
        self.assertIn("Allow and continue", body)

    def test_oidc_hosted_consent_ui_returns_404_for_unknown_session(self):
        hosted_ui = self.http.get("/oidc/hosted-consent/missing-session")
        self.assertEqual(hosted_ui.status_code, 404)
        self.assertEqual(hosted_ui.json()["detail"], "Authorization session not found")

    def test_oidc_hosted_login_complete_binds_account_to_authorization_session(self):
        self.http.post(
            "/oidc/clients/register",
            json={
                "client_id": "amazon.web",
                "client_name": "Amazon Web",
                "redirect_uris": ["https://amazon.example/callback"],
                "allowed_scopes": ["openid", "profile", "vault.basic"],
            },
        )
        salt = "s" * 16
        password = "eclipse-bridge"
        self.http.post(
            "/oidc/hosted-accounts",
            json={
                "login_handle": "pilot.one",
                "password_salt": salt,
                "password_verifier": self._build_hosted_password_verifier(salt, password),
                "display_name": "Pilot One",
                "vault_id": "vault-123",
                "vault_number": 7,
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
        session = authorize.json()

        completed = self.http.post(
            "/oidc/hosted-login/complete",
            data={
                "session_id": session["session_id"],
                "login_handle": "pilot.one",
                "password": password,
                "approve_consent": "true",
            },
        )
        self.assertEqual(completed.status_code, 200)
        completed_payload = completed.json()
        self.assertEqual(completed_payload["status"], "ready")
        self.assertEqual(completed_payload["next_step"], "exchange_code")
        self.assertEqual(completed_payload["policy_mode"], "hosted_only")
        self.assertEqual(completed_payload["available_login_methods"], ["hosted_account"])
        self.assertEqual(completed_payload["active_login_method"], "hosted_account")
        self.assertTrue(completed_payload["authorization_code"])

        token = self.http.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": completed_payload["authorization_code"],
                "redirect_uri": "https://amazon.example/callback",
                "client_id": "amazon.web",
                "code_verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
            },
        )
        self.assertEqual(token.status_code, 200)
        token_payload = token.json()

        userinfo = self.http.get(
            "/userinfo",
            headers={"Authorization": f"Bearer {token_payload['access_token']}"},
        )
        self.assertEqual(userinfo.status_code, 200)
        profile = userinfo.json()
        self.assertEqual(profile["sub"], "hosted::pilot.one")
        self.assertEqual(profile["display_name"], "Pilot One")
        self.assertEqual(profile["vault_id"], "vault-123")
        self.assertEqual(profile["vault_number"], 7)
        self.assertEqual(profile["auth_strength"], "hosted_account_verified")

    def test_oidc_hosted_login_complete_returns_pending_consent_without_auto_grant(self):
        self.http.post(
            "/oidc/clients/register",
            json={
                "client_id": "amazon.web",
                "client_name": "Amazon Web",
                "redirect_uris": ["https://amazon.example/callback"],
                "allowed_scopes": ["openid", "profile"],
            },
        )
        salt = "s" * 16
        password = "eclipse-bridge"
        self.http.post(
            "/oidc/hosted-accounts",
            json={
                "login_handle": "pilot.one",
                "password_salt": salt,
                "password_verifier": self._build_hosted_password_verifier(salt, password),
                "display_name": "Pilot One",
            },
        )
        authorize = self.http.get(
            "/authorize",
            params={
                "response_type": "code",
                "client_id": "amazon.web",
                "redirect_uri": "https://amazon.example/callback",
                "scope": "openid profile",
                "state": "state-123",
                "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                "code_challenge_method": "S256",
            },
        )
        session = authorize.json()

        completed = self.http.post(
            "/oidc/hosted-login/complete",
            data={
                "session_id": session["session_id"],
                "login_handle": "pilot.one",
                "password": password,
                "approve_consent": "false",
            },
        )
        self.assertEqual(completed.status_code, 200)
        payload = completed.json()
        self.assertEqual(payload["status"], "pending_consent")
        self.assertEqual(payload["next_step"], "grant_consent")
        self.assertEqual(payload["policy_mode"], "hosted_only")
        self.assertEqual(payload["available_login_methods"], ["hosted_account"])
        self.assertEqual(payload["active_login_method"], "hosted_account")
        self.assertIsNone(payload["authorization_code"])

    def test_oidc_hosted_login_complete_rejects_invalid_credentials(self):
        self.http.post(
            "/oidc/clients/register",
            json={
                "client_id": "amazon.web",
                "client_name": "Amazon Web",
                "redirect_uris": ["https://amazon.example/callback"],
                "allowed_scopes": ["openid", "profile"],
            },
        )
        salt = "s" * 16
        self.http.post(
            "/oidc/hosted-accounts",
            json={
                "login_handle": "pilot.one",
                "password_salt": salt,
                "password_verifier": self._build_hosted_password_verifier(salt, "eclipse-bridge"),
                "display_name": "Pilot One",
            },
        )
        authorize = self.http.get(
            "/authorize",
            params={
                "response_type": "code",
                "client_id": "amazon.web",
                "redirect_uri": "https://amazon.example/callback",
                "scope": "openid profile",
                "state": "state-123",
                "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                "code_challenge_method": "S256",
            },
        )
        session = authorize.json()

        rejected = self.http.post(
            "/oidc/hosted-login/complete",
            data={
                "session_id": session["session_id"],
                "login_handle": "pilot.one",
                "password": "wrong-password",
            },
        )
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(rejected.json()["detail"], "Invalid hosted login credentials")

    def test_oidc_hosted_login_policy_blocks_local_proof_after_hosted_binding(self):
        self.http.post(
            "/oidc/clients/register",
            json={
                "client_id": "amazon.web",
                "client_name": "Amazon Web",
                "redirect_uris": ["https://amazon.example/callback"],
                "allowed_scopes": ["openid", "profile"],
            },
        )
        salt = "s" * 16
        password = "eclipse-bridge"
        self.http.post(
            "/oidc/hosted-accounts",
            json={
                "login_handle": "pilot.one",
                "password_salt": salt,
                "password_verifier": self._build_hosted_password_verifier(salt, password),
                "display_name": "Pilot One",
            },
        )
        session = self.http.get(
            "/authorize",
            params={
                "response_type": "code",
                "client_id": "amazon.web",
                "redirect_uri": "https://amazon.example/callback",
                "scope": "openid profile",
                "state": "state-123",
                "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                "code_challenge_method": "S256",
            },
        ).json()
        self.http.post(
            "/oidc/hosted-login/complete",
            data={
                "session_id": session["session_id"],
                "login_handle": "pilot.one",
                "password": password,
                "approve_consent": "false",
            },
        )
        blocked = self.http.post(f"/oidc/local-proof/challenge/{session['session_id']}")
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.json()["detail"], "Authorization session policy does not allow local proof")

    def test_oidc_local_proof_policy_blocks_hosted_login_after_local_binding(self):
        self.http.post(
            "/oidc/clients/register",
            json={
                "client_id": "amazon.web",
                "client_name": "Amazon Web",
                "redirect_uris": ["https://amazon.example/callback"],
                "allowed_scopes": ["openid", "profile"],
            },
        )
        salt = "s" * 16
        password = "eclipse-bridge"
        self.http.post(
            "/oidc/hosted-accounts",
            json={
                "login_handle": "pilot.one",
                "password_salt": salt,
                "password_verifier": self._build_hosted_password_verifier(salt, password),
                "display_name": "Pilot One",
            },
        )
        session = self.http.get(
            "/authorize",
            params={
                "response_type": "code",
                "client_id": "amazon.web",
                "redirect_uri": "https://amazon.example/callback",
                "scope": "openid profile",
                "state": "state-123",
                "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                "code_challenge_method": "S256",
            },
        ).json()
        challenge = self.http.post(f"/oidc/local-proof/challenge/{session['session_id']}").json()
        blocked = self.http.post(
            "/oidc/hosted-login/complete",
            data={
                "session_id": session["session_id"],
                "login_handle": "pilot.one",
                "password": password,
            },
        )
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(blocked.json()["detail"], "Authorization session is already bound to local proof")
        self.assertEqual(challenge["status"], "pending_local_proof")

    def test_oidc_local_proof_complete_rejects_invalid_signature(self):
        self.http.post(
            "/oidc/clients/register",
            json={
                "client_id": "amazon.web",
                "client_name": "Amazon Web",
                "redirect_uris": ["https://amazon.example/callback"],
                "allowed_scopes": ["openid", "profile"],
            },
        )
        authorize = self.http.get(
            "/authorize",
            params={
                "response_type": "code",
                "client_id": "amazon.web",
                "redirect_uri": "https://amazon.example/callback",
                "scope": "openid profile",
                "state": "state-123",
                "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                "code_challenge_method": "S256",
            },
        ).json()
        challenge = self.http.post(f"/oidc/local-proof/challenge/{authorize['session_id']}").json()
        rejected = self.http.post(
            "/oidc/local-proof/complete",
            json={
                "session_id": authorize["session_id"],
                "challenge_id": challenge["challenge_id"],
                "challenge_token": challenge["challenge_token"],
                "vault_id": "vault-123",
                "proof_signature": "00" * 32,
                "approve_consent": True,
            },
        )
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(rejected.json()["detail"], "Invalid local proof signature")


if __name__ == "__main__":
    unittest.main()
