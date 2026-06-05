"""Backward-compatibility tests for the 7D Escrow envelope format.

These tests freeze the v1 wire format and prove that adding a future v2
schema/crypto-suite cannot break existing v1 envelopes. They double as
documentation of the rule: each schema_version owns a FROZEN mac_input
function, and old crypto suites must stay registered.
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allow running this test directly without installing the package
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.protocols.escrow_7d.envelope import EscrowEnvelope, _MAC_INPUT_BY_VERSION
from src.protocols.escrow_7d.conditions import TimeLock, OwnerSignature, CombinedAll
from src.protocols.escrow_7d.format_version import (
    CryptoSuite,
    FormatError,
    _REGISTRY,
    SUPPORTED_SCHEMA_VERSIONS,
    get_suite,
)
from src.protocols.escrow_7d.sealer import (
    seal, unseal, verify, reseal, is_current_format, UnsealError,
)


VAULT_KEY = b"k" * 32


# ---------------------------------------------------------------------------
# 1. Round-trip sanity
# ---------------------------------------------------------------------------

class RoundTripTests(unittest.TestCase):
    def test_seal_then_unseal(self):
        payload = b"the launch codes are 1234"
        env = seal(payload, VAULT_KEY, label="codes")
        self.assertEqual(env.schema_version, 1)
        self.assertEqual(env.crypto_suite, "alpha-v1")
        decoded = unseal(env, VAULT_KEY)
        self.assertEqual(decoded, payload)

    def test_wrong_key_rejected(self):
        env = seal(b"top secret", VAULT_KEY)
        with self.assertRaises(UnsealError):
            unseal(env, b"x" * 32)

    def test_tampered_ciphertext_rejected(self):
        env = seal(b"data", VAULT_KEY)
        env.ciphertext = bytes(b ^ 0x01 for b in env.ciphertext)
        with self.assertRaises(UnsealError):
            unseal(env, VAULT_KEY)

    def test_time_lock_blocks_then_releases(self):
        future = datetime.now(timezone.utc) + timedelta(days=365)
        env = seal(b"locked", VAULT_KEY, conditions=[TimeLock(future)])
        with self.assertRaises(UnsealError):
            unseal(env, VAULT_KEY)
        # Replace with an already-passed lock and re-seal
        past = datetime.now(timezone.utc) - timedelta(seconds=5)
        env2 = seal(b"unlocked", VAULT_KEY, conditions=[TimeLock(past)])
        self.assertEqual(unseal(env2, VAULT_KEY), b"unlocked")

    def test_combined_all_evaluates_each_child(self):
        past = datetime.now(timezone.utc) - timedelta(seconds=5)
        import hashlib
        owner_prefix = hashlib.sha256(VAULT_KEY).hexdigest()
        env = seal(
            b"composite",
            VAULT_KEY,
            conditions=[CombinedAll(TimeLock(past), OwnerSignature(owner_prefix))],
        )
        self.assertEqual(unseal(env, VAULT_KEY), b"composite")


# ---------------------------------------------------------------------------
# 2. Format-frozen guarantees
# ---------------------------------------------------------------------------

class FrozenFormatTests(unittest.TestCase):
    def test_v1_mac_input_is_stable(self):
        """The exact bytes of v1 mac_input must never change.

        If this test fails after a code edit, you've silently broken every
        v1 envelope that was ever produced. Revert your changes to
        EscrowEnvelope._mac_input_v1.
        """
        env = EscrowEnvelope(
            escrow_id="esc_deadbeefcafebabe1234567890abcdef",
            deposited_at="2026-01-01T00:00:00+00:00",
            depositor_vault_id_prefix="0123456789abcdef",
            conditions=[],
            kdf_salt=b"\x00" * 32,
            aes_nonce=b"\x01" * 12,
            ciphertext=b"\x02" * 16,
            aes_tag=b"\x03" * 16,
            payload_size=16,
            integrity_mac=b"",  # not in mac_input
            label="frozen",
            schema_version=1,
            min_reader_version=1,
            crypto_suite="alpha-v1",
            producer="eidolon-escrow-7d/alpha-v1",
        )
        expected = (
            b'{"aes_nonce":"AQEBAQEBAQEBAQEB","aes_tag":"AwMDAwMDAwMDAwMDAwMDAw==",'
            b'"ciphertext":"AgICAgICAgICAgICAgICAg==","conditions":[],'
            b'"crypto_suite":"alpha-v1",'
            b'"deposited_at":"2026-01-01T00:00:00+00:00",'
            b'"depositor_vault_id_prefix":"0123456789abcdef",'
            b'"escrow_id":"esc_deadbeefcafebabe1234567890abcdef",'
            b'"kdf_salt":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",'
            b'"label":"frozen","min_reader_version":1,"payload_size":16,'
            b'"producer":"eidolon-escrow-7d/alpha-v1","schema_version":1}'
        )
        self.assertEqual(env.mac_input(), expected)

    def test_v1_mac_input_function_is_registered(self):
        self.assertIn(1, _MAC_INPUT_BY_VERSION)

    def test_alpha_v1_suite_is_registered(self):
        suite = get_suite("alpha-v1")
        self.assertEqual(suite.session_key_info, b"EIDOLON_ESCROW_SESSION_KEY_v1")
        self.assertEqual(suite.integrity_info, b"EIDOLON_ESCROW_INTEGRITY_v1")

    def test_supported_versions_includes_one(self):
        self.assertIn(1, SUPPORTED_SCHEMA_VERSIONS)


# ---------------------------------------------------------------------------
# 3. Future-version simulation
# ---------------------------------------------------------------------------
# We temporarily monkey-patch a hypothetical v2 schema + crypto suite into the
# registries, write a v1 envelope to disk, then verify it still loads & unseals.
# This proves "a future v2 release does not break v1 envelopes".

class FutureVersionTests(unittest.TestCase):
    def setUp(self):
        # Save originals
        self._orig_supported = set(SUPPORTED_SCHEMA_VERSIONS)
        self._orig_mac_fns = dict(_MAC_INPUT_BY_VERSION)
        self._orig_suites = dict(_REGISTRY)

    def tearDown(self):
        # Restore: drop the simulated v2 entries we added
        SUPPORTED_SCHEMA_VERSIONS_obj = sys.modules[
            "src.protocols.escrow_7d.format_version"
        ]
        # frozenset reassignment via module attribute
        SUPPORTED_SCHEMA_VERSIONS_obj.SUPPORTED_SCHEMA_VERSIONS = frozenset(self._orig_supported)
        _MAC_INPUT_BY_VERSION.clear()
        _MAC_INPUT_BY_VERSION.update(self._orig_mac_fns)
        _REGISTRY.clear()
        _REGISTRY.update(self._orig_suites)

    def test_v1_envelope_still_loads_after_simulated_v2_release(self):
        # Produce a real v1 envelope
        env_v1 = seal(b"vintage 2026 secret", VAULT_KEY, label="2026")
        env_v1_json = env_v1.to_json()

        # Simulate a v2 release: new schema + new crypto suite registered.
        # Critically, the old v1 mac_input function and the alpha-v1 suite
        # MUST stay in their registries.
        def _mac_input_v2(self) -> bytes:  # noqa: N805 - mirrors method signature
            # Imaginary v2 layout adds a new field
            import json
            from src.protocols.escrow_7d.envelope import _b64e
            payload = {
                "schema_version": self.schema_version,
                "min_reader_version": self.min_reader_version,
                "crypto_suite": self.crypto_suite,
                "producer": self.producer,
                "escrow_id": self.escrow_id,
                "deposited_at": self.deposited_at,
                "depositor_vault_id_prefix": self.depositor_vault_id_prefix,
                "label": self.label,
                "conditions": self.conditions,
                "kdf_salt": _b64e(self.kdf_salt),
                "aes_nonce": _b64e(self.aes_nonce),
                "ciphertext": _b64e(self.ciphertext),
                "aes_tag": _b64e(self.aes_tag),
                "payload_size": self.payload_size,
                "imaginary_v2_field": "demo",  # new in v2
            }
            return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

        _MAC_INPUT_BY_VERSION[2] = _mac_input_v2

        fv = sys.modules["src.protocols.escrow_7d.format_version"]
        fv.SUPPORTED_SCHEMA_VERSIONS = frozenset({1, 2})
        _REGISTRY["alpha-v2"] = CryptoSuite(
            name="alpha-v2",
            aead_algo="aes-256-gcm",
            kdf_algo="hkdf-sha256",
            mac_algo="hmac-sha256",
            session_key_info=b"EIDOLON_ESCROW_SESSION_KEY_v2",
            integrity_info=b"EIDOLON_ESCROW_INTEGRITY_v2",
        )

        # Now load the v1 envelope under the simulated v2 build
        reloaded = EscrowEnvelope.from_json(env_v1_json)
        self.assertEqual(reloaded.schema_version, 1, "must NOT be auto-migrated")
        self.assertEqual(reloaded.crypto_suite, "alpha-v1")

        ok, reason = verify(reloaded, VAULT_KEY)
        self.assertTrue(ok, f"v1 envelope failed to verify under v2 build: {reason}")

        decoded = unseal(reloaded, VAULT_KEY)
        self.assertEqual(decoded, b"vintage 2026 secret")

    def test_unknown_schema_version_refused(self):
        env_v1 = seal(b"data", VAULT_KEY)
        d = env_v1.to_dict()
        d["schema_version"] = 99  # not in registry
        with self.assertRaises(FormatError):
            EscrowEnvelope.from_dict(d)

    def test_unknown_crypto_suite_refused(self):
        env_v1 = seal(b"data", VAULT_KEY)
        d = env_v1.to_dict()
        d["crypto_suite"] = "alpha-v99"
        with self.assertRaises(FormatError):
            EscrowEnvelope.from_dict(d)

    def test_reseal_preserves_payload_and_conditions(self):
        past = datetime.now(timezone.utc) - timedelta(seconds=5)
        env = seal(b"important", VAULT_KEY, conditions=[TimeLock(past)], label="lbl")
        new_env = reseal(env, VAULT_KEY)
        self.assertNotEqual(new_env.escrow_id, env.escrow_id)
        self.assertNotEqual(new_env.kdf_salt, env.kdf_salt)
        self.assertNotEqual(new_env.aes_nonce, env.aes_nonce)
        self.assertEqual(new_env.label, "lbl")
        self.assertEqual(unseal(new_env, VAULT_KEY), b"important")
        self.assertTrue(is_current_format(new_env))


if __name__ == "__main__":
    unittest.main(verbosity=2)
