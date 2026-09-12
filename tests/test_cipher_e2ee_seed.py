"""
Contrat v1 : derivation coffre -> seed E2EE Cipher.

Les vecteurs de `tests/fixtures/cipher_e2ee_seed/` sont deux coffres
SYNTHETIQUES generes le 2026-09-12 par le generateur Python de la ceremonie
(`enable_pq=False` puis `True`), jamais enregistres. `vault_key_hex` et
`vault_id` y proviennent directement du generateur ; `e2ee_seed_hex` est
l'etape C calculee par deux implementations independantes (cryptography.HKDF
et HMAC manuel) qui concordent.

Le parseur natif Rust n'est pas toujours installe dans l'environnement de test :
le framing (marqueur + u32 BE + zlib) est alors reproduit en stdlib, comme dans
`test_psnx_native_format.py`. La derivation elle-meme passe par le generateur
de production.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import struct
import sys
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto import cipher_e2ee_seed as mod  # noqa: E402
from src.crypto.psnx_native_format import PSNX_COMPLETE_KEY_MARKER  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "cipher_e2ee_seed"


def _stdlib_parse(raw: bytes) -> dict:
    marker = PSNX_COMPLETE_KEY_MARKER
    if not raw.startswith(marker):
        raise ValueError("Invalid .psnx file")
    (length,) = struct.unpack(">I", raw[len(marker):len(marker) + 4])
    body = raw[len(marker) + 4:]
    if len(body) != length:
        raise ValueError("Invalid .psnx file")
    return json.loads(zlib.decompress(body).decode("utf-8"))


def _hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    out, block, counter = b"", b"", 1
    while len(out) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        out += block
        counter += 1
    return out[:length]


class CipherE2EESeedStepCTests(unittest.TestCase):
    """Etape C seule : HKDF-SHA256, sans coffre."""

    def test_constants_are_the_published_contract(self):
        self.assertEqual(mod.CIPHER_E2EE_SEED_VERSION, "v1")
        self.assertEqual(mod.CIPHER_E2EE_SEED_SALT, b"PSNX_EXPAND")
        self.assertEqual(mod.CIPHER_E2EE_SEED_INFO, b"cipherpulse:e2ee:masterkey:v1")
        self.assertEqual(mod.CIPHER_E2EE_SEED_LENGTH, 32)

    def test_seed_matches_independent_hkdf(self):
        vault_key = bytes(range(32))
        expected = _hkdf_sha256(vault_key, b"PSNX_EXPAND", b"cipherpulse:e2ee:masterkey:v1", 32)
        self.assertEqual(mod.derive_cipher_e2ee_seed(vault_key), expected)
        self.assertEqual(len(expected), 32)

    def test_seed_is_deterministic_and_key_sensitive(self):
        a = mod.derive_cipher_e2ee_seed(b"\x01" * 32)
        b = mod.derive_cipher_e2ee_seed(b"\x01" * 32)
        c = mod.derive_cipher_e2ee_seed(b"\x02" * 32)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_rejects_wrong_key_length(self):
        with self.assertRaises(ValueError):
            mod.derive_cipher_e2ee_seed(b"\x00" * 31)
        with self.assertRaises(ValueError):
            mod.derive_vault_id(b"\x00" * 16)

    def test_vault_id_is_sha256_of_vault_key(self):
        vault_key = bytes(range(32))
        self.assertEqual(mod.derive_vault_id(vault_key), hashlib.sha256(vault_key).hexdigest())


class CipherE2EESeedVectorTests(unittest.TestCase):
    """Chaine complete sur les deux coffres synthetiques."""

    def _run_vector(self, label: str):
        raw = (FIXTURES / f"vector_{label}.psnx").read_bytes()
        expected = json.loads((FIXTURES / f"vector_{label}.expected.json").read_text(encoding="utf-8"))
        with patch.object(mod, "parse_native_psnx_bytes", _stdlib_parse):
            result = mod.derive_cipher_e2ee_seed_from_psnx_bytes(raw)
        self.assertEqual(result.version, "v1")
        self.assertEqual(result.key_id, expected["key_id"])
        self.assertEqual(result.vault_id, expected["vault_id"])
        self.assertEqual(result.seed_hex, expected["e2ee_seed_hex"])
        self.assertNotIn("seed", result.to_public_dict())
        return expected

    def test_vector_without_post_quantum(self):
        expected = self._run_vector("nopq")
        self.assertFalse(expected["pq_enabled"])

    def test_vector_with_post_quantum(self):
        expected = self._run_vector("pq")
        self.assertTrue(expected["pq_enabled"])

    def test_vault_key_step_matches_generator_output(self):
        raw = (FIXTURES / "vector_pq.psnx").read_bytes()
        expected = json.loads((FIXTURES / "vector_pq.expected.json").read_text(encoding="utf-8"))
        key_id, vault_key = mod.derive_vault_key_from_psnx_payload(_stdlib_parse(raw))
        self.assertEqual(key_id, expected["key_id"])
        self.assertEqual(vault_key.hex(), expected["vault_key_hex"])

    def test_rejects_payload_without_key_data(self):
        with self.assertRaises(ValueError):
            mod.derive_vault_key_from_psnx_payload({"marker": "PSNX7D_COMPLETE_V2"})


if __name__ == "__main__":
    unittest.main()
