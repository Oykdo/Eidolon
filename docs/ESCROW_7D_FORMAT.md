# 7D Escrow — envelope format (schema v1, crypto suite `alpha-v1`)

Status: frozen. This document describes the bytes that `src/protocols/escrow_7d`
writes and reads. A change to anything below requires a new `schema_version`
and/or a new `crypto_suite`; existing envelopes are never rewritten (see
"Versioning"). A frozen envelope is published in `tests/vectors/escrow_7d_v1.json`
and checked by `tests/test_escrow_7d_api_store.py::GoldenVectorTests`.

## 1. Purpose and scope

An escrow envelope stores one document, encrypted, together with the release
conditions under which its owner intends to open it again. Phase 1 is local and
single-user: the only trust root is the vault key (32 bytes or more). Whoever holds
it can open every envelope of that vault; nobody else can open any, nor alter one
undetected.

Symmetric primitives only: AES-256-GCM, HKDF-SHA256, HMAC-SHA256. No post-quantum
KEM or signature is involved in this phase.

## 2. File

- Location: `<data dir>/vaults/escrows/<depositor_vault_id_prefix>/<escrow_id>.escrow7d`
- Encoding: UTF-8 JSON object, `json.dumps(indent=2)` layout (whitespace is not
  significant: the reader parses JSON, the MAC is computed on a canonical form).
- The file name **must** equal `escrow_id + ".escrow7d"`, and the directory name
  **must** equal `depositor_vault_id_prefix`; a reader reports any mismatch as
  unreadable rather than trusting either side.
- Files ending in `.escrow7d.tmp` are write-in-progress leftovers and are ignored.

## 3. Fields

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | int | Layout of this JSON object. `1`. |
| `min_reader_version` | int | Lowest reader able to process it. `1`. |
| `crypto_suite` | string | Named bundle of algorithms and parameters. `"alpha-v1"`. |
| `producer` | string | Diagnostic tag of the writer. `"eidolon-escrow-7d/alpha-v1"`. Bound by the MAC, not interpreted. |
| `escrow_id` | string | `"esc_"` + 32 lowercase hex characters (16 random bytes). Non-empty string required. |
| `deposited_at` | string | ISO 8601 UTC instant with offset, e.g. `2026-09-15T00:00:00+00:00`. Informational. |
| `depositor_vault_id_prefix` | string | First 16 hex characters of `sha256(vault_key)`. |
| `label` | string | Free text chosen by the depositor. **Cleartext.** |
| `conditions` | array of objects | Release conditions (§5). **Cleartext.** May be empty. |
| `kdf_salt` | base64 | 32 random bytes, fresh per envelope. |
| `aes_nonce` | base64 | 12 random bytes, fresh per envelope. |
| `ciphertext` | base64 | AES-256-GCM ciphertext of the payload (without the tag). |
| `aes_tag` | base64 | 16-byte GCM tag. |
| `payload_size` | int | Length of the plaintext in bytes. **Cleartext.** |
| `integrity_mac` | base64 | 32-byte HMAC-SHA256 over the canonical form (§4). |

All fields except `integrity_mac` are covered by the MAC. Base64 is standard
alphabet with padding; readers are lenient about non-alphabet characters (they
are ignored, as `base64.b64decode(validate=False)` does) but strict about padding.

Required for a reader: `schema_version`, `min_reader_version`, `crypto_suite`,
`escrow_id`, `deposited_at`, `depositor_vault_id_prefix`, `kdf_salt`, `aes_nonce`,
`ciphertext`, `aes_tag`, `payload_size`. Missing `label` reads as `""`, missing
`conditions` as `[]`, missing `producer` as the current tag, missing
`integrity_mac` as empty (which fails verification).

Confidentiality: only the payload is encrypted. The label, the conditions
(including a TimeLock's release date), the deposit time, the payload size and the
depositor prefix are readable by anyone who reads the file.

## 4. Cryptography (`alpha-v1`)

Let `K` be the vault key (≥ 32 bytes), `salt` the 32-byte `kdf_salt`.

```
session_key   = HKDF-SHA256(IKM = K, salt = salt, info = "EIDOLON_ESCROW_SESSION_KEY_v1", L = 32)
integrity_key = HKDF-SHA256(IKM = K, salt = salt, info = "EIDOLON_ESCROW_INTEGRITY_v1",   L = 32)
ciphertext || aes_tag = AES-256-GCM(session_key, aes_nonce, plaintext, AAD = none)
integrity_mac = HMAC-SHA256(integrity_key, mac_input)
```

HKDF is RFC 5869 (extract with the salt as HMAC key, expand with a one-byte
counter starting at 1). `tests/test_escrow_7d_api_store.py::HkdfVectorTests`
checks the implementation against RFC 5869 A.1–A.3.

### 4.1 Canonical MAC input (schema v1)

`mac_input` is the UTF-8 encoding of the JSON serialisation, with keys sorted and
separators `(",", ":")` (no whitespace), of the object:

```
{
  "aes_nonce": <base64>, "aes_tag": <base64>, "ciphertext": <base64>,
  "conditions": <the conditions array, as stored>,
  "crypto_suite": <string>, "deposited_at": <string>,
  "depositor_vault_id_prefix": <string>, "escrow_id": <string>,
  "kdf_salt": <base64>, "label": <string>, "min_reader_version": <int>,
  "payload_size": <int>, "producer": <string>, "schema_version": <int>
}
```

Base64 values are re-encoded from the decoded bytes (canonical), so cosmetic
differences in the file's base64 do not change the MAC. Nested objects inside
`conditions` are serialised the same way (sorted keys, no whitespace).
`test_escrow_7d_backward_compat.py::test_v1_mac_input_is_stable` pins the exact
bytes for a synthetic envelope; the golden vector pins a real one.

### 4.2 Verification and opening

1. Parse; refuse if `min_reader_version` is above what this build reads, if
   `schema_version` is unknown, or if `crypto_suite` is unknown.
2. Recompute `integrity_mac`; compare in constant time. Refuse on mismatch or if
   absent. **Nothing below runs on an envelope that fails here** — a wrong key,
   a tampered field or a foreign file is rejected before any condition is read.
3. Evaluate every entry of `conditions` in order; refuse on the first that is not
   satisfied (or malformed).
4. Decrypt with `session_key`; the GCM tag must verify.

Anti-downgrade: the three version fields are inside the MAC, so they cannot be
edited without the key.

## 5. Release conditions

Each entry is an object with a `type`:

| `type` | Fields | Satisfied when |
|---|---|---|
| `time_lock` | `release_after`: ISO 8601 instant, stored in UTC with `+00:00` | The reader's clock (UTC) is at or after `release_after`. Enforced by the machine that holds the key: a self-imposed lock, not a third-party one. |
| `owner_signature` | `expected_vault_id`: 64 hex (full `sha256(vault_key)`) — writers store the full id; readers also accept the 16-hex prefix in legacy envelopes | The key that opens the envelope has that id (exact, or prefix match for a 16-hex value). Derived from the key, never from caller input. Not a signature. |
| `combined_all` | `children`: non-empty array of conditions | Every child is satisfied. |
| `combined_any` | `children`: non-empty array of conditions | At least one child is satisfied (evaluated in order, first success wins). |

Structural rules: `conditions` must be an array of objects; `children` must be a
non-empty array; nesting depth is at most 32 levels (enforced at seal and at
unseal so the verdict does not depend on the reader's stack); an unknown `type`
or a malformed field makes the envelope unopenable (integrity still verifies).

A writer refuses to seal an `owner_signature` naming a vault other than the
depositor: since only the depositing key can pass step 2, such an envelope could
never be opened.

## 6. Versioning

- `schema_version` owns the canonical MAC input: each version has its own frozen
  `mac_input` function in the reader. Adding a field means a new version and a
  new function; old envelopes keep verifying with theirs.
- `crypto_suite` names the algorithm bundle and the HKDF `info` strings; a new
  suite gets new `info` strings so its keys never collide with an older suite's.
- `min_reader_version` lets a writer mark an envelope as unreadable by older
  builds. The reader compares it with the highest schema it supports
  (`READER_VERSION`), not with the version it writes.
- There is no in-place migration. `reseal()` decrypts with the original suite and
  writes a **new** envelope (new id, salt, nonce, MAC) under the current one.

## 7. Golden vector

`tests/vectors/escrow_7d_v1.json` fixes: the vault key, the plaintext, the salt,
the nonce, the escrow id, the deposit time, a `combined_all(time_lock,
owner_signature)` condition, the resulting envelope, its canonical `mac_input`,
both derived keys and the reason string a wrong key produces. A conforming
implementation must verify and open it, and must reproduce `integrity_mac` when
sealing the same inputs.
