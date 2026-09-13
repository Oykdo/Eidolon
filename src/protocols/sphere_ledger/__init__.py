"""Sphere custody ledger — the public verifier (Tier 1).

A sphere is a self-verifying file: a mint record authenticated by its
inclusion in a signed genesis root, custody records each signed by a
one-time WOTS+ key committed in the previous record, and receipts or
checkpoint proofs from the anchor that ordered its heads. Everything here is
hash-based and public-standard: SHA3-256, WOTS+ (RFC 8391), SLH-DSA
(FIPS 205), canonical JSON, a Merkle sum tree.

Format: ``docs/SPHERE_LEDGER_FORMAT.md``. Nothing in this package derives,
stores or touches a vault key; key material only ever enters as opaque bytes
(``ledger.ReceiverKey.derive``). Minting, the genesis treasury and the
ceremony are not part of the public verifier.

Modules
    hash_sig    WOTS+ one-time signatures (n = 32, w = 16)
    slh_dsa     SLH-DSA-SHA2-128s with per-purpose domain separation
    checkpoint  Merkle sum tree, inclusion proofs, conservation, signed checkpoints
    ledger      records, sphere file, ``verify_sphere``, ``detect_fork``
    flux        the divergence balance and the anchor invariant
"""
from . import checkpoint, flux, hash_sig, ledger, slh_dsa

__all__ = ["hash_sig", "slh_dsa", "checkpoint", "ledger", "flux"]
