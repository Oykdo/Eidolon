"""Functional tests for the Escrow Nexus public API, store and CLI.

Complements test_escrow_7d_backward_compat.py (in-memory sealer/envelope) with
what happens on disk and at the API boundary: lifecycle, isolation between
vaults, corrupt files, the error contract, the golden v1 vector, and the CLI
safety rules (an interrupted prompt never writes anything).

Every test uses its own vault key, so its escrows live in their own
``escrows/<prefix>/`` directory under an isolated EIDOLON_DATA_DIR (set by
tests/conftest.py under pytest, or by this module under unittest).
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import secrets
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

# tests/conftest.py isolates EIDOLON_DATA_DIR under pytest; do the same for the
# unittest runner so this module never writes into the real user data directory.
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-escrow-tests-"))

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.protocols.escrow_7d import (  # noqa: E402
    CombinedAll,
    CombinedAny,
    ConditionError,
    EscrowError,
    EscrowStoreError,
    FormatError,
    OwnerSignature,
    TimeLock,
    UnsealError,
    delete_escrow,
    deposit_document,
    list_escrows,
    list_unreadable_escrows,
    retrieve_document,
    vault_id_from_key,
    verify_integrity,
    verify_provenance,
)
from src.protocols.escrow_7d import cli, sealer  # noqa: E402
from src.protocols.escrow_7d.conditions import MAX_CONDITION_DEPTH, Condition  # noqa: E402
from src.protocols.escrow_7d.envelope import EscrowEnvelope  # noqa: E402
from src.protocols.escrow_7d.format_version import (  # noqa: E402
    READER_VERSION,
    SUPPORTED_SCHEMA_VERSIONS,
)
from src.protocols.escrow_7d.store import EscrowStore  # noqa: E402
from config.paths import get_vaults_root  # noqa: E402

VECTORS = ROOT / "tests" / "vectors"


_RUN = secrets.token_hex(4)  # keys differ per run, so a reused data dir never collides


def _key(name: str) -> bytes:
    """A distinct 32-byte vault key per test (and per run), derived from its name."""
    return hashlib.sha256(f"escrow-test-{_RUN}-{name}".encode()).digest()


def _prefix(vault_key: bytes) -> str:
    return hashlib.sha256(vault_key).hexdigest()[:16]


def _escrow_dir(vault_key: bytes) -> Path:
    return get_vaults_root() / "escrows" / _prefix(vault_key)


def _envelope_path(vault_key: bytes, escrow_id: str) -> Path:
    return _escrow_dir(vault_key) / f"{escrow_id}.escrow7d"


# ---------------------------------------------------------------------------
# 1. Lifecycle on disk
# ---------------------------------------------------------------------------

class LifecycleTests(unittest.TestCase):
    def test_deposit_list_verify_retrieve_delete(self):
        key = _key("lifecycle")
        escrow_id = deposit_document(b"hello escrow", key, label="note.txt")
        self.assertTrue(escrow_id.startswith("esc_"))
        self.assertTrue(_envelope_path(key, escrow_id).is_file())

        summaries = list_escrows(key)
        self.assertEqual([s["escrow_id"] for s in summaries], [escrow_id])
        self.assertEqual(summaries[0]["label"], "note.txt")
        self.assertEqual(summaries[0]["payload_size"], 12)
        self.assertEqual(list_unreadable_escrows(key), [])

        self.assertEqual(verify_integrity(escrow_id, key), (True, "integrity ok"))
        self.assertEqual(retrieve_document(escrow_id, key), b"hello escrow")

        self.assertTrue(delete_escrow(escrow_id, key))
        self.assertFalse(delete_escrow(escrow_id, key))
        with self.assertRaises(KeyError):
            retrieve_document(escrow_id, key)
        self.assertFalse(verify_integrity(escrow_id, key)[0])

    def test_empty_and_bytearray_payloads(self):
        key = _key("payloads")
        empty = deposit_document(b"", key)
        self.assertEqual(retrieve_document(empty, key), b"")
        ba = deposit_document(bytearray(b"mutable"), key)
        self.assertEqual(retrieve_document(ba, key), b"mutable")

    def test_label_round_trips_verbatim(self):
        key = _key("label")
        label = 'He said "hi"\nline2\ttab é中😀 ../../x'
        escrow_id = deposit_document(b"x", key, label=label)
        self.assertEqual(list_escrows(key)[0]["label"], label)
        self.assertEqual(retrieve_document(escrow_id, key), b"x")

    def test_time_lock_blocks_then_releases(self):
        key = _key("timelock")
        future = TimeLock(datetime.now(timezone.utc) + timedelta(days=365))
        locked = deposit_document(b"later", key, conditions=[future])
        with self.assertRaises(UnsealError) as ctx:
            retrieve_document(locked, key)
        self.assertIn("time_lock", str(ctx.exception))
        # The lock never touched the ciphertext: integrity still verifies.
        self.assertTrue(verify_integrity(locked, key)[0])

        past = TimeLock(datetime.now(timezone.utc) - timedelta(seconds=5))
        released = deposit_document(b"now", key, conditions=[past])
        self.assertEqual(retrieve_document(released, key), b"now")

    def test_condition_depth_is_bounded_deterministically(self):
        key = _key("depth")
        past = TimeLock(datetime(2000, 1, 1, tzinfo=timezone.utc))

        def nest(levels):
            cond = past
            for _ in range(levels):
                cond = CombinedAll(cond)
            return cond

        ok = deposit_document(b"deep", key, conditions=[nest(MAX_CONDITION_DEPTH)])
        self.assertEqual(retrieve_document(ok, key), b"deep")
        with self.assertRaises(sealer.SealError) as ctx:
            deposit_document(b"deeper", key, conditions=[nest(MAX_CONDITION_DEPTH + 1)])
        self.assertIn("deeper than", str(ctx.exception))
        # A stored tree beyond the bound (crafted by the key holder) is refused
        # with the same verdict whatever the reader's stack depth.
        env = sealer.seal(b"x", key)
        raw = past.to_dict()
        for _ in range(MAX_CONDITION_DEPTH + 1):
            raw = {"type": "combined_all", "children": [raw]}
        env.conditions = [raw]
        suite = sealer.get_suite(env.crypto_suite)
        ikey = sealer._hkdf(key, env.kdf_salt, suite.integrity_info, suite.mac_len)
        env.integrity_mac = sealer._mac(suite, ikey, env.mac_input())
        EscrowStore(_prefix(key)).save(env)
        with self.assertRaises(UnsealError) as ctx:
            retrieve_document(env.escrow_id, key)
        self.assertIn("deeper than", str(ctx.exception))

    def test_combined_any_and_all(self):
        key = _key("composite")
        past = TimeLock(datetime(2000, 1, 1, tzinfo=timezone.utc))
        future = TimeLock(datetime(2999, 1, 1, tzinfo=timezone.utc))
        any_id = deposit_document(b"any", key, conditions=[CombinedAny(future, past)])
        self.assertEqual(retrieve_document(any_id, key), b"any")
        all_id = deposit_document(b"all", key, conditions=[CombinedAll(past, future)])
        with self.assertRaises(UnsealError):
            retrieve_document(all_id, key)


# ---------------------------------------------------------------------------
# 1b. OwnerSignature: bound to the key, never bypassable, never self-locking
# ---------------------------------------------------------------------------

class OwnerSignatureTests(unittest.TestCase):
    def test_prefix_full_id_and_for_vault_key_all_open(self):
        key = _key("owner-forms")
        full = vault_id_from_key(key)
        for cond in (
            OwnerSignature(full),
            OwnerSignature(full.upper()),
            OwnerSignature(full[:16]),
            OwnerSignature.for_vault_key(key),
        ):
            with self.subTest(expected=cond.expected_vault_id):
                escrow_id = deposit_document(b"mine", key, conditions=[cond])
                self.assertEqual(retrieve_document(escrow_id, key), b"mine")
        # The prefix form is exactly what the summary shows.
        self.assertEqual(list_escrows(key)[0]["depositor_vault_id_prefix"], full[:16])

    def test_another_vault_is_refused_at_seal_time(self):
        key, other = _key("owner-a"), _key("owner-b")
        other_id = vault_id_from_key(other)
        past = TimeLock(datetime(2000, 1, 1, tzinfo=timezone.utc))
        for conds in (
            [OwnerSignature(other_id)],
            [OwnerSignature(other_id[:16])],
            [CombinedAll(past, OwnerSignature(other_id))],
            [CombinedAny(past, CombinedAll(past, OwnerSignature(other_id)))],
        ):
            with self.subTest(conds=[c.type_id for c in conds]):
                with self.assertRaises(sealer.SealError) as ctx:
                    deposit_document(b"x", key, conditions=conds)
                self.assertIn("could never be opened", str(ctx.exception))
        self.assertEqual(list_escrows(key), [])

    def test_context_cannot_impersonate(self):
        key, other = _key("owner-ctx"), _key("owner-ctx-other")
        # A stored envelope naming another vault (crafted by re-MACing, which
        # only the key holder can do) stays closed whatever the caller claims.
        env = sealer.seal(b"x", key)
        env.conditions = [OwnerSignature.for_vault_key(other).to_dict()]
        suite = sealer.get_suite(env.crypto_suite)
        ikey = sealer._hkdf(key, env.kdf_salt, suite.integrity_info, suite.mac_len)
        env.integrity_mac = sealer._mac(suite, ikey, env.mac_input())
        EscrowStore(_prefix(key)).save(env)
        for context in (None, {"requester_vault_id": vault_id_from_key(other)}):
            with self.subTest(context=context):
                with self.assertRaises(UnsealError) as ctx:
                    retrieve_document(env.escrow_id, key, context=context)
                self.assertIn("does not match depositor", str(ctx.exception))
        # And a bogus context does not lock the real owner out either.
        mine = deposit_document(b"ok", key, conditions=[OwnerSignature.for_vault_key(key)])
        self.assertEqual(
            retrieve_document(mine, key, context={"requester_vault_id": "nobody"}), b"ok"
        )

    def test_invalid_identifiers_are_condition_errors(self):
        for bad in ("", "nobody", "deadbeef", "g" * 16, "0" * 65, None, 7):
            with self.subTest(bad=bad):
                with self.assertRaises(ConditionError):
                    OwnerSignature(bad)  # type: ignore[arg-type]
                with self.assertRaises(ConditionError):
                    Condition.deserialize({"type": "owner_signature", "expected_vault_id": bad})

    def test_combined_any_with_owner_releases_immediately(self):
        key = _key("owner-any")
        future = TimeLock(datetime(2999, 1, 1, tzinfo=timezone.utc))
        escrow_id = deposit_document(
            b"x", key, conditions=[CombinedAny(future, OwnerSignature.for_vault_key(key))]
        )
        self.assertEqual(retrieve_document(escrow_id, key), b"x")

    def test_prefix_is_stored_as_the_full_id(self):
        key = _key("owner-canonical")
        full = vault_id_from_key(key)
        escrow_id = deposit_document(
            b"x", key, conditions=[CombinedAll(OwnerSignature(full[:16].upper()))]
        )
        stored = json.loads(_envelope_path(key, escrow_id).read_text(encoding="utf-8"))
        self.assertEqual(
            stored["conditions"],
            [{"type": "combined_all", "children": [
                {"type": "owner_signature", "expected_vault_id": full}]}],
        )

    def test_seal_checks_the_stored_bytes_not_the_objects(self):
        key, other = _key("owner-sneaky"), _key("owner-sneaky-other")

        class Sneaky(TimeLock):
            """Claims to be a time lock but stores another vault's owner_signature."""

            def to_dict(self):
                return OwnerSignature.for_vault_key(other).to_dict()

        past = datetime(2000, 1, 1, tzinfo=timezone.utc)
        with self.assertRaises(sealer.SealError):
            deposit_document(b"x", key, conditions=[Sneaky(past)])
        self.assertEqual(list_escrows(key), [])

    def test_context_must_be_a_mapping(self):
        key = _key("owner-context-type")
        escrow_id = deposit_document(b"x", key)
        for bad in ("requester_vault_id", 1, [("requester_vault_id", "x")]):
            with self.subTest(bad=bad):
                with self.assertRaises(UnsealError):
                    retrieve_document(escrow_id, key, context=bad)  # type: ignore[arg-type]
        self.assertEqual(retrieve_document(escrow_id, key, context={}), b"x")

    def test_walk_reaches_nested_leaves(self):
        past = TimeLock(datetime(2000, 1, 1, tzinfo=timezone.utc))
        tree = CombinedAll(past, CombinedAny(past, OwnerSignature("0" * 16)))
        self.assertEqual(
            [c.type_id for c in tree.walk()],
            ["combined_all", "time_lock", "combined_any", "time_lock", "owner_signature"],
        )


# ---------------------------------------------------------------------------
# 2. Input validation at the API boundary
# ---------------------------------------------------------------------------

class ValidationTests(unittest.TestCase):
    def test_non_bytes_payload_rejected(self):
        with self.assertRaises(TypeError):
            deposit_document("text", _key("validation"))  # type: ignore[arg-type]

    def test_non_str_label_rejected_before_anything_is_written(self):
        # A non-str label used to seal an envelope whose MAC could never be
        # verified again (MAC over 42, reloaded as "42"). It must be refused.
        key = _key("label-type")
        for bad in (42, 1.5, True, ["a"], {"a": 1}):
            with self.assertRaises(TypeError):
                deposit_document(b"x", key, label=bad)  # type: ignore[arg-type]
            with self.assertRaises(sealer.SealError):
                sealer.seal(b"x", key, label=bad)  # type: ignore[arg-type]
        self.assertEqual(list_escrows(key), [])
        self.assertFalse(_escrow_dir(key).exists())

    def test_none_label_means_empty(self):
        key = _key("label-none")
        escrow_id = deposit_document(b"x", key, label=None)  # type: ignore[arg-type]
        self.assertEqual(list_escrows(key)[0]["label"], "")
        self.assertEqual(retrieve_document(escrow_id, key), b"x")

    def test_short_key_rejected(self):
        with self.assertRaises(sealer.SealError):
            deposit_document(b"x", b"k" * 31)

    def test_bad_escrow_ids_are_store_errors(self):
        key = _key("bad-ids")
        for bad in ("", "a/b", "a\\b", "..\\..\\x"):
            with self.assertRaises(EscrowStoreError):
                retrieve_document(bad, key)
            with self.assertRaises(EscrowStoreError):
                delete_escrow(bad, key)
            self.assertFalse(verify_integrity(bad, key)[0])
        # Unknown but well-formed ids are simply absent.
        with self.assertRaises(KeyError):
            retrieve_document("esc_" + "0" * 32, key)
        self.assertEqual(verify_integrity("esc_" + "0" * 32, key)[0], False)


# ---------------------------------------------------------------------------
# 3. Isolation between vaults, read-only calls leave no trace
# ---------------------------------------------------------------------------

class IsolationTests(unittest.TestCase):
    def test_other_vault_cannot_see_or_open(self):
        a, b = _key("iso-a"), _key("iso-b")
        escrow_id = deposit_document(b"A's", a, label="a")
        self.assertEqual(list_escrows(b), [])
        with self.assertRaises(KeyError):
            retrieve_document(escrow_id, b)
        # A's file copied into B's directory is reported as foreign, never
        # listed as B's, and (one layer down) B's key does not verify A's MAC.
        _escrow_dir(b).mkdir(parents=True, exist_ok=True)
        (_escrow_dir(b) / f"{escrow_id}.escrow7d").write_bytes(
            _envelope_path(a, escrow_id).read_bytes()
        )
        ok, reason = verify_integrity(escrow_id, b)
        self.assertFalse(ok)
        self.assertIn("another vault", reason)
        with self.assertRaises(EscrowStoreError):
            retrieve_document(escrow_id, b)
        self.assertEqual(list_escrows(b), [])
        self.assertEqual([u["escrow_id"] for u in list_unreadable_escrows(b)], [escrow_id])
        env = EscrowEnvelope.from_json(_envelope_path(a, escrow_id).read_text(encoding="utf-8"))
        self.assertIn("MAC mismatch", sealer.verify(env, b)[1])

    def test_read_only_calls_create_no_directory(self):
        key = _key("no-trace")
        self.assertEqual(list_escrows(key), [])
        self.assertEqual(list_unreadable_escrows(key), [])
        self.assertFalse(verify_integrity("esc_" + "1" * 32, key)[0])
        self.assertFalse(delete_escrow("esc_" + "1" * 32, key))
        with self.assertRaises(KeyError):
            retrieve_document("esc_" + "1" * 32, key)
        self.assertFalse(_escrow_dir(key).exists())

    def test_store_scope_is_enforced_on_save(self):
        a, b = _key("scope-a"), _key("scope-b")
        env = sealer.seal(b"x", a)
        with self.assertRaises(EscrowStoreError):
            EscrowStore(_prefix(b)).save(env)
        with self.assertRaises(EscrowStoreError):
            EscrowStore("not-a-prefix")


# ---------------------------------------------------------------------------
# 4. Corrupt files: reported, never hidden, never a raw exception
# ---------------------------------------------------------------------------

class CorruptFileTests(unittest.TestCase):
    def _plant(self, key: bytes, name: str, content) -> str:
        d = _escrow_dir(key)
        d.mkdir(parents=True, exist_ok=True)
        data = content if isinstance(content, bytes) else content.encode("utf-8")
        (d / f"{name}.escrow7d").write_bytes(data)
        return name

    def _good_json(self, key: bytes) -> dict:
        escrow_id = deposit_document(b"ok", key, label="good")
        return json.loads(_envelope_path(key, escrow_id).read_text(encoding="utf-8"))

    def test_every_corruption_is_an_escrow_error(self):
        key = _key("corrupt")
        good = self._good_json(key)
        deep = '{"type":"combined_all","children":[' * 1500 + "{}" + "]}" * 1500
        cases = {
            "esc_badjson": "{not json",
            "esc_missing": json.dumps({"schema_version": 1}),
            "esc_null": "null",
            "esc_badb64": json.dumps({**good, "ciphertext": "QUJDRA"}),  # bad padding
            "esc_b64none": json.dumps({**good, "kdf_salt": None}),
            "esc_b64utf": json.dumps({**good, "aes_tag": "é"}),
            "esc_schemastr": json.dumps({**good, "schema_version": "abc"}),
            "esc_schemanone": json.dumps({**good, "schema_version": None}),
            "esc_overflow": json.dumps({**good, "payload_size": 1e400}),
            "esc_idint": json.dumps({**good, "escrow_id": 7}),
            "esc_copy": json.dumps(good),  # valid envelope, wrong file name
            "esc_condstr": json.dumps({**good, "conditions": "abc"}),
            "esc_condint": json.dumps({**good, "conditions": [5]}),
            "esc_utf16": "{}".encode("utf-16"),
            "esc_deep": json.dumps({**good, "conditions": []}).replace(
                '"conditions": []', '"conditions": [' + deep + "]"
            ),
        }
        for name, content in cases.items():
            self._plant(key, name, content)

        for name in cases:
            with self.subTest(name=name):
                with self.assertRaises(EscrowStoreError):
                    retrieve_document(name, key)
                ok, reason = verify_integrity(name, key)
                self.assertFalse(ok)
                self.assertIn("unreadable", reason)

        # Non-alphabet characters are dropped by the lenient base64 decoder
        # (format tolerance): such a file parses, then fails its MAC.
        junk_id = good["escrow_id"]
        junk_path = _envelope_path(key, junk_id)
        original = junk_path.read_bytes()
        junk_path.write_text(json.dumps({**good, "ciphertext": "!!!"}), encoding="utf-8")
        with self.assertRaises(UnsealError):
            retrieve_document(junk_id, key)
        self.assertIn("MAC mismatch", verify_integrity(junk_id, key)[1])
        junk_path.write_bytes(original)

        # A directory named like an envelope is neither readable nor deletable.
        (_escrow_dir(key) / "esc_dir.escrow7d").mkdir()
        with self.assertRaises(KeyError):
            retrieve_document("esc_dir", key)
        self.assertFalse(delete_escrow("esc_dir", key))
        self.assertEqual(len(list_escrows(key)), 1)

        # The good one is listed; every bad one is reported, none hidden.
        self.assertEqual(len(list_escrows(key)), 1)
        unreadable = {u["escrow_id"] for u in list_unreadable_escrows(key)}
        self.assertEqual(unreadable, set(cases))
        self.assertEqual(len(EscrowStore(_prefix(key))), 1 + len(cases))

    def test_unreadable_file_can_still_be_deleted(self):
        key = _key("delete-unreadable")
        deposit_document(b"x", key)
        self._plant(key, "esc_bad", "{broken")
        self.assertEqual([u["escrow_id"] for u in list_unreadable_escrows(key)], ["esc_bad"])
        self.assertTrue(delete_escrow("esc_bad", key))
        self.assertEqual(list_unreadable_escrows(key), [])

    def test_stray_tmp_file_is_ignored(self):
        key = _key("tmp")
        deposit_document(b"x", key)
        (_escrow_dir(key) / "esc_crash.escrow7d.tmp").write_text("x")
        self.assertEqual(len(list_escrows(key)), 1)
        self.assertEqual(list_unreadable_escrows(key), [])

    def test_orphan_tmp_file_is_swept_by_the_next_save_only_when_stale(self):
        # A crash between write and rename leaves ``<id>.escrow7d.tmp`` behind.
        # Read paths never touch it; the next save removes it once it is older
        # than the sweep age, so a write in flight elsewhere is never deleted.
        key = _key("tmp-sweep")
        first = deposit_document(b"x", key)
        stale = _escrow_dir(key) / "esc_crash.escrow7d.tmp"
        fresh = _escrow_dir(key) / "esc_inflight.escrow7d.tmp"
        stale.write_text("x")
        fresh.write_text("y")
        old = time.time() - 3600
        os.utime(stale, (old, old))

        list_escrows(key)
        self.assertEqual(verify_integrity(first, key)[0], True)
        self.assertTrue(stale.exists() and fresh.exists())  # reads leave the disk alone

        deposit_document(b"y", key)
        self.assertFalse(stale.exists())
        self.assertTrue(fresh.exists())
        self.assertEqual(len(list_escrows(key)), 2)
        self.assertEqual(list_unreadable_escrows(key), [])
        fresh.unlink()

    def test_unknown_condition_type_in_mac_valid_envelope_is_unseal_error(self):
        key = _key("unknown-cond")
        env = sealer.seal(b"x", key)
        env.conditions = [{"type": "nope"}]
        # Re-MAC so the condition list is authentic (only the key holder can).
        suite = sealer.get_suite(env.crypto_suite)
        ikey = sealer._hkdf(key, env.kdf_salt, suite.integrity_info, suite.mac_len)
        env.integrity_mac = sealer._mac(suite, ikey, env.mac_input())
        EscrowStore(_prefix(key)).save(env)
        with self.assertRaises(UnsealError) as ctx:
            retrieve_document(env.escrow_id, key)
        self.assertIn("invalid release condition", str(ctx.exception))

    def test_condition_deserialisers_raise_condition_error(self):
        for bad in (
            "not a dict",
            {"type": "time_lock", "release_after": None},
            {"type": "time_lock", "release_after": 5},
            {"type": "owner_signature", "expected_vault_id": 7},
            {"type": "combined_all", "children": "x"},
            {"type": "combined_all", "children": []},
            {"type": "combined_any", "children": ["x"]},
            {"type": None},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ConditionError):
                    Condition.deserialize(bad)  # type: ignore[arg-type]

    def test_error_hierarchy(self):
        for exc in (EscrowStoreError, FormatError, ConditionError, sealer.SealError, UnsealError):
            self.assertTrue(issubclass(exc, EscrowError), exc)

    def test_from_json_rejects_non_object_and_deep_nesting(self):
        with self.assertRaises(FormatError):
            EscrowEnvelope.from_json("[]")
        with self.assertRaises(FormatError):
            EscrowEnvelope.from_json("[" * 100000 + "]" * 100000)


# ---------------------------------------------------------------------------
# 5. Format guards: golden v1 vector and RFC 5869
# ---------------------------------------------------------------------------

class GoldenVectorTests(unittest.TestCase):
    """The v1 wire format is frozen. If this fails, stored escrows are unreadable."""

    @classmethod
    def setUpClass(cls):
        cls.v = json.loads((VECTORS / "escrow_7d_v1.json").read_text(encoding="utf-8"))
        cls.key = bytes.fromhex(cls.v["vault_key_hex"])
        cls.env = EscrowEnvelope.from_dict(cls.v["envelope"])

    def test_mac_input_bytes_are_frozen(self):
        self.assertEqual(self.env.mac_input().hex(), self.v["mac_input_hex"])

    def test_verify_and_unseal(self):
        self.assertEqual(sealer.verify(self.env, self.key), (True, "integrity ok"))
        self.assertEqual(sealer.unseal(self.env, self.key), bytes.fromhex(self.v["payload_hex"]))

    def test_wrong_key_reason(self):
        ok, reason = sealer.verify(self.env, bytes.fromhex(self.v["wrong_key_hex"]))
        self.assertFalse(ok)
        self.assertEqual(reason, self.v["expected_wrong_key_reason"])

    def test_derived_keys(self):
        suite = sealer.get_suite(self.env.crypto_suite)
        session = sealer._hkdf(
            self.key, self.env.kdf_salt, suite.session_key_info, suite.session_key_len
        )
        integrity = sealer._hkdf(self.key, self.env.kdf_salt, suite.integrity_info, suite.mac_len)
        self.assertEqual(session.hex(), self.v["session_key_hex"])
        self.assertEqual(integrity.hex(), self.v["integrity_key_hex"])

    def test_resealing_the_vector_reproduces_the_mac(self):
        # Same key, salt, nonce, id, timestamp, label and conditions -> same MAC.
        salt, nonce = self.env.kdf_salt, self.env.aes_nonce
        saved = (sealer.os.urandom, sealer.secrets.token_hex, sealer.datetime)

        class _FixedDT(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime.fromisoformat(self.env.deposited_at)

        sealer.os.urandom = lambda n: salt if n == len(salt) else nonce
        sealer.secrets.token_hex = lambda n=16: self.env.escrow_id[len("esc_"):]
        sealer.datetime = _FixedDT
        try:
            conds = [Condition.deserialize(c) for c in self.env.conditions]
            resealed = sealer.seal(bytes.fromhex(self.v["payload_hex"]), self.key,
                                   conditions=conds, label=self.env.label)
        finally:
            sealer.os.urandom, sealer.secrets.token_hex, sealer.datetime = saved
        self.assertEqual(resealed.to_dict(), self.v["envelope"])


class HkdfVectorTests(unittest.TestCase):
    """RFC 5869 appendix A, SHA-256 cases, against the package's own HKDF."""

    CASES = [
        (  # A.1
            "0b" * 22, "000102030405060708090a0b0c", "f0f1f2f3f4f5f6f7f8f9", 42,
            "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865",
        ),
        (  # A.2
            "".join(f"{i:02x}" for i in range(0x00, 0x50)),
            "".join(f"{i:02x}" for i in range(0x60, 0xb0)),
            "".join(f"{i:02x}" for i in range(0xb0, 0x100)), 82,
            "b11e398dc80327a1c8e7f78c596a49344f012eda2d4efad8a050cc4c19afa97c"
            "59045a99cac7827271cb41c65e590e09da3275600c2f09b8367793a9aca3db71"
            "cc30c58179ec3e87c14c01d5c1f3434f1d87",
        ),
        (  # A.3
            "0b" * 22, "", "", 42,
            "8da4e775a563c18f715f802a063c5a31b8a11f5c5ee1879ec3454e5f3c738d2d9d201395faa4b61a96c8",
        ),
    ]

    def test_rfc5869_sha256(self):
        for ikm, salt, info, length, okm in self.CASES:
            with self.subTest(length=length):
                out = sealer._hkdf(
                    bytes.fromhex(ikm), bytes.fromhex(salt), bytes.fromhex(info), length
                )
                self.assertEqual(out.hex(), okm)

    def test_reader_version_is_the_highest_supported_schema(self):
        self.assertEqual(READER_VERSION, max(SUPPORTED_SCHEMA_VERSIONS))

    def test_provenance(self):
        self.assertTrue(verify_provenance())


# ---------------------------------------------------------------------------
# 6. CLI safety: an interrupted prompt never writes, invalid lock never silent
# ---------------------------------------------------------------------------

class _Inputs:
    """Feed scripted answers to cli._prompt; an exception instance is raised."""

    def __init__(self, answers):
        self.answers = list(answers)

    def __call__(self, _msg=""):
        if not self.answers:
            raise EOFError
        item = self.answers.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class CliTests(unittest.TestCase):
    def _run(self, fn, key, answers):
        import builtins
        buf = io.StringIO()
        saved = builtins.input
        builtins.input = _Inputs(answers)
        try:
            with redirect_stdout(buf):
                fn(key, "vault #test")
        finally:
            builtins.input = saved
        return buf.getvalue()

    def test_interrupt_at_save_prompt_writes_nothing(self):
        key = _key("cli-interrupt")
        deposit_document(b"my inline secret", key, label="inline")
        default = (Path.home() / "Downloads" / "inline.txt")
        before = default.exists()
        for interrupt in (EOFError(), KeyboardInterrupt()):
            out = self._run(cli._action_retrieve, key, ["1", interrupt])
            self.assertIn("cancelled", out)
            self.assertNotIn("bytes written", out)
        self.assertEqual(default.exists(), before)

    def test_quit_at_save_prompt_writes_nothing(self):
        key = _key("cli-quit")
        deposit_document(b"secret", key, label="s")
        out = self._run(cli._action_retrieve, key, ["1", "q"])
        self.assertIn("nothing written", out)

    def test_retrieve_writes_to_chosen_path_and_asks_before_overwrite(self):
        key = _key("cli-write")
        deposit_document(b"payload", key, label="doc.txt")
        target = get_vaults_root().parent / f"cli_out_{_RUN}" / "doc.txt"
        out = self._run(cli._action_retrieve, key, ["1", str(target)])
        self.assertIn("written", out)
        self.assertEqual(target.read_bytes(), b"payload")
        for refusal in ("no", "overwrite", ""):
            out = self._run(cli._action_retrieve, key, ["1", str(target), refusal])
            self.assertIn("nothing written", out)
        out = self._run(cli._action_retrieve, key, ["1", str(target), "OVERWRITE"])
        self.assertIn("written", out)

    def test_invalid_time_lock_is_reasked_not_silently_dropped(self):
        key = _key("cli-lock")
        answers = ["", "secret text", "lbl", "7d", "-1", "2"]
        out = self._run(cli._action_deposit, key, answers)
        self.assertIn("not a whole number", out)
        self.assertIn("must be >= 0", out)
        self.assertIn("time lock set until", out)
        conds = list_escrows(key)[0]["conditions"]
        self.assertEqual(conds, ["time_lock"])

    def test_zero_lock_is_announced(self):
        key = _key("cli-nolock")
        out = self._run(cli._action_deposit, key, ["", "secret text", "lbl", "0"])
        self.assertIn("no time lock", out)

    def test_interrupt_during_deposit_deposits_nothing(self):
        key = _key("cli-dep-int")
        self._run(cli._action_deposit, key, ["", "secret", KeyboardInterrupt()])
        self.assertEqual(list_escrows(key), [])

    def test_verify_all_counts_unreadable_files(self):
        key = _key("cli-verify")
        deposit_document(b"x", key)
        (_escrow_dir(key) / "esc_bad.escrow7d").write_text("{broken")
        out = self._run(cli._action_verify, key, ["all"])
        self.assertIn("esc_bad: unreadable", out)
        self.assertIn("verified 1 ok / 1 failed", out)

    def test_list_shows_unreadable_files(self):
        key = _key("cli-list")
        deposit_document(b"x", key)
        (_escrow_dir(key) / "esc_bad.escrow7d").write_text("{broken")
        out = self._run(cli._action_list, key, [])
        self.assertIn("unreadable: esc_bad", out)

    def test_list_shows_unreadable_files_even_without_readable_ones(self):
        key = _key("cli-list-only-bad")
        _escrow_dir(key).mkdir(parents=True, exist_ok=True)
        (_escrow_dir(key) / "esc_bad.escrow7d").write_text("{broken")
        out = self._run(cli._action_list, key, [])
        self.assertIn("no escrows", out)
        self.assertIn("unreadable: esc_bad", out)

    def test_delete_requires_exact_token_and_handles_unreadable(self):
        key = _key("cli-delete")
        escrow_id = deposit_document(b"x", key)
        (_escrow_dir(key) / "esc_bad.escrow7d").write_text("{broken")
        out = self._run(cli._action_delete, key, [escrow_id, "delete"])
        self.assertIn("aborted", out)
        self.assertEqual(len(list_escrows(key)), 1)
        self._run(cli._action_delete, key, [escrow_id, KeyboardInterrupt()])
        self.assertEqual(len(list_escrows(key)), 1)
        out = self._run(cli._action_delete, key, ["esc_bad", "DELETE"])
        self.assertIn("removed", out)
        self.assertEqual(list_unreadable_escrows(key), [])
        out = self._run(cli._action_delete, key, [escrow_id, "DELETE"])
        self.assertIn("removed", out)
        self.assertEqual(list_escrows(key), [])

    def test_menu_treats_interrupt_inside_an_action_as_cancel(self):
        import builtins
        key = _key("cli-menu-int")
        buf = io.StringIO()
        saved = builtins.input
        # "1" opens Deposit; its first prompt raises KeyboardInterrupt (cancel),
        # "Press Enter" gets "", then "Q" leaves the menu.
        builtins.input = _Inputs(["1", KeyboardInterrupt(), "", "Q"])
        try:
            with redirect_stdout(buf):
                cli.escrow_menu(key, "vault #test")
        finally:
            builtins.input = saved
        self.assertIn("cancelled", buf.getvalue())
        self.assertEqual(list_escrows(key), [])

    def test_menu_survives_eof(self):
        buf = io.StringIO()
        import builtins
        saved = builtins.input
        builtins.input = _Inputs(["2", EOFError()])
        try:
            with redirect_stdout(buf):
                cli.escrow_menu(_key("cli-menu"), "vault #test")
        finally:
            builtins.input = saved
        self.assertIn("no escrows", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
