"""7D Escrow — post-quantum document escrow protocol.

Phase 1 (current): local, single-user. A document is sealed with AES-256-GCM,
the session key is wrapped with HKDF(vault_key, salt), and the whole envelope
carries an HMAC integrity tag. Retrieval requires the vault key AND the
satisfaction of any attached release conditions (e.g. TimeLock).

Phase 2+ will add Shamir threshold sharding, ML-DSA signatures for inter-vault
verification, and optional Merkle anchoring on-chain.

Public API:
    from src.protocols.escrow_7d import (
        deposit_document, retrieve_document, list_escrows,
        verify_integrity, delete_escrow,
        TimeLock, OwnerSignature, CombinedAll, CombinedAny,
    )
"""

from .api import (
    deposit_document,
    retrieve_document,
    list_escrows,
    verify_integrity,
    delete_escrow,
)
from .conditions import (
    Condition,
    TimeLock,
    OwnerSignature,
    CombinedAll,
    CombinedAny,
    ConditionError,
)
from .envelope import EscrowEnvelope, ESCROW_SCHEMA_VERSION
from .provenance import (
    PROVENANCE_AUTHOR,
    PROVENANCE_TIMESTAMP,
    PROVENANCE_KEYPRINT,
    verify_provenance,
)

__all__ = [
    "deposit_document",
    "retrieve_document",
    "list_escrows",
    "verify_integrity",
    "delete_escrow",
    "Condition",
    "TimeLock",
    "OwnerSignature",
    "CombinedAll",
    "CombinedAny",
    "ConditionError",
    "EscrowEnvelope",
    "ESCROW_SCHEMA_VERSION",
    "PROVENANCE_AUTHOR",
    "PROVENANCE_TIMESTAMP",
    "PROVENANCE_KEYPRINT",
    "verify_provenance",
]
