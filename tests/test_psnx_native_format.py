import json
import struct
import sys
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.psnx_native_format import (
    INVALID_PSNX_ERROR,
    PSNX_COMPLETE_KEY_MARKER,
    build_native_psnx_bytes,
    parse_native_psnx_bytes,
)


class PsnxNativeFormatTests(unittest.TestCase):
    def test_build_native_psnx_bytes_writes_expected_framing(self):
        payload = {
            "marker": PSNX_COMPLETE_KEY_MARKER.decode(),
            "version": 2,
            "user_name": "VectorUser",
            "key_data": {"key_id": "vector-key", "version": 2},
            "created_at": "2026-04-02T00:00:00",
        }

        raw = build_native_psnx_bytes(payload)
        self.assertEqual(raw[: len(PSNX_COMPLETE_KEY_MARKER)], PSNX_COMPLETE_KEY_MARKER)

        compressed_len = struct.unpack(
            ">I",
            raw[len(PSNX_COMPLETE_KEY_MARKER) : len(PSNX_COMPLETE_KEY_MARKER) + 4],
        )[0]
        compressed = raw[len(PSNX_COMPLETE_KEY_MARKER) + 4 :]
        self.assertEqual(len(compressed), compressed_len)
        self.assertEqual(json.loads(zlib.decompress(compressed).decode("utf-8")), payload)

    def test_build_native_psnx_bytes_accepts_rust_builder_output(self):
        payload = {"marker": PSNX_COMPLETE_KEY_MARKER.decode(), "version": 2}
        rust_blob = PSNX_COMPLETE_KEY_MARKER + struct.pack(">I", 4) + b"rust"

        with patch(
            "src.core.psnx_native_format.is_rust_crypto_available",
            return_value=True,
        ), patch(
            "src.core.psnx_native_format.rust_complete_psnx_build",
            return_value=rust_blob,
        ) as mocked_build:
            built = build_native_psnx_bytes(payload)

        self.assertEqual(built, rust_blob)
        built_json = json.loads(mocked_build.call_args.args[0].decode("utf-8"))
        self.assertEqual(built_json, payload)

    def test_parse_native_psnx_bytes_round_trip(self):
        payload = {
            "marker": PSNX_COMPLETE_KEY_MARKER.decode(),
            "version": 2,
            "user_name": "VectorUser",
        }
        raw = build_native_psnx_bytes(payload)
        self.assertEqual(parse_native_psnx_bytes(raw), payload)

    def test_parse_native_psnx_bytes_rejects_invalid_marker(self):
        with self.assertRaisesRegex(ValueError, INVALID_PSNX_ERROR):
            parse_native_psnx_bytes(b"NOT_A_REAL_PSNX")

    def test_parse_native_psnx_bytes_normalizes_rust_errors(self):
        with patch(
            "src.core.psnx_native_format.is_rust_crypto_available",
            return_value=True,
        ), patch(
            "src.core.psnx_native_format.rust_complete_psnx_parse",
            side_effect=RuntimeError("native parse failed"),
        ):
            with self.assertRaisesRegex(ValueError, INVALID_PSNX_ERROR):
                parse_native_psnx_bytes(b"broken")


if __name__ == "__main__":
    unittest.main()
