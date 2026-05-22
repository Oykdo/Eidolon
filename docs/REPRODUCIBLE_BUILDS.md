# Eidolon — Reproducible Builds & Release Signing

**Version:** 1.0  
**Date:** 2026-05-22  
**Status:** Planned — this document describes the target state

---

## Current State

- Eidolon builds are **not yet reproducible**: PyInstaller bundles include timestamps, the Rust wheel is built with `maturin` which may vary across environments, and compression levels are not pinned.
- Eidolon releases are **not code-signed**: Windows SmartScreen warns; Linux binaries have no GPG signature.
- SHA-256 checksums are published manually alongside releases.

---

## Reproducible Builds — Target

### Windows (PyInstaller)

1. **Pin all dependencies**: `requirements.txt` with exact versions (`==`), `pip freeze > requirements-lock.txt` in the build environment.
2. **Set `PYTHONHASHSEED=0`** before running PyInstaller to eliminate hash randomization.
3. **Strip timestamps**: PyInstaller's `BUILD_TIMESTAMP` can be overridden. Use `--exclude-module pytest` and `--noconfirm`.
4. **Deterministic compression**: `zlib.compress(level=9)` is deterministic; `UPX` compression must be disabled or pinned.
5. **Rust wheel**: Build with `maturin build --release --strip` in a Docker container or CI runner with pinned Rust toolchain (`rust-toolchain.toml` with `channel = "1.xx.x"`).

### Linux (PyInstaller)

Same as Windows, plus:
1. **Build in a manylinux container** to ensure glibc ABI compatibility.
2. **Static-link the Rust crate** when possible to avoid glibc version drift.

### Verification

After two independent builds from the same source:
```bash
sha256sum dist/eidolon_crypto-*.whl
sha256sum release/Eidolon.exe
# Should match byte-for-byte
```

---

## Release Signing — Target

### Windows

- **Azure Trusted Signing** (same as Cipher's planned flow):
  - Provision an Azure Trusted Signing account
  - CI step: `azure/trusted-signing-action` signs the `.exe` after build
  - SmartScreen shows "Cipher · Verified Publisher" after reputation accumulation
- Alternative: **DigiCert EV Code Signing** certificate (more expensive, but immediate SmartScreen trust)

### Linux

- **GPG detach-sign** all release artifacts:
  ```bash
  gpg --armor --detach-sign Eidolon-1.1.2-linux-x64.tar.gz
  # Produces Eidolon-1.1.2-linux-x64.tar.gz.asc
  ```
- Publish the public signing key on the repo and on keyservers.
- Users verify with:
  ```bash
  gpg --verify Eidolon-1.1.2-linux-x64.tar.gz.asc
  ```

### SHA-256SUMS (current, manual)

Already published alongside releases. To improve:
- Generate inside CI (not locally) to prevent tampering
- Sign the SHA256SUMS file with GPG as well

---

## Implementation Order

1. **GPG signing** (quick win — no account provisioning needed)
2. **Reproducible builds** (requires CI setup with pinned environments)
3. **Azure Trusted Signing** (requires Azure account provisioning and secrets configuration)

---

## What External Reviewers Can Do Now

1. Download the published binaries
2. Compute SHA-256 and compare with published `SHA256SUMS`
3. Run test vectors: install the wheel, run `generate_test_vectors.py`, compare output with `docs/TEST_VECTORS.json`
4. Verify the formal spec claims against the test vector outputs
5. Verify ML-KEM/ML-DSA outputs against NIST reference implementations (the PQ public key hashes are in the test vectors)
