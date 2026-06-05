# Changelog

All notable changes to the Eidolon project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
