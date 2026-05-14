import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.key_bundle import (
    EidolonKeyBundleManager,
    KEYBUNDLE_MARKER,
)
from src.core.keybundle_format import (
    INVALID_KEYBUNDLE_ERROR,
    build_keybundle_bytes,
    parse_keybundle_bytes,
)
from src.core.rust_crypto import sha256_hexdigest


class KeybundleFormatTests(unittest.TestCase):
    def test_build_keybundle_bytes_writes_expected_framing(self):
        payload = {
            "format": "EIDOLON_KEYBUNDLE",
            "version": 1,
            "created_at": "2026-04-02T00:00:00",
            "psnx": {"filename": "vault.psnx", "sha256": "aa", "content_b64": "YQ=="},
            "blend_data": {
                "filename": "vault.blend_data",
                "sha256": "bb",
                "content_b64": "Yg==",
            },
        }

        raw = build_keybundle_bytes(payload)
        self.assertEqual(raw[: len(KEYBUNDLE_MARKER)], KEYBUNDLE_MARKER)

        compressed_len = struct.unpack(
            ">I",
            raw[len(KEYBUNDLE_MARKER) : len(KEYBUNDLE_MARKER) + 4],
        )[0]
        compressed = raw[len(KEYBUNDLE_MARKER) + 4 :]
        self.assertEqual(len(compressed), compressed_len)
        self.assertEqual(json.loads(zlib.decompress(compressed).decode("utf-8")), payload)

    def test_parse_keybundle_bytes_round_trip(self):
        payload = {
            "format": "EIDOLON_KEYBUNDLE",
            "version": 1,
            "psnx": {"filename": "vault.psnx"},
            "blend_data": {"filename": "vault.blend_data"},
        }
        self.assertEqual(parse_keybundle_bytes(build_keybundle_bytes(payload)), payload)

    def test_parse_keybundle_bytes_rejects_invalid_marker(self):
        with self.assertRaisesRegex(ValueError, INVALID_KEYBUNDLE_ERROR):
            parse_keybundle_bytes(b"NOT_A_KEYBUNDLE")

    def test_manager_create_and_load_bundle_round_trip(self):
        manager = EidolonKeyBundleManager()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            psnx_path = tmp_path / "vault.psnx"
            blend_path = tmp_path / "vault.blend_data"
            psnx_path.write_bytes(b"psnx-content")
            blend_path.write_text(
                json.dumps({"format": "PSNX_BLEND_DATA", "key_id": "vault-001"}),
                encoding="utf-8",
            )

            bundle_path = manager.create_bundle(str(psnx_path), str(blend_path))
            payload = manager.load_bundle(bundle_path)

        self.assertEqual(payload["format"], "EIDOLON_KEYBUNDLE")
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["psnx"]["filename"], "vault.psnx")
        self.assertEqual(payload["blend_data"]["filename"], "vault.blend_data")

    def test_manager_stores_stable_sha256_hashes(self):
        manager = EidolonKeyBundleManager()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            psnx_path = tmp_path / "vault.psnx"
            blend_path = tmp_path / "vault.blend_data"
            psnx_bytes = b"psnx-content"
            blend_bytes = json.dumps(
                {"format": "PSNX_BLEND_DATA", "key_id": "vault-001"}
            ).encode("utf-8")

            psnx_path.write_bytes(psnx_bytes)
            blend_path.write_bytes(blend_bytes)

            bundle_path = manager.create_bundle(str(psnx_path), str(blend_path))
            payload = manager.load_bundle(bundle_path)

        self.assertEqual(payload["psnx"]["sha256"], sha256_hexdigest(psnx_bytes))
        self.assertEqual(payload["blend_data"]["sha256"], sha256_hexdigest(blend_bytes))

    def test_extract_bundle_refuses_overwrite_when_existing_file_differs(self):
        manager = EidolonKeyBundleManager()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            psnx_path = tmp_path / "vault.psnx"
            blend_path = tmp_path / "vault.blend_data"
            psnx_path.write_bytes(b"psnx-content")
            blend_path.write_text(
                json.dumps({"format": "PSNX_BLEND_DATA", "key_id": "vault-001"}),
                encoding="utf-8",
            )

            bundle_path = manager.create_bundle(str(psnx_path), str(blend_path))
            extract_dir = tmp_path / "extract"
            extract_dir.mkdir()
            (extract_dir / "vault.psnx").write_bytes(b"different-content")

            with self.assertRaisesRegex(ValueError, "Refusing to overwrite different existing file"):
                manager.extract_bundle(bundle_path, str(extract_dir))


if __name__ == "__main__":
    unittest.main()
