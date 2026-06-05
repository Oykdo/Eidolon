"""Frozen versioning for vault migration archives.

The same backward-compatibility rule as escrow_7d applies here:

    The canonical bytes covered by an archive's integrity MAC are FROZEN
    forever per schema_version. NEVER mutate _mac_input_v{N}. To add a
    field, bump CURRENT_SCHEMA_VERSION and register a new mac_input
    function. Old archives must remain readable by future builds.

The archive container format itself is also versioned (see archive.py header).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


# ---------------------------------------------------------------------------
# Schema versioning
# ---------------------------------------------------------------------------

CURRENT_SCHEMA_VERSION: int = 1
MINIMUM_READER_VERSION: int = 1
SUPPORTED_SCHEMA_VERSIONS: frozenset = frozenset({1})


# ---------------------------------------------------------------------------
# Format suite registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FormatSuite:
    """Cryptographic parameters for a named archive format suite."""

    name: str
    aead_algo: str
    kdf_algo: str
    mac_algo: str
    payload_key_info: bytes
    integrity_info: bytes
    payload_key_len: int = 32
    nonce_len: int = 12
    salt_len: int = 32
    mac_len: int = 32


_REGISTRY: Dict[str, FormatSuite] = {
    "alpha-v1": FormatSuite(
        name="alpha-v1",
        aead_algo="aes-256-gcm",
        kdf_algo="hkdf-sha256",
        mac_algo="hmac-sha256",
        payload_key_info=b"EIDOLON_MIGRATION_PAYLOAD_KEY_v1",
        integrity_info=b"EIDOLON_MIGRATION_INTEGRITY_v1",
    ),
}

CURRENT_FORMAT_SUITE: str = "alpha-v1"


def get_suite(name: str) -> FormatSuite:
    suite = _REGISTRY.get(name)
    if suite is None:
        raise FormatError(
            f"unknown format_suite {name!r} - this reader supports: "
            f"{sorted(_REGISTRY)}"
        )
    return suite


def all_suite_names() -> List[str]:
    return sorted(_REGISTRY)


# ---------------------------------------------------------------------------
# File / producer constants
# ---------------------------------------------------------------------------

MIGRATION_FILE_SUFFIX: str = ".eidolon_keybundle_full"
ARCHIVE_MAGIC: bytes = b"EIDMIG"
PRODUCER_TAG: str = "eidolon-migration/alpha-v1"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class FormatError(Exception):
    pass


def check_compatibility(schema_version: int, min_reader_version: int,
                        format_suite: str) -> None:
    if min_reader_version > CURRENT_SCHEMA_VERSION:
        raise FormatError(
            f"archive requires reader >= v{min_reader_version} "
            f"but this build is v{CURRENT_SCHEMA_VERSION}. "
            "Update Eidolon to read this migration archive."
        )
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise FormatError(
            f"unknown schema_version {schema_version}. "
            f"This build supports: {sorted(SUPPORTED_SCHEMA_VERSIONS)}. "
            "Update Eidolon to read this archive."
        )
    get_suite(format_suite)
