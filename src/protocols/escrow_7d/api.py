"""High-level API for Escrow Nexus.

All functions accept ``vault_key`` (raw bytes — 32 bytes minimum) to avoid
coupling this module to Eidolon's vault identity loader. The launcher
resolves the vault key from the active session and forwards it here.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Tuple

from .conditions import Condition, ConditionError
from .envelope import EscrowEnvelope
from .errors import EscrowError
from .format_version import FormatError
from .sealer import check_release as _check_release, seal, unseal, verify, SealError, UnsealError
from .store import EscrowStore, EscrowStoreError


def _depositor_prefix(vault_key: bytes) -> str:
    return hashlib.sha256(vault_key).hexdigest()[:16]


def deposit_document(
    payload: bytes,
    vault_key: bytes,
    conditions: Optional[List[Condition]] = None,
    label: str = "",
) -> str:
    """Encrypt ``payload`` and persist a new escrow envelope.

    Returns the generated ``escrow_id``. Raises TypeError for a non-bytes
    payload or a non-str label, SealError for a bad key or unknown suite.
    """
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
    if label is None:
        label = ""
    if not isinstance(label, str):
        raise TypeError("label must be str")
    envelope = seal(bytes(payload), vault_key, conditions=conditions, label=label)
    store = EscrowStore(_depositor_prefix(vault_key))
    store.save(envelope)
    return envelope.escrow_id


def retrieve_document(
    escrow_id: str,
    vault_key: bytes,
    context: Optional[Dict] = None,
) -> bytes:
    """Verify integrity, evaluate release conditions, then decrypt.

    Raises KeyError(escrow_id) if no such escrow exists for this vault,
    EscrowStoreError if the id is malformed or the file cannot be parsed,
    UnsealError if the integrity check, a release condition or the
    decryption fails. All three derive from EscrowError. The cleartext
    payload is returned.
    """
    store = EscrowStore(_depositor_prefix(vault_key))
    envelope = store.load(escrow_id)
    if envelope is None:
        raise KeyError(escrow_id)
    return unseal(envelope, vault_key, context=context)


def list_escrows(vault_key: bytes) -> List[Dict]:
    """Return metadata for every readable escrow owned by this vault.

    Files that cannot be parsed are not listed here; see
    :func:`list_unreadable_escrows` so they are never silently lost.
    """
    store = EscrowStore(_depositor_prefix(vault_key))
    return store.list_summaries()


def list_unreadable_escrows(vault_key: bytes) -> List[Dict]:
    """Report this vault's files that cannot be parsed.

    Returns ``[{"escrow_id": ..., "error": ...}]`` for envelopes that are corrupt
    or were written by a newer format this build does not read.
    """
    store = EscrowStore(_depositor_prefix(vault_key))
    return store.list_unreadable()


def verify_integrity(escrow_id: str, vault_key: bytes) -> Tuple[bool, str]:
    """Recompute the integrity MAC without decrypting. Useful for audits.

    Never raises for a bad file or a malformed id: both are reported as
    ``(False, reason)`` like any other failed verification.
    """
    store = EscrowStore(_depositor_prefix(vault_key))
    try:
        envelope = store.load(escrow_id)
    except EscrowStoreError as exc:
        return False, f"unreadable: {exc}"
    if envelope is None:
        return False, f"escrow {escrow_id} not found"
    return verify(envelope, vault_key)


def check_release(escrow_id: str, vault_key: bytes) -> Tuple[bool, str]:
    """Would ``retrieve_document`` succeed right now? Answered without decrypting.

    ``(True, "releasable")`` when the envelope exists, its MAC verifies under
    ``vault_key`` and every release condition is satisfied; otherwise
    ``(False, reason)`` — the reason ``retrieve_document`` would raise, or
    "escrow … not found" / "unreadable: …". Never raises for a bad file or a
    malformed id.
    """
    store = EscrowStore(_depositor_prefix(vault_key))
    try:
        envelope = store.load(escrow_id)
    except EscrowStoreError as exc:
        return False, f"unreadable: {exc}"
    if envelope is None:
        return False, f"escrow {escrow_id} not found"
    return _check_release(envelope, vault_key)


def delete_escrow(escrow_id: str, vault_key: bytes) -> bool:
    """Delete an escrow on disk (readable or not). True if a file was removed.

    Raises EscrowStoreError for a malformed id or a file that cannot be removed.
    """
    store = EscrowStore(_depositor_prefix(vault_key))
    return store.delete(escrow_id)


__all__ = [
    "deposit_document",
    "retrieve_document",
    "list_escrows",
    "list_unreadable_escrows",
    "verify_integrity",
    "check_release",
    "delete_escrow",
    "EscrowError",
    "EscrowStoreError",
    "FormatError",
    "ConditionError",
    "SealError",
    "UnsealError",
]
