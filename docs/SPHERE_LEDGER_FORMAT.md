# Sphere Custody Ledger — Format Specification (v1)

Status: public (Tier 1, sign-off recorded in `IP-BOUNDARY.md` §7, 2026-09-13).
Reference implementation: `src/protocols/sphere_ledger/`.

A sphere is a rare, transferable object. Its ledger is **per sphere**: one
file, verifiable offline, from its mint to its current head. There are no
blocks and no consensus. Scarcity is guaranteed by a **genesis root** signed
once by the issuer; uniqueness of the head is guaranteed by an **anchor**
that orders heads ("first head wins"). All signatures are hash-based.

## 1. Encoding and hashing

- Canonical JSON: keys sorted, separators `(",", ":")`, UTF-8, no ASCII escaping
  (`ensure_ascii=False`). A string that cannot be encoded as UTF-8 (lone
  surrogate) is a format error.
- Binary values are lowercase hexadecimal strings. Identifiers of vaults and
  anchors are opaque strings; a vault id is 32 bytes (64 hex chars).
- Record hash: `SHA3-256(DOMAIN || canonical(unsigned_fields))` with the
  domains below. Signatures never cover a field named `signature`,
  `issuer_pk`, `anchor_pk`, `signer_seed`.

| Domain | Used by |
|---|---|
| `EIDOLON_CUSTODY_V1:` | `MintRecord`, `CustodyRecord`, `AnchorReceipt` |
| `EIDOLON_GENESIS_V1:` | `GenesisRoot` |
| `EIDOLON_CHECKPOINT_V1:` | `Checkpoint` |
| `EIDOLON_SPHERE_COMMIT_V1:` | `sphere_commit` (template commitment) |
| `EIDOLON_SUMLEAF_V1:`, `EIDOLON_SUMNODE_V1:`, `EIDOLON_SUMPAD_V1` | sum tree |
| `EIDOLON_SLH_V1:` | SLH-DSA tagged messages |
| `EIDOLON_WOTS_SECRET_V1:`, `EIDOLON_WOTS_PUBLIC_V1:` | WOTS+ key derivation |

## 2. Signatures

**WOTS+** (RFC 8391): n = 32, w = 16, len = 67, SHA-256 based F/H/PRF with the
RFC's byte-prefixed keyed constructions, L-tree compression of the 67 chain
ends. A public key is `(seed, ots_index = 0, root)` where `root` (32 bytes)
is the L-tree output. A signature is 67 × 32 = 2 144 bytes over a 32-byte
message digest. **One key signs once.** The verifier reconstructs the root
from the signature and compares it to the root committed in the previous
record; a mismatch is a failure.

**SLH-DSA** (FIPS 205, SLH-DSA-SHA2-128s): public key 32 bytes, signature
7 856 bytes. The signed message is
`SHA3-256("EIDOLON_SLH_V1:" || purpose || ":" || payload)` with `purpose` in
`{"mint", "receipt", "checkpoint", "genesis"}`, so a signature is bound to its
use. Used by the issuer (genesis root, optionally mint records) and by
anchors (receipts, checkpoints).

**Key derivation** (client side): a vault derives its one-time key for a
sphere and a hop as
`secret = SHA3-256("EIDOLON_WOTS_SECRET_V1:" || material || ":" || tag)`,
`public_seed = SHA3-256("EIDOLON_WOTS_PUBLIC_V1:" || material || ":" || tag)`,
`tag = len(sphere_id) as 2 bytes BE || sphere_id || seq as 8 bytes BE`,
where `seq` is the sequence number of the record in which the root is
committed (0 = mint, 1 = claim, …) and the key signs record `seq + 1`.
`material` is at least 32 bytes and is never part of the format. Mailbox
roots use `sphere_id = "mailbox"` and `seq = n`.

## 3. Records

All records carry `kind` and `version` (1).

```
MintRecord      kind "mint"
  sphere_id, rarity, index (0 ≤ index < caps[rarity]), sphere_commit (hex),
  vault_id (first holder; the treasury for a genesis mint), ots_root (hex, root of the
  first controller's WOTS+ key), anchor_id, issued_at (ISO-8601 UTC), external_seal (hex|null)
  optional: issuer_pk, signature (SLH-DSA "mint" over record_hash)

CustodyRecord   kind "custody"
  sphere_id, seq (1, 2, …), prev_hash (record_hash of the previous record),
  from_vault_id, to_vault_id (null for burn), next_ots_root (hex|null for burn),
  reason: "transfer" | "claim" | "burn" | "reanchor" | "reissue-key",
  anchor_id (new anchor, reanchor only, else null), issued_at,
  signer_seed (hex, the signer's WOTS+ public seed), signature (hex, 2 144 bytes)

AnchorReceipt   kind "receipt"
  sphere_id, custody_head (hex), seq, anchor_id, received_at
  anchor_pk, signature (SLH-DSA "receipt")

GenesisRoot     kind "genesis"
  genesis_seq (≥ 1), root (hex, sum-tree root over all mint leaves), totals, caps, count,
  distribution_sha256 (hex, digest of the frozen distribution file), treasury_id,
  anchor_id, issued_at, supersedes (hex record_hash of the replaced root, or null)
  issuer_pk, signature (SLH-DSA "genesis")

Checkpoint      kind "checkpoint"
  anchor_id, checkpoint_seq (≥ 0), root (hex, sum-tree root over all current heads),
  totals, burned, issued_at
  anchor_pk, signature (SLH-DSA "checkpoint")
```

`sphere_commit` = `SHA3-256("EIDOLON_SPHERE_COMMIT_V1:" || canonical(template))`
where `template` is the sphere's template object without the keys
`createdAt`, `created_at`, `sphereHash`.

## 4. The sphere file

```json
{"format": "EIDOLON_SPHERE", "version": 1,
 "mint": MintRecord, "custody": [CustodyRecord…], "receipts": [AnchorReceipt…],
 "genesis_proof": SumProof | null, "template": object | null,
 "checkpoint": Checkpoint | null, "checkpoint_proof": SumProof | null}
```

- `head` = last custody record, or the mint. `owner` = head's `to_vault_id`
  (mint's `vault_id`). `burned` = any custody record with reason `burn`.
- `anchor_id` of the file = the last `reanchor` record's `anchor_id`, else the
  mint's. Every head is ordered by the anchor in force *when it was
  produced*: a `reanchor` record itself is still ordered by the old anchor.
- `template`, when present, must recompute `mint.sphere_commit`
  (**reveal at claim**: the catalogue stays committed but hidden until a
  sphere is claimed).
- `checkpoint` and `checkpoint_proof` travel together: the anchor's signed
  checkpoint and the sum-tree proof that one of the file's heads is a leaf of
  it (**batched finality**, §6). A client refreshes them when it
  synchronises; a receiver re-verifies them offline like a receipt.

## 5. Verification rules (`verify_sphere`)

1. **Mint.** `rarity ∈ caps` and `0 ≤ index < caps[rarity]`. With a genesis
   root: the root signature verifies under the expected issuer key and
   `genesis_proof` proves the leaf
   `(sphere_id, rarity, head = mint.record_hash, alive = true)` against
   `root.root` with `root.totals`; a mint signature, if present, must also
   verify. Without a genesis root: the mint signature must verify under the
   expected issuer key.
2. **Chain.** For record i (1-based): same `sphere_id`; `seq == i`;
   `prev_hash` = previous record's hash; `from_vault_id` = previous holder;
   no record after a `burn`; reason known; `burn` has neither destination
   nor next root, every other reason has both; `reanchor`/`reissue-key` keep
   `to_vault_id == from_vault_id`; `reanchor` carries a non-empty
   `anchor_id`, other reasons carry none; `claim` is the first hop, leaves
   the mint's vault, and — when treasury ids are known — a treasury only
   `claim`s or `burn`s. The WOTS+ signature over `record_hash` must
   reconstruct the root committed in the previous record.
3. **Receipts.** A receipt must cite a head present in the file and come from
   the anchor in force for that head; a receipt from another anchor is an
   error. The head is **final** when a receipt of that anchor, known to the
   verifier, cites the current head — or when a signed checkpoint includes
   it (§6). `final_by` reports which (`"receipt"` or `"checkpoint"`).
4. **Checkpoint.** If `checkpoint` or `checkpoint_proof` is present, both
   must be. The proof's leaf must name this sphere, its genesis rarity and a
   head present in the file, with `alive = true` unless that head is the
   `burn` record itself; the checkpoint must come from the anchor in force
   for that head (another anchor is an error); when the verifier knows that
   anchor's key, the checkpoint signature must verify and the proof must
   lead to `checkpoint.root` with `checkpoint.totals`. A checkpoint of an
   unknown anchor counts for nothing, without being an error. A checkpoint
   that includes an *older* head of the file is valid but does not finalise
   the current one (`checkpoint_seq` is reported only for the current head).
5. **Template.** If present, `sphere_commit(template) == mint.sphere_commit`.
6. A malformed file yields `ok = false`, never an exception.

Two files of the same sphere that diverge after a common record are a
**fork** (`detect_fork`): the double spend seen by a third party, which only
the anchor settles.

## 6. Sum tree, proofs, checkpoints

Leaves `(sphere_id, rarity, head, alive)` sorted by `sphere_id`; leaf hash
`SHA3-256("EIDOLON_SUMLEAF_V1:" || canonical(leaf))`, leaf sums
`{rarity: 1}` if alive else `{}`; node hash
`SHA3-256("EIDOLON_SUMNODE_V1:" || left || right || canonical(sums))` with
`sums` the merged counts; odd levels are padded with
`SHA3-256("EIDOLON_SUMPAD_V1")` and empty sums. A proof carries the **leaf
itself** plus the sibling `(hash, sums, side)` per level; the verifier
re-hashes the leaf and recomputes root **and** totals.

Conservation: for every rarity, `alive + burned ≤ cap`, all counts ≥ 0.
The anchor's checkpoint proof (`leaf.head == file head`) is the batched
finality: one SLH-DSA signature per checkpoint instead of one per receipt.
The sphere file carries it (§4, `checkpoint` + `checkpoint_proof`);
`verify_checkpoint_inclusion(file, checkpoint, proof, anchor_pk)` applies
the same rule to a checkpoint obtained separately (`GET …/checkpoint-proof`).

## 7. Flux invariant (anchor reconciler)

Between two consecutive checkpoints of the same anchor, for each rarity:
`Δtotals = mints − burns` (claims and transfers have zero divergence, `reanchor`
and `reissue-key` move nothing); every mint is in the genesis root under its
genesis rarity and was not already counted; `Δburned = burns`; conservation
holds at both checkpoints; `checkpoint_seq` advances by one. With a treasury:
every `claim` leaves the treasury, the treasury never `transfer`s.

## 8. Versioning

`version` is a format version. A genesis root is never modified: a
replacement root carries `genesis_seq + 1` and `supersedes` = the replaced
root's `record_hash`, signed by the same issuer; proofs against a superseded
root must be re-issued. New reasons or fields require a new format version.
The optional `checkpoint` / `checkpoint_proof` fields of the sphere file were
added on 2026-09-14, before any v1 file existed outside disposable trial
lots; v1 therefore includes them, and a file without them stays valid.
