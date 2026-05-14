import unittest

from src.api.server import ChallengeResponse, EnrollResponse, LogoutResponse, TokenResponse


class APIAuthContractTests(unittest.TestCase):
    def test_challenge_response_defaults_to_schema_v1(self):
        response = ChallengeResponse(challenge="abc123", expires_in=300)

        self.assertEqual(response.schema_version, "v1")
        self.assertEqual(response.challenge, "abc123")
        self.assertEqual(response.expires_in, 300)
        self.assertEqual(response.auth_mode, "legacy")

    def test_token_response_defaults_to_schema_v1(self):
        response = TokenResponse(
            access_token="access.jwt.token",
            refresh_token="refresh.jwt.token",
            expires_in=1800,
        )

        self.assertEqual(response.schema_version, "v1")
        self.assertEqual(response.token_type, "bearer")
        self.assertEqual(response.expires_in, 1800)
        self.assertIsNone(response.vault_id)
        self.assertIsNone(response.auth_strength)

    def test_enroll_response_exposes_zkp_metadata(self):
        response = EnrollResponse(
            vault_id="vault-123",
            vault_number=7,
            public_commitment="0xabc",
            message="ok",
        )

        self.assertEqual(response.schema_version, "v1")
        self.assertEqual(response.vault_id, "vault-123")
        self.assertEqual(response.vault_number, 7)
        self.assertEqual(response.public_commitment, "0xabc")
        self.assertEqual(response.zkp_scheme, "psnx_schnorr_v1")
        self.assertEqual(response.zkp_version, "v1")

    def test_logout_response_defaults_to_schema_v1(self):
        response = LogoutResponse(message="Logged out successfully")

        self.assertEqual(response.schema_version, "v1")
        self.assertEqual(response.message, "Logged out successfully")


if __name__ == "__main__":
    unittest.main()
