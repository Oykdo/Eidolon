# Eidolon — Threat Model

**Version:** 1.0  
**Date:** 2026-05-22  
**Status:** Public

---

## 1. System Description

Eidolon is a local-first cryptographic vault system. All key material is generated, stored, and used on the user's device. The server (Eidolon Connect / lock server) never sees private keys, vault keys, or plaintext. Authentication uses Schnorr NIZK proofs of possession.

---

## 2. Assets

| Asset | Location | Exposure risk |
|-------|----------|--------------|
| Master seed (512-bit) | Device RAM during generation only | Never persisted to disk |
| Vault key `K_final` | Device RAM during use; sealed in `.blend_data` (encrypted) | Exposure requires both `.psnx` + `.blend_data` + temporal context |
| `.psnx` file | User's disk (~17 KB) | Contains only public material + PQ public keys + commitment |
| `.blend_data` file | User's disk (~156 KB) | Contains temporally-masked private material; useless without `.psnx` |
| PQ private keys | Device RAM during generation; sealed in `.blend_data` | Same as `K_final` |
| Schnorr private scalar | Device RAM during proof generation | Ephemeral; zeroed after use |
| Machine lock hash | User's disk (`data/`) | One-way hash of machine identifiers; no secret material |

---

## 3. Adversary Model

### 3.1 In Scope

| Adversary | Capability | Mitigation |
|-----------|-----------|------------|
| **Passive network adversary** | Observes all traffic between client and server | All sensitive data is encrypted (TLS + application-layer E2EE); server never sees plaintext |
| **Quantum-capable adversary (post-harvest)** | Can break RSA/ECDH retroactively from captured traffic | ML-KEM (Kyber1024) + ML-DSA (Dilithium5) at NIST Level 5; Classic McEliece/HQC as lattice-independent backup |
| **Compromised server** | Full read access to server database and memory | Server stores only ciphertext, public keys, PSNX hash proofs, and ZKP commitments; no private material ever transmitted |
| **File-copy attacker** | Obtains `.psnx` OR `.blend_data` (but not both) | Neither file alone can reconstruct `K_final`; AEAD tag binds them cryptographically |
| **Replay attacker** | Replays a previous ZKP proof | Proofs include timestamp + challenge; 5-minute expiry enforced server-side |

### 3.2 Out of Scope (explicitly NOT protected against)

| Threat | Why out of scope |
|--------|-----------------|
| **Endpoint compromise** (malware, keylogger, rootkit) | If the device is fully compromised, no local-first system can protect keys in memory. Mitigation: hardware security modules (future), OS-level sandboxing. |
| **OS-level data leakage** (swap, crash dumps, hibernation files, clipboard) | The vault key exists in process memory during operation. OS memory management may persist it to swap or crash dumps. Mitigation: memory locking (`mlock`), disabling core dumps (planned). |
| **User operational errors** (backing up wrong files, storing vault files in cloud storage, sharing `.psnx` + `.blend_data` together) | The system can only protect data it controls. If a user uploads both vault files to an insecure location, the system cannot prevent it. Mitigation: UI warnings, separate-file storage guidance. |
| **Side-channel attacks** (timing, power, cache) on the local execution environment | The Rust native extension implements constant-time operations where practical (Scrypt, HMAC verification). Full side-channel resistance against a local attacker with physical access is not claimed. |
| **Supply-chain attacks** (compromised PyPI/npm packages, malicious Rust crate builds) | The user is responsible for verifying download integrity via SHA-256 checksums. Reproducible builds are planned to allow independent binary verification. |
| **Social engineering** (phishing the user into running modified software) | Out of scope for a cryptographic protocol. Mitigated by code signing (planned). |

---

## 4. Cryptographic Assumptions

| Assumption | Strength | Failure impact |
|------------|----------|---------------|
| SHA3-512 is preimage-resistant | Standard (NIST FIPS 202) | Pipeline hash chain broken; `K_final` recovery becomes feasible |
| ML-KEM (Kyber1024) is IND-CCA2 at Level 5 | Standard (NIST FIPS 203) | Session key confidentiality broken; Classic McEliece/HQC provides independent backup |
| ML-DSA (Dilithium5) is EUF-CMA at Level 5 | Standard (NIST FIPS 204) | Vault attestation signatures forgeable |
| Scrypt (N=2^17, r=8, p=1) provides ~128-bit resistance | Standard (RFC 7914) | `K_final` derivable from pipeline state without brute force |
| Schnorr NIZK is zero-knowledge under random oracle | Standard (Fiat-Shamir transform) | Proof leaks information about private scalar |

A break in the hash chain or Scrypt assumption compromises the custom pipeline but **does not** compromise the PQ layer. A break in the PQ layer **does not** compromise the hash chain. The two pillars are independent.

---

## 5. Specific Risks

### 5.1 Dual-file requirement

Both `.psnx` and `.blend_data` must be present to unlock a vault. If either is lost, the vault is permanently inaccessible. **There is no recovery without both files.** The Shamir secret sharing module can split a vault key across `n` custodians (any `k` of `n` can reconstruct), but this must be configured **before** loss.

### 5.2 Temporal prism masking

The `.blend_data` file is masked by a temporal seed. A copy made at `t_0` cannot be used at `t_1` without the original temporal context. This is a feature (prevents stale-file attacks) but also a risk: if the user loses the temporal context (e.g., system clock was wrong during generation), the file may become unusable. Mitigation: temporal tolerance window of ±60 seconds.

### 5.3 Machine lock binding

Vaults are bound to a specific machine via a hash of hardware identifiers. This prevents trivial file-copy attacks between machines, but legitimate migration is supported via the vault migration protocol (`src/protocols/vault_migration/`): the user exports an encrypted archive (`.eidolon_keybundle_full`) from the source machine using the vault key, then imports it on the target machine. The import re-binds the vault to the new hardware. A user who simply copies both files to a new machine **without** using the migration protocol will fail authentication.

**If the original machine is lost** but the user has both vault files (.psnx + .blend_data) accessible from a backup, they can still import the vault on a new machine via the migration protocol. The machine lock is not a recovery obstacle — it is an anti-copy safeguard that the migration protocol explicitly bypasses. The actual risk is losing the files, not losing the hardware.

**Critical note:** possession of both `.psnx` and `.blend_data` files is sufficient to reconstruct the vault key. There is no additional passphrase or user-memorized secret required in the current design. Anyone who obtains both files has full access to the vault. The machine lock prevents cross-machine use of copied files, but does not prevent a determined attacker who also has access to the migration protocol. This makes secure storage of both files the single most important user responsibility.

### 5.4 Entropy source quality

The entire pipeline is seeded by a single 512-bit CSPRNG output. If the system's entropy source is compromised or predictable, all derived keys are compromised. The pipeline does not add entropy — it structures and transforms it. On systems with poor entropy (embedded devices, early-boot scenarios), additional entropy injection should be used.

---

## 6. Security Goals

| Goal | Achieved? | Notes |
|------|-----------|-------|
| Server never sees plaintext | Yes (architectural) | Plaintext exists only in client memory |
| Server cannot impersonate user | Yes | ZKP proof requires private scalar; server only has public commitment |
| Vault files individually useless | Yes (cryptographic) | AEAD tag binds `.psnx` values into `.blend_data` decryption |
| Forward secrecy against quantum adversary | Partial | PQ layer is quantum-resistant; custom pipeline hash chain relies on SHA3-512 (standard assumption, not proven PQ-resistant) |
| Resistance to file-copy attack | Yes (machine lock) | Cross-machine copy fails authentication |
| Resistance to replay attack | Yes | Timestamp + challenge in ZKP proof |
| Protection against endpoint compromise | No (out of scope) | See §3.2 |
| Protection against OS data leakage | No (out of scope) | See §3.2 |

---

## 7. Recommended Verifications for External Reviewers

1. **Test vectors**: Verify that the published binary produces the expected outputs for fixed-seed inputs (test vectors to be published).
2. **Reproducible builds**: Build from the signed source and verify byte-identity with the published binary (reproducible build tooling planned).
3. **Formal spec review**: Validate the composition claims in `FORMAL_SPEC.md` against the security assumptions.
4. **PQ primitive verification**: The ML-KEM and ML-DSA implementations can be verified against the NIST reference implementations independently.
5. **ZKP protocol review**: The Schnorr NIZK construction follows the standard Fiat-Shamir transform over Curve25519 and can be verified against the RFC.

---

## 8. Not a Guarantee

This threat model describes what Eidolon is **designed to protect against** and what it **explicitly does not**. It is not a formal proof of security. The composition of 9 phases introduces complexity that could harbor subtle vulnerabilities. External cryptographic review is recommended before relying on Eidolon for high-value assets.
