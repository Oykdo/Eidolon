# Changelog

All notable changes to Eidolon will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release preparation

## [1.0.0] - 2026-01-06

### Added
- **Core Modules**
  - `spatial_capture`: 7D spatial capture with EPR calibration
  - `spinor_crypto`: Clifford algebra Cl(0,7) based encryption
  - `quantum_verification`: Bell correlation verification
  - `poly_spinor_hash`: Composite spinorial hash
  - `physics_engine`: Polyhedron physics simulation
  - `material_database`: Materials database
  - `blender_engine`: Blender visualization engine
  - `complete_key_generator`: Complete key generator (9 phases)
  - `evm_wallet`: EVM wallet for ERC20/NFTs
  - `real_post_quantum`: Real post-quantum algorithms
  - `secure_key_storage`: Secure key storage
  - `persistent_vault`: Persistent vault manager
  - `vault_config`: Vault configuration system

- **Protocols**
  - `document_escrow`: Document escrow with spinorial seal
  - `escrow_seal`: Multi-authority escrow seal
  - `escrow_recovery`: Recovery with Bell verification
  - `vault_monitoring`: Real-time vault monitoring
  - `scheduled_tasks`: Scheduled task system
  - `authority_rotation`: Authority rotation
  - `emergency_protocol`: Controlled emergency access

- **UI Components**
  - `vault_gui_complete`: Complete vault GUI (tkinter)
  - `vault_monitor`: Vault monitoring GUI
  - Blender panels for key generation and visualization

- **Configuration**
  - JSON-based configuration system
  - User-overridable settings
  - Multi-chain blockchain support

- **Docker Support**
  - Production Dockerfile
  - Docker Compose with full stack
  - Prometheus and Grafana integration
  - Automated backup service

### Security
- AES-256-GCM encryption for vault data
- PBKDF2/Argon2 key derivation
- Dual-key authentication (.psnx + .blend_data)
- Post-quantum cryptography support
- Bell inequality verification for integrity

## [0.9.0] - 2025-12-01

### Added
- Beta release with core functionality
- Initial vault system implementation
- Basic monitoring capabilities

---

[Unreleased]: https://github.com/polyspinor/nexus-7d/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/polyspinor/nexus-7d/releases/tag/v1.0.0
[0.9.0]: https://github.com/polyspinor/nexus-7d/releases/tag/v0.9.0
