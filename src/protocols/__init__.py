"""Eidolon protocols namespace (public, Tier 1).

- escrow_7d: sealed, time-locked document envelopes bound to a vault key
  (AES-256-GCM / HKDF / HMAC; Phase 1: local single-user; frozen v1 envelope in
  tests/vectors/escrow_7d_v1.json)
- vault_migration: export / import / archive of a vault with a versioned manifest
- sphere_ledger: the sphere custody ledger verifier (docs/SPHERE_LEDGER_FORMAT.md)
- eidos_witness: the Eidos witness — judge an Eidos signed head, output proof,
  transaction and eidos.carnet offline (docs/EIDOS_WITNESS_FORMAT.md)
"""
