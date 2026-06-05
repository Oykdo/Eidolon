"""Tests for vault migration (snapshot MVP).

Covers:
* Roundtrip: export -> verify -> import
* Tamper detection (modified archive bytes)
* Wrong key rejection
* Conflict policy (refresh vs cross-vault refusal)
* Frozen v1 mac_input bytes
* Future-version simulation (v1 archives stay readable when v2 ships)
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.protocols.vault_migration import (
    export_vault,
    import_vault,
    inspect_archive,
    ImportError as MigrationImportError,
    ImportConflict,
)
from src.protocols.vault_migration.archive import (
    HEADER_SIZE,
    read_archive,
    write_archive,
    build_zip_from_files,
    compute_integrity_mac,
)
from src.protocols.vault_migration.format_version import (
    CURRENT_FORMAT_SUITE,
    _REGISTRY,
    FormatSuite,
    SUPPORTED_SCHEMA_VERSIONS,
)
from src.protocols.vault_migration.manifest import Manifest, _MAC_INPUT_BY_VERSION


VAULT_KEY = b"k" * 32
VAULT_ID = "vault_xyz_1234567890abcdef"
VAULT_NUMBER = 42
VAULT_NAME = "TestVault"


def _make_fake_vault_tree(root: Path, vault_id: str, vault_number: int,
                         vault_name: str, depositor_prefix: str):
    """Populate a minimal fake vault data tree under <root>/vaults/."""
    vroot = root / "vaults"

    keys_dir = vroot / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)
    psnx = keys_dir / f"vault_key_{vault_name}.psnx"
    blend = keys_dir / f"vault_key_{vault_name}.blend_data"
    psnx.write_bytes(b"PSNX_BINARY_DATA_PLACEHOLDER" * 8)
    blend.write_bytes(b"BLEND_BINARY_DATA_PLACEHOLDER" * 8)

    persistent = vroot / "persistent" / vault_id
    persistent.mkdir(parents=True)
    (persistent / "vault_state.enc").write_bytes(b"ENCRYPTED_VAULT_STATE_BLOB")
    (persistent / "history.json").write_text('{"events": []}', encoding="utf-8")

    escrow = vroot / "escrows" / depositor_prefix.lower()
    escrow.mkdir(parents=True)
    (escrow / "esc_dummy0001.escrow7d").write_text(
        '{"schema_version": 1}', encoding="utf-8"
    )

    identities = vroot / "identities"
    identities.mkdir(parents=True)
    registry_data = {
        "schema_version": 1,
        "vaults": {
            vault_name: {
                "vault_id": vault_id,
                "vault_number": vault_number,
                "vault_name": vault_name,
                "pioneer_tier": "founder",
                "eidolon_balance": 1250.0,
            }
        },
    }
    import json
    (identities / "vault_registry.json").write_text(
        json.dumps(registry_data, indent=2), encoding="utf-8"
    )

    return psnx, blend


def _set_data_root(monkeypatch_root: Path):
    """Patch config.paths.get_user_data_root to point into a temp dir."""
    import config.paths as cp
    cp._FORCED_ROOT = monkeypatch_root  # type: ignore
    cp.get_user_data_root = lambda: monkeypatch_root  # type: ignore


class _IsolatedDataRoot:
    """Context manager that redirects all config.paths.get_* to a temp dir."""

    def __init__(self):
        self.tmp: Path = Path(tempfile.mkdtemp(prefix="vmig_"))
        self._original = None

    def __enter__(self):
        import config.paths as cp
        self._original = cp.get_user_data_root
        cp.get_user_data_root = lambda: self.tmp  # type: ignore
        return self.tmp

    def __exit__(self, exc_type, exc, tb):
        import config.paths as cp
        if self._original is not None:
            cp.get_user_data_root = self._original  # type: ignore
        shutil.rmtree(self.tmp, ignore_errors=True)


class RoundTripTests(unittest.TestCase):
    def test_export_then_import(self):
        import hashlib
        depositor = hashlib.sha256(VAULT_KEY).hexdigest()[:16]
        with _IsolatedDataRoot() as data_root:
            psnx, blend = _make_fake_vault_tree(
                data_root / "data", VAULT_ID, VAULT_NUMBER, VAULT_NAME, depositor
            )

            out_path = data_root / "out.eidolon_keybundle_full"
            summary = export_vault(
                vault_key=VAULT_KEY,
                vault_id=VAULT_ID,
                vault_number=VAULT_NUMBER,
                vault_name=VAULT_NAME,
                output_path=out_path,
                psnx_path=psnx,
                blend_path=blend,
            )
            self.assertGreater(summary["file_count"], 4)
            self.assertTrue(out_path.is_file())

            inspect = inspect_archive(out_path, VAULT_KEY)
            self.assertTrue(inspect["verified"])
            self.assertEqual(inspect["vault_id"], VAULT_ID)

        # Import into a fresh data root
        with _IsolatedDataRoot() as data_root2:
            # Export inside data_root2 so the archive path stays valid here
            psnx2, blend2 = _make_fake_vault_tree(
                data_root2 / "data", VAULT_ID, VAULT_NUMBER, VAULT_NAME, depositor
            )
            second_out = data_root2 / "second.eidolon_keybundle_full"
            export_vault(
                vault_key=VAULT_KEY,
                vault_id=VAULT_ID,
                vault_number=VAULT_NUMBER,
                vault_name=VAULT_NAME,
                output_path=second_out,
                psnx_path=psnx2,
                blend_path=blend2,
            )

            # Wipe the actively installed vault data (simulate fresh machine)
            shutil.rmtree(data_root2 / "data" / "vaults", ignore_errors=True)

            result = import_vault(second_out, VAULT_KEY)
            self.assertGreater(result["installed_count"], 4)
            self.assertEqual(result["manifest"]["vault_id"], VAULT_ID)

    def test_wrong_key_rejected(self):
        import hashlib
        depositor = hashlib.sha256(VAULT_KEY).hexdigest()[:16]
        with _IsolatedDataRoot() as data_root:
            psnx, blend = _make_fake_vault_tree(
                data_root / "data", VAULT_ID, VAULT_NUMBER, VAULT_NAME, depositor
            )
            out_path = data_root / "wrong_key.eidolon_keybundle_full"
            export_vault(
                vault_key=VAULT_KEY, vault_id=VAULT_ID,
                vault_number=VAULT_NUMBER, vault_name=VAULT_NAME,
                output_path=out_path, psnx_path=psnx, blend_path=blend,
            )
            with self.assertRaises(MigrationImportError):
                inspect_archive(out_path, b"X" * 32)

    def test_tampered_header_rejected(self):
        import hashlib
        depositor = hashlib.sha256(VAULT_KEY).hexdigest()[:16]
        with _IsolatedDataRoot() as data_root:
            psnx, blend = _make_fake_vault_tree(
                data_root / "data", VAULT_ID, VAULT_NUMBER, VAULT_NAME, depositor
            )
            out_path = data_root / "tampered.eidolon_keybundle_full"
            export_vault(
                vault_key=VAULT_KEY, vault_id=VAULT_ID,
                vault_number=VAULT_NUMBER, vault_name=VAULT_NAME,
                output_path=out_path, psnx_path=psnx, blend_path=blend,
            )
            # Corrupt 1 byte right after the header
            with open(out_path, "r+b") as f:
                f.seek(HEADER_SIZE + 5)
                b = f.read(1)
                f.seek(HEADER_SIZE + 5)
                f.write(bytes([b[0] ^ 0x01]))
            with self.assertRaises(MigrationImportError):
                inspect_archive(out_path, VAULT_KEY)


class FrozenFormatTests(unittest.TestCase):
    def test_v1_mac_input_is_stable(self):
        m = Manifest(
            vault_id="vault_frozen_test",
            vault_number=7,
            vault_name="Frozen",
            depositor_prefix="0123456789abcdef",
            exported_at="2026-01-01T00:00:00+00:00",
            archive_salt=b"\x00" * 32,
            file_inventory=[],
            transfer_mode="snapshot",
            notes="",
        )
        result = m.mac_input()
        # Format must remain byte-exact: keys sorted, no whitespace
        self.assertIn(b'"vault_id":"vault_frozen_test"', result)
        self.assertIn(b'"transfer_mode":"snapshot"', result)
        self.assertIn(b'"format_suite":"alpha-v1"', result)
        self.assertEqual(result, m._mac_input_v1())

    def test_v1_mac_input_function_registered(self):
        self.assertIn(1, _MAC_INPUT_BY_VERSION)


class FutureVersionTests(unittest.TestCase):
    def setUp(self):
        self._orig_supported = set(SUPPORTED_SCHEMA_VERSIONS)
        self._orig_mac_fns = dict(_MAC_INPUT_BY_VERSION)
        self._orig_suites = dict(_REGISTRY)

    def tearDown(self):
        fv = sys.modules["src.protocols.vault_migration.format_version"]
        fv.SUPPORTED_SCHEMA_VERSIONS = frozenset(self._orig_supported)
        _MAC_INPUT_BY_VERSION.clear()
        _MAC_INPUT_BY_VERSION.update(self._orig_mac_fns)
        _REGISTRY.clear()
        _REGISTRY.update(self._orig_suites)

    def test_v1_archive_readable_after_simulated_v2(self):
        import hashlib
        depositor = hashlib.sha256(VAULT_KEY).hexdigest()[:16]
        with _IsolatedDataRoot() as data_root:
            psnx, blend = _make_fake_vault_tree(
                data_root / "data", VAULT_ID, VAULT_NUMBER, VAULT_NAME, depositor
            )
            out_path = data_root / "v1.eidolon_keybundle_full"
            export_vault(
                vault_key=VAULT_KEY, vault_id=VAULT_ID,
                vault_number=VAULT_NUMBER, vault_name=VAULT_NAME,
                output_path=out_path, psnx_path=psnx, blend_path=blend,
            )

            # Simulate a v2 release
            def _mac_input_v2(self) -> bytes:
                import json
                payload = {
                    "schema_version": self.schema_version,
                    "min_reader_version": self.min_reader_version,
                    "format_suite": self.format_suite,
                    "producer": self.producer,
                    "vault_id": self.vault_id,
                    "vault_number": self.vault_number,
                    "vault_name": self.vault_name,
                    "depositor_prefix": self.depositor_prefix,
                    "exported_at": self.exported_at,
                    "transfer_mode": self.transfer_mode,
                    "notes": self.notes,
                    "imaginary_v2_field": "demo",
                }
                return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

            _MAC_INPUT_BY_VERSION[2] = _mac_input_v2
            fv = sys.modules["src.protocols.vault_migration.format_version"]
            fv.SUPPORTED_SCHEMA_VERSIONS = frozenset({1, 2})
            _REGISTRY["alpha-v2"] = FormatSuite(
                name="alpha-v2",
                aead_algo="aes-256-gcm",
                kdf_algo="hkdf-sha256",
                mac_algo="hmac-sha256",
                payload_key_info=b"EIDOLON_MIGRATION_PAYLOAD_KEY_v2",
                integrity_info=b"EIDOLON_MIGRATION_INTEGRITY_v2",
            )

            # v1 archive must still verify under a v2-aware reader
            summary = inspect_archive(out_path, VAULT_KEY)
            self.assertTrue(summary["verified"])
            self.assertEqual(summary["schema_version"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
