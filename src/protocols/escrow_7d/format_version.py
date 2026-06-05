"""Version management for 7D Escrow.

Two orthogonal version axes are tracked:

* ``schema_version``  - shape of the JSON envelope (fields, layout). Bump when
                        adding/removing/renaming fields. Migrations live in
                        ``MIGRATIONS``.

* ``crypto_suite``    - named bundle of algorithms + parameters (KDF info
                        strings, AEAD, MAC, lengths). Bump when changing any
                        cryptographic primitive or its domain separator.

Both axes are bound into the integrity MAC, so a tampered version field
causes verification to fail (anti-downgrade).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping

# ---------------------------------------------------------------------------
# Schema versioning
# ---------------------------------------------------------------------------

CURRENT_SCHEMA_VERSION: int = 1
"""Bump when adding, removing, or renaming envelope JSON fields."""

MINIMUM_READER_VERSION: int = 1
"""Lowest reader code version that can correctly process current envelopes."""

SUPPORTED_SCHEMA_VERSIONS: frozenset = frozenset({1})
"""Schema versions this build knows how to read directly (no migration)."""


# ---------------------------------------------------------------------------
# Crypto suite registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CryptoSuite:
    """Named bundle of cryptographic parameters.

    All info strings are versioned so a future suite cannot accidentally
    decrypt an envelope produced by a previous suite.
    """

    name: str
    aead_algo: str
    kdf_algo: str
    mac_algo: str
    session_key_info: bytes
    integrity_info: bytes
    session_key_len: int = 32
    nonce_len: int = 12
    salt_len: int = 32
    mac_len: int = 32


_REGISTRY: Dict[str, CryptoSuite] = {
    "alpha-v1": CryptoSuite(
        name="alpha-v1",
        aead_algo="aes-256-gcm",
        kdf_algo="hkdf-sha256",
        mac_algo="hmac-sha256",
        session_key_info=b"EIDOLON_ESCROW_SESSION_KEY_v1",
        integrity_info=b"EIDOLON_ESCROW_INTEGRITY_v1",
    ),
}

CURRENT_CRYPTO_SUITE: str = "alpha-v1"


def get_suite(name: str) -> CryptoSuite:
    """Look up a crypto suite by name; raise FormatError on unknown name."""
    suite = _REGISTRY.get(name)
    if suite is None:
        raise FormatError(
            f"unknown crypto_suite {name!r} - this reader supports: "
            f"{sorted(_REGISTRY)}"
        )
    return suite


def all_suite_names() -> List[str]:
    return sorted(_REGISTRY)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class FormatError(Exception):
    """Raised on schema/crypto-suite incompatibility or migration failure."""


# ---------------------------------------------------------------------------
# Compatibility check
# ---------------------------------------------------------------------------

def check_compatibility(schema_version: int, min_reader_version: int,
                        crypto_suite: str) -> None:
    """Verify this build can read an envelope with the given version triple.

    Raises FormatError with a precise reason on incompatibility.
    """
    if min_reader_version > CURRENT_SCHEMA_VERSION:
        raise FormatError(
            f"envelope requires reader >= v{min_reader_version} "
            f"but this build is v{CURRENT_SCHEMA_VERSION}. "
            "Update Eidolon to read this escrow."
        )
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise FormatError(
            f"unknown schema_version {schema_version}. "
            f"This build supports: {sorted(SUPPORTED_SCHEMA_VERSIONS)}. "
            "Update Eidolon to read this escrow."
        )
    get_suite(crypto_suite)  # raises FormatError if unknown


# ---------------------------------------------------------------------------
# NO migration framework for envelopes.
#
# An escrow envelope's cryptographic state (ciphertext, MAC) is bound to its
# original schema_version and crypto_suite at deposit time. The MAC was
# computed over its v1 canonical bytes; mutating the JSON shape afterwards
# would invalidate it.
#
# To "upgrade" an envelope to the latest suite, use ``sealer.reseal()``:
# it decrypts with the original suite (the vault key is required) and
# re-encrypts with the current one. That is cryptographically honest;
# silent migration would not be.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Producer identification (for diagnostics, not security)
# ---------------------------------------------------------------------------

PRODUCER_TAG: str = "eidolon-escrow-7d/alpha-v1"


def producer_summary() -> Mapping[str, str]:
    return {
        "producer": PRODUCER_TAG,
        "schema_version": str(CURRENT_SCHEMA_VERSION),
        "min_reader_version": str(MINIMUM_READER_VERSION),
        "crypto_suite": CURRENT_CRYPTO_SUITE,
    }
