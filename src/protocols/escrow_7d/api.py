"""High-level API for 7D Escrow.

All functions accept ``vault_key`` (raw bytes — 32 bytes minimum) to avoid
coupling this module to Eidolon's vault identity loader. The launcher
resolves the vault key from the active session and forwards it here.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Tuple

from .conditions import Condition
from .envelope import EscrowEnvelope
from .sealer import seal, unseal, verify, SealError, UnsealError
from .store import EscrowStore


def _depositor_prefix(vault_key: bytes) -> str:
    return hashlib.sha256(vault_key).hexdigest()[:16]


def deposit_document(
    payload: bytes,
    vault_key: bytes,
    conditions: Optional[List[Condition]] = None,
    label: str = "",
) -> str:
    """Encrypt ``payload`` and persist a new escrow envelope.

    Returns the generated ``escrow_id``.
    """
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
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

    Raises UnsealError or KeyError(escrow_id) if the envelope cannot be
    retrieved. The cleartext payload is returned.
    """
    store = EscrowStore(_depositor_prefix(vault_key))
    envelope = store.load(escrow_id)
    if envelope is None:
        raise KeyError(escrow_id)
    return unseal(envelope, vault_key, context=context)


def list_escrows(vault_key: bytes) -> List[Dict]:
    """Return metadata for every escrow owned by this vault."""
    store = EscrowStore(_depositor_prefix(vault_key))
    return store.list_summaries()


def verify_integrity(escrow_id: str, vault_key: bytes) -> Tuple[bool, str]:
    """Recompute the integrity MAC without decrypting. Useful for audits."""
    store = EscrowStore(_depositor_prefix(vault_key))
    envelope = store.load(escrow_id)
    if envelope is None:
        return False, f"escrow {escrow_id} not found"
    return verify(envelope, vault_key)


def delete_escrow(escrow_id: str, vault_key: bytes) -> bool:
    """Delete an escrow on disk. Returns True if a file was removed."""
    store = EscrowStore(_depositor_prefix(vault_key))
    return store.delete(escrow_id)


__all__ = [
    "deposit_document",
    "retrieve_document",
    "list_escrows",
    "verify_integrity",
    "delete_escrow",
    "SealError",
    "UnsealError",
]
