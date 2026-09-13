# IP Boundary & Ownership Doctrine

**Owner:** Logos Project — © 2024–2026. All rights reserved.
**Status:** Authoritative. Last updated 2026-06-05.
**Scope:** Eidolon, Cipher, Esoptron (the "Logos ecosystem").

This document fixes **what is open and what is closed** across the ecosystem,
and **why**. It is governance, not marketing. Any change that would move
material across the boundary defined here must follow the *Change Control*
section below — convenience, refactors, or "it's just a test" do not override
it.

> This file is written to be safe for public distribution: it names the
> **categories** that are closed, never the constructions themselves. Adding
> any concrete primitive, parameter, constant, or domain separator to this
> file would itself be a leak.

---

## 1. Principle: open standard, closed engine

The ecosystem deliberately **opens the *what*** and **closes the *how***:

- The **protocol, formats, and security guarantees** are open — to earn
  adoption, interoperability, auditability, and trust.
- The **cryptographic construction** that realizes those guarantees is closed —
  it is the core of value and is not reproducible without the source.

Copyright on all three projects is held by a **single owner (Logos Project)**;
the projects differ only in the **grant** attached to each. Same owner,
different licenses — that is what keeps the model both open *and* controlled.

---

## 2. The three tiers

| Tier | Contents | License | Purpose |
|---|---|---|---|
| **0 — Open standard** (Esoptron) | Protocol specification, message/format definitions, the **EEP interface family** (claims + black-box test vectors), SDK stubs | **MIT**, © Logos Project | Adoption, interop, audit |
| **1 — Public integration** (Eidolon, public surface) | API contracts, the **compiled `eidolon_crypto` distribution (binary wheel)**, docs describing **properties** (not construction), integration tests run **against the wheel** | **Proprietary** + Named-Project Integration Exception | Let Cipher/Esoptron consume without exposing the engine |
| **2 — Closed core** (never published) | The native crypto crate, the private `src/` cryptographic packages, the **EEP-001 construction**, the poly-spinor transformation, pipeline internals, parameters, and domain separators | **Trade secret**, compiled-only | The value lock |

The owner is identical across tiers; only the grant changes.

---

## 3. The EEP-001 cut (the crux)

EEP-001 exists in **two distinct forms**, and they must never be conflated:

- **Property contract (OPEN).** *What* EEP-001 guarantees — e.g. deterministic
  reproducibility, divergence across epochs, a strong avalanche threshold,
  output uniformity, and lossless round-tripping. These are **black-box
  behaviors**, safe to publish, and useful for trust and audit.
- **Construction (CLOSED).** *How* those guarantees are produced — the exact
  choice and composition of primitives, their parameters, seed derivation, and
  domain separators. This is **never published**, in any form.

**Operational rule.** Public tests, docs, and SDKs may express **properties and
input/output vectors only**. They must **never import internal modules**, nor
restate the construction. The canonical public test suite exercises the
**compiled wheel's public API as a black box** — it does not depend on the
private `src/` packages.

---

## 4. Esoptron ↔ Eidolon boundary

Esoptron is the **foundational (mother) protocol** and is **MIT**. Eidolon is a
**proprietary realization** built on it.

- **Esoptron (MIT)** defines the **EEP family as an interface** ("EEP-00x"):
  the contract a realization must satisfy, plus non-sensitive reference
  material. It is open so that others — and Cipher — can implement against it.
- **Eidolon (proprietary)** ships **one specific realization, EEP-001**, whose
  construction lives in Tier 2.

**Hard constraint.** Esoptron must **not** contain enough construction to let a
third party reproduce a realization. The interface is open; the engine is not.
If a change to Esoptron would let someone rebuild EEP-001's construction, it
belongs in Tier 2, not Esoptron.

---

## 5. Protection posture (strongest to weakest)

1. **Trade secret + compiled-only.** The engine ships as a native binary wheel
   with stripped symbols. This is the real protection: the law cannot recover a
   secret that has already leaked.
2. **No construction in public.** Tests, docs, and SDKs describe properties and
   I/O vectors only — never internal modules, parameters, or primitives.
3. **Legal.** Eidolon's proprietary license names **EEP-001 (temporal prism)**
   and the **poly-spinor transformation** as reserved components, with
   anti-reverse-engineering and anti-derivative terms. The Named-Project
   Integration Exception grants Cipher and Esoptron use of the **public
   interface + compiled wheel only**, with **mandatory attribution**.
4. **Provenance.** Released artifacts carry a tamper-evident provenance keyprint
   (author mark + timestamp + frozen hash) to establish authorship in disputes.
5. **Trademark & naming.** Protect "Eidolon" / "Logos Project". **Internal
   codenames must not appear on any public surface** (repo files, asset text,
   package metadata, contact addresses).

**Patent vs. trade secret.** A patent *publishes* the construction in exchange
for enforceable exclusivity. For this crypto engine the default is **trade
secret**; patenting is considered only for a deliberate commercial reason, by
owner decision.

---

## 6. Hard rules (operational checklist)

**Never publish (Tier 2):**
- The native crypto crate or any private `src/` cryptographic package.
- The EEP-001 construction, the poly-spinor transformation, or pipeline
  internals — names, parameters, constants, domain separators, or reference
  implementations.
- Tests, notebooks, or docs that **import** Tier-2 modules or restate their
  construction.
- Internal codenames, internal contact domains, or build artifacts that embed
  either.

**Safe to publish:**
- Protocol/interface specs and message formats (Esoptron).
- Property claims and black-box test vectors for EEP-00x.
- API contracts and the **compiled** `eidolon_crypto` wheel.
- Application clients (Cipher) consuming the public interface.

---

## 7. Change control (one-way ratchet)

Opening is **irreversible** — once material is public, it cannot be un-published
(history, forks, and caches persist). Therefore:

- Moving anything **closed → open** requires explicit owner sign-off and a
  recorded rationale here.
- Moving anything **open → closed** for already-shipped material requires both
  removal from the current tree **and** a history-rewrite + force-push decision,
  acknowledging that prior public copies may persist.
- When in doubt, treat material as **Tier 2** until a sign-off says otherwise.

### Sign-offs (closed → open)

- **2026-09-13 — Sphere custody ledger verifier.** `src/protocols/sphere_ledger/`
  (WOTS+ per RFC 8391, SLH-DSA per FIPS 205, Merkle sum-tree proofs, custody
  chain verification, flux invariant), its public tests (`tests/test_ledger_*.py`)
  and the format specification `docs/SPHERE_LEDGER_FORMAT.md` are **Tier 1**.
  Rationale: the ledger is a protocol and a message format built only on public
  standards; it deliberately contains no element of EEP-001 (the spinor hash is
  not an address); its domain separators belong to the ledger protocol and are
  required by any verifier; a vault's key material only enters as opaque bytes.
  Minting, the genesis treasury, treasury key windows and the ceremony remain
  Tier 2. Decision of the owner, Jérémy Zgonec, recorded on his instruction.
