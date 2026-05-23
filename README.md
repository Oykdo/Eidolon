<div align="center">

<h1>Eidolon</h1>

![Security](https://img.shields.io/badge/security-post--quantum-brightgreen?style=flat-square)
![Rust](https://img.shields.io/badge/rust-native-orange?style=flat-square)
![Python](https://img.shields.io/badge/python-3.9+-yellow?style=flat-square)
![License](https://img.shields.io/badge/license-Proprietary-red?style=flat-square)
![Release](https://img.shields.io/badge/release-v1.1.1-blue?style=flat-square)

**Post-quantum cryptographic vault with holographic key derivation**

Powers identity and resonance for [Cipher](https://github.com/Oykdo/cipher) — the secure post-quantum messaging client.

---

### ⬇️ Download Eidolon v1.1.1

| Platform | Download |
|----------|----------|
| **Windows x64** | [![Windows](https://img.shields.io/badge/⬇_Download-Windows_x64-2ea44f?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/Oykdo/Eidolon/releases/download/v1.1.1/Eidolon-v1.1.1-windows-x64.exe) |
| **Linux x64** | [![Linux](https://img.shields.io/badge/⬇_Download-Linux_x64-2ea44f?style=for-the-badge&logo=linux&logoColor=white)](https://github.com/Oykdo/Eidolon/releases/download/v1.1.1/Eidolon-v1.1.1-linux-x64) |

<sub>Or grab the [full release page](https://github.com/Oykdo/Eidolon/releases/tag/v1.1.1) with archives + `SHA256SUMS`.</sub>

---

[Distribution Model](#distribution-model) • [Quick Start](#quick-start) • [Features](#features) • [Cipher Integration](#cipher-integration-sustainable-ecosystem)

</div>

---

## Distribution Model

Eidolon ships as **two layers**:

| Layer | What | Where |
|---|---|---|
| **Public** (this repo) | Integration tests, Python examples, daemon CLI source, build tooling, public API contracts, whitepapers (research). | `github.com/Oykdo/Eidolon` |
| **Proprietary** (compiled wheel) | Holographic key-generation pipeline, post-quantum primitives, Merkle / ecosystem registry, ZKP modules. | Distributed as the `eidolon-crypto` native wheel; sou[...]

This dual-layer model lets integrators audit the public API surface and validate it against the shipped test suite, while protecting the cryptographic IP that makes Eidolon's pipeline distinct. Th[...]

---

## Why Eidolon?

| Problem | Eidolon Solution |
|---------|------------------|
| Quantum computers will break RSA/ECC | **Kyber1024 + Dilithium5** (NIST PQC standards) |
| Cloud vaults = trust third parties | **Local-first**, your keys never leave your machine |
| Simple hashing is vulnerable | **Multi-layer holographic key derivation** |
| Hard to verify without revealing data | **Merkle proofs** for selective disclosure |

---

## Quick Start

### 1. Install the native wheel

```bash
pip install eidolon-crypto
```

> The `eidolon-crypto` wheel ships the protected pipeline as a native
> Rust binary with PyO3 bindings. It is the **only required dependency**
> for vault generation and verification.

### 2. Generate your first vault

```python
import eidolon_crypto as ec

vault = ec.pipeline_generate(
    user_name="MyVault",
    enable_pq=True,
    surface_material="granite",
)

print(f"Vault ID:    {vault['key_id']}")
print(f"Post-Quantum: {vault['pq_enabled']}")

# Persist the dual-key files
with open("MyVault.psnx", "wb") as f:
    f.write(bytes(vault["psnx_bytes"]))
with open("MyVault.blend_data", "w") as f:
    f.write(vault["blend_json"])
```

The pipeline produces a **`.psnx`** file (compressed key material) and a
**`.blend_data`** file (holographic entropy + signatures). **Both files are
required** to unlock the vault.

### 3. Run the public test suite

```bash
git clone https://github.com/Oykdo/Eidolon.git
cd Eidolon
pip install -r requirements.txt
python -m pytest tests/ --ignore=tests/_dormant -v
```

The public test suite validates the wheel's API against the documented
contracts (post-quantum keys, Merkle proofs, secret sharing, ZKP).

---

## Features

### Holographic Key Derivation

Vault keys are produced by a proprietary multi-stage transformation that
expands a CSPRNG master seed into post-quantum cryptographic material.
The pipeline combines a holographic entropy capture step, a domain-separated
hardening chain and a NIST post-quantum wrap (Kyber + Dilithium), and finishes
by anchoring the result inside a Merkle tree for selective disclosure.

*Pipeline internals are proprietary and reserved.*

### Merkle Tree Verification

```python
import eidolon_crypto as ec

tree = ec.MerkleTree([b"doc1", b"doc2", b"doc3"])
proof = tree.prove(1)
assert proof.verify()  # True

# Detect tampering
tree.update_leaf(1, b"tampered")
# Root hash changes — tampering detected
```

### Ecosystem Registry

```python
registry = ec.EcosystemRegistry()
proof = registry.register_vault(entry)
anchor = registry.export_anchor()
# {"root": "abc...", "vault_count": 42, "version": 7}
```

---

## Cipher Integration: Sustainable Ecosystem

Eidolon provides the cryptographic backbone for
[**Cipher**](https://github.com/Oykdo/cipher) (post-quantum messaging) through
a symbiotic economic model. The live integration is shipping in Cipher v1.3.0.

### Key Concepts

| Concept | Description | Role |
|---------|-------------|------|
| **Resonance** | Activity score (0–100) measuring vault engagement | Active users gain resonance, improving yield factors |
| **Entropy** | Inactivity penalty (0–100) accumulating over time | Encourages regular participation to avoid decay |
| **Realms** | Temporal collectives for post-quantum pioneers | Shared governance and epoch distribution |
| **Ticks** | Periodic processing events (1 per epoch) | Distributes rewards and applies decay |
| **Epochs** | Time-based reward units (~1 hour intervals) | Accumulated through activity, convertible to EIDOLON |
| **Spheres** | Rarity-based digital artifacts | Pioneer rewards with Fibonacci-weighted distribution |

### How It Works

```
Cipher activity  →  Resonance gain  →  Better yield factors
       ↓
   Realm tick   →  Epoch distribution (tier-weighted)
       ↓
   Vesting     →  EIDOLON claim
       ↓
   Treasury    →  Realm growth
```

1. Users authenticate with Eidolon vault (`.psnx` + `.blend_data`).
2. Cipher activity (logins, message sends) generates **Resonance** deltas.
3. Realms process **ticks** distributing **Epochs** based on tier multipliers.
4. Epochs vest over time (20% per week) before EIDOLON conversion.
5. Inactive realms decay, redistributing value to active participants.
6. Governance voting weight is based on vested epochs.

### Tier Multipliers

| Tier | Epoch Multiplier | Description |
|------|------------------|-------------|
| Supreme | 2.5× | Vaults #1–33 |
| Elite | 1.5× | Vaults #34–100 |
| Founder | 0.5× | Vaults #101–1000 |
| Pioneer | 0.3× | Vaults #1001–10000 |
| Standard | 0.1× | All others |

### Sphere Distribution

Spheres are distributed to the first 10,000 vaults with guaranteed minimum rarities:

| Cohort | Vaults | Spheres / vault | Guaranteed minimum |
|--------|--------|-----------------|---------------------|
| Apex | #1–10 | 8 | 1 Primordial + 1 Genesis |
| Supreme | #11–33 | 6 | 1 Genesis |
| Founder Elite | #34–100 | 4 | 1 Legendary |
| Founder | #101–1000 | 3 | 1 Epic |
| Pioneer | #1001–10000 | 2 | RNG-weighted |

**21,186 unique sphere templates** across the first 10,000 vaults — one per instance, with
Fibonacci-weighted rarity assignment distributed as: 9 Primordial, 64 Genesis, 192 Mythic,
1,152 Legendary, 1,440 Epic, 2,160 Rare, 3,600 Uncommon, 5,620 Common (templates reusable
across vaults via instance IDs).

---

## Repository Structure

What ships publicly in this repository:

```
src/daemon/         Public daemon CLI (eidolond service)
tests/              Integration & contract tests against the public wheel API
tests/vectors/      Reference vectors (rust_crypto, secret_sharing)
assets/             Renders and reference visuals
config/             Public configuration templates
.github/workflows/  CI (Python + Rust pipelines)
```

What is **not** in the public tree (shipped only via the proprietary wheel):

```
eidolon_crypto.pipeline_generate(...)   # Holographic key generation
eidolon_crypto.MerkleTree(...)           # Merkle primitives
eidolon_crypto.EcosystemRegistry(...)    # Vault registry + anchoring
eidolon_crypto.schnorr_zkp.*             # ZKP authentication
eidolon_crypto.secret_sharing.*          # Shamir splitting
```

---

## Security Model

### Dual-Key Authentication

| File | Approx. size | Purpose |
|------|--------------|---------|
| `.psnx` | ~17 KB | Primary encrypted key material |
| `.blend_data` | ~156 KB | Holographic entropy + signatures |

Neither file alone can unlock the vault. Compromise of one reveals nothing.

### Post-Quantum Stack

```
Key Encapsulation:    Kyber1024, McEliece-4096, HQC-256, NTRU
Digital Signatures:   Dilithium5 (ML-DSA-65), SPHINCS+, Falcon
Symmetric:            AES-256-GCM, ChaCha20-Poly1305
Hashing:              SHA-3-512 (Keccak)
Zero-Knowledge:       Schnorr ZKP, Merkle proofs
```

### Key Generation Pipeline

Proprietary multi-stage transformation that hardens a CSPRNG master seed
into post-quantum cryptographic material.

*Pipeline details reserved.*

---

## Rust Crypto API

The protected cryptographic pipeline is available via the `eidolon_crypto`
native module. All examples below run against the published wheel — no
proprietary Python source required.

```python
import eidolon_crypto

# Generate a vault via the holographic pipeline
result = eidolon_crypto.pipeline_generate(
    user_name="Alice",
    enable_pq=True,             # Post-quantum (Kyber1024 + Dilithium5)
    surface_material="granite",
)

vault_key  = bytes(result["vault_key"])
key_id     = result["key_id"]
merkle_root = result["merkle_root"]
psnx_bytes = bytes(result["psnx_bytes"])
blend_json = result["blend_json"]

# Merkle tree for verification
tree = eidolon_crypto.MerkleTree([b"data1", b"data2", b"data3"])
proof = tree.prove(0)
assert proof.verify()

# Ecosystem registry
registry = eidolon_crypto.EcosystemRegistry()
entry = eidolon_crypto.VaultEntry(
    vault_id="vault_001",
    key_id=key_id,
    owner_hash="...",
    merkle_root=merkle_root,
    pq_enabled=True,
    tier="supreme",
    eidolon_score=8500.0,
)
proof  = registry.register_vault(entry)
anchor = registry.export_anchor()   # For blockchain anchoring
```

---

## Development

### Public test suite

```bash
make test                # Python contract tests against the wheel
make test-rust-bridge    # Python <-> Rust bridge tests
make lint                # Ruff + Black formatting
make check               # Type checking (mypy)
```

The rust-native tests live in the proprietary crate and are not part of the
public repository.

---

## What NOT to Commit

The following are protected by `.gitignore`:

```
*.psnx
*.blend_data
*.eidolon_keybundle
*.private_key
*.master_key
*seed_phrase*
*mnemonic*
.env
data/vaults/
data/api/
backups/
```

Never commit private keys, mnemonics, seeds, vault artifacts, or
deployment credentials.

---

## License

**Eidolon Proprietary Commercial License**

Copyright (c) 2024–2026 Logos Project. All rights reserved.

This software is proprietary. No permission is granted to use, copy, modify, distribute, sublicense, or sell the Software without prior written commercial license.

- Commercial use prohibited without authorization
- Production deployment prohibited without authorization
- ML training on this codebase prohibited without authorization

Third-party dependencies retain their respective licenses.

**For licensing inquiries:** jrzg7f2k@proton.me

See `LICENSE` for full terms.

---

## Contact

- **Repository:** [github.com/Oykdo/Eidolon](https://github.com/Oykdo/Eidolon)
- **Companion product:** [Cipher](https://github.com/Oykdo/cipher) (post-quantum messaging)
- **Licensing & inquiries:** jrzg7f2k@proton.me

---

<div align="center">

*Eidolon — where cryptographic security meets sustainable economics.*

</div>
