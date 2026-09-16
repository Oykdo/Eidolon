# Changelog

All notable changes to the Eidolon project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.0] - 2026-09-16

### Fixed

- **Escrow Nexus hardening (`src/protocols/escrow_7d`, audit of 2026-09-15).** No change
  to the v1 wire format — a frozen golden envelope (`tests/vectors/escrow_7d_v1.json`)
  now pins it. Every escrow-level error derives from `EscrowError`
  (`EscrowStoreError`, `FormatError`, `ConditionError`, `SealError`, `UnsealError`;
  bad argument types still raise `TypeError`); `retrieve_document` only lets
  `KeyError` / `EscrowStoreError` / `UnsealError` escape, and `verify_integrity`
  reports an unreadable file or a malformed id as `(False, reason)` instead of
  raising. A non-`str` label is refused at deposit (it used to seal an envelope
  whose MAC could never verify again; `None` still means no label). A corrupt,
  truncated or newer-format `.escrow7d` — or a file whose inner `escrow_id` does not
  match its file name — no longer crashes `list_escrows` and is no longer hidden
  either: `list_unreadable_escrows()` reports it, the CLI list shows it, "Verify →
  all" counts it as failed and Delete can remove it. Read-only calls no longer
  create the vault's escrow directory (`EscrowStore` now requires the 16-hex
  depositor prefix the API always passed). The reader version is a constant of its
  own (`READER_VERSION`) instead of being aliased to the schema version. CLI: an
  interrupted prompt (Ctrl-C / EOF) now cancels — it used to be read as "accept the
  default", which wrote the decrypted document to `~/Downloads`; Ctrl-C during an
  action returns to the escrow menu instead of quitting the launcher; an invalid or
  negative time-lock input is asked again instead of silently depositing without a
  lock; retrieve asks before overwriting an existing file (exact `OVERWRITE`, as
  Delete requires exact `DELETE`), accepts `Q`, and defaults to the home directory
  rather than the working directory when `~/Downloads` is absent. Store: an orphan
  `<id>.escrow7d.tmp` left by a crash between write and rename is ignored by every
  read path and removed by the next save once it is older than a minute (a write in
  flight elsewhere is never touched). New public
  tests: `tests/test_escrow_7d_api_store.py` (lifecycle on disk, isolation, corrupt
  files, error contract, golden vector, RFC 5869 HKDF vectors, CLI safety).
- **`vault_migration` CLI no longer imports the launcher.** Like the escrow CLI,
  `src/protocols/vault_migration/cli.py` carries its own console helpers (same
  palette, colours only on a terminal and unless `NO_COLOR` is set): a public
  protocol package imports nothing private, in a clone or in the full tree.

### Changed

- **The document escrow protocol is called Escrow Nexus.** Display name only: the
  package path `src/protocols/escrow_7d`, the `.escrow7d` suffix, the producer tag
  and the v1 golden vector are unchanged, so existing envelopes open as before.
  The launcher entry `[X]` reads "Escrow Nexus" and describes what the protocol
  does (sealed, time-locked document envelopes) instead of "post-quantum". The
  "7-day" wording of the 1.2.0 entry below was a misnomer: no seven-day semantic
  exists in the protocol; a time lock is whatever date the depositor chooses.
- **Packaging: a wheel or sdist built from the full working tree now contains
  only the public packages** (`src`, `src.daemon`, `src.protocols`, `config`) —
  the same set a clone yields. `pyproject.toml` and `MANIFEST.in` used to list
  `src.identity`, `src.api`, `src.ui` and `src.utils` under "public", so
  `python -m build` from the private tree packaged Tier 2 code (verified: 49
  private files, plus two untracked config files, in a wheel built before the
  change; 44 tracked public files after). Nothing installs that distribution today;
  this closes the path before anything does.
- **`OwnerSignature` is now a real release condition** (`src/protocols/escrow_7d`).
  It accepts the vault's 64-hex id (`vault_id_from_key(vault_key)`, or
  `OwnerSignature.for_vault_key(vault_key)`) or the 16-hex
  `depositor_vault_id_prefix` shown in listings — an envelope sealed with the
  prefix used to be locked forever. The requester identity is derived from the
  key that opens the envelope and can no longer be supplied through `context`.
  `seal()` refuses an `OwnerSignature` naming another vault (such an escrow could
  never be opened, since only the depositing key verifies the MAC), and an
  identifier that is neither form raises `ConditionError`. The check runs on the
  serialised conditions — the bytes the MAC binds — and a prefix is stored as the
  full id, so every envelope this version writes also opens with the previous
  reader. Composite nesting is bounded (`MAX_CONDITION_DEPTH` = 32) at seal and at
  unseal, so the verdict never depends on the reader's stack. Stored envelopes with
  a full-id `OwnerSignature` open exactly as before.
- **Escrow Nexus said plainly.** The package, `src/protocols/__init__.py` and the
  threat model (`docs/THREAT_MODEL.md` §5.4) now state what Phase 1 is: symmetric
  256-bit primitives (no post-quantum KEM or signature), a session key *derived*
  by HKDF (not wrapped), time locks enforced by the key holder's own clock, and
  cleartext metadata (label, conditions, deposit time, size, depositor prefix).
  The wire format has a specification, `docs/ESCROW_7D_FORMAT.md`, and the v1
  format is pinned by `tests/vectors/escrow_7d_v1.json`. The escrow CLI
  no longer imports the launcher (a public package importing private code): it
  carries its own console helpers, coloured only on a terminal and unless
  `NO_COLOR` is set. The store fsyncs before renaming, reports an envelope copied
  from another vault's directory as unreadable instead of listing it, and the list
  column reads `none` (not `owner`) when an escrow has no condition. Packaging:
  `src.protocols` is now part of the wheel (`pyproject.toml`) and the sdist
  (`MANIFEST.in`).

### Removed

- **`docs/CHANGELOG.md`** (pre-rename, January 2026) is no longer in the public
  tree: it described modules and an escrow design that do not exist here and
  contradicted this file. `CHANGELOG.md` at the repository root is the only
  changelog. Package metadata (`pyproject.toml`, `setup.cfg`, `CONTRIBUTING.md`)
  now carries the project's name and public contact address.

### Added

- **Escrow Nexus in the Cipher runtime (`cipher-runtime escrow …`, runtime 1.3.0).**
  `deposit`, `list`, `show`, `retrieve`, `verify`, `delete` — one JSON line per
  call, on the model of `sphere …`. The vault key is derived from the `.psnx`
  in-process; the document only ever travels as a file (`--file` in, `--out`
  out), never inside the JSON; envelopes go to the same store as the launcher's
  `[X]` menu, so both sides see the same escrows. `deposit` takes an optional
  `--release-after <ISO 8601>` time lock and `--owner-only`; `retrieve` never
  overwrites without `--overwrite`; `delete` requires `--confirm`. `error_code`
  tells the client what happened without parsing the message: `not_found`,
  `locked` (with `release_after`), `integrity`, `unreadable`, `exists`,
  `invalid_input`, `confirmation_required`. Public API: `check_release(escrow_id,
  vault_key)` answers "would `retrieve_document` succeed now?" — MAC and release
  conditions — without decrypting, with the exact reason `retrieve_document`
  would raise; `list`/`show` report it as `releasable` / `reason` /
  `release_after`.
- **Genesis root 1 (`config/genesis/`).** The genesis ceremony was held offline on
  2026-09-16: `root.json` is the signed genesis root (21 186 sphere mints,
  distribution `220f67fd…`, Merkle root `28f7b9e5…`, issued
  `2026-09-16T03:25:14Z`, SLH-DSA-SHA2-128s signature), `issuer_public.json` the
  issuer's public key `6dad3cb1…3e31f8`, and `trust.json` now pins the issuer and
  the root's record hash `89fb26b1…f0053e` next to the anchor key. Verifiable with
  the public verifier: `GenesisRoot.from_dict(root).verify(issuer_pk)`. The anchor
  serves this root; the first key window (vaults 1–500) is released.
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
- **Sphere client: `burn`, `reissue-key`, `queue` (runtime 1.2.1).**
  `sphere burn --confirm` ends a sphere's custody chain (the file stays in
  the inventory as its own tombstone, state *brûlée*; the anchor refuses any
  record after it); `sphere reissue-key` retires the key controlling a sphere
  in favour of the next derived one without moving it (`--force` revokes a
  signed, unsubmitted transfer by a second signature — the one deliberate
  exception to « a key signs once », settled by the anchor); `sphere queue`
  lists the caller's claims the anchor deferred for lack of a released key
  window, and `sync` now reports them (`queued`) as well as spheres burnt
  from another device (`burned`). All three follow the transfer rule: read
  the head at the anchor, write the signed record before submitting it,
  never sign twice for the same head.
- **Sphere client: anchor error codes (runtime 1.2.1).** `error_code` now
  says where a failure comes from, so Cipher decides without parsing the
  message: `anchor_unreachable` (no answer, 408, 429, 5xx — retry with
  back-off), `not_enrolled` (the anchor does not know this vault: enrolment
  is the lock server's, retry much later), `anchor_refused` (any other anchor
  error — fork, unknown sphere, empty mailbox…); `wallet_refused` is kept for
  the client's own refusals (stale head, key already signed, foreign file).
  `WalletError.code` carries it in-process. The HTTP status stays in the
  message, in parentheses, for older clients; a submission the anchor did
  not answer on the merits (a halted anchor's 503, not only a cut) is now
  reported as unreachable, the signed record waiting in `pending/` as before.

## [1.2.0] - 2026-06-05

*Tag only — no release page, no binaries (see the README's releases table).*

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

## [1.1.1] - 2026-05-20

### Changed

- Sphere Visualizer polish. No protocol change; `v1.1.0` vaults are compatible.
  Latest desktop build: `Eidolon-1.1.1-windows-x64.zip` + `Eidolon.exe`,
  `Eidolon-1.1.1-linux-x64.tar.gz` + `Eidolon`, `SHA256SUMS`.

## [1.1.0] - 2026-05-20

### Changed

- Logos Project rebrand. Same asset set as `v1.1.1`.

## [1.0.0] - 2026-05-14

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
