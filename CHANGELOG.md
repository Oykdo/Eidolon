# Changelog

All notable changes to the Eidolon project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
