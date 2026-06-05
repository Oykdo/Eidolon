"""Crypto core for 7D Escrow.

All cryptographic parameters live in ``format_version.CryptoSuite`` so the
choices for AEAD, KDF, MAC, key/nonce/salt lengths, and HKDF info strings
are versioned together. A future ``alpha-v2`` suite can ship without
touching this file beyond registering it in the registry.

Sealing path:
    1. Generate a random ``salt`` and AEAD ``nonce`` of the suite's lengths.
    2. Derive a session key with HKDF(vault_key, salt, suite.session_key_info).
    3. AEAD-encrypt the cleartext payload with the session key.
    4. Build the envelope (with version triple), compute its canonical MAC
       input, derive an integrity key the same way as the session key but
       with suite.integrity_info, and HMAC over the canonical bytes.

Unsealing path:
    1. Run format_version.check_compatibility() (already done by from_dict).
    2. Re-derive the integrity key and recompute the MAC. Abort on mismatch.
    3. Walk each release condition. Abort on first failure.
    4. Re-derive the session key, AEAD-decrypt.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .conditions import Condition
from .envelope import EscrowEnvelope
from .format_version import (
    CURRENT_CRYPTO_SUITE,
    CURRENT_SCHEMA_VERSION,
    CryptoSuite,
    FormatError,
    MINIMUM_READER_VERSION,
    PRODUCER_TAG,
    check_compatibility,
    get_suite,
)

_CURRENT_FORMAT = (CURRENT_SCHEMA_VERSION, CURRENT_CRYPTO_SUITE)


class SealError(Exception):
    pass


class UnsealError(Exception):
    pass


# ----------------------------------------------------------------------------
# HKDF (RFC 5869) - minimal SHA-256 implementation
# ----------------------------------------------------------------------------

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


def _hkdf(vault_key: bytes, salt: bytes, info: bytes, length: int,
          algo: str = "hkdf-sha256") -> bytes:
    if algo != "hkdf-sha256":
        raise SealError(f"unsupported KDF: {algo}")
    prk = _hkdf_extract(salt, vault_key)
    return _hkdf_expand(prk, info, length)


# ----------------------------------------------------------------------------
# AEAD wrapper (single algorithm for now: AES-256-GCM)
# ----------------------------------------------------------------------------

def _aead_encrypt(suite: CryptoSuite, key: bytes, nonce: bytes,
                  plaintext: bytes) -> Tuple[bytes, bytes]:
    if suite.aead_algo != "aes-256-gcm":
        raise SealError(f"unsupported AEAD: {suite.aead_algo}")
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise SealError(f"cryptography library unavailable: {exc}")
    aesgcm = AESGCM(key)
    blob = aesgcm.encrypt(nonce, plaintext, associated_data=None)
    return blob[:-16], blob[-16:]


def _aead_decrypt(suite: CryptoSuite, key: bytes, nonce: bytes,
                  ciphertext: bytes, tag: bytes) -> bytes:
    if suite.aead_algo != "aes-256-gcm":
        raise UnsealError(f"unsupported AEAD: {suite.aead_algo}")
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise UnsealError(f"cryptography library unavailable: {exc}")
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext + tag, associated_data=None)
    except Exception as exc:
        raise UnsealError(f"AEAD decryption failed: {exc}")


def _mac(suite: CryptoSuite, key: bytes, data: bytes) -> bytes:
    if suite.mac_algo != "hmac-sha256":
        raise SealError(f"unsupported MAC: {suite.mac_algo}")
    return hmac.new(key, data, hashlib.sha256).digest()


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------

def _depositor_vault_id_prefix(vault_key: bytes) -> str:
    return hashlib.sha256(vault_key).hexdigest()[:16]


def _new_escrow_id() -> str:
    return "esc_" + secrets.token_hex(16)


def seal(
    payload: bytes,
    vault_key: bytes,
    conditions: Optional[List[Condition]] = None,
    label: str = "",
    suite_name: str = CURRENT_CRYPTO_SUITE,
) -> EscrowEnvelope:
    if not isinstance(payload, (bytes, bytearray)):
        raise SealError("payload must be bytes")
    if not vault_key or len(vault_key) < 32:
        raise SealError("vault_key must be at least 32 bytes")

    suite = get_suite(suite_name)
    conditions = conditions or []

    salt = os.urandom(suite.salt_len)
    nonce = os.urandom(suite.nonce_len)
    session_key = _hkdf(vault_key, salt, suite.session_key_info,
                        suite.session_key_len, suite.kdf_algo)
    ciphertext, tag = _aead_encrypt(suite, session_key, nonce, bytes(payload))

    envelope = EscrowEnvelope(
        escrow_id=_new_escrow_id(),
        deposited_at=datetime.now(timezone.utc).isoformat(),
        depositor_vault_id_prefix=_depositor_vault_id_prefix(vault_key),
        label=label or "",
        conditions=[c.to_dict() for c in conditions],
        kdf_salt=salt,
        aes_nonce=nonce,
        ciphertext=ciphertext,
        aes_tag=tag,
        payload_size=len(payload),
        schema_version=CURRENT_SCHEMA_VERSION,
        min_reader_version=MINIMUM_READER_VERSION,
        crypto_suite=suite.name,
        producer=PRODUCER_TAG,
    )

    integrity_key = _hkdf(vault_key, salt, suite.integrity_info,
                          suite.mac_len, suite.kdf_algo)
    envelope.integrity_mac = _mac(suite, integrity_key, envelope.mac_input())
    return envelope


def verify(envelope: EscrowEnvelope, vault_key: bytes) -> Tuple[bool, str]:
    if not envelope.integrity_mac:
        return False, "envelope has no integrity_mac"
    try:
        check_compatibility(
            envelope.schema_version,
            envelope.min_reader_version,
            envelope.crypto_suite,
        )
    except FormatError as exc:
        return False, f"version check failed: {exc}"
    try:
        suite = get_suite(envelope.crypto_suite)
        integrity_key = _hkdf(vault_key, envelope.kdf_salt,
                              suite.integrity_info, suite.mac_len, suite.kdf_algo)
        expected = _mac(suite, integrity_key, envelope.mac_input())
    except Exception as exc:
        return False, f"unable to recompute MAC: {exc}"
    if not hmac.compare_digest(expected, envelope.integrity_mac):
        return False, "integrity MAC mismatch (wrong key or tampered envelope)"
    return True, "integrity ok"


def unseal(
    envelope: EscrowEnvelope,
    vault_key: bytes,
    context: Optional[Dict] = None,
) -> bytes:
    ok, reason = verify(envelope, vault_key)
    if not ok:
        raise UnsealError(f"integrity verification failed: {reason}")

    ctx = dict(context or {})
    ctx.setdefault("requester_vault_id", hashlib.sha256(vault_key).hexdigest())

    for raw in envelope.conditions:
        cond = Condition.deserialize(raw)
        passed, why = cond.is_satisfied(ctx)
        if not passed:
            raise UnsealError(
                f"release condition '{cond.type_id}' not satisfied: {why}"
            )

    suite = get_suite(envelope.crypto_suite)
    session_key = _hkdf(vault_key, envelope.kdf_salt, suite.session_key_info,
                        suite.session_key_len, suite.kdf_algo)
    return _aead_decrypt(suite, session_key, envelope.aes_nonce,
                         envelope.ciphertext, envelope.aes_tag)


def reseal(
    envelope: EscrowEnvelope,
    vault_key: bytes,
    new_suite_name: str = CURRENT_CRYPTO_SUITE,
    context: Optional[Dict] = None,
) -> EscrowEnvelope:
    """Decrypt with the envelope's original suite and re-encrypt with the new one.

    This is the cryptographically honest "upgrade" path: it requires the vault
    key, produces fresh salt/nonce/MAC, and yields a new envelope object that
    can replace the old one on disk. The conditions and label are preserved.
    Returns a new EscrowEnvelope; does NOT modify the input or any file.

    Use when:
      * A new crypto suite is available and you want to migrate stored escrows
      * You want to refresh salts/nonces for hygiene
    """
    payload = unseal(envelope, vault_key, context=context)
    from .conditions import Condition
    conds = [Condition.deserialize(c) for c in envelope.conditions]
    return seal(
        payload=payload,
        vault_key=vault_key,
        conditions=conds,
        label=envelope.label,
        suite_name=new_suite_name,
    )


def is_current_format(envelope: EscrowEnvelope) -> bool:
    """True iff this envelope is using the latest schema AND crypto suite."""
    return (envelope.schema_version, envelope.crypto_suite) == _CURRENT_FORMAT
