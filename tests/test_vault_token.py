"""Contrat du jeton de coffre signe (QR / code manuel Cipher).

Le vecteur de reference a ete calcule avec Node en executant ``stableJson``
et ``createHmac`` du bridge Cipher (``apps/bridge/src/routes/auth.ts``) :
si ce test casse, c'est le bridge qui rejettera le jeton en 401.
"""

import base64
import json
import unittest

from src.crypto.vault_token import (
    VAULT_TOKEN_FALLBACK_SECRET_ENV,
    VAULT_TOKEN_SECRET_ENV,
    canonical_json,
    compute_vault_token_hmac,
    encode_vault_token,
    resolve_vault_token_secret,
    sign_vault_token,
)

VECTOR_PAYLOAD = {
    "vault_id": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "vault_number": 7,
    "vault_name": "Coffre Ünï",
    "issued_at": "2026-09-12T00:00:00Z",
}
VECTOR_CANONICAL = (
    '{"issued_at":"2026-09-12T00:00:00Z",'
    '"vault_id":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",'
    '"vault_name":"Coffre Ünï","vault_number":7}'
)
VECTOR_SECRET = "test-secret"
VECTOR_HMAC = "d3f0ec91d34c374a6f5c71faf0a12ba9ff92d7844f91197864c05cbd1ff54d29"


class CanonicalJsonTests(unittest.TestCase):
    def test_matches_bridge_stable_json_vector(self):
        self.assertEqual(canonical_json(VECTOR_PAYLOAD), VECTOR_CANONICAL)

    def test_key_order_of_input_is_irrelevant(self):
        reordered = {
            "issued_at": VECTOR_PAYLOAD["issued_at"],
            "vault_number": VECTOR_PAYLOAD["vault_number"],
            "vault_name": VECTOR_PAYLOAD["vault_name"],
            "vault_id": VECTOR_PAYLOAD["vault_id"],
        }
        self.assertEqual(canonical_json(reordered), VECTOR_CANONICAL)

    def test_nested_objects_are_sorted_recursively_without_whitespace(self):
        payload = {"z": {"b": 1, "a": [3, {"y": None, "x": True}]}, "a": "v"}
        self.assertEqual(canonical_json(payload), '{"a":"v","z":{"a":[3,{"x":true,"y":null}],"b":1}}')

    def test_unicode_is_not_ascii_escaped_and_control_chars_match_json_stringify(self):
        self.assertEqual(canonical_json({"n": "Ünï"}), '{"n":"Ünï"}')
        # JSON.stringify: \n, \t, quote and backslash use short escapes, other
        # control characters use lowercase \u00XX.
        self.assertEqual(canonical_json({"n": 'a"b\\c\n\t\x01'}), '{"n":"a\\"b\\\\c\\n\\t\\u0001"}')


class SignVaultTokenTests(unittest.TestCase):
    def test_hmac_matches_bridge_vector(self):
        self.assertEqual(compute_vault_token_hmac(VECTOR_PAYLOAD, VECTOR_SECRET), VECTOR_HMAC)

    def test_sign_returns_payload_plus_lowercase_hex_hmac(self):
        signed = sign_vault_token(VECTOR_PAYLOAD, VECTOR_SECRET)
        self.assertEqual(signed["hmac"], VECTOR_HMAC)
        self.assertEqual(signed["hmac"], signed["hmac"].lower())
        self.assertEqual(len(signed["hmac"]), 64)
        for key, value in VECTOR_PAYLOAD.items():
            self.assertEqual(signed[key], value)
        # Input is not mutated.
        self.assertNotIn("hmac", VECTOR_PAYLOAD)

    def test_sign_is_independent_of_input_key_order(self):
        reordered = dict(reversed(list(VECTOR_PAYLOAD.items())))
        self.assertEqual(sign_vault_token(reordered, VECTOR_SECRET)["hmac"], VECTOR_HMAC)

    def test_existing_hmac_field_is_excluded_from_the_signed_material(self):
        tampered = dict(VECTOR_PAYLOAD, hmac="00" * 32)
        self.assertEqual(sign_vault_token(tampered, VECTOR_SECRET)["hmac"], VECTOR_HMAC)

    def test_different_secret_or_payload_changes_hmac(self):
        self.assertNotEqual(sign_vault_token(VECTOR_PAYLOAD, "other-secret")["hmac"], VECTOR_HMAC)
        self.assertNotEqual(
            sign_vault_token(dict(VECTOR_PAYLOAD, vault_number=8), VECTOR_SECRET)["hmac"],
            VECTOR_HMAC,
        )

    def test_empty_secret_is_refused(self):
        with self.assertRaises(ValueError):
            sign_vault_token(VECTOR_PAYLOAD, "")

    def test_encode_round_trips_through_the_bridge_decoding_path(self):
        token = encode_vault_token(sign_vault_token(VECTOR_PAYLOAD, VECTOR_SECRET))
        # Bridge: JSON.parse(Buffer.from(vaultToken, 'base64').toString('utf8'))
        decoded = json.loads(base64.b64decode(token).decode("utf-8"))
        self.assertEqual(decoded["hmac"], VECTOR_HMAC)
        self.assertEqual(decoded["vault_name"], "Coffre Ünï")
        self.assertEqual(decoded["vault_number"], 7)
        # Signature recomputed by the bridge over everything but hmac still matches.
        decoded.pop("hmac")
        self.assertEqual(compute_vault_token_hmac(decoded, VECTOR_SECRET), VECTOR_HMAC)


class ResolveVaultTokenSecretTests(unittest.TestCase):
    def test_returns_none_when_nothing_is_configured(self):
        self.assertIsNone(resolve_vault_token_secret({}))
        self.assertIsNone(resolve_vault_token_secret({VAULT_TOKEN_SECRET_ENV: "   "}))
        self.assertIsNone(resolve_vault_token_secret({VAULT_TOKEN_FALLBACK_SECRET_ENV: ""}))

    def test_dedicated_secret_wins_over_connect_secret(self):
        env = {VAULT_TOKEN_SECRET_ENV: "dedicated", VAULT_TOKEN_FALLBACK_SECRET_ENV: "connect"}
        self.assertEqual(resolve_vault_token_secret(env), "dedicated")

    def test_falls_back_to_connect_session_secret(self):
        self.assertEqual(resolve_vault_token_secret({VAULT_TOKEN_FALLBACK_SECRET_ENV: "connect"}), "connect")

    def test_values_are_stripped(self):
        self.assertEqual(resolve_vault_token_secret({VAULT_TOKEN_SECRET_ENV: "  s3cret \n"}), "s3cret")

    def test_reads_process_environment_by_default(self):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {VAULT_TOKEN_SECRET_ENV: "", VAULT_TOKEN_FALLBACK_SECRET_ENV: "from-env"}, clear=False):
            self.assertEqual(resolve_vault_token_secret(), "from-env")
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(resolve_vault_token_secret())


if __name__ == "__main__":
    unittest.main()


class PsnxProofTests(unittest.TestCase):
    """Preuve de possession du fichier : vecteurs partages avec le bridge
    (apps/bridge/src/__tests__/vault-token.test.ts)."""

    PAYLOAD = {
        "vault_id": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "vault_number": 7,
        "vault_name": "Coffre Ünï",
        "issued_at": "2026-09-12T00:00:00Z",
    }
    PSNX_BYTES = b"PSNX7D_COMPLETE_V2 fake vector bytes for proof test"
    PSNX_HASH = "e8f6ea0299489866ce3990d8d32ab8f26fe307987b5bec0cae96ef63c64273f3"
    PROOF = "66292a0271ed7dca187152ae985656d3d45581d46ac60cd508f6944122e8abc0"

    def test_proof_matches_bridge_vector(self):
        import hashlib
        from src.crypto.vault_token import compute_psnx_proof

        self.assertEqual(hashlib.sha256(self.PSNX_BYTES).hexdigest(), self.PSNX_HASH)
        self.assertEqual(compute_psnx_proof(self.PAYLOAD, self.PSNX_BYTES), self.PROOF)
        # Le champ hmac et une preuve deja presente sont ignores.
        self.assertEqual(
            compute_psnx_proof({**self.PAYLOAD, "hmac": "x", "psnx_proof": "y"}, self.PSNX_BYTES),
            self.PROOF,
        )

    def test_sign_adds_proof_then_hmac_covering_it(self):
        from src.crypto.vault_token import (
            VAULT_TOKEN_HMAC_FIELD,
            VAULT_TOKEN_PROOF_FIELD,
            compute_vault_token_hmac,
            sign_vault_token,
        )

        signed = sign_vault_token(self.PAYLOAD, "test-secret", psnx_bytes=self.PSNX_BYTES)
        self.assertEqual(signed[VAULT_TOKEN_PROOF_FIELD], self.PROOF)
        unsigned = {k: v for k, v in signed.items() if k != VAULT_TOKEN_HMAC_FIELD}
        self.assertEqual(signed[VAULT_TOKEN_HMAC_FIELD], compute_vault_token_hmac(unsigned, "test-secret"))
        # Sans preuve, le hmac vaut le vecteur historique.
        plain = sign_vault_token(self.PAYLOAD, "test-secret")
        self.assertNotIn(VAULT_TOKEN_PROOF_FIELD, plain)
        self.assertEqual(
            plain[VAULT_TOKEN_HMAC_FIELD],
            "d3f0ec91d34c374a6f5c71faf0a12ba9ff92d7844f91197864c05cbd1ff54d29",
        )

    def test_rejects_empty_file(self):
        from src.crypto.vault_token import compute_psnx_proof

        with self.assertRaises(ValueError):
            compute_psnx_proof(self.PAYLOAD, b"")
