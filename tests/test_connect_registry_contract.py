import tempfile
import unittest
from pathlib import Path

from src.api.connect import (
    ConnectAppRegistrationRequest,
    ConnectClientRegistrationRequest,
    ConnectClientUpdateRequest,
    ConsentGrantRequest,
    PartnerOnboardingRequest,
    HostedAccountCreateRequest,
    HostedLoginSessionCreateRequest,
)
from src.api.connect_registry import (
    ConnectAppRegistry,
    OIDCClientRegistry,
    ConsentGrantRegistry,
    PartnerOnboardingRegistry,
    HostedAccountRegistry,
    HostedLoginSessionRegistry,
)


class ConnectRegistryContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry = ConnectAppRegistry(storage_dir=Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_register_app_persists_pending_record(self):
        response = self.registry.register_app(
            ConnectAppRegistrationRequest(
                app_id="cipher.desktop",
                app_name="Cipher Desktop",
                scopes=["encrypt", "auth", "encrypt"],
                display_origin="cipher://desktop",
            )
        )
        self.assertEqual(response.app_id, "cipher.desktop")
        self.assertEqual(response.requested_scopes, ["auth", "encrypt"])
        self.assertEqual(response.granted_scopes, [])
        self.assertEqual(response.status, "pending_consent")

        reloaded = ConnectAppRegistry(storage_dir=Path(self.temp_dir.name))
        stored = reloaded.get_app("cipher.desktop")
        self.assertIsNotNone(stored)
        self.assertEqual(stored.requested_scopes, ["auth", "encrypt"])
        self.assertEqual(stored.granted_scopes, [])

    def test_register_app_rejects_unknown_scope(self):
        with self.assertRaisesRegex(ValueError, "Unsupported Eidolon Connect scopes"):
            self.registry.register_app(
                ConnectAppRegistrationRequest(
                    app_id="cipher.desktop",
                    app_name="Cipher Desktop",
                    scopes=["auth", "admin"],
                )
            )

    def test_get_registration_status_returns_contract_shape(self):
        self.registry.register_app(
            ConnectAppRegistrationRequest(
                app_id="cipher.desktop",
                app_name="Cipher Desktop",
                scopes=["auth", "encrypt"],
            )
        )
        status = self.registry.get_registration_status("cipher.desktop")
        self.assertIsNotNone(status)
        self.assertEqual(status.app_id, "cipher.desktop")
        self.assertEqual(status.requested_scopes, ["auth", "encrypt"])
        self.assertEqual(status.status, "pending_consent")

    def test_approve_app_grants_requested_scopes(self):
        self.registry.register_app(
            ConnectAppRegistrationRequest(
                app_id="cipher.desktop",
                app_name="Cipher Desktop",
                scopes=["auth", "encrypt"],
            )
        )
        status = self.registry.approve_app("cipher.desktop")
        self.assertEqual(status.status, "approved")
        self.assertEqual(status.granted_scopes, ["auth", "encrypt"])

    def test_revoke_app_returns_to_pending_consent(self):
        self.registry.register_app(
            ConnectAppRegistrationRequest(
                app_id="cipher.desktop",
                app_name="Cipher Desktop",
                scopes=["auth", "encrypt"],
            )
        )
        self.registry.approve_app("cipher.desktop")
        status = self.registry.revoke_app("cipher.desktop")
        self.assertEqual(status.status, "pending_consent")
        self.assertEqual(status.granted_scopes, [])


class OIDCClientRegistryContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry = OIDCClientRegistry(storage_dir=Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_register_client_persists_oidc_contract(self):
        response = self.registry.register_client(
            ConnectClientRegistrationRequest(
                client_id="amazon.web",
                client_name="Amazon Web",
                redirect_uris=["https://amazon.example/callback"],
                allowed_scopes=["vault.basic", "openid", "profile"],
            )
        )
        self.assertEqual(response.client_id, "amazon.web")
        self.assertEqual(response.allowed_scopes, ["openid", "profile", "vault.basic"])
        self.assertIn("vault_id", response.claims_supported)
        self.assertIn("display_name", response.claims_supported)

        reloaded = OIDCClientRegistry(storage_dir=Path(self.temp_dir.name))
        stored = reloaded.get_client("amazon.web")
        self.assertIsNotNone(stored)
        self.assertEqual(stored.redirect_uris, ["https://amazon.example/callback"])
        self.assertFalse(response.client_secret_issued)

    def test_register_client_rejects_unknown_oidc_scope(self):
        with self.assertRaisesRegex(ValueError, "Unsupported Eidolon OIDC scopes"):
            self.registry.register_client(
                ConnectClientRegistrationRequest(
                    client_id="amazon.web",
                    client_name="Amazon Web",
                    redirect_uris=["https://amazon.example/callback"],
                    allowed_scopes=["openid", "admin.root"],
                )
            )

    def test_register_confidential_client_requires_client_secret_post_and_secret_hash(self):
        response = self.registry.register_client(
            ConnectClientRegistrationRequest(
                client_id="amazon.server",
                client_name="Amazon Server",
                redirect_uris=["https://amazon.example/callback"],
                allowed_scopes=["openid"],
                client_type="confidential",
                token_endpoint_auth_method="client_secret_post",
            )
        )
        self.assertTrue(response.client_secret_issued)
        stored = self.registry.get_client("amazon.server")
        self.assertIsNotNone(stored.client_secret_hash)

    def test_register_public_client_rejects_secret_auth_method(self):
        with self.assertRaisesRegex(ValueError, "Public clients must use token_endpoint_auth_method=none"):
            self.registry.register_client(
                ConnectClientRegistrationRequest(
                    client_id="amazon.web",
                    client_name="Amazon Web",
                    redirect_uris=["https://amazon.example/callback"],
                    allowed_scopes=["openid"],
                    client_type="public",
                    token_endpoint_auth_method="client_secret_post",
                )
            )

    def test_rotate_client_secret_and_authenticate_confidential_client(self):
        self.registry.register_client(
            ConnectClientRegistrationRequest(
                client_id="amazon.server",
                client_name="Amazon Server",
                redirect_uris=["https://amazon.example/callback"],
                allowed_scopes=["openid"],
                client_type="confidential",
                token_endpoint_auth_method="client_secret_post",
            )
        )
        rotated = self.registry.rotate_client_secret("amazon.server")
        self.assertEqual(rotated.client_id, "amazon.server")
        self.assertTrue(rotated.client_secret)
        self.assertTrue(self.registry.authenticate_confidential_client("amazon.server", rotated.client_secret))

    def test_update_client_refreshes_redirects_scopes_and_metadata(self):
        self.registry.register_client(
            ConnectClientRegistrationRequest(
                client_id="amazon.web",
                client_name="Amazon Web",
                redirect_uris=["https://amazon.example/callback"],
                allowed_scopes=["openid", "profile"],
            )
        )
        updated = self.registry.update_client(
            "amazon.web",
            ConnectClientUpdateRequest(
                client_name="Amazon Marketplace",
                redirect_uris=["https://amazon.example/oidc/callback"],
                allowed_scopes=["openid", "vault.basic"],
                logo_uri="https://amazon.example/logo.png",
                policy_uri="https://amazon.example/privacy",
                environment="production",
                branding_name="Amazon Identity",
                consent_text="Share your Eidolon profile with Amazon.",
                status="active",
            ),
        )
        self.assertEqual(updated.client_name, "Amazon Marketplace")
        self.assertEqual(updated.redirect_uris, ["https://amazon.example/oidc/callback"])
        self.assertEqual(updated.allowed_scopes, ["openid", "vault.basic"])
        self.assertIn("vault_id", updated.claims_supported)
        self.assertEqual(updated.logo_uri, "https://amazon.example/logo.png")
        self.assertEqual(updated.environment, "production")
        self.assertEqual(updated.branding_name, "Amazon Identity")

    def test_list_clients_returns_sorted_registered_clients(self):
        self.registry.register_client(
            ConnectClientRegistrationRequest(
                client_id="zeta.web",
                client_name="Zeta Web",
                redirect_uris=["https://zeta.example/callback"],
                allowed_scopes=["openid"],
            )
        )
        self.registry.register_client(
            ConnectClientRegistrationRequest(
                client_id="amazon.web",
                client_name="Amazon Web",
                redirect_uris=["https://amazon.example/callback"],
                allowed_scopes=["openid"],
            )
        )
        clients = self.registry.list_clients()
        self.assertEqual([client.client_id for client in clients], ["amazon.web", "zeta.web"])


class PartnerOnboardingRegistryContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry = PartnerOnboardingRegistry(storage_dir=Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_submit_request_persists_partner_onboarding_state(self):
        response = self.registry.submit_request(
            PartnerOnboardingRequest(
                partner_name="Amazon Web",
                contact_email="dev@amazon.example",
                requested_client_id="amazon.web",
                redirect_uris=["https://amazon.example/callback"],
                requested_scopes=["vault.basic", "openid", "profile"],
                integration_notes="Need Sign in with Eidolon for checkout accounts.",
            )
        )
        self.assertEqual(response.request_id, "por_amazon.web")
        self.assertEqual(response.status, "pending_review")
        self.assertEqual(response.requested_scopes, ["openid", "profile", "vault.basic"])
        self.assertIn("vault_id", response.claims_supported)
        self.assertTrue(response.next_steps)

        reloaded = PartnerOnboardingRegistry(storage_dir=Path(self.temp_dir.name))
        stored = reloaded.get_request("por_amazon.web")
        self.assertIsNotNone(stored)
        self.assertEqual(stored.partner_name, "Amazon Web")

    def test_submit_request_rejects_unknown_oidc_scope(self):
        with self.assertRaisesRegex(ValueError, "Unsupported Eidolon OIDC scopes"):
            self.registry.submit_request(
                PartnerOnboardingRequest(
                    partner_name="Amazon Web",
                    contact_email="dev@amazon.example",
                    requested_client_id="amazon.web",
                    redirect_uris=["https://amazon.example/callback"],
                    requested_scopes=["openid", "admin.root"],
                )
            )


class ConsentGrantRegistryContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry = ConsentGrantRegistry(storage_dir=Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_grant_consent_persists_scope_and_claims(self):
        response = self.registry.grant_consent(
            ConsentGrantRequest(
                client_id="amazon.web",
                subject_id="subject-12345678",
                granted_scopes=["vault.basic", "openid"],
            )
        )
        self.assertEqual(response.client_id, "amazon.web")
        self.assertEqual(response.subject_id, "subject-12345678")
        self.assertEqual(response.granted_scopes, ["openid", "vault.basic"])
        self.assertIn("vault_id", response.claims_granted)

        reloaded = ConsentGrantRegistry(storage_dir=Path(self.temp_dir.name))
        stored = reloaded.get_consent("amazon.web", "subject-12345678")
        self.assertIsNotNone(stored)
        self.assertEqual(stored.granted_scopes, ["openid", "vault.basic"])

    def test_has_consent_for_scopes_requires_superset(self):
        self.registry.grant_consent(
            ConsentGrantRequest(
                client_id="amazon.web",
                subject_id="subject-12345678",
                granted_scopes=["openid", "profile"],
            )
        )
        self.assertTrue(self.registry.has_consent_for_scopes("amazon.web", "subject-12345678", ["openid"]))
        self.assertFalse(self.registry.has_consent_for_scopes("amazon.web", "subject-12345678", ["vault.basic"]))


class HostedAccountRegistryContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry = HostedAccountRegistry(storage_dir=Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_account_persists_hosted_identity_contract(self):
        response = self.registry.create_account(
            HostedAccountCreateRequest(
                login_handle="Pilot.One",
                password_salt="a" * 16,
                password_verifier="b" * 32,
                display_name="Pilot One",
                vault_id="vault-123",
                vault_number=7,
            )
        )
        self.assertEqual(response.account_id, "ha_pilot.one")
        self.assertEqual(response.subject_id, "hosted::pilot.one")
        self.assertEqual(response.login_handle, "pilot.one")
        self.assertEqual(response.auth_strength, "hosted_account_verified")
        self.assertEqual(response.vault_id, "vault-123")

        reloaded = HostedAccountRegistry(storage_dir=Path(self.temp_dir.name))
        stored = reloaded.get_account_by_login_handle("pilot.one")
        self.assertIsNotNone(stored)
        self.assertEqual(stored.display_name, "Pilot One")
        self.assertEqual(stored.vault_number, 7)

    def test_mark_login_success_updates_last_login(self):
        account = self.registry.create_account(
            HostedAccountCreateRequest(
                login_handle="pilot.one",
                password_salt="a" * 16,
                password_verifier="b" * 32,
                display_name="Pilot One",
            )
        )
        updated = self.registry.mark_login_success(account.account_id)
        self.assertIsNotNone(updated.last_login_at)


class HostedLoginSessionRegistryContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry = HostedLoginSessionRegistry(storage_dir=Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_session_persists_authorization_binding(self):
        response = self.registry.create_session(
            HostedLoginSessionCreateRequest(
                authorization_session_id="auth-session-123",
                account_id="ha_pilot.one",
                client_id="amazon.web",
                scope="openid profile",
            ),
            subject_id="hosted::pilot.one",
            expires_at="2026-04-04T12:00:00",
        )
        self.assertEqual(response.hosted_session_id, "hs_auth-session-123")
        self.assertEqual(response.authorization_session_id, "auth-session-123")
        self.assertEqual(response.subject_id, "hosted::pilot.one")
        self.assertEqual(response.status, "pending_hosted_login")

        reloaded = HostedLoginSessionRegistry(storage_dir=Path(self.temp_dir.name))
        stored = reloaded.get_session("hs_auth-session-123")
        self.assertIsNotNone(stored)
        self.assertEqual(stored.client_id, "amazon.web")

    def test_mark_authenticated_updates_status(self):
        session = self.registry.create_session(
            HostedLoginSessionCreateRequest(
                authorization_session_id="auth-session-123",
                account_id="ha_pilot.one",
                client_id="amazon.web",
                scope="openid profile",
            ),
            subject_id="hosted::pilot.one",
            expires_at="2026-04-04T12:00:00",
        )
        updated = self.registry.mark_authenticated(session.hosted_session_id)
        self.assertEqual(updated.status, "authenticated")
        self.assertIsNotNone(updated.authenticated_at)


if __name__ == "__main__":
    unittest.main()
