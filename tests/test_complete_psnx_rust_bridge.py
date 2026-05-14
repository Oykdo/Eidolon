import json
import struct
import sys
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.complete_key_generator import CompleteKeyFileGenerator
from src.crypto.rust_crypto import (
    complete_psnx_build,
    complete_psnx_parse,
    is_rust_crypto_available,
)


class CompletePsnxRustBridgeTests(unittest.TestCase):
    def test_complete_psnx_build_round_trip(self):
        payload = {
            "marker": CompleteKeyFileGenerator.KEY_MARKER.decode(),
            "version": 2,
            "user_name": "VectorUser",
            "key_data": {"key_id": "vector-key", "version": 2},
            "created_at": "2026-04-02T00:00:00",
        }
        json_bytes = json.dumps(payload).encode("utf-8")

        file_data = complete_psnx_build(json_bytes)
        parsed = complete_psnx_parse(file_data)

        self.assertEqual(parsed["marker"], "PSNX7D_COMPLETE_V2")
        self.assertEqual(json.loads(parsed["json_bytes"].decode("utf-8")), payload)

    def test_complete_psnx_parse_round_trip(self):
        payload = {
            "marker": CompleteKeyFileGenerator.KEY_MARKER.decode(),
            "version": 2,
            "user_name": "VectorUser",
            "key_data": {"key_id": "vector-key", "version": 2},
            "created_at": "2026-04-02T00:00:00",
        }
        json_bytes = json.dumps(payload).encode("utf-8")
        compressed = zlib.compress(json_bytes, level=9)
        file_data = (
            CompleteKeyFileGenerator.KEY_MARKER
            + struct.pack(">I", len(compressed))
            + compressed
        )

        parsed = complete_psnx_parse(file_data)
        self.assertEqual(parsed["marker"], "PSNX7D_COMPLETE_V2")
        self.assertEqual(parsed["compressed_length"], len(compressed))
        self.assertEqual(json.loads(parsed["json_bytes"].decode("utf-8")), payload)

    def test_complete_psnx_parse_rejects_invalid_marker(self):
        with self.assertRaises(Exception):
            complete_psnx_parse(b"NOT_A_REAL_PSNX")

    def test_rust_extension_is_available(self):
        self.assertIsInstance(is_rust_crypto_available(), bool)


if __name__ == "__main__":
    unittest.main()
