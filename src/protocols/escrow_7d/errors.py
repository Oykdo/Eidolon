"""Exception hierarchy for Escrow Nexus.

Every error the package raises derives from :class:`EscrowError`, so a caller
can catch one type for "this escrow operation failed" and still discriminate
the cause with the subclasses defined next to the code that raises them:

    FormatError       envelope JSON / version triple cannot be read
    EscrowStoreError  on-disk problem (bad id, unreadable file, wrong scope)
    ConditionError    release condition malformed
    SealError         sealing refused (bad payload, key, label, suite)
    UnsealError       integrity, condition or decryption failure
"""

from __future__ import annotations


class EscrowError(Exception):
    """Base class for every error raised by ``src.protocols.escrow_7d``."""
