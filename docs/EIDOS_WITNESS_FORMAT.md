# Eidos Witness — Format Specification (v1)

Status: public (Tier 1, sign-off recorded in `IP-BOUNDARY.md` §7, 2026-09-13).
Reference implementation: `src/protocols/eidos_witness/`.
Upstream: [Oykdo/Eidos](https://github.com/Oykdo/Eidos) (Apache-2.0), commit `2637c97`.

Eidos is a federated post-quantum chain built on hashing alone: WOTS+ for
spends, XMSS for validators, SHA-256 everywhere, standard library only. An
Eidolon vault can **hold Eidos assets** — eidôla, recovered relics — because
the two WOTS+ implementations (`Eidos/wots.py` and
`sphere_ledger/hash_sig.py`, both RFC 8391 with n = 32, w = 16, len = 67) verify
each other's signatures byte for byte; only the seed derivation differs. This
document fixes what the witness checks and the two files it produces. It
adds **nothing** to Eidos: the node, the atelier and `eidos.carnet` are
unchanged, and Eidos never has to know Eidolon exists.

## 1. Eidos primitives (ported, not redefined)

| Object | Rule (Eidos) | Module |
|---|---|---|
| Seed of key `n` | `graine_n = SHA-256("<maitre>/<n>")`, `maitre` a string (a 256-bit seed is 64 lowercase hex) | `wots.graine_de` |
| WOTS+ key | `graine_pub = SHA-256(graine ‖ "pub")`, `sk_i = PRF(graine, ADRS(OTS 0, chain i))`, L-tree root | `wots.racine` |
| Address / fingerprint | `SHA-256(graine_pub ‖ root)[:20]` / `SHA-256(graine_pub ‖ root)` | `wots.adresse`, `wots.empreinte` |
| Spend witness | `(graine_pub, signature)` = 32 + 2 144 bytes over `sighash(i) = SHA-256(txid ‖ i(4))` | `wots.signer`, `envoi.sighash` |
| Transaction core | `VERSION(4)=2 n_in(2) [txid(32) vout(4)]* n_out(2) [addr(20) atomes(8)]*`, `txid = SHA-256d(core)` | `envoi.core_tx` |
| Serialised tx | `len_core(4) core n_temoins(2) [flag(1) (graine_pub sig)?]*`, base64 in 76-column lines between `-----EIDOS-----` / `-----FIN-----` | `envoi.ser_tx`, `envoi.encapsuler` |
| Coin selection | at most 3 inputs; change below 10 000 atoms becomes fees | `coinselect.selectionner` |
| UTXO leaf | `SHA-256d(txid ‖ rang(4) ‖ adresse(20) ‖ montant(8))`, canonical order `(txid, rang)`, odd levels duplicate the last node, empty = 32 zero bytes | `preuve.feuille_sortie`, `preuve.utxo_root` |
| Inclusion proof | `{"v": 1, "feuille": hex, "freres": [{"cote": "gauche"\|"droite", "hash": hex}…], "racine": hex}` | `preuve.preuve_de`, `preuve.verifier_preuve` |
| Federated header | `E.header = height(8) prev(32) merkle(32) ts(8) nonce(8)` (frozen, nonce = 0), `id_bloc = SHA-256d(E.header ‖ utxo_root)` | `tete.id_bloc` |
| Validator signature | XMSS: `(indice, WOTS+ sig, chemin)`, leaf `i` = L-tree of the key implied by the signature (ADRS OTS i / L i), path with `rand_hash` at ADRS (tree, height k, parent) | `xmss.verifier_mss` |
| Signed head | `etat.json.tete_signee`: hauteur, prev, merkle, ts, utxo_root, id_bloc, validateur, indice, signature, chemin | `tete.TeteSignee` |
| Federation | `federation.json`: `racines`, `graines_publiques`, `hauteur_mss`, optional `t0_unix`, `creneau_s`, `pas_rotation` (n divisible by the step is refused) | `tete.Federation` |
| Vault file | `eidos.carnet` (`eidos-carnet/1`): `{v, kind, alg: "sha256d", sig: "lamport-sha256", feuillet, adresse, empreinte, tour}`, `empreinte = SHA-256d("eidos-carnet/1" ‖ JSON.stringify(corps))`, `tour` outside the fingerprint | `carnet` |

The witness serialises JSON exactly as `JSON.stringify` (no spaces, insertion
order, UTF-8 unescaped, integral floats as integers), so an `eidos.carnet`
written here opens in the atelier and one written by the atelier re-exports
byte-identical. `objets` and `tour` are stored as read, never renormalised.

## 2. What the witness checks (`tete.verifier_tete`)

1. `validateur` is within the federation.
2. `id_bloc` recomputed from the head equals the declared `id_bloc`.
3. The XMSS signature over `id_bloc` verifies under `racines[validateur]`,
   `graines_publiques[validateur]`, `hauteur_mss`.
4. When the federation gives `t0_unix`, `creneau_s` and `pas_rotation`: the
   slot `s = (ts − t0) // creneau_s` is not before genesis and
   `validateur == (pas · s) mod n` — the proposer of that slot.

A head is judged, never trusted. A proof is judged against a head
(`preuve.juger`): `aveugle` without a head, `rompue` if the path does not
reach its own root, `etrangere` if that root is not the head's `utxo_root`,
`incluse` otherwise — the four verdicts of the atelier's Witness page.

## 3. The asset dossier (`EIDOLON_EIDOS_ACTIF`)

What counts in Eidos is anchored: a coin is an unspent output proven against
the UTXO root of a signed head. A recovered relic is a coin (the spend of the
relic to the vault); an age seal is a reading of it. The dossier therefore
stores the same thing in every case.

```json
{"format": "EIDOLON_EIDOS_ACTIF", "version": 1,
 "genre": "piece" | "relique",
 "reseau": "essai" | null,
 "tete": <etat.json.tete_signee>,
 "sortie": {"txid": hex32, "rang": int, "adresse": hex20, "montant": int ≥ 1},
 "preuve": {"v": 1, "feuille": hex32, "freres": [...], "racine": hex32},
 "indice": int | null,
 "age": "Satya" | "Treta" | "Dvapara" | "Kali" | null,
 "note": string}
```

`actif.juger_actif(dossier, federation)` returns `(ok, code, detail, hauteur)`:

| code | meaning |
|---|---|
| `forme` | malformed dossier (never an exception) |
| `tete` | the head does not verify under this federation (§2) |
| `rompue` | the leaf is not that of `sortie`, or the path is broken |
| `etrangere` | the proof's root is not the head's `utxo_root` |
| `incluse` | the output was in the ledger at block `tete.hauteur` |

A dossier proves that the output **was** there at `tete.hauteur`, never that
it still is: only the current published state says whether it has been spent
since. A dossier names itself `txid:rang` (`actif.identifiant`).

## 4. The vault sidecar (`EIDOLON_EIDOS_COFFRE`)

Where a vault keeps its Eidos state. How the vault obtains its Eidos keys and
the key that seals this file are Tier 2; the envelope is public so that
migration tooling can carry it.

```
identities/vault_data/<vault_id[:16]>/eidos/coffre.eidolon
identities/vault_data/<vault_id[:16]>/eidos/actifs/<txid>-<rang>.json
```

```json
{"format": "EIDOLON_EIDOS_COFFRE", "version": 1, "suite": "aes-256-gcm",
 "vault_prefix": "<vault_id[:16]>", "nonce": hex12, "corps": hex}
```

`corps` is AES-256-GCM over the coffre state serialised as in §1 (every
`eidos.carnet` field except `maitre`), under a key only that vault can
derive, bound to `vault_id`. **The master seed is never written**: a sealed
file that carries one is refused. The file is opaque to everything but that
vault; `vault_migration` exports and reinstalls it unchanged
(`vault_state/vault_data/<prefix>/eidos/…`).

Losing the sidecar loses little: `n` and the outputs are recovered by
rescanning the published state (`etat.sorties_du_coffre`, indices
`0 … n + 8`); burnt keys are remembered by the chain itself (an address spends
once); only game readings (objects, Tower) are lost, which Eidos declares
readings, not proofs.

## 5. The stateful-key rule

A WOTS+ key signs once. The client rule is that of `ReceiverKey.derive` in
the sphere ledger: read the published state before signing, and write the
burnt fingerprints and the advanced index **before** returning a signature.
`eidos_witness` exposes what a client needs (`envoi.signer_entrees` refuses a
key that does not match the address it spends; `envoi.verifier_envoi` replays
the ledger's own check); the vault-side client enforces the write-before-return.

## 6. Vectors

- `tests/vectors/eidos_vecteurs.json` — Eidos's own `vecteurs.json`
  (`eidos-vecteurs/1`): families `wots`, `tx`, `xmss`, `carnet`, `tete`,
  `veillee`, `relique`, `glyphes`, `coffre`. The witness reproduces `wots`,
  `tx`, `xmss`, `carnet` and `tete` to the byte (`tests/test_eidos_witness_vectors.py`).
- `tests/vectors/eidos_croises.json` — a WOTS+ signature made by Eidos's
  original `wots.py` verified by `sphere_ledger.hash_sig`, and one made by
  `hash_sig.WotsKeyPair` verified by Eidos's `wots.verifier`.
- `tests/fixtures/eidos/carnet_atelier.json` — an `eidos.carnet` written by the
  atelier (`exporterCarnet`, with a carried object and a started Tower);
  `carnet_eidolon.json` — one written here and opened without refusal by the
  atelier's `ouvrirFichier`, which re-exported it byte-identical.

## 7. Versioning

`version` fields are format versions. New dossier genres or fields, or a new
sidecar suite, require a new version. Eidos formats (`eidos-carnet/1`,
`eidos-etat/1`, `eidos-federation/2`, chain format 3) are Eidos's to change;
when they do, this witness follows with a new version, never with a tolerant
reading.
