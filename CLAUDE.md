# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Eidolon is a post-quantum cryptographic vault system with game-like economy features. It combines 9-phase entropy key generation (~8,400 bits holographic key), Bell 7D verification, Zero-Knowledge Proofs, and EVM/Bitcoin wallet integration. The system includes NFT avatars, genesis spheres, and a founder rewards system for the first 100,000 users.

## Essential Commands

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development (includes pre-commit)

# Generate a new vault key
python scripts/public/generate_key.py --name "VaultName"

# Launch the main CLI interface
python src/ui/launcher.py

# Launch vault monitor GUI
python src/ui/vault_monitor.py --auth

# Run tests (always exclude dormant tests)
python -m pytest tests/ --ignore=tests/_dormant -v
python -m pytest tests/ --ignore=tests/_dormant -v -x --tb=short  # Stop on first failure
python -m pytest tests/test_security_suite.py -v  # Security-specific tests (7/7)

# Code quality
make lint    # flake8 + mypy + bandit
make format  # black + isort
make check   # lint + test combined

# Rust crypto crate
make test-rust-native        # cargo test -p eidolon_crypto
make test-rust-bridge        # Python contract checks
make build-rust-wheel        # maturin build
```

## Architecture — 4 Subsystems

The codebase is organized into 4 subsystem packages under `src/`:

### 1. Cryptographic Pipeline (`src/crypto/`)

Core holographic key generation and cryptographic primitives.

```
src/crypto/
├── complete_key_generator.py  # 9-phase orchestrator (~8,400 bits)
├── rust_crypto.py             # Rust/Python facade (40+ functions, auto-fallback)
├── real_post_quantum.py       # McEliece/HQC/ML-DSA/Falcon/SPHINCS+ (production)
├── post_quantum_keys.py       # Legacy PQ types (PostQuantumMasterKey, HKDF)
├── zkp_auth.py                # Schnorr ZKP authentication
├── secret_sharing.py          # Shamir secret sharing (v1 + v2 large)
├── security_suite.py          # Integrated security manager
├── constant_time.py           # Constant-time operations + blinded scalars
├── authenticated_files.py     # HMAC-verified file I/O
├── psnx_native_format.py      # .psnx binary format parser/builder
├── psnx_signing.py            # PSNX file signing
├── key_bundle.py              # Key bundle packaging
├── keybundle_format.py        # Key bundle wire format
├── poly_spinor_hash.py        # Spinorial composite hash (SHA3-512)
├── spinor_crypto.py           # Clifford Cl(0,7) algebra
├── quantum_verification.py    # Bell 7D correlation verification
├── quantum_entropy.py         # Hybrid entropy sources (ANU + OS)
├── fingerprint_utils.py       # 256-bit fingerprint utilities
└── nonce_store.py             # ZKP nonce management
```

**Key:** `rust_crypto.py` is the foundation — all crypto flows through it. When the Rust wheel (`eidolon_crypto`) is installed, it uses native Rust; otherwise falls back to Python (`cryptography` lib). Both produce identical results, verified by `test_rust_crypto_bridge.py`.

### 2. Vault Identity & Persistence (`src/identity/`)

Vault creation, registration, and encrypted state management.

```
src/identity/
├── vault_identity.py       # Register/link vaults, credit EIDOLON, distribute spheres
├── persistent_vault.py     # Encrypted JSON state, asset storage, transfers
├── vault_registry.py       # Local vault database (by vault_number, key_id)
├── vault_config.py         # Vault configuration manager
├── machine_lock.py         # Per-device registration (one vault per machine)
├── identity_registry.py    # Cross-vault identity resolution
├── server_registration.py  # Remote server registration (HMAC-signed)
├── secure_key_storage.py   # Key derivation + encrypted key store
├── secure_memory.py        # DoD-wipe secure buffers
└── protected_vault_api.py  # Authenticated vault API wrapper
```

### 3. Game Economy (`src/game/`)

Sphere evolution, materials, physics simulation, and economy.

```
src/game/
├── eidolon_economy.py           # EIDOLON token balance, rewards, maintenance
├── genesis_incubator.py         # Sphere evolution (incubation cycles)
├── genesis_eggs.py              # Legacy egg → sphere bridge
├── genesis_system.py            # Genesis block creation + founder tiers
├── sphere_genesis.py            # Reward profiles by rank
├── sphere_library.py            # Sphere catalog + visual generators
├── sphere_distribution_v2.py    # Sphere allocation per vault tier
├── sphere_visual_generator.py   # 3D sphere visuals
├── runtime_spheres.py           # Runtime sphere state management
├── runtime_tick.py              # Periodic economy tick
├── yield_processor.py           # EIDOLON yield computation
├── asset_monitor.py             # Unified asset monitoring
├── pioneer_mint.py              # Pioneer mint tiers + allocation
├── runes_vesting.py             # PSNX vesting schedules (100 tiers)
├── runes_monitor.py             # PSNX runes tracking
├── spatial_capture.py           # 7D spatial capture + EPR calibration
├── physics_engine.py            # Polyhedron throw simulation
├── material_database.py         # Material properties DB
├── material_fingerprint.py      # Material-based entropy extraction
├── material_simulation_pipeline.py  # Complete material simulation
├── blender_engine.py            # 3D Blender visualization export
├── potion_system.py             # Consumable items
├── hardware_security.py         # HSM integration (YubiHSM2, TPM2)
├── alchemy_integration.py       # Alchemy API client
└── avatar_system/               # Avatar generation, management, tokenization
```

### 4. Blockchain Integration (`src/blockchain/`)

```
src/blockchain/
├── evm_wallet.py              # HD wallet (ETH/Polygon/Arbitrum/Base)
├── ordinals_avatar.py         # Bitcoin Ordinals avatar inscriptions
├── ordinals_collection.py     # Ordinals collection management
├── avatar_nft_collection.py   # EVM NFT collections
├── avatar_transfer.py         # Cross-chain avatar transfers
├── avatar_visualization.py    # Three.js avatar rendering
└── contracts/                 # Smart contract interfaces
    ├── ordinals_contract.py
    └── rune_contract.py
```

### Compatibility Layer (`src/core/__init__.py`)

`src/core/` contains only a backward-compatible `__init__.py` that re-exports symbols from the 4 subsystems. Existing `from src.core.X import Y` imports continue to work. **New code should import directly from the subsystem packages.**

### Dormant Modules (`src/_dormant/`)

32 modules that were developed but never integrated into any entry point. Preserved for future reactivation. See `src/_dormant/README.md`.

### API (`src/api/server.py`)

REST API with JWT + ZKP authentication:
```
POST /auth/challenge  - ZKP challenge
POST /auth/login      - Authentication
POST /vault/encrypt   - Encrypt data
POST /vault/decrypt   - Decrypt data
POST /vault/shares    - Create Shamir shares
```

### Entry Points

| Entry | Description |
|-------|-------------|
| `src/ui/launcher.py` | Main CLI launcher |
| `src/ui/quick_connect.py` | Quick vault authentication |
| `scripts/public/generate_key.py` | Key generation with Genesis block |
| `src/api/server.py` | FastAPI REST server |

## Key Architectural Patterns

**Dual-Key Authentication**: All vault access requires both `.psnx` (17 KB) + `.blend_data` (156 KB) files. Neither alone can unlock a vault.

**Vault Lifecycle**:
1. Genesis (`scripts/public/generate_key.py`) → Creates vault + identity + genesis block
2. Identity Registration (`src/identity/vault_identity.py`) → Links vault to machine
3. Persistent State (`src/identity/persistent_vault.py`) → Encrypted asset storage

**Machine Lock**: One vault per machine, enforced via `src/identity/machine_lock.py`.

**Local-First, File-Based**: No central database. All state is JSON in `data/`. Use `config/paths.py` `get_*_dir()` functions — never hardcode paths.

**Rust Migration**: `src/crypto/rust_crypto.py` wraps 40+ crypto functions with optional Rust acceleration via PyO3. Python fallback is always available. Cross-language parity verified by test vectors in `tests/vectors/`.

## Code Conventions

- **Formatting**: black (line-length=100), isort (profile=black), flake8, mypy, bandit
- **Security**: No plaintext keys, dual-key auth required, constant-time comparisons, secure memory wipe
- **Paths**: Always use `config/paths.py` `get_*_dir()`, never hardcode
- **Dependencies**: `cryptography`, `numpy`, `web3` (core); `pqcrypto`, `bpy` (optional, graceful fallback)

## Testing

```bash
# Full suite (exclude dormant tests)
python -m pytest tests/ --ignore=tests/_dormant -v

# Key test files
python -m pytest tests/test_security_suite.py -v        # Security features (7/7)
python -m pytest tests/test_rust_crypto_bridge.py -v    # Rust/Python parity
python -m pytest tests/test_zkp_auth_contract.py -v     # ZKP authentication
python -m pytest tests/test_secure_rng.py -v            # Entropy quality
python -m pytest tests/test_secure_storage.py -v        # Key derivation
```

**Dormant tests** (`tests/_dormant/`): Tests for modules in `src/_dormant/`. Not run by default. Will be reactivated when corresponding modules are integrated.

## Founder/Pioneer System

First 100,000 vaults get allocations:
- Supreme (#1-33): 6M PSNX, 5% immediate, 24 months vesting
- Founder 100 (#34-100): 1.5M PSNX, 10% immediate, 18 months vesting
- Founder 1000 (#101-1000): 350K PSNX, 15% immediate, 12 months vesting
- Pioneer (#1001-10000): 33K PSNX, 25% immediate, 6 months vesting
- Standard (#10001+): 1K PSNX, 50% immediate, 3 months vesting

## Project Structure

```
Eidolon/
├── src/
│   ├── crypto/              # Cryptographic pipeline (20 modules)
│   ├── identity/            # Vault identity & persistence (11 modules)
│   ├── game/                # Game economy & physics (25 modules)
│   ├── blockchain/          # EVM/Bitcoin/Ordinals (7 modules)
│   ├── core/                # Backward-compat re-export layer
│   ├── api/                 # REST API server
│   ├── ui/                  # User interfaces (CLI, GUI)
│   ├── utils/               # Shared utilities
│   └── _dormant/            # Unused modules (32, preserved)
│
├── config/                  # Configuration (paths.py, vault_config.json)
├── data/                    # Runtime data (JSON, created at runtime)
├── rust/                    # Rust crypto crate (eidolon_crypto)
├── scripts/
│   ├── public/              # User-facing scripts
│   └── admin/               # Administrative scripts
├── sdk/                     # SDKs (Python, JavaScript, Go, Rust)
├── contracts/               # Smart contracts (Solidity)
├── tests/                   # Active test suite (266 tests)
│   └── _dormant/            # Dormant tests (25, not run by default)
└── docs/                    # Documentation + archived code
```
