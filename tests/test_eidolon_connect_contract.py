import unittest

from src.api.connect import (
    CONNECT_CAPABILITIES,
    CONNECT_SCHEMA_VERSION,
    ConnectAppRegistrationRequest,
    ConnectAppRegistrationResponse,
    ConnectCapabilitiesResponse,
    HostedAccountCreateRequest,
    HostedAccountResponse,
    HostedLoginSessionCreateRequest,
    HostedLoginSessionResponse,
    build_app_scoped_kdf_label,
    build_connect_capabilities,
    normalize_connect_scopes,
)


class EidolonConnectContractTests(unittest.TestCase):
    def test_normalize_scopes_deduplicates_in_canonical_order(self):
        scopes = normalize_connect_scopes(["decrypt", "auth", "auth", "read_public_identity"])
        self.assertEqual(scopes, ["auth", "decrypt", "read_public_identity"])

    def test_normalize_scopes_rejects_unknown_scope(self):
        with self.assertRaisesRegex(ValueError, "Unsupported Eidolon Connect scopes"):
            normalize_connect_scopes(["auth", "root"])

    def test_capabilities_payload_is_stable(self):
        payload = build_connect_capabilities()
        self.assertEqual(payload["schema_version"], CONNECT_SCHEMA_VERSION)
        self.assertEqual(payload["capabilities"], list(CONNECT_CAPABILITIES))
        self.assertTrue(payload["consent_required"])
        self.assertTrue(payload["app_scoped_keys"])
        self.assertFalse(payload["raw_vault_key_export"])

    def test_app_scoped_label_is_stable(self):
        label = build_app_scoped_kdf_label("Notes.App", "encrypt", "vault_123")
        self.assertEqual(label, "eidolon-connect:v1:notes.app:encrypt:vault_123")

    def test_app_scoped_label_defaults_to_wildcard_vault(self):
        label = build_app_scoped_kdf_label("notes.app", "auth")
        self.assertEqual(label, "eidolon-connect:v1:notes.app:auth:*")

    def test_registration_request_accepts_connect_shape(self):
        body = ConnectAppRegistrationRequest(
            app_id="notes.app",
            app_name="Notes",
            scopes=["auth", "encrypt"],
            display_origin="https://notes.example",
            redirect_uri="notes://callback",
        )
        self.assertEqual(body.app_id, "notes.app")
        self.assertEqual(body.scopes, ["auth", "encrypt"])

    def test_registration_response_supports_pending_consent(self):
        body = ConnectAppRegistrationResponse(
            app_id="notes.app",
            requested_scopes=["auth", "encrypt"],
            granted_scopes=[],
            status="pending_consent",
        )
        self.assertEqual(body.requested_scopes, ["auth", "encrypt"])
        self.assertEqual(body.granted_scopes, [])

    def test_capabilities_response_matches_connect_payload(self):
        body = ConnectCapabilitiesResponse(**build_connect_capabilities())
        self.assertEqual(body.schema_version, "v1")
        self.assertEqual(body.capabilities, list(CONNECT_CAPABILITIES))
        self.assertTrue(body.consent_required)

    def test_hosted_account_contract_supports_linked_vault_identity(self):
        request = HostedAccountCreateRequest(
            login_handle="pilot.one",
            password_salt="a" * 16,
            password_verifier="b" * 32,
            display_name="Pilot One",
            vault_id="vault-123",
            vault_number=7,
        )
        response = HostedAccountResponse(
            account_id="ha_pilot.one",
            subject_id="hosted::pilot.one",
            login_handle=request.login_handle,
            display_name=request.display_name,
            vault_id=request.vault_id,
            vault_number=request.vault_number,
            created_at="2026-04-04T10:00:00",
            updated_at="2026-04-04T10:00:00",
        )
        self.assertEqual(response.auth_strength, "hosted_account_verified")
        self.assertEqual(response.vault_id, "vault-123")

    def test_hosted_login_session_contract_tracks_authorization_binding(self):
        request = HostedLoginSessionCreateRequest(
            authorization_session_id="auth-session-123",
            account_id="ha_pilot.one",
            client_id="amazon.web",
            scope="openid profile",
        )
        response = HostedLoginSessionResponse(
            hosted_session_id="hs_auth-session-123",
            authorization_session_id=request.authorization_session_id,
            account_id=request.account_id,
            subject_id="hosted::pilot.one",
            client_id=request.client_id,
            scope=request.scope,
            created_at="2026-04-04T10:00:00",
            expires_at="2026-04-04T10:05:00",
        )
        self.assertEqual(response.status, "pending_hosted_login")
        self.assertEqual(response.client_id, "amazon.web")


if __name__ == "__main__":
    unittest.main()
