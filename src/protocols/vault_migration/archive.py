"""Encrypted archive container for vault migration.

Container layout (binary, big-endian for multi-byte integers):

    Offset  Size  Field
    ------  ----  ---------------------------------------------------
    0       6     magic            b"EIDMIG"
    6       2     container_version  uint16  (currently 1)
    8       4     schema_version     uint32  (mirrors manifest)
    12      32    salt               random per-archive
    44      12    nonce              random per-archive
    56      8     payload_length     uint64  (size of ciphertext+tag)
    64      N     payload            AES-256-GCM ciphertext + 16-byte tag

The payload, when decrypted, is a standard ZIP archive whose root contains
``manifest.json`` plus the file inventory.

Encryption key is HKDF(vault_key, salt, suite.payload_key_info).
"""

from __future__ import annotations

import hashlib
import hmac
import io
import os
import struct
import zipfile
from typing import IO, Tuple

from .format_version import (
    ARCHIVE_MAGIC,
    CURRENT_FORMAT_SUITE,
    CURRENT_SCHEMA_VERSION,
    FormatError,
    FormatSuite,
    check_compatibility,
    get_suite,
)


CONTAINER_VERSION: int = 1
HEADER_SIZE: int = 6 + 2 + 4 + 32 + 12 + 8


class ArchiveError(Exception):
    pass


# ---------------------------------------------------------------------------
# HKDF helpers (mirror sealer.py for consistency)
# ---------------------------------------------------------------------------

def _hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    if not salt:
        salt = b"\x00" * hashlib.sha256().digest_size
    return hmac.new(salt, ikm, hashlib.sha256).digest()


def _hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    blocks = b""
    last = b""
    counter = 1
    while len(blocks) < length:
        last = hmac.new(prk, last + info + bytes([counter]), hashlib.sha256).digest()
        blocks += last
        counter += 1
    return blocks[:length]


def _hkdf(vault_key: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    return _hkdf_expand(_hkdf_extract(salt, vault_key), info, length)


# ---------------------------------------------------------------------------
# AEAD
# ---------------------------------------------------------------------------

def _aead_encrypt(suite: FormatSuite, key: bytes, nonce: bytes,
                  plaintext: bytes) -> bytes:
    if suite.aead_algo != "aes-256-gcm":
        raise ArchiveError(f"unsupported AEAD: {suite.aead_algo}")
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise ArchiveError(f"cryptography library unavailable: {exc}")
    return AESGCM(key).encrypt(nonce, plaintext, associated_data=None)


def _aead_decrypt(suite: FormatSuite, key: bytes, nonce: bytes,
                  ciphertext_with_tag: bytes) -> bytes:
    if suite.aead_algo != "aes-256-gcm":
        raise ArchiveError(f"unsupported AEAD: {suite.aead_algo}")
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise ArchiveError(f"cryptography library unavailable: {exc}")
    try:
        return AESGCM(key).decrypt(nonce, ciphertext_with_tag, associated_data=None)
    except Exception as exc:
        raise ArchiveError(f"AEAD decryption failed: {exc}")


# ---------------------------------------------------------------------------
# ZIP writer/reader (in-memory)
# ---------------------------------------------------------------------------

def build_zip_from_files(
    file_entries,  # iterable[(archive_path, bytes)]
    manifest_bytes: bytes,
) -> bytes:
    """Build an in-memory ZIP containing manifest + all entries."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", manifest_bytes)
        for archive_path, data in file_entries:
            zf.writestr(archive_path, data)
    return buf.getvalue()


def read_zip_to_files(zip_bytes: bytes):
    """Return (manifest_bytes, {archive_path: bytes_payload})."""
    files = {}
    manifest_bytes = b""
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        for info in zf.infolist():
            if info.filename == "manifest.json":
                manifest_bytes = zf.read(info.filename)
            else:
                files[info.filename] = zf.read(info.filename)
    if not manifest_bytes:
        raise ArchiveError("archive is missing manifest.json")
    return manifest_bytes, files


# ---------------------------------------------------------------------------
# Container write/read
# ---------------------------------------------------------------------------

def write_archive(
    out_path,
    vault_key: bytes,
    zip_bytes: bytes,
    suite_name: str = CURRENT_FORMAT_SUITE,
) -> None:
    """Encrypt the ZIP payload and write the full container to disk."""
    if not vault_key or len(vault_key) < 32:
        raise ArchiveError("vault_key must be at least 32 bytes")
    suite = get_suite(suite_name)

    salt = os.urandom(suite.salt_len)
    nonce = os.urandom(suite.nonce_len)
    payload_key = _hkdf(vault_key, salt, suite.payload_key_info, suite.payload_key_len)

    payload = _aead_encrypt(suite, payload_key, nonce, zip_bytes)
    payload_length = len(payload)

    header = (
        ARCHIVE_MAGIC
        + struct.pack(">H", CONTAINER_VERSION)
        + struct.pack(">I", CURRENT_SCHEMA_VERSION)
        + salt
        + nonce
        + struct.pack(">Q", payload_length)
    )
    if len(header) != HEADER_SIZE:
        raise ArchiveError(f"header size mismatch: {len(header)} != {HEADER_SIZE}")

    with open(out_path, "wb") as f:
        f.write(header)
        f.write(payload)


def read_archive_header(stream: IO[bytes]) -> dict:
    """Parse the binary header. Stream must be positioned at offset 0."""
    raw = stream.read(HEADER_SIZE)
    if len(raw) != HEADER_SIZE:
        raise ArchiveError("archive shorter than header")
    if raw[:6] != ARCHIVE_MAGIC:
        raise ArchiveError(f"bad magic: got {raw[:6]!r}, expected {ARCHIVE_MAGIC!r}")
    container_version = struct.unpack(">H", raw[6:8])[0]
    if container_version != CONTAINER_VERSION:
        raise ArchiveError(
            f"unsupported container_version {container_version}; this build is {CONTAINER_VERSION}"
        )
    schema_version = struct.unpack(">I", raw[8:12])[0]
    salt = raw[12:44]
    nonce = raw[44:56]
    payload_length = struct.unpack(">Q", raw[56:64])[0]
    return {
        "container_version": container_version,
        "schema_version": schema_version,
        "salt": salt,
        "nonce": nonce,
        "payload_length": payload_length,
    }


def read_archive(
    archive_path,
    vault_key: bytes,
    suite_name: str = CURRENT_FORMAT_SUITE,
) -> Tuple[dict, bytes]:
    """Read + decrypt container. Returns (header_dict, zip_bytes)."""
    if not vault_key or len(vault_key) < 32:
        raise ArchiveError("vault_key must be at least 32 bytes")
    suite = get_suite(suite_name)

    with open(archive_path, "rb") as f:
        header = read_archive_header(f)
        payload = f.read(header["payload_length"])

    if len(payload) != header["payload_length"]:
        raise ArchiveError(
            f"truncated archive: expected {header['payload_length']} bytes, got {len(payload)}"
        )

    payload_key = _hkdf(
        vault_key, header["salt"], suite.payload_key_info, suite.payload_key_len
    )
    zip_bytes = _aead_decrypt(suite, payload_key, header["nonce"], payload)
    return header, zip_bytes


def compute_integrity_mac(
    vault_key: bytes,
    salt: bytes,
    manifest_canonical: bytes,
    suite_name: str = CURRENT_FORMAT_SUITE,
) -> bytes:
    """Compute the manifest-level HMAC carried inside manifest.json."""
    suite = get_suite(suite_name)
    integrity_key = _hkdf(vault_key, salt, suite.integrity_info, suite.mac_len)
    if suite.mac_algo != "hmac-sha256":
        raise ArchiveError(f"unsupported MAC: {suite.mac_algo}")
    return hmac.new(integrity_key, manifest_canonical, hashlib.sha256).digest()
