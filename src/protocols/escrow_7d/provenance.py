"""Provenance keyprint for the 7D Escrow proof of concept.

This is an **authorship / proof-of-concept marker**, not a security control:
it does not gate any escrow operation and is intentionally *not* part of the
envelope integrity MAC (binding it into the MAC would change the crypto format
and break envelope backward-compatibility).

It binds the author mark ``"Alef & Zgo"`` to a fixed UTC timestamp through a
SHA-256 keyprint. The digest below is frozen as a literal, so the stamp is
tamper-evident: change the author, the timestamp, or the feature id and
:func:`verify_provenance` no longer matches. Anyone can independently recompute

    sha256("Alef & Zgo|2026-06-05T17:11:18Z|eidolon.protocols.escrow_7d")

and confirm it equals :data:`PROVENANCE_KEYPRINT`.
"""

from __future__ import annotations

import hashlib

PROVENANCE_AUTHOR: str = "Alef & Zgo"
"""Author mark for the escrow_7d proof of concept."""

PROVENANCE_TIMESTAMP: str = "2026-06-05T17:11:18Z"
"""ISO 8601 UTC instant at which the PoC keyprint was sealed."""

PROVENANCE_FEATURE: str = "eidolon.protocols.escrow_7d"
"""Stable identifier of the feature this stamp attests to."""

PROVENANCE_KEYPRINT: str = (
    "d6405b1b9658385b1264bfe5701d0ea53fbb1f45b7bd8f11c61e765afd777bb3"
)
"""Frozen SHA-256 of ``f"{AUTHOR}|{TIMESTAMP}|{FEATURE}"`` — the proof."""


def compute_keyprint(
    author: str = PROVENANCE_AUTHOR,
    timestamp: str = PROVENANCE_TIMESTAMP,
    feature: str = PROVENANCE_FEATURE,
) -> str:
    """Return the SHA-256 hex digest binding ``(author, timestamp, feature)``."""
    canonical = f"{author}|{timestamp}|{feature}".encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def verify_provenance() -> bool:
    """Recompute the keyprint from the embedded marks and compare to the frozen
    digest. Returns ``False`` if any of the three marks has been altered."""
    return compute_keyprint() == PROVENANCE_KEYPRINT
