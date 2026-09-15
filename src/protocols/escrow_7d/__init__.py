"""7D Escrow — sealed, time-locked document envelopes bound to a vault key.

Phase 1 (current): local, single-user. A document is encrypted with AES-256-GCM
under a session key derived by HKDF-SHA256 from the vault key and a fresh salt;
the whole envelope (versions, metadata, conditions, ciphertext) is bound by an
HMAC-SHA256 tag under a second derived key. Retrieval requires the vault key
AND the satisfaction of every attached release condition (TimeLock,
OwnerSignature, CombinedAll / CombinedAny).

Scope, stated plainly: symmetric 256-bit primitives only (no post-quantum KEM
or signature in this phase); a TimeLock is enforced by the clock of the
machine that holds the key, not by a third party; the label, the conditions,
the deposit time, the payload size and the depositor's vault-id prefix are
stored in cleartext — only the payload is encrypted. The v1 wire format is
frozen by the golden envelope in tests/vectors/escrow_7d_v1.json and the
canonical-bytes tests in tests/test_escrow_7d_*.py.

Phase 2+ (not started): threshold sharding, post-quantum signatures for
inter-vault release, optional anchoring.

Public API:
    from src.protocols.escrow_7d import (
        deposit_document, retrieve_document, list_escrows,
        list_unreadable_escrows, verify_integrity, delete_escrow,
        TimeLock, OwnerSignature, CombinedAll, CombinedAny, vault_id_from_key,
        EscrowError, EscrowStoreError, FormatError, SealError, UnsealError,
        ESCROW_SCHEMA_VERSION, READER_VERSION,
    )
"""

from .api import (
    deposit_document,
    retrieve_document,
    list_escrows,
    list_unreadable_escrows,
    verify_integrity,
    delete_escrow,
)
from .errors import EscrowError
from .format_version import FormatError
from .sealer import SealError, UnsealError
from .store import EscrowStoreError
from .conditions import (
    Condition,
    TimeLock,
    OwnerSignature,
    CombinedAll,
    CombinedAny,
    ConditionError,
    vault_id_from_key,
)
from .envelope import EscrowEnvelope, ESCROW_SCHEMA_VERSION
from .format_version import READER_VERSION
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
    "list_unreadable_escrows",
    "verify_integrity",
    "delete_escrow",
    "EscrowError",
    "EscrowStoreError",
    "FormatError",
    "SealError",
    "UnsealError",
    "Condition",
    "TimeLock",
    "OwnerSignature",
    "CombinedAll",
    "CombinedAny",
    "ConditionError",
    "vault_id_from_key",
    "EscrowEnvelope",
    "ESCROW_SCHEMA_VERSION",
    "READER_VERSION",
    "PROVENANCE_AUTHOR",
    "PROVENANCE_TIMESTAMP",
    "PROVENANCE_KEYPRINT",
    "verify_provenance",
]
