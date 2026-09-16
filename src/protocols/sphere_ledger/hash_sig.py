"""WOTS+ — signature à usage unique par hachage pur (RFC 8391, §3.1).

Première brique de la chaîne de garde des sphères : chaque transfert d'une
sphère est signé par une clé à usage unique dont la clé publique a été
engagée (hachée) dans l'enregistrement précédent. Rien d'autre que du
hachage : ni courbe, ni réseau, ni hypothèse structurée. La sécurité repose
sur la résistance aux secondes préimages de la fonction de hachage, ce qui
survit à un adversaire quantique (Grover ne divise l'effort que par deux en
exposant).

Construction, fidèle à RFC 8391 avec le jeu de paramètres n=32, w=16 :

- ``len_1 = 64`` chaînes portent le message (256 bits en base 16),
  ``len_2 = 3`` chaînes portent la somme de contrôle, ``len = 67``.
- Une chaîne avance par ``F(key, M ⊕ bitmask)``, la clé et le masque de
  chaque pas étant dérivés par ``PRF(seed_public, adresse)``. L'adresse
  encode la chaîne et le pas, ce qui rend chaque pas d'une chaîne distinct de
  tous les autres (séparation de domaine).
- La clé publique (67 × 32 octets) est compressée en une seule valeur de
  32 octets par un L-tree (RFC 8391 §4.1.5) : c'est l'**adresse à usage
  unique** que l'on engage dans un enregistrement.

Ce qui n'est PAS ici, à dessein : XMSS (l'arbre de clés WOTS+ avec un index
d'état). Une clé XMSS restaurée depuis une sauvegarde re-signe avec une
feuille déjà consommée, et deux signatures WOTS+ d'une même clé livrent
assez de chaîne pour forger. Pour des sphères qui voyagent de voûte en
voûte, l'état est le risque ; ici la seule règle est « une clé, une
signature », et la clé n'existe que le temps d'un transfert.

Les fonctions de hachage sont celles de RFC 8391 pour SHA-256 :
``F = SHA-256(toByte(0,32) || KEY || M)``,
``H = SHA-256(toByte(1,32) || KEY || M)``,
``PRF = SHA-256(toByte(3,32) || KEY || M)``.
L'implémentation est en Python pur ; les performances (≈ 4 300 hachages
par signature) sont sans importance à l'échelle d'un transfert de sphère.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import List, Optional, Sequence

N = 32          # octets par valeur de hachage
W = 16          # base de Winternitz
LOG_W = 4
LEN_1 = 64      # ceil(8n / log2 w)
LEN_2 = 3       # floor(log2(len_1 (w-1)) / log2 w) + 1
LEN = LEN_1 + LEN_2

# Types d'adresse (RFC 8391 §2.5) : ici seuls OTS (0) et L-tree (1) servent.
_ADRS_OTS = 0
_ADRS_LTREE = 1


class HashSigError(ValueError):
    """Signature WOTS+ mal formée, ou clé déjà consommée."""


# ---------------------------------------------------------------------------
# Adresses (RFC 8391 §2.5) — 32 octets, 8 mots de 4 octets grands-boutistes.
# ---------------------------------------------------------------------------

class Address:
    """Une adresse de hachage, mutée par le code appelant comme dans la RFC."""

    __slots__ = ("words",)

    def __init__(self, layer: int = 0, tree: int = 0, adrs_type: int = _ADRS_OTS):
        self.words = [layer, tree & 0xFFFFFFFF, (tree >> 32) & 0xFFFFFFFF, adrs_type, 0, 0, 0, 0]

    # Mot 4 : OTS address / L-tree address ; mot 5 : chain / tree height ;
    # mot 6 : hash / tree index ; mot 7 : keyAndMask.
    def set_type(self, t: int) -> None:
        self.words[3] = t
        self.words[4] = self.words[5] = self.words[6] = self.words[7] = 0

    def set_ots(self, i: int) -> None:
        self.words[4] = i

    def set_chain(self, i: int) -> None:
        self.words[5] = i

    def set_hash(self, i: int) -> None:
        self.words[6] = i

    def set_key_and_mask(self, i: int) -> None:
        self.words[7] = i

    def set_ltree(self, i: int) -> None:
        self.words[4] = i

    def set_tree_height(self, i: int) -> None:
        self.words[5] = i

    def set_tree_index(self, i: int) -> None:
        self.words[6] = i

    def to_bytes(self) -> bytes:
        return b"".join(w.to_bytes(4, "big") for w in self.words)


# ---------------------------------------------------------------------------
# Fonctions de hachage à clé (RFC 8391 §5.1, jeu SHA-256)
# ---------------------------------------------------------------------------

def _to_byte(value: int, length: int) -> bytes:
    return value.to_bytes(length, "big")


def F(key: bytes, message: bytes) -> bytes:
    return hashlib.sha256(_to_byte(0, N) + key + message).digest()


def H(key: bytes, message: bytes) -> bytes:
    return hashlib.sha256(_to_byte(1, N) + key + message).digest()


def PRF(key: bytes, message: bytes) -> bytes:
    return hashlib.sha256(_to_byte(3, N) + key + message).digest()


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


# ---------------------------------------------------------------------------
# Chaînes et encodage du message
# ---------------------------------------------------------------------------

def _chain(x: bytes, start: int, steps: int, seed: bytes, adrs: Address) -> bytes:
    """Avance la chaîne de ``start`` à ``start + steps`` (RFC 8391 algo 2)."""
    if steps == 0:
        return x
    if start + steps > W - 1:
        raise HashSigError("chaîne au-delà de w-1")
    tmp = x
    for i in range(start, start + steps):
        adrs.set_hash(i)
        adrs.set_key_and_mask(0)
        key = PRF(seed, adrs.to_bytes())
        adrs.set_key_and_mask(1)
        mask = PRF(seed, adrs.to_bytes())
        tmp = F(key, _xor(tmp, mask))
    return tmp


def _base_w(data: bytes, out_len: int) -> List[int]:
    """Découpe ``data`` en ``out_len`` chiffres en base w (RFC 8391 algo 1)."""
    out: List[int] = []
    total = 0
    bits = 0
    idx = 0
    for _ in range(out_len):
        if bits == 0:
            total = data[idx]
            idx += 1
            bits = 8
        bits -= LOG_W
        out.append((total >> bits) & (W - 1))
    return out


def _message_digits(message_digest: bytes) -> List[int]:
    """Les 67 chiffres : 64 du message, 3 de la somme de contrôle."""
    if len(message_digest) != N:
        raise HashSigError(f"le message signé doit être un condensat de {N} octets")
    msg = _base_w(message_digest, LEN_1)
    csum = sum((W - 1) - d for d in msg)
    # Décalage à gauche pour aligner sur un octet (RFC 8391 algo 5).
    csum <<= 8 - ((LEN_2 * LOG_W) % 8)
    csum_bytes = csum.to_bytes((LEN_2 * LOG_W + 7) // 8, "big")
    return msg + _base_w(csum_bytes, LEN_2)


# ---------------------------------------------------------------------------
# Clés et signatures
# ---------------------------------------------------------------------------

def _expand_secret(secret_seed: bytes) -> List[bytes]:
    """RFC 8391 §3.1.3 : sk_i = PRF(secret_seed, toByte(i, 32))."""
    return [PRF(secret_seed, _to_byte(i, 32)) for i in range(LEN)]


def _public_from_secret(sk: Sequence[bytes], seed: bytes, adrs: Address) -> List[bytes]:
    pk = []
    for i, s in enumerate(sk):
        adrs.set_chain(i)
        pk.append(_chain(s, 0, W - 1, seed, adrs))
    return pk


def ltree(pk: Sequence[bytes], seed: bytes, adrs: Address) -> bytes:
    """Compresse les 67 valeurs de clé publique en une seule (RFC 8391 algo 8)."""
    nodes = list(pk)
    adrs.set_tree_height(0)
    while len(nodes) > 1:
        nxt = []
        for i in range(len(nodes) // 2):
            adrs.set_tree_index(i)
            nxt.append(_rand_hash(nodes[2 * i], nodes[2 * i + 1], seed, adrs))
        if len(nodes) % 2 == 1:
            nxt.append(nodes[-1])
        nodes = nxt
        adrs.set_tree_height(adrs.words[5] + 1)
    return nodes[0]


def _rand_hash(left: bytes, right: bytes, seed: bytes, adrs: Address) -> bytes:
    """RAND_HASH (RFC 8391 algo 7)."""
    adrs.set_key_and_mask(0)
    key = PRF(seed, adrs.to_bytes())
    adrs.set_key_and_mask(1)
    bm0 = PRF(seed, adrs.to_bytes())
    adrs.set_key_and_mask(2)
    bm1 = PRF(seed, adrs.to_bytes())
    return H(key, _xor(left, bm0) + _xor(right, bm1))


@dataclass
class WotsPublicKey:
    """Clé publique WOTS+ : le seed public, l'adresse et la valeur compressée."""
    seed: bytes
    ots_index: int
    root: bytes          # sortie du L-tree : l'adresse à usage unique (32 octets)

    def to_dict(self) -> dict:
        return {"seed": self.seed.hex(), "ots_index": self.ots_index, "root": self.root.hex()}

    @classmethod
    def from_dict(cls, d: dict) -> "WotsPublicKey":
        return cls(bytes.fromhex(d["seed"]), int(d["ots_index"]), bytes.fromhex(d["root"]))


@dataclass
class WotsSignature:
    sig: List[bytes]     # 67 valeurs de 32 octets

    def to_bytes(self) -> bytes:
        return b"".join(self.sig)

    @classmethod
    def from_bytes(cls, data: bytes) -> "WotsSignature":
        if len(data) != LEN * N:
            raise HashSigError(f"signature WOTS+ de {len(data)} octets, {LEN * N} attendus")
        return cls([data[i * N:(i + 1) * N] for i in range(LEN)])


class WotsKeyPair:
    """Une clé à usage unique. ``sign()`` ne fonctionne qu'une fois.

    Le seed secret est effacé après la signature : la classe ne peut pas
    resigner même si l'appelant insiste. Une seconde signature avec la même
    clé livrerait à un observateur des maillons intermédiaires de chaînes,
    donc la possibilité de signer d'autres messages.
    """

    def __init__(self, secret_seed: Optional[bytes] = None, public_seed: Optional[bytes] = None,
                 ots_index: int = 0):
        self._secret_seed: Optional[bytes] = secret_seed or secrets.token_bytes(N)
        self.public_seed = public_seed or secrets.token_bytes(N)
        self.ots_index = ots_index
        self.used = False
        adrs = Address(adrs_type=_ADRS_OTS)
        adrs.set_ots(ots_index)
        sk = _expand_secret(self._secret_seed)
        pk = _public_from_secret(sk, self.public_seed, adrs)
        ladrs = Address(adrs_type=_ADRS_LTREE)
        ladrs.set_ltree(ots_index)
        self.public_key = WotsPublicKey(self.public_seed, ots_index, ltree(pk, self.public_seed, ladrs))

    def sign(self, message_digest: bytes) -> WotsSignature:
        if self.used or self._secret_seed is None:
            raise HashSigError("clé WOTS+ déjà consommée : une clé, une signature")
        digits = _message_digits(message_digest)
        adrs = Address(adrs_type=_ADRS_OTS)
        adrs.set_ots(self.ots_index)
        sk = _expand_secret(self._secret_seed)
        sig = []
        for i, d in enumerate(digits):
            adrs.set_chain(i)
            sig.append(_chain(sk[i], 0, d, self.public_seed, adrs))
        self.used = True
        self._secret_seed = None
        return WotsSignature(sig)


def public_key_from_signature(signature: WotsSignature, message_digest: bytes,
                              public_seed: bytes, ots_index: int) -> bytes:
    """Reconstruit l'adresse à usage unique depuis une signature (RFC 8391 algo 6 + L-tree).

    C'est la seule opération du vérifieur : si la valeur reconstruite est
    celle engagée dans l'enregistrement précédent, la signature est valide.
    """
    digits = _message_digits(message_digest)
    adrs = Address(adrs_type=_ADRS_OTS)
    adrs.set_ots(ots_index)
    pk = []
    for i, d in enumerate(digits):
        adrs.set_chain(i)
        pk.append(_chain(signature.sig[i], d, (W - 1) - d, public_seed, adrs))
    ladrs = Address(adrs_type=_ADRS_LTREE)
    ladrs.set_ltree(ots_index)
    return ltree(pk, public_seed, ladrs)


def verify(public_key: WotsPublicKey, message_digest: bytes, signature: WotsSignature) -> bool:
    """Vrai si ``signature`` sur ``message_digest`` mène à ``public_key.root``."""
    try:
        candidate = public_key_from_signature(signature, message_digest, public_key.seed, public_key.ots_index)
    except HashSigError:
        return False
    return secrets.compare_digest(candidate, public_key.root)


def digest(message: bytes) -> bytes:
    """Le condensat que l'on signe : SHA3-256, la fonction du reste du cœur."""
    return hashlib.sha3_256(message).digest()


__all__ = [
    "N", "W", "LEN", "HashSigError", "WotsKeyPair", "WotsPublicKey", "WotsSignature",
    "verify", "public_key_from_signature", "digest", "ltree",
]
