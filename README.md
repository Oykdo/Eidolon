<div align="center">

<h1>Eidolon</h1>

**Post-quantum cryptographic vault, holographic key derivation, and a hash-based custody ledger for the artifacts a vault holds.**

Powers identity, custody and resonance for [Cipher](https://github.com/Oykdo/cipher) — the post-quantum messaging client.

[![CI](https://github.com/Oykdo/Eidolon/actions/workflows/ci.yml/badge.svg)](https://github.com/Oykdo/Eidolon/actions/workflows/ci.yml)
[![Release gate](https://github.com/Oykdo/Eidolon/actions/workflows/release.yml/badge.svg)](https://github.com/Oykdo/Eidolon/actions/workflows/release.yml)
[![Release](https://img.shields.io/github/v/release/Oykdo/Eidolon?style=flat-square&label=release&color=blue)](https://github.com/Oykdo/Eidolon/releases/latest)
[![Desktop build](https://img.shields.io/badge/desktop%20build-v1.1.1-green?style=flat-square)](https://github.com/Oykdo/Eidolon/releases/tag/v1.1.1)
[![Cipher runtime](https://img.shields.io/badge/cipher--runtime-1.3.0%20(20260916)-green?style=flat-square)](https://github.com/Oykdo/cipher/releases/tag/cipher-runtime-20260916)
![Post-quantum](https://img.shields.io/badge/security-post--quantum-brightgreen?style=flat-square)
![Rust](https://img.shields.io/badge/engine-Rust%20%2B%20PyO3-orange?style=flat-square)
![Python](https://img.shields.io/badge/python-3.9%2B%20(3.12%20recommended)-yellow?style=flat-square)
![License](https://img.shields.io/badge/license-Proprietary-red?style=flat-square)

**Download** — engine wheels `eidolon_crypto` 0.1.0 (release [`v1.3.0`](https://github.com/Oykdo/Eidolon/releases/tag/v1.3.0)): [Windows x64](https://github.com/Oykdo/Eidolon/releases/download/v1.3.0/eidolon_crypto-0.1.0-cp39-abi3-win_amd64.whl) · [Linux x86_64](https://github.com/Oykdo/Eidolon/releases/download/v1.3.0/eidolon_crypto-0.1.0-cp39-abi3-manylinux_2_34_x86_64.whl) · [SHA256SUMS](https://github.com/Oykdo/Eidolon/releases/download/v1.3.0/SHA256SUMS)
Desktop build [`v1.1.1`](https://github.com/Oykdo/Eidolon/releases/tag/v1.1.1): [Windows x64 zip](https://github.com/Oykdo/Eidolon/releases/download/v1.1.1/Eidolon-1.1.1-windows-x64.zip) · [Linux x64 tar.gz](https://github.com/Oykdo/Eidolon/releases/download/v1.1.1/Eidolon-1.1.1-linux-x64.tar.gz) · [SHA256SUMS](https://github.com/Oykdo/Eidolon/releases/download/v1.1.1/SHA256SUMS)
Cipher runtime `1.3.0` ([`cipher-runtime-20260916`](https://github.com/Oykdo/cipher/releases/tag/cipher-runtime-20260916)): [Windows x64](https://github.com/Oykdo/cipher/releases/download/cipher-runtime-20260916/cipher-runtime.exe) · [Linux x86_64](https://github.com/Oykdo/cipher/releases/download/cipher-runtime-20260916/cipher-runtime) · [SHA256SUMS](https://github.com/Oykdo/cipher/releases/download/cipher-runtime-20260916/SHA256SUMS)

[Releases](#releases) · [At a glance](#at-a-glance) · [Quick start](#quick-start) · [Public protocols](#public-protocols) · [Sphere custody ledger](#sphere-custody-ledger) · [Cipher integration](#cipher-integration) · [Security](#security-model) · [Development](#development)

</div>

---

## Releases

Three badges because they answer three different questions. The **release**
is where the source and the engine wheels are (`v1.3.0`, `src/__init__.py`);
the **desktop build** is the last release that shipped the Eidolon desktop
binaries (`v1.1.1`); the **Cipher runtime** is the frozen engine Cipher
embeds (`1.3.0`, published on Oykdo/cipher). Cipher users never install
Eidolon: the engine reaches them inside the Cipher installer.

| Tag | Date | What it is | Published on the release page |
|---|---|---|---|
| **`v1.3.0`** | 2026-09-16 | Escrow Nexus (audit-hardened `escrow_7d`, real `OwnerSignature`, `check_release`, the Cipher bridge), genesis root 1 pinned in `config/genesis/`, the sphere custody ledger and client, the Eidos witness, batched finality, Connect escrow primitives, public-only packaging | **Source release**: the two vendored `eidolon_crypto` 0.1.0 wheels (`win_amd64`, `manylinux_2_34_x86_64`) + `SHA256SUMS`. No desktop build — use `v1.1.1`. The matching Cipher runtime is `cipher-runtime-20260916` below. |
| `v1.2.0` | 2026-06-05 | `escrow_7d` + `vault_migration` protocols, scoped legacy-PSNX normalisation | *Tag only — no release, no binaries.* Build from source or use the `v1.1.1` desktop build. |
| **`v1.1.1`** | 2026-05-20 | Sphere Visualizer polish; no protocol change, `v1.1.0` vaults compatible | **Latest desktop build**: `Eidolon-1.1.1-windows-x64.zip` + `Eidolon.exe`, `Eidolon-1.1.1-linux-x64.tar.gz` + `Eidolon`, `SHA256SUMS` |
| `v1.1.0` | 2026-05-20 | Logos Project rebrand | Same asset set as `v1.1.1` |
| `v1.0.0` | 2026-05-14 (released 05-16) | First public release — post-quantum vault, 9-phase pipeline, `eidolond` | `eidolon.exe` (Windows only) |

`v1.3.0` tags everything that had accumulated under *[Unreleased]* since
June — see [`CHANGELOG.md`](CHANGELOG.md). Every `v*` tag runs the
[release gate](.github/workflows/release.yml): the four public protocol
suites on a clean clone, and tag = `__version__` = a dated changelog section.

### The Cipher runtime

The Genesis ceremony, keybundle import/export, the E2EE seed and the sphere
client ship to Cipher users as one frozen binary, `cipher-runtime`. This
public tree holds no crypto core to build it from, so the binary is published
as a release asset on **[Oykdo/cipher](https://github.com/Oykdo/cipher/releases)**,
where Cipher's build pins it by name and SHA-256.

| Runtime release | `--version` | Built from | Status |
|---|---|---|---|
| [`cipher-runtime-20260912`](https://github.com/Oykdo/cipher/releases/tag/cipher-runtime-20260912) | `1.0.0` | private core `8a51d13`, after the machine-lock fix (fail-closed offline, key generated after the check, server-chosen vault number) | **Shipped** in Cipher `v1.4.2` and `v1.4.3`. Linux x86_64 (glibc ≥ 2.35) and Windows x64, `SHA256SUMS` alongside. |
| `cipher-runtime-20260909` | `1.0.0` | private core before that fix | Superseded; do not use. |
| [`cipher-runtime-20260916`](https://github.com/Oykdo/cipher/releases/tag/cipher-runtime-20260916) | `1.3.0` | private core after the genesis ceremony of 2026-09-16 (public tree `v1.3.0`) | Sphere custody client (`sphere list … trust`, `burn` / `reissue-key` / `queue`), **Escrow Nexus** (`escrow deposit … delete`), the genesis trust root compiled in (issuer `6dad3cb1…`, root `89fb26b1…`). Linux x86_64 (glibc ≥ 2.35) and Windows x64, `SHA256SUMS` alongside. Cipher's next release pins it. |

Verify any download with `sha256sum -c SHA256SUMS`.

---

## At a glance

| | |
|---|---|
| **Vault** | Two files, both required to unlock: `.psnx` (~17 KB, key material) + `.blend_data` (~156 KB, holographic entropy + signatures). Local-first: keys never leave the machine. |
| **Post-quantum engine** | Kyber1024 + Dilithium5 inside the compiled pipeline; ML-DSA-65, Falcon-512, SPHINCS+ (SHA2-256f), McEliece-6960119 and HQC-256 in the Python layer; AES-256-GCM, HKDF, scrypt, SHA-3. |
| **Custody ledger** | Hash-based, no curves, no lattices: SHA3-256, WOTS+ (RFC 8391) one-time signatures, SLH-DSA-SHA2-128s (FIPS 205) for issuers and anchors, Merkle **sum** trees. Fully verifiable offline with the public verifier. |
| **Genesis** | 21,186 spheres committed by **one** signed root; every sphere file carries its own inclusion proof (15 levels, ≈1.6 KB, verified in under half a millisecond). |
| **Tests** | 588 public tests in 69 files (166 of them pure-protocol: Python + `pqcrypto`, no native wheel — the CI runs exactly these); 729 with the private suites. Counted on 2026-09-16. |
| **Public surface** | Four protocol packages (`escrow_7d`, `vault_migration`, `sphere_ledger`, `eidos_witness`), the `eidolond` daemon, SDK stubs (Python, TypeScript, Go, Rust), format specs, threat model, reproducible-build notes. |

<details>
<summary><b>Measured on the public verifier (pure Python 3.12, Windows laptop, 2026-09-14 — median of repeated runs)</b></summary>

| Operation | Figure |
|---|---|
| WOTS+ (n = 32, w = 16) key generation + one signature | ≈100 ms |
| WOTS+ signature / public root | 2,144 B / 32 B |
| WOTS+ verification | ≈35 ms |
| SLH-DSA-SHA2-128s key generation / signature / verification | 0.5 s / 4.1 s / 3.5 ms |
| SLH-DSA public key / signature | 32 B / 7,856 B |
| Sum tree over 21,186 leaves (build) | 1.6 s |
| Inclusion proof at that scale (levels / size / verification) | 15 / 1,587 B / ≈0.4 ms |
| Sphere file: mint + three custody records + anchor receipt (size / `verify_sphere`) | 47 KB / ≈120 ms |
| Signed genesis root (`root.json`) / full mint list (`mints.jsonl`) | 16.6 KB / 9.8 MB |

Reading the figures: an SLH-DSA signature is slow and large, which is why it
is spent only where it counts — one per mint batch (the genesis root), one per
receipt, one per checkpoint — while every custody hop is a WOTS+ signature. A
verifier pays ≈35 ms per hop and ≈3.5 ms per anchor signature; the sum-tree
proof that ties a head to a checkpoint is essentially free.

</details>

---

## Distribution model

Eidolon ships as **two layers**. Publicness is a design decision, recorded in
[`IP-BOUNDARY.md`](IP-BOUNDARY.md) and enforced by a pre-commit guard
([`tools/hooks/pre-commit`](tools/hooks/pre-commit)).

| Layer | What | Where |
|---|---|---|
| **Public** (this repository) | Protocol packages and their format specifications, the daemon CLI, integration and contract tests, reference vectors, SDK stubs, whitepapers, the client trust root. | `github.com/Oykdo/Eidolon` |
| **Compiled** (native wheel) | The holographic key-generation pipeline, post-quantum wrapping, Merkle / ecosystem registry, ZKP and secret-sharing primitives. | `eidolon_crypto` wheel (Rust, PyO3, abi3) vendored under [`prebuilt_wheels/`](prebuilt_wheels) — Windows x64 and manylinux x86_64; source not distributed |
| **Private** (never shipped) | Minting, the genesis treasury and its ceremony, the anchor, the vault-side clients, the API server. | — |

Integrators audit the public API surface and the shipped test suite; the
construction that makes the pipeline distinct stays in the compiled layer.
Everything a **verifier** needs — formats, domain separators, signature
schemes, proof shapes, trusted keys — is public, because a ledger nobody can
check is not a ledger.

---

## Quick start

### 1. Install

```bash
git clone https://github.com/Oykdo/Eidolon.git
cd Eidolon
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                    # pins pqcrypto==0.4.0 (1.x renames its modules)

# The native engine is vendored, not on PyPI. Pick your platform:
pip install prebuilt_wheels/eidolon_crypto-0.1.0-cp39-abi3-win_amd64.whl              # Windows x64
pip install prebuilt_wheels/eidolon_crypto-0.1.0-cp39-abi3-manylinux_2_34_x86_64.whl  # Linux x86_64
```

The wheel is needed for vault generation, PSNX, ZKP, machine lock and secret
sharing. The four protocol packages and their tests run without it.

### 2. Generate a vault

```python
import eidolon_crypto as ec

vault = ec.pipeline_generate(user_name="MyVault", enable_pq=True, surface_material="granite")
print(vault["key_id"], vault["pq_enabled"])

with open("MyVault.psnx", "wb") as f:
    f.write(bytes(vault["psnx_bytes"]))
with open("MyVault.blend_data", "w") as f:
    f.write(vault["blend_json"])
```

Neither file alone unlocks the vault; compromise of one reveals nothing.

### 3. Verify a sphere — offline, with the public verifier

```python
import json
from src.protocols.sphere_ledger.ledger import SphereFile, GenesisRoot, verify_sphere

trust   = json.load(open("config/genesis/trust.json"))                # shipped with the client, not fetched
sphere  = SphereFile.from_json(open("RARE_0003__I00002.sphere.json").read())
genesis = GenesisRoot.from_dict(json.load(open("root.json")))         # served by the anchor, pinned by you

v = verify_sphere(
    sphere,
    issuer_pk=bytes.fromhex(trust["issuer_pk"]) if trust["issuer_pk"] else None,   # null until the ceremony
    genesis=genesis,
    known_anchors={k: bytes.fromhex(pk) for k, pk in trust["anchors"].items()},
    treasury_ids={genesis.treasury_id},
)
print(v.ok, v.owner, "final" if v.final else "waiting", v.final_by, v.errors)
```

`ok` means the mint is in the signed genesis root, every custody hop is
signed by the key committed in the previous hop, and every receipt or
checkpoint comes from the sphere's anchor of record. `final` means that anchor
has ordered the current head (`final_by` says whether by receipt or by
checkpoint). A malformed file yields a verdict, never an exception.

The same verdict from the frozen runtime, no vault involved:

```bash
cipher-runtime sphere verify --file RARE_0003__I00002.sphere.json --genesis root.json   # [--trust trust.json]
# → {"ok": true, "valid": true, "final": …, "final_by": …, "state": …, "owner": …, "genesis_checked": true, "trusted_issuer": false}
```

### 4. Run the tests

```bash
export EIDOLON_API_SECRET=0123456789abcdef0123456789abcdef   # >= 32 chars, read at import by one API test
python -m pytest tests/ --ignore=tests/_dormant -q

# Protocol suites only — no native wheel required (166 tests):
python -m pytest tests/test_ledger_*.py tests/test_eidos_witness_*.py \
                 tests/test_vault_migration.py tests/test_escrow_7d_*.py -q
```

---

## Public protocols

All four live under [`src/protocols/`](src/protocols) and import nothing
from the compiled layer: vault key material only ever enters as opaque bytes.

| Package | What it does | Spec |
|---|---|---|
| **`sphere_ledger`** | The custody ledger verifier: WOTS+ one-time signatures, SLH-DSA with per-purpose domain separation, Merkle sum trees with inclusion proofs and conservation checks, `verify_sphere`, `verify_checkpoint_inclusion`, `detect_fork`, the flux invariant an anchor must satisfy between two checkpoints. | [`docs/SPHERE_LEDGER_FORMAT.md`](docs/SPHERE_LEDGER_FORMAT.md) |
| **`eidos_witness`** | A byte-exact port of the public verifier surface of [Eidos](https://github.com/Oykdo/Eidos): WOTS+ derivation, XMSS validator signatures, signed head, UTXO inclusion proofs, transaction encoding, the `eidos.carnet` exchange format, and a self-contained asset dossier judged offline. | [`docs/EIDOS_WITNESS_FORMAT.md`](docs/EIDOS_WITNESS_FORMAT.md) |
| **`vault_migration`** | Export / import / archive of a vault with a versioned, MAC-bound manifest; carries the vault's sidecars (Eidos coffre, sphere files) without ever copying a directory. | in-package docstrings |
| **`escrow_7d`** (Escrow Nexus) | Sealed, time-locked document envelopes bound to a vault key (AES-256-GCM, HKDF-derived session key, HMAC-bound) with composable release conditions (`TimeLock`, `OwnerSignature`, `CombinedAll/Any`); phase 1 — local, single-user, the time lock is enforced by the clock of the machine holding the key; symmetric primitives only, metadata in cleartext, a frozen golden envelope pins the v1 format. The package also carries a static authorship keyprint (`verify_provenance()`). | [`docs/ESCROW_7D_FORMAT.md`](docs/ESCROW_7D_FORMAT.md) |

Also public: [`src/daemon/`](src/daemon) (`eidolond` — start/stop/status, vault
create/list/info, background service on port 8420),
[`config/genesis/trust.json`](config/genesis/trust.json) (the client trust root),
[`docs/FORMAL_SPEC.md`](docs/FORMAL_SPEC.md), [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md),
[`docs/REPRODUCIBLE_BUILDS.md`](docs/REPRODUCIBLE_BUILDS.md),
[`docs/TEST_VECTORS.json`](docs/TEST_VECTORS.json), and the vectors under [`tests/vectors/`](tests/vectors).

---

## Sphere custody ledger

A sphere is a **self-verifying file**, not a row in someone's database.

```
MintRecord ──▶ CustodyRecord #1 ──▶ CustodyRecord #2 ──▶ … ──▶ head
 (in the         (signed WOTS+ by       (signed by the key
  signed          the key committed      committed in #1)
  genesis root)   in the mint)
                                     AnchorReceipt / Checkpoint proof ──▶ final
```

- **One key, one signature.** Each custody hop is signed with a WOTS+ key whose
  root was committed in the previous record; the receiver supplies the next
  root. A client re-derives its keys from its vault key — nothing to back up —
  and writes a signed transfer to disk *before* submitting it, never signing
  twice for one head. The single deliberate exception: `reissue-key --force`
  revokes a signed, unsubmitted transfer by a second signature, settled by the
  anchor.
- **First head wins.** An *anchor* orders heads: for a given predecessor, the
  first record received becomes the head, the second is a fork and is refused.
  It signs receipts (per head) and **checkpoints** (one SLH-DSA signature over a
  sum tree of *all* heads — batched finality); a file carries the checkpoint
  and its inclusion proof. Anchors federate: a sphere names its anchor of
  record in its mint, and moving to another one is a custody record of its
  own (`reanchor`), still ordered by the old anchor.
- **Conservation is provable.** Leaves count 1 per live sphere per rarity, so a
  checkpoint root commits both the heads and the totals; `minted = held +
  burned` holds rarity by rarity, and the anchor's own reconciler halts the
  anchor if a checkpoint would violate the flux invariant. A burnt sphere stays
  in its owner's inventory as its own tombstone; the anchor refuses any record
  after it.
- **Commit-and-reveal catalogue.** The genesis root commits every template by
  hash; a sphere reveals its template only when claimed, and any receiver
  recomputes the commitment.
- **Trust travels out of band.** The issuer key, anchor keys and pinned genesis
  roots are compiled into the client ([`config/genesis/trust.json`](config/genesis/trust.json)),
  not fetched from the server they would otherwise vouch for. The client
  takes the genesis root once from the anchor, checks it against that trust
  root and caches it; a replacement root is accepted only if it supersedes
  the known one (`genesis_seq + 1`, same issuer). Without an anchor key,
  everything stays *en attente*; without an issuer key, a genesis root is
  believed only by pinning — `sphere trust` says which is the case.
  `issuer_pk` is `null` until the genesis ceremony has run; the signed
  `root.json` and `issuer_public.json` will be published next to it.

The desktop client — `cipher-runtime sphere list | claim | transfer | import |
export | sync | mailbox | queue | burn | reissue-key | verify | trust`, one JSON
line per call, no secret ever on stdout — shows every sphere as **finale**,
**en attente**, **brûlée** or **invalide**. A received file is verified
offline first (public verifier + trust root), then confronted with the anchor
("local heads = anchor heads"): same head → the receipt and checkpoint are
completed; anchor behind → the client submits what it lacks; fork → refused
as the losing branch; stale → refused. An export carries a signed, unsubmitted
transfer so that the *receiver* submits it when the sender was offline.
`sync` also reports claims the anchor deferred (`queued`) and spheres burnt
from another device (`burned`); `verify --file` needs no vault at all.

The anchor's client-facing contract, under `/api/v1/sphere/` on the REST API:
`GET genesis/root`, `genesis/mints`, `checkpoint[/{seq}]`, `{id}/head`,
`{id}/file` (with the latest checkpoint and proof when they include the
head), `{id}/checkpoint-proof`, `owned`, `claim/instances`, `claim/queue`,
`mailbox/{vault_id}`; `POST custody`, `mailbox`, `claim`. Vault-scoped routes
take the vault's challenge–proof login and require an **enrolled** vault; the
client never enrols by itself, since enrolment fixes the vault number.

---

## Cipher integration

Eidolon is the cryptographic backbone of [**Cipher**](https://github.com/Oykdo/cipher):
a vault is the account, the E2EE root derives from it, and activity feeds a
symbiotic economy.

| Concept | Description |
|---|---|
| **Resonance** | Activity score (0–100); active vaults gain resonance and better yield factors |
| **Entropy** | Inactivity penalty (0–100) accumulating over time |
| **Realms** | Temporal collectives of pioneers; shared governance and epoch distribution |
| **Ticks / Epochs** | Periodic processing distributes tier-weighted epochs (~1 hour units), which vest (20 % per week) before EIDOLON conversion |
| **Spheres** | The custody-ledger artifacts above, with yield, evolution and quests |
| **Holds** | EIDOLON locked on a vault as a behavioural bond by an approved app: leaves the balance at hold time, returns on release, goes to a counterparty (or is burnt) on forfeit. Reported as `eidolon_held`. |

```
Cipher activity → resonance → realm tick → epochs (tier-weighted) → vesting → EIDOLON claim → treasury → realm growth
```

**Connect escrow primitives.** An application running a postal escrow on top
of Eidolon authenticates as an app (Connect secret + approval), not as a user,
and gets two things: `POST /connect/vault/seal` / `open` seal small records
(≤ 16 KiB) under a key derived per (app, subject) — the app keeps the blob,
Eidolon keeps the key — and `POST /connect/vault/economy/holds` with
`/{id}/release`, `/{id}/forfeit`, `GET /{id}` for the holds above. Every move
lands in the vault's operations trail.

### Tier multipliers

| Tier | Epoch multiplier | Vaults |
|---|---|---|
| Supreme | 2.5× | #1–33 |
| Elite | 1.5× | #34–100 |
| Founder | 0.5× | #101–1,000 |
| Pioneer | 0.3× | #1,001–10,000 |
| Standard | 0.1× | all others |

### Genesis distribution

The first 10,000 vaults receive spheres with guaranteed minimum rarities, from
a distribution frozen once and committed by hash in the signed genesis root:

| Cohort | Vaults | Spheres / vault | Guaranteed minimum |
|---|---|---|---|
| Apex | #1–10 | 8 | 1 Primordial + 1 Genesis |
| Supreme | #11–33 | 6 | 1 Genesis |
| Founder Elite | #34–100 | 4 | 1 Legendary |
| Founder | #101–1,000 | 3 | 1 Epic |
| Pioneer | #1,001–10,000 | 2 | weighted draw |

**21,186 unique templates, one instance each, never reused** — 11 Primordial
(9 Core + 2 Echo), 58 Genesis, 360 Mythical, 720 Legendary, 1,440 Epic, 2,160
Rare, 3,600 Uncommon, 12,837 Common. The upper tiers descend from 8 Cosmic
Cycles (11 Primordial → 58 Genesis → 360 Mythical → 720 Legendary); the 9th
Core Primordial, *L'Inconnu*, is reserved for Vault #1.

<details>
<summary><b>Runtime lifecycle, quest spheres, resonance bridge</b></summary>

**Lifecycle** — `DORMANT → EVOLVING → AWAKENED → ASCENDED`. Activation costs 2×
base yield, at most 5 concurrent evolution slots per vault, with vault-maturity
gates by rarity (Rare 48 eons … Primordial 1,320). An awakened sphere yields
daily (`base × cycle_quality × state`, cycle quality 0.5× to 1.6×); ascension
(1.2×) needs three successful cycles or one perfect cycle. Daily base yields:
Common 4.0, Uncommon 5.5, Rare 7.0, Epic 8.0, Legendary 12.0, Mythical 18.0,
Genesis 28.0, Primordial 42.0 EIDOLON.

**Quest spheres (second era)** — minted on demand as quest rewards with their
own rarity ladder (Stone 81.4 % · Crystal 15 % · Lunar 3 % · Stellar 0.5 % ·
Cosmic 0.1 %; yield 1.0× to 5.0×), **fusion** (3 same-tier → 1 next tier),
**trade** with a 10 % burn, **decay** after 30 days of inactivity. Twin spheres
are non-tradeable artifacts derived from CHSH Bell-test correlations between
paired vaults.

**Sphere ↔ resonance bridge** — evolving spheres add passive resonance per
epoch; awakening grants a one-shot bonus; Mythical-or-higher holdings feed the
Rosetta Stone yield-bonus eligibility.

</details>

---

## Security model

| Layer | Primitives |
|---|---|
| Vault engine (compiled) | Kyber1024 (KEM) + Dilithium5 (signatures), AES-256-GCM, HKDF-SHA256/512, scrypt, PBKDF2, SHA-3; Schnorr ZKP for authentication; Shamir secret sharing (v1 and large-secret v2); Merkle proofs for selective disclosure |
| Python PQ layer | McEliece-6960119 and HQC-256 (code-based KEMs — no lattice dependency), ML-DSA-65 (FIPS 204), Falcon-512, SPHINCS+-SHA2-256f (FIPS 205) |
| Custody ledger | SHA3-256 everywhere, WOTS+ (RFC 8391, n = 32, w = 16), SLH-DSA-SHA2-128s with per-purpose domain separation (`mint`, `receipt`, `checkpoint`, `genesis`), canonical JSON |
| Escrow | `escrow_7d`: AES-256-GCM under an HKDF-derived session key, HMAC-bound envelopes, composable release conditions (symmetric primitives only). Connect seal/open: keys derived per (app, subject) from a secret distinct from the JWT secret |

Design documents: [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md),
[`docs/FORMAL_SPEC.md`](docs/FORMAL_SPEC.md),
[`docs/REPRODUCIBLE_BUILDS.md`](docs/REPRODUCIBLE_BUILDS.md).
The key-generation pipeline itself is proprietary; its *properties* (inputs,
outputs, sizes, test vectors) are documented, its construction is not.

---

## Native engine API

Everything below runs against the vendored wheel.

```python
import eidolon_crypto as ec

result = ec.pipeline_generate(user_name="Alice", enable_pq=True, surface_material="granite")
vault_key, key_id, merkle_root = bytes(result["vault_key"]), result["key_id"], result["merkle_root"]

tree = ec.MerkleTree([b"data1", b"data2", b"data3"])
assert tree.prove(0).verify()

registry = ec.EcosystemRegistry()
proof = registry.register_vault(ec.VaultEntry(
    vault_id="vault_001", key_id=key_id, owner_hash="…", merkle_root=merkle_root,
    pq_enabled=True, tier="supreme", eidolon_score=8500.0,
))
anchor = registry.export_anchor()          # {"root": …, "vault_count": …, "version": …}
```

Also exported: `aes_gcm_encrypt/decrypt`, `hkdf_sha256_derive`, `hkdf_sha512_derive`,
`scrypt_derive`, `pbkdf2_sha256_derive`, `hmac_sha256`, `shamir_split_v1/reconstruct_v1`,
`shamir_split_large_v2/reconstruct_large_v2`, `zkp_*`, `machine_lock_*`,
`secure_key_storage_*`, `complete_psnx_build/parse`, `verify_merkle_proof`,
`constant_time_compare`.

---

## Development

```bash
python -m pytest tests/ --ignore=tests/_dormant     # public suite (needs the wheel + EIDOLON_API_SECRET)
make lint                                             # flake8 + mypy + bandit
make format                                           # black + isort (line length 100)
make build-rust-wheel && make install-rust-wheel      # engine wheel, when you have the crate
```

Conventions: conventional-commit prefixes (`feat:`, `fix:`, `docs:`, `test:`),
`CHANGELOG.md` for user-visible changes, version in `src/__init__.py` only.
Never commit `.psnx`, `.blend_data`, keybundles, seeds or `.env` files — the
pre-commit guard refuses them, and `.gitignore` keeps every private path out.

### Repository structure

```
src/protocols/        sphere_ledger · eidos_witness · vault_migration · escrow_7d   (public, Tier 1)
src/daemon/           eidolond CLI and background service
config/genesis/       trust.json — issuer key, anchor keys, pinned genesis roots (root.json + issuer_public.json after the ceremony)
tests/                contract and protocol tests · tests/vectors · tests/fixtures
docs/                 format specs, formal spec, threat model, reproducible builds, test vectors
sdk/                  SDK stubs (python · javascript · go · rust)
prebuilt_wheels/      eidolon_crypto abi3 wheels (win_amd64 · manylinux_2_34_x86_64)
tools/hooks/          pre-commit publication guard
assets/visuals/       renders
.github/workflows/    ci.yml (compile + manifest checks), release.yml (frozen desktop builds on v* tags)
IP-BOUNDARY.md        what is open, what is closed, and the sign-offs that moved things across
```

---

## License

**Eidolon Proprietary Commercial License** — Copyright (c) 2024–2026 Logos Project. All rights reserved.

No permission is granted to use, copy, modify, distribute, sublicense or sell
the Software without a prior written commercial license. Commercial use,
production deployment and ML training on this codebase are prohibited without
authorization. Third-party dependencies retain their own licenses. See
[`LICENSE`](LICENSE).

## Contact

- Repository: [github.com/Oykdo/Eidolon](https://github.com/Oykdo/Eidolon)
- Companion product: [Cipher](https://github.com/Oykdo/cipher) · sibling chain: [Eidos](https://github.com/Oykdo/Eidos)
- Licensing and inquiries: jrzg7f2k@proton.me

<div align="center">

*Eidolon — where cryptographic security meets sustainable economics.*

*This README describes the `main` tree at tag `v1.3.0` (2026-09-16).*

</div>
