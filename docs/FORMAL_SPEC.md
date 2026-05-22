# Eidolon Cryptographic Pipeline — Formal Specification

**Version:** 1.0  
**Date:** 2026-05-22  
**Status:** Public — describes mathematical structure, not implementation

This document specifies the inputs, outputs, and security guarantees of each phase in the Eidolon 9-phase holographic key derivation pipeline. It does **not** contain implementation details. The purpose is to allow external review of the composition and security claims without exposing proprietary source code.

---

## Notation

| Symbol | Meaning |
|--------|---------|
| `seed` | 512-bit master seed (CSPRNG output) |
| `H(x)` | SHA3-512 hash |
| `HKDF(salt, info, ikm, L)` | HKDF-SHA512 derive of `L` bytes |
| `Scrypt(N, r, p, salt, dkLen)` | Scrypt key derivation |
| `M` | Material descriptor from 256-entry catalog |
| `S ⊂ R^7` | Spatial sampling manifold |
| `t` | Temporal prism seed (epoch) |
| `K_final` | 256-bit vault key (output of pipeline) |
| `CL(0,7)` | Clifford algebra of signature (0,7) |

---

## Phase 1: Master Seed Generation

**Input:** System entropy (CSPRNG, min-entropy ≥ 256 bits)  
**Output:** `seed ∈ {0,1}^512`  
**Guarantee:** `seed` is computationally indistinguishable from uniform. An HKDF-SHA512 derivation step with a fixed salt ensures domain separation from raw CSPRNG output.  
**Audit note:** The seed is the sole entropy source for the entire pipeline. If the CSPRNG is compromised, all subsequent phases are compromised. The pipeline does not add entropy — it structures and transforms it.

---

## Phase 2: 7D Spatial Capture with EPR Correlations

**Input:** `seed`  
**Output:** Spatial sample set `S = {s_1, …, s_N}` where each `s_i ∈ R^7`  
**Guarantee:** Points are deterministically derived from `seed` via HKDF. The EPR correlation structure is computed (not measured) and serves as a structural binding between dimensions. The "quantum" label refers to the mathematical structure (Bell-inequality-compatible correlation tensors), not a hardware quantum source.  
**Entropy contribution:** 0 additional bits (all derived from `seed`). Structural complexity ~1,050 conditional bits.

---

## Phase 3: Physics Simulation

**Input:** `seed`, material descriptor `M`, spatial sample set `S`  
**Output:** Trajectory hash `h_phys ∈ {0,1}^512`  
**Guarantee:** A parameterized phase function over 256 catalogued real materials produces deterministic trajectories. The output hash binds the material choice and spatial coordinates to the pipeline state. Collision resistance follows from SHA3-512 preimage resistance.  
**Entropy contribution:** 0 additional bits (deterministic function of `seed`, `M`, `S`).

---

## Phase 4: Clifford Algebra Spinor Transformation

**Input:** Accumulated pipeline state from phases 1–3  
**Output:** 128 complex coefficients `c_1, …, c_128 ∈ C` (spinor representation over CL(0,7))  
**Guarantee:** The transformation maps the 4096-bit working buffer through a keyed permutation in the 128-dimensional spinor representation of CL(0,7). The output is preimage-resistant under the SHA3-512 assumption.  
**Security claim:** Inverting the transformation (recovering the pre-phase-4 state from the coefficients) is at least as hard as inverting SHA3-512.  
**Entropy contribution:** ~4,096 effective bits of structured state.

---

## Phase 5: Bell 7D Verification

**Input:** Spinor coefficients from Phase 4  
**Output:** CHSH inequality test result `v_bell ∈ {pass, fail}`  
**Guarantee:** Verifies that the correlation structure from Phase 2 satisfies the Bell/CHSH inequality with a threshold derived from Tsirelson's bound. A failure would indicate that the spatial sampling was corrupted or incorrectly derived. In practice this always passes (the derivation is deterministic and correct by construction), but the check provides a runtime integrity guarantee.  
**This phase does not modify the pipeline state.** It is a verification gate.

---

## Phase 6: Composite Spinor Hash

**Input:** Spinor coefficients from Phase 4  
**Output:** `h_spinor ∈ {0,1}^512` (SHA3-512 of spinor data), `h_quaternion ∈ {0,1}^512` (quaternion matrix hash)  
**Guarantee:** Two independent hash computations over the spinor data produce a 1024-bit binding. Preimage resistance and collision resistance follow from SHA3-512 properties.  
**This phase does not add entropy.** It compresses the Phase 4 state into a fixed-size hash.

---

## Phase 7: Post-Quantum Cryptography

**Input:** Pipeline state from phases 1–6  
**Output:** 
- ML-KEM (Kyber1024) keypair: `(pk_kem, sk_kem)` — IND-CCA2 at NIST Level 5
- ML-DSA (Dilithium5) keypair: `(pk_sig, sk_sig)` — EUF-CMA at NIST Level 5
- Optional: Classic McEliece keypair (code-based, independent security assumption)
- Optional: HQC keypair (alternative code-based KEM)

**Guarantee:** These are standard NIST PQC primitives with their documented security levels. The pipeline binds the PQ public keys to the preceding phases by hashing the public key material into the Merkle tree (Phase 8).  
**Security claim:** The PQ layer's security is independent of the custom pipeline — a break in phases 1–6 does not weaken ML-KEM/ML-DSA, and a break in ML-KEM/ML-DSA does not weaken the pipeline hash chain.

---

## Phase 8: Vault Key Derivation

**Input:** All preceding phase outputs  
**Output:**
- Merkle root `r_merkle` (SHA3-256 over ordered leaves)
- Vault key `K_final ∈ {0,1}^256` (Scrypt + HKDF derivation)

**Construction:**
```
combined = H(seed) || H(h_spinor) || H(h_phys) || r_merkle
intermediate = SHA3-512(combined)
salt = SHA3-256("PSNX_SCRYPT_SALT_" || combined[:32])
K_scrypt = Scrypt(N=2^17, r=8, p=1, salt, dkLen=32)
K_final = HKDF(salt=r_merkle, info="eidolon-vault-key-v1", ikm=K_scrypt, L=32)
```

**Guarantee:** `K_final` is a deterministic function of the master seed and the pipeline parameters. The Scrypt parameters (N=2^17, r=8, p=1) provide ~128-bit resistance against GPU/ASIC attacks. The final HKDF step provides domain separation from the Scrypt output.

---

## Phase 9: Genesis Data Generation

**Input:** `K_final`, PQ keypairs, Merkle tree  
**Output:**
- `.psnx` file (~17 KB): public material, PQ public keys, Schnorr commitment, authenticated metadata
- `.blend_data` file (~156 KB): temporally-masked private material

**Guarantee:** Neither file alone can reconstruct `K_final`. The AEAD tag in `.blend_data` depends on values published only in `.psnx`. The temporal prism mask ensures that `.blend_data` produced at `t_0` cannot be used at `t_1` without the original temporal seed.

---

## Composition Security Claim

The pipeline's overall security rests on two independent pillars:

1. **Hash chain security**: The composition `H ∘ H ∘ … ∘ H` with phase-specific domain separation is preimage-resistant and collision-resistant under the standard SHA3-512 assumption.
2. **Post-quantum security**: ML-KEM (Kyber1024) and ML-DSA (Dilithium5) provide their documented NIST Level 5 guarantees independently.

A break in one pillar does not compromise the other. The custom phases (2–6) add structural complexity but **do not add entropy** beyond the master seed. The security reduction is: if SHA3-512 is preimage-resistant and ML-KEM/ML-DSA are secure at their claimed levels, then `K_final` is computationally infeasible to recover without `seed`.

---

## Test Vector Availability

Test vectors (deterministic input → expected output pairs) will be published for each phase to allow verification of any conforming implementation without access to the source code. Vectors use fixed seeds and deterministic parameter choices.

*Test vectors are not yet published. They will be added in a future release alongside the reproducible build tooling.*

---

## Threat Model Summary

See `THREAT_MODEL.md` for the full document.

**In scope:** Passive network adversary, quantum-capable adversary (post-harvest), compromised server (ciphertext-only), file-copy attack on vault files individually.  
**Out of scope (explicit):** Endpoint compromise (malware, keylogger), OS-level data leakage (swap, crash dumps, clipboard), user operational errors (backing up wrong files, weak password), side-channel attacks on the local execution environment.
