import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.complete_key_generator import CompleteKeyFileGenerator
from src.crypto.psnx_native_format import PSNX_COMPLETE_KEY_MARKER


class _FakeKeyData:
    def __init__(self, payload):
        self._payload = payload

    def to_dict(self):
        return self._payload


class _FakeGenerator:
    def __init__(self):
        self.verified_key_data = None

    def verify_and_derive_key(self, key_data):
        self.verified_key_data = key_data
        return True, b"\x42" * 32


class CompletePsnxFormatContractTests(unittest.TestCase):
    def test_key_marker_is_stable(self):
        self.assertEqual(CompleteKeyFileGenerator.KEY_MARKER, b"PSNX7D_COMPLETE_V2")
        self.assertEqual(PSNX_COMPLETE_KEY_MARKER, b"PSNX7D_COMPLETE_V2")

    def test_save_psnx_file_writes_expected_framing(self):
        generator = _FakeGenerator()
        file_gen = CompleteKeyFileGenerator(generator)
        key_data = _FakeKeyData(
            {
                "key_id": "vector-key",
                "version": 2,
                "signing": {"algorithm": "Ed25519"},
                "payload": {"hello": "world"},
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vault.psnx"
            file_gen._save_psnx_file(str(path), key_data, "VectorUser")

            raw = path.read_bytes()
            marker = raw[: len(file_gen.KEY_MARKER)]
            self.assertEqual(marker, file_gen.KEY_MARKER)

            compressed_len = struct.unpack(
                ">I",
                raw[len(file_gen.KEY_MARKER) : len(file_gen.KEY_MARKER) + 4],
            )[0]
            compressed = raw[len(file_gen.KEY_MARKER) + 4 :]
            self.assertEqual(len(compressed), compressed_len)

            payload = json.loads(zlib.decompress(compressed).decode("utf-8"))
            self.assertEqual(payload["marker"], file_gen.KEY_MARKER.decode())
            self.assertEqual(payload["version"], 2)
            self.assertEqual(payload["user_name"], "VectorUser")
            self.assertIn("created_at", payload)
            self.assertEqual(payload["key_data"]["key_id"], "vector-key")
            self.assertEqual(payload["key_data"]["signing"]["algorithm"], "Ed25519")

    def test_save_psnx_file_accepts_rust_builder_output(self):
        generator = _FakeGenerator()
        file_gen = CompleteKeyFileGenerator(generator)
        key_data = _FakeKeyData({"key_id": "vector-key", "version": 2})
        expected_payload = {
            "marker": file_gen.KEY_MARKER.decode(),
            "version": 2,
            "user_name": "VectorUser",
            "key_data": {"key_id": "vector-key", "version": 2},
            "created_at": "2026-04-02T00:00:00",
        }
        rust_blob = file_gen.KEY_MARKER + struct.pack(
            ">I", 4
        ) + b"rust"

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vault_rust.psnx"
            with patch(
                "src.core.complete_key_generator.datetime"
            ) as mocked_datetime, patch(
                "src.core.complete_key_generator.build_native_psnx_bytes",
                return_value=rust_blob,
            ) as mocked_build:
                mocked_datetime.utcnow.return_value.isoformat.return_value = (
                    "2026-04-02T00:00:00"
                )
                file_gen._save_psnx_file(str(path), key_data, "VectorUser")

            self.assertEqual(path.read_bytes(), rust_blob)
            self.assertEqual(mocked_build.call_args.args[0], expected_payload)

    def test_extract_key_from_file_rejects_invalid_marker(self):
        generator = _FakeGenerator()
        file_gen = CompleteKeyFileGenerator(generator)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.psnx"
            path.write_bytes(b"NOT_A_REAL_PSNX")
            with self.assertRaisesRegex(ValueError, "Invalid .psnx file"):
                file_gen.extract_key_from_file(str(path))

    def test_extract_key_from_file_uses_embedded_key_data_payload(self):
        generator = _FakeGenerator()
        file_gen = CompleteKeyFileGenerator(generator)
        payload = {
            "marker": file_gen.KEY_MARKER.decode(),
            "version": 2,
            "user_name": "VectorUser",
            "key_data": {
                "key_id": "embedded-key",
                "version": 2,
                "vault_key_hash": "deadbeef",
            },
            "created_at": "2026-04-02T00:00:00",
        }

        compressed = zlib.compress(json.dumps(payload).encode("utf-8"), level=9)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "extract.psnx"
            path.write_bytes(
                file_gen.KEY_MARKER + struct.pack(">I", len(compressed)) + compressed
            )

            sentinel_key_data = object()
            with patch(
                "src.core.complete_key_generator.CompleteKeyData.from_bytes",
                return_value=sentinel_key_data,
            ) as mocked_from_bytes:
                key_data, vault_key = file_gen.extract_key_from_file(str(path))

            self.assertIs(key_data, sentinel_key_data)
            self.assertEqual(vault_key, b"\x42" * 32)
            self.assertIs(generator.verified_key_data, sentinel_key_data)
            mocked_from_bytes.assert_called_once()

    def test_extract_key_from_file_accepts_rust_parsed_payload(self):
        generator = _FakeGenerator()
        file_gen = CompleteKeyFileGenerator(generator)
        payload = {
            "marker": file_gen.KEY_MARKER.decode(),
            "version": 2,
            "user_name": "VectorUser",
            "key_data": {
                "key_id": "rust-embedded-key",
                "version": 2,
            },
            "created_at": "2026-04-02T00:00:00",
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "extract_rust.psnx"
            path.write_bytes(b"placeholder")

            sentinel_key_data = object()
            with patch(
                "src.core.complete_key_generator.parse_native_psnx_file",
                return_value={
                    "marker": file_gen.KEY_MARKER.decode(),
                    "version": 2,
                    "user_name": "VectorUser",
                    "key_data": payload["key_data"],
                    "created_at": payload["created_at"],
                },
            ) as mocked_parse, patch(
                "src.core.complete_key_generator.CompleteKeyData.from_bytes",
                return_value=sentinel_key_data,
            ):
                key_data, vault_key = file_gen.extract_key_from_file(str(path))

            self.assertIs(key_data, sentinel_key_data)
            self.assertEqual(vault_key, b"\x42" * 32)
            self.assertIs(generator.verified_key_data, sentinel_key_data)
            mocked_parse.assert_called_once_with(str(path))


if __name__ == "__main__":
    unittest.main()
