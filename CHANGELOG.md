# Changelog

All notable changes to the Eidolon project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Connect escrow primitives** (`src/api/server.py`, `src/identity/vault_identity.py`).
  What an application running a postal escrow on top of Eidolon (CardSwap)
  was missing, app-authenticated (Connect secret + approved app) rather
  than bound to a user JWT: `POST /connect/vault/seal` / `open` seal small
  records (≤ 16 KiB) under a key derived per (app, subject) from a new
  `EIDOLON_SEAL_SECRET` (generated and persisted like the JWT secret, never
  the same value) — the app keeps the blob, Eidolon keeps the key; and
  `POST /connect/vault/economy/holds` (+ `/{id}/release`, `/{id}/forfeit`,
  `GET /{id}`) lock EIDOLON on a vault as a behavioural bond: the amount
  leaves the balance at hold time, comes back on release, and on forfeit is
  credited to a counterparty vault (or burnt) and counted as spent.
  Holds live in `identities/economic_holds.json`, every move is in the
  vault's operations trail (`hold`, `hold_release`, `hold_forfeit`,
  `hold_forfeit_credit`), and `GET /connect/vault/economy/{vault_id}` now
  reports `eidolon_held`. The legacy demo `/vault/encrypt` stays
  demo-gated.

- **Eidos witness (`src/protocols/eidos_witness`, Tier 1).** A byte-exact port of
  what the Eidos atelier's Witness page needs to judge without replaying:
  Eidos's WOTS+ derivation (`wots`), XMSS validator signatures (`xmss`), the
  signed head against `federation.json` (`tete`), UTXO root and inclusion
  proofs (`preuve`), `etat.json` reading (`etat`), transaction core / witnesses /
  base64 encapsulation and coin selection (`envoi`, `coinselect`), the
  `eidos.carnet` exchange format written and re-read byte-identical to the
  atelier (`carnet`), and the `EIDOLON_EIDOS_ACTIF` dossier — signed head +
  output + proof — judged offline (`actif`). Format in
  `docs/EIDOS_WITNESS_FORMAT.md`; vectors are Eidos's own `vecteurs.json` plus
  cross-implementation WOTS+ vectors against `sphere_ledger.hash_sig`.
- **Eidos coffre in the vault (Tier 2 client).** A vault holds Eidos assets:
  it keeps its coffre state in a sealed sidecar under
  `identities/vault_data/<prefix>/eidos/` (no seed is ever written), syncs with
  the published state, signs spends with write-before-return of burnt keys,
  exports/imports `eidos.carnet`, and files judged Eidos assets.
- **Vault migration** now carries `identities/vault_data/<prefix>/eidos/`
  (`vault_state/vault_data/…` in the archive).
- **Sphere file: batched finality (`sphere_ledger`, Tier 1).** The
  `EIDOLON_SPHERE` container gains two optional fields, `checkpoint` and
  `checkpoint_proof`: the anchor's signed checkpoint and the sum-tree proof
  that one of the file's heads is a leaf of it. `verify_sphere` treats them
  like a receipt (same anchor-in-force rule, unknown anchor counts for
  nothing, foreign anchor is an error) and reports `final_by`
  (`"receipt"` / `"checkpoint"`) and `checkpoint_seq`;
  `verify_checkpoint_inclusion` applies the rule to a checkpoint obtained
  separately. Spec: `docs/SPHERE_LEDGER_FORMAT.md` §4–§6.
- **Sphere custody client in the Cipher runtime (`cipher-runtime sphere …`,
  runtime 1.2.0).** `list`, `claim`, `transfer`, `import`, `export`, `sync`,
  `mailbox`, `verify`, `trust` — one JSON line per call. A vault's one-time
  keys are re-derived from its vault key (nothing to back up); a signed
  transfer is written to disk before it is submitted and is never re-signed
  for the same head; an imported file is verified offline against a trust
  root compiled into the runtime (issuer key, anchor keys, pinned genesis
  roots — `config/genesis/trust.json`) and then confronted with the anchor
  (« local heads = anchor heads »); every sphere is shown as *finale* or
  *en attente*. Sphere files live under
  `identities/vault_data/<prefix>/spheres/` and travel with the vault
  (`vault_migration`) or by export/import, never by directory copy.
- **Anchor API**: `GET /api/v1/sphere/owned` (spheres held by the caller's
  vault) and `GET /api/v1/sphere/claim/instances` (the caller's genesis slots
  and their state); `GET /{sphere_id}/file` now carries the latest checkpoint
  and proof when they include the head.

## [1.2.0] - 2026-06-05

### Added

- **7-day document escrow protocol (`src/protocols/escrow_7d`).** Post-quantum
  local single-user escrow: time-locked + owner-signature release conditions
  (`TimeLock`, `OwnerSignature`, `CombinedAll`), versioned sealed envelopes with
  MAC binding per format version, a sealer/store layer, and an API + CLI surface.
  Carries a tamper-evident proof-of-concept provenance keyprint
  (`verify_provenance()`) — a frozen SHA-256 binding the author mark
  "Alef & Zgo" to a fixed UTC timestamp.
- **Vault migration protocol (`src/protocols/vault_migration`).** Export / import
  / archive of vaults with a versioned manifest, inventory, and CLI — enabling a
  vault to be moved or backed up across machines.
- **Sphere economy documentation.** Full specification of the 21,186 unique
  (never-reused) sphere templates: rarity distribution, the 8 Cosmic Cycle
  hierarchy (Primordial → Genesis → Mythical → Legendary), the four-state
  runtime lifecycle (DORMANT → EVOLVING → AWAKENED → ASCENDED) with EEP-001
  epoch gates and daily EIDOLON yields, the second-era Quest Sphere system
  (fusion / trade / decay, Twin spheres from CHSH Bell correlations), and the
  Sphere ↔ Resonance bridge coupling to Cipher activity.

### Changed

- **Legacy PSNX prism payload normalization is now scoped.** Boolean coercion
  in `psnx_normalize_legacy_prism_payload_json` only promotes the canonical
  `"True"`/`"False"` markers on recognized crypto-property fields, leaving
  unrelated string values (e.g. a `label` of `"True"`) untouched. Covered by
  `test_legacy_prism_payload_normalization_is_scoped`.

## [1.0.0] - 2025-01-XX

### Added

#### Core Pipeline (Protected - Rust Native Binary)
- **Phase 1**: Master seed generation (512-bit CSPRNG + HKDF)
- **Phase 2**: 7D Spatial Capture with EPR quantum correlations
- **Phase 3**: Physics simulation (RK4) with 256-material catalog
- **Phase 4**: Cl(0,7) Clifford algebra spinor transformation (128D)
- **Phase 5**: Bell 7D verification (CHSH inequality testing)
- **Phase 6**: Composite spinor hash (SHA3-512 + quaternion matrix)
- **Phase 7**: Post-Quantum cryptography (Kyber1024 + Dilithium5)
- **Phase 8**: Vault key derivation (Scrypt N=2^17 + HKDF)
- **Phase 9**: Genesis data generation (Merkle tree + file output)

#### Merkle Tree System
- Full Merkle tree implementation with domain separation
- Proof generation and verification (O(log n))
- Incremental leaf updates
- Tamper detection
- Serialization for storage/transmission

#### Ecosystem Registry
- Global vault registry with Merkle root
- Membership proofs for vault verification
- Blockchain anchoring data export
- Cross-vault verification support

#### Daemon CLI (`eidolond`)
- `start` / `stop` / `status` commands
- `vault create` - Create new vault with 9-phase pipeline
- `vault list` - List registered vaults
- `vault info` - Show vault details

#### Security
- Native Rust compilation (cannot be decompiled)
- Post-quantum resistance (NIST standards)
- Domain-separated hashing
- Constant-time operations for sensitive data
- No secrets in codebase

### Protected
- Holographic pipeline source code (Rust)
- Python crypto modules excluded from distribution
- Only public API exposed via PyO3 bindings

### Technical Details
- 57 Rust unit tests passing
- 15 Python integration tests passing
- ~450 KB native wheel (with PQ crypto)
- ~270 KB Python wheel (daemon/api only)
- Windows x64 build verified

## [0.1.0] - 2024-XX-XX

### Added
- Initial Python implementation
- Basic vault creation
- CLI interface

---

## Migration Notes

### From 0.x to 1.0.0
- Install `eidolon_crypto` wheel for protected pipeline
- Remove direct imports from `src.crypto` (use Rust module)
- Update vault creation to use `eidolon_crypto.pipeline_generate()`
