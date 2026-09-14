<div align="center">

<h1>Eidolon</h1>

**Post-quantum cryptographic vault, holographic key derivation, and a hash-based custody ledger for the artifacts a vault holds.**

Powers identity, custody and resonance for [Cipher](https://github.com/Oykdo/cipher) — the post-quantum messaging client.

[![CI](https://github.com/Oykdo/Eidolon/actions/workflows/ci.yml/badge.svg)](https://github.com/Oykdo/Eidolon/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Oykdo/Eidolon?style=flat-square&color=blue)](https://github.com/Oykdo/Eidolon/releases/latest)
![Post-quantum](https://img.shields.io/badge/security-post--quantum-brightgreen?style=flat-square)
![Rust](https://img.shields.io/badge/engine-Rust%20%2B%20PyO3-orange?style=flat-square)
![Python](https://img.shields.io/badge/python-3.9%2B%20(3.12%20recommended)-yellow?style=flat-square)
![License](https://img.shields.io/badge/license-Proprietary-red?style=flat-square)

[Downloads](#downloads) · [At a glance](#at-a-glance) · [Quick start](#quick-start) · [Public protocols](#public-protocols) · [Sphere custody ledger](#sphere-custody-ledger) · [Cipher integration](#cipher-integration) · [Security](#security-model) · [Development](#development)

</div>

---

## Downloads

Desktop builds (Windows x64, Linux x64) and `SHA256SUMS` are published on the
**[latest release page](https://github.com/Oykdo/Eidolon/releases/latest)**.
Cipher ships the same engine as a frozen runtime (`cipher-runtime`), so a
Cipher user never installs Eidolon separately.

---

## At a glance

| | |
|---|---|
| **Vault** | Two files, both required to unlock: `.psnx` (~17 KB, key material) + `.blend_data` (~156 KB, holographic entropy + signatures). Local-first: keys never leave the machine. |
| **Post-quantum engine** | Kyber1024 + Dilithium5 inside the compiled pipeline; ML-DSA-65, Falcon-512, SPHINCS+ (SHA2-256f), McEliece-6960119 and HQC-256 in the Python layer; AES-256-GCM, HKDF, scrypt, SHA-3. |
| **Custody ledger** | Hash-based, no curves, no lattices: SHA3-256, WOTS+ (RFC 8391) one-time signatures, SLH-DSA-SHA2-128s (FIPS 205) for issuers and anchors, Merkle **sum** trees. Fully verifiable offline with the public verifier. |
| **Genesis** | 21,186 spheres committed by **one** signed root; every sphere file carries its own inclusion proof (15 levels, ≈1.9 KB, verified in 0.2 ms). |
| **Tests** | 526 public tests (101 of them pure-protocol: Python + `pqcrypto` only); 622 with the private suites — all green on 2026-09-14. |
| **Public surface** | Four protocol packages (`escrow_7d`, `vault_migration`, `sphere_ledger`, `eidos_witness`), the `eidolond` daemon, SDK stubs (Python, TypeScript, Go, Rust), format specs, threat model, reproducible-build notes. |

<details>
<summary><b>Measured on the public verifier (pure Python, laptop, 2026-09-14)</b></summary>

| Operation | Figure |
|---|---|
| WOTS+ (n = 32, w = 16) key generation + one signature | ≈34 ms |
| WOTS+ signature / public root | 2,144 B / 32 B |
| WOTS+ verification | ≈37 ms |
| SLH-DSA-SHA2-128s key generation / signature / verification | 0.19 s / 1.4 s / 1.6 ms |
| SLH-DSA public key / signature | 32 B / 7,856 B |
| Sum tree over 21,186 leaves (build) | 0.72 s |
| Inclusion proof at that scale (levels / size / verification) | 15 / 1,936 B / 0.23 ms |
| Whole sphere file, three custody hops + receipt, `verify_sphere` | ≈23 ms |
| Signed genesis root (`root.json`) / full mint list (`mints.jsonl`) | 16.6 KB / 9.8 MB |

</details>

---

## Distribution model

Eidolon ships as **two layers**. Publicness is a design decision, recorded in
[`IP-BOUNDARY.md`](IP-BOUNDARY.md) and enforced by a pre-commit guard
([`tools/hooks/pre-commit`](tools/hooks/pre-commit)).

| Layer | What | Where |
|---|---|---|
| **Public** (this repository) | Protocol packages and their format specifications, the daemon CLI, integration and contract tests, reference vectors, SDK stubs, whitepapers. | `github.com/Oykdo/Eidolon` |
| **Compiled** (native wheel) | The holographic key-generation pipeline, post-quantum wrapping, Merkle / ecosystem registry, ZKP and secret-sharing primitives. | `eidolon-crypto` wheel (Rust, PyO3, abi3); source not distributed |
| **Private** (never shipped) | Minting, the genesis treasury and its ceremony, the vault-side clients, the API server. | — |

Integrators audit the public API surface and the shipped test suite; the
construction that makes the pipeline distinct stays in the compiled layer.
Everything a **verifier** needs — formats, domain separators, signature
schemes, proof shapes — is public, because a ledger nobody can check is not a
ledger.

---

## Quick start

### 1. Install

```bash
git clone https://github.com/Oykdo/Eidolon.git
cd Eidolon
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                    # pins pqcrypto==0.4.0 (1.x renames its modules)
pip install eidolon-crypto                         # the native engine, needed for vault generation
```

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

sphere  = SphereFile.from_json(open("RARE_0003__I00002.sphere.json").read())
genesis = GenesisRoot.from_dict(json.load(open("root.json")))      # served by the anchor, pinned by you

v = verify_sphere(
    sphere,
    issuer_pk=bytes.fromhex(ISSUER_PUBLIC_KEY),                    # from a channel independent of the server
    genesis=genesis,
    known_anchors={"eidolon-anchor-1": bytes.fromhex(ANCHOR_PUBLIC_KEY)},
    treasury_ids={genesis.treasury_id},
)
print(v.ok, v.owner, "final" if v.final else "waiting", v.final_by, v.errors)
```

`ok` means the mint is in the signed genesis root, every custody hop is
signed by the key committed in the previous hop, and every receipt or
checkpoint comes from the sphere's anchor of record. `final` means that anchor
has ordered the current head. A malformed file yields a verdict, never an
exception.

### 4. Run the tests

```bash
export EIDOLON_API_SECRET=0123456789abcdef0123456789abcdef   # >= 32 chars, read at import by one API test
python -m pytest tests/ --ignore=tests/_dormant -q

# Protocol suites only — no native wheel required:
python -m pytest tests/test_ledger_*.py tests/test_eidos_witness_*.py tests/test_vault_migration.py -q
```

---

## Public protocols

All four live under [`src/protocols/`](src/protocols) and import nothing
from the compiled layer: vault key material only ever enters as opaque bytes.

| Package | What it does | Spec |
|---|---|---|
| **`sphere_ledger`** | The custody ledger verifier: WOTS+ one-time signatures, SLH-DSA with per-purpose domain separation, Merkle sum trees with inclusion proofs and conservation checks, `verify_sphere`, `detect_fork`, the flux invariant an anchor must satisfy between two checkpoints. | [`docs/SPHERE_LEDGER_FORMAT.md`](docs/SPHERE_LEDGER_FORMAT.md) |
| **`eidos_witness`** | A byte-exact port of the public verifier surface of [Eidos](https://github.com/Oykdo/Eidos): WOTS+ derivation, XMSS validator signatures, signed head, UTXO inclusion proofs, transaction encoding, the `eidos.carnet` exchange format, and a self-contained asset dossier judged offline. | [`docs/EIDOS_WITNESS_FORMAT.md`](docs/EIDOS_WITNESS_FORMAT.md) |
| **`vault_migration`** | Export / import / archive of a vault with a versioned, MAC-bound manifest; carries the vault's sidecars (Eidos coffre, sphere files) without ever copying a directory. | in-package docstrings |
| **`escrow_7d`** | Time-locked sealed envelopes (AES-256-GCM, HKDF-wrapped session key, HMAC tag) with composable release conditions (`TimeLock`, `OwnerSignature`, `CombinedAll/Any`) and a provenance keyprint. | in-package docstrings |

Also public: [`src/daemon/`](src/daemon) (`eidolond` — start/stop/status, vault
create/list/info, background service on port 8420), [`docs/FORMAL_SPEC.md`](docs/FORMAL_SPEC.md),
[`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md), [`docs/REPRODUCIBLE_BUILDS.md`](docs/REPRODUCIBLE_BUILDS.md),
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
  twice for one head.
- **First head wins.** An *anchor* orders heads: for a given predecessor, the
  first record received becomes the head, the second is a fork and is refused.
  It signs receipts (per head) and **checkpoints** (one SLH-DSA signature over a
  sum tree of *all* heads — batched finality); a file carries the checkpoint
  and its inclusion proof.
- **Conservation is provable.** Leaves count 1 per live sphere per rarity, so a
  checkpoint root commits both the heads and the totals; `minted = held +
  burned` holds rarity by rarity, and the anchor's own reconciler halts the
  anchor if a checkpoint would violate the flux invariant.
- **Commit-and-reveal catalogue.** The genesis root commits every template by
  hash; a sphere reveals its template only when claimed, and any receiver
  recomputes the commitment.
- **Trust travels out of band.** The issuer key, anchor keys and pinned genesis
  roots are compiled into the client (`config/genesis/trust.json`), not fetched
  from the server they would otherwise vouch for.

The desktop client (`cipher-runtime sphere list|claim|transfer|import|export|sync|mailbox|verify|trust`)
shows every sphere as **finale** or **en attente**; a received file is verified
offline first, then confronted with the anchor ("local heads = anchor heads").

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

```
Cipher activity → resonance → realm tick → epochs (tier-weighted) → vesting → EIDOLON claim → treasury → realm growth
```

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
| Escrow | AES-256-GCM, HKDF-wrapped session keys, HMAC-bound envelopes, composable release conditions |

Design documents: [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md),
[`docs/FORMAL_SPEC.md`](docs/FORMAL_SPEC.md),
[`docs/REPRODUCIBLE_BUILDS.md`](docs/REPRODUCIBLE_BUILDS.md).
The key-generation pipeline itself is proprietary; its *properties* (inputs,
outputs, sizes, test vectors) are documented, its construction is not.

---

## Native engine API

Everything below runs against the published wheel.

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
tests/                contract and protocol tests · tests/vectors · tests/fixtures
docs/                 format specs, formal spec, threat model, reproducible builds, test vectors
sdk/                  SDK stubs (python · javascript · go · rust)
tools/hooks/          pre-commit publication guard
assets/visuals/       renders
.github/workflows/    ci.yml (compile + manifest checks), release.yml (frozen desktop builds)
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

</div>
