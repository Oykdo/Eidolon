"""WOTS+ tel qu'Eidos le dérive — port à l'octet de ``wots.py`` (Oykdo/Eidos).

Même construction que ``sphere_ledger.hash_sig`` (RFC 8391, n = 32, w = 16,
len = 67, F/H/PRF SHA-256 préfixées, arbre L) : les deux vérifieurs se
reconnaissent mutuellement, vecteurs croisés à l'appui. Ce qui diffère, et
que ce module porte, c'est la **dérivation** propre à Eidos :

  graine_n   = SHA-256("<maitre>/<n>")                 (lamport.ts, graineDe)
  graine_pub = SHA-256(graine ‖ "pub")
  sk_i       = PRF(graine, ADRS(OTS 0, chaîne i))
  pk_i       = chaîne(sk_i, 0 → 15)
  racine     = arbre L des 67 pk_i
  adresse    = SHA-256(graine_pub ‖ racine)[:20]
  empreinte  = SHA-256(graine_pub ‖ racine)            (usage unique dans la chaîne)

Un témoin de dépense est ``(graine_pub, signature)`` : 32 + 2 144 octets. Le
vérifieur reconstruit la racine depuis la signature et compare l'adresse.

Les noms sont ceux d'Eidos (``chaine``, ``arbre_l``, ``signer``, ``verifier``…)
pour que le port se relise ligne à ligne contre l'original. Bibliothèque
standard seulement.

AVERTISSEMENT. Une clé WOTS+ ne signe QU'UNE FOIS. Le carnet d'Eidos refuse
une adresse dépensée deux fois ; le client doit lire l'état avant de signer et
noter la clé brûlée avant de rendre la signature.
"""
from __future__ import annotations

import hashlib
from typing import List, Optional, Sequence, Tuple

N = 32
W = 16
LOG_W = 4
LEN1 = 64
LEN2 = 3
LEN = LEN1 + LEN2          # 67
OCTETS_SIG = LEN * N       # 2 144
OCTETS_GRAINE = 32
OCTETS_TEMOIN = OCTETS_GRAINE + OCTETS_SIG   # 2 176

TYPE_OTS, TYPE_LTREE, TYPE_ARBRE = 0, 1, 2

Temoin = Tuple[bytes, bytes]   # (graine publique, signature)


def sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def _to_byte(x: int, n: int) -> bytes:
    return x.to_bytes(n, "big")


# ---------------------------------------------------------------------------
# 1. Adresses de hachage (ADRS, 32 octets) et fonctions tweakées
# ---------------------------------------------------------------------------

def adrs(type_: int, couche: int = 0, arbre: int = 0, a: int = 0, b: int = 0,
         c: int = 0, masque: int = 0) -> bytes:
    """layer(4) tree(8) type(4) x(4) y(4) z(4) keyAndMask(4).
    OTS : x = adresse OTS, y = chaîne, z = maillon ; L : x = adresse L,
    y = hauteur, z = indice ; arbre : x = 0, y = hauteur, z = indice."""
    return (_to_byte(couche, 4) + _to_byte(arbre, 8) + _to_byte(type_, 4)
            + _to_byte(a, 4) + _to_byte(b, 4) + _to_byte(c, 4) + _to_byte(masque, 4))


def _masque(ad: bytes, m: int) -> bytes:
    return ad[:28] + _to_byte(m, 4)


def F(cle: bytes, m: bytes) -> bytes:
    return sha256(_to_byte(0, N) + cle + m)


def H(cle: bytes, m: bytes) -> bytes:
    return sha256(_to_byte(1, N) + cle + m)


def PRF(cle: bytes, m: bytes) -> bytes:
    return sha256(_to_byte(3, N) + cle + m)


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def chaine(x: bytes, depart: int, pas: int, graine_pub: bytes, ad: bytes) -> bytes:
    """Applique F de ``depart`` à ``depart + pas - 1``, clé et masque dérivés
    de (graine publique, ADRS) à chaque maillon."""
    for j in range(depart, depart + pas):
        ad_j = ad[:24] + _to_byte(j, 4) + _to_byte(0, 4)
        cle = PRF(graine_pub, ad_j)
        bm = PRF(graine_pub, _masque(ad_j, 1))
        x = F(cle, _xor(x, bm))
    return x


def rand_hash(gauche: bytes, droite: bytes, graine_pub: bytes, ad: bytes) -> bytes:
    cle = PRF(graine_pub, _masque(ad, 0))
    bm0 = PRF(graine_pub, _masque(ad, 1))
    bm1 = PRF(graine_pub, _masque(ad, 2))
    return H(cle, _xor(gauche, bm0) + _xor(droite, bm1))


# ---------------------------------------------------------------------------
# 2. WOTS+ : base w, somme de contrôle, génération, signature, vérification
# ---------------------------------------------------------------------------

def base_w(msg32: bytes) -> List[int]:
    """64 chiffres en base 16 (quartets, poids fort d'abord), puis 3 chiffres
    de somme de contrôle : csum = Σ(15 − m_i), décalée de 4 bits, sur 2 octets."""
    chiffres: List[int] = []
    for o in msg32:
        chiffres.append(o >> 4)
        chiffres.append(o & 15)
    csum = sum(W - 1 - m for m in chiffres) << 4
    cs = _to_byte(csum, 2)
    chiffres += [cs[0] >> 4, cs[0] & 15, cs[1] >> 4]
    assert len(chiffres) == LEN
    return chiffres


def graine_publique(graine: bytes) -> bytes:
    return sha256(graine + b"pub")


def _ad_chaine(ad_ots: bytes, i: int) -> bytes:
    return ad_ots[:20] + _to_byte(i, 4) + _to_byte(0, 8)


def _sk(graine: bytes, ad_ots: bytes, i: int) -> bytes:
    return PRF(graine, _ad_chaine(ad_ots, i))


def cle_publique(graine: bytes, graine_pub: bytes, ad_ots: bytes) -> List[bytes]:
    """67 éléments de 32 octets."""
    return [chaine(_sk(graine, ad_ots, i), 0, W - 1, graine_pub, _ad_chaine(ad_ots, i))
            for i in range(LEN)]


def signer_wots(graine: bytes, graine_pub: bytes, ad_ots: bytes, msg32: bytes) -> bytes:
    if len(msg32) != N:
        raise ValueError("message de 32 octets attendu")
    return b"".join(chaine(_sk(graine, ad_ots, i), 0, m, graine_pub, _ad_chaine(ad_ots, i))
                    for i, m in enumerate(base_w(msg32)))


def cle_depuis_signature(sig: bytes, graine_pub: bytes, ad_ots: bytes,
                         msg32: bytes) -> Optional[List[bytes]]:
    """Termine les chaînes : la clé publique que cette signature implique."""
    if len(sig) != OCTETS_SIG or len(msg32) != N:
        return None
    return [chaine(sig[i * N:(i + 1) * N], m, W - 1 - m, graine_pub, _ad_chaine(ad_ots, i))
            for i, m in enumerate(base_w(msg32))]


# ---------------------------------------------------------------------------
# 3. Arbre L : compression des 67 éléments en une racine de 32 octets
# ---------------------------------------------------------------------------

def arbre_l(pk: Sequence[bytes], graine_pub: bytes, ad_l: bytes) -> bytes:
    noeuds = list(pk)
    hauteur = 0
    while len(noeuds) > 1:
        suivant = []
        for i in range(len(noeuds) // 2):
            ad = ad_l[:20] + _to_byte(hauteur, 4) + _to_byte(i, 4) + _to_byte(0, 4)
            suivant.append(rand_hash(noeuds[2 * i], noeuds[2 * i + 1], graine_pub, ad))
        if len(noeuds) % 2:
            suivant.append(noeuds[-1])
        noeuds = suivant
        hauteur += 1
    return noeuds[0]


# ---------------------------------------------------------------------------
# 4. Clé à usage unique pour une transaction (ADRS OTS 0, arbre L 0)
# ---------------------------------------------------------------------------
AD_OTS_TX = adrs(TYPE_OTS)
AD_L_TX = adrs(TYPE_LTREE)


def racine(graine: bytes) -> Tuple[bytes, bytes]:
    """(graine publique, racine de l'arbre L)."""
    gp = graine_publique(graine)
    return gp, arbre_l(cle_publique(graine, gp, AD_OTS_TX), gp, AD_L_TX)


def adresse(graine_pub: bytes, racine_l: bytes) -> bytes:
    return sha256(graine_pub + racine_l)[:20]


def empreinte(graine_pub: bytes, racine_l: bytes) -> bytes:
    return sha256(graine_pub + racine_l)


def adresse_de_graine(graine: bytes) -> bytes:
    return adresse(*racine(graine))


def empreinte_de_graine(graine: bytes) -> bytes:
    return empreinte(*racine(graine))


def signer(graine: bytes, msg32: bytes) -> Temoin:
    """Témoin : (graine publique, signature)."""
    gp = graine_publique(graine)
    return gp, signer_wots(graine, gp, AD_OTS_TX, msg32)


def racine_depuis_temoin(temoin: Temoin, msg32: bytes) -> Optional[bytes]:
    """None si le témoin n'a pas la forme attendue."""
    try:
        gp, sig = temoin
    except (TypeError, ValueError):
        return None
    if not isinstance(gp, (bytes, bytearray)) or not isinstance(sig, (bytes, bytearray)):
        return None
    if len(gp) != OCTETS_GRAINE:
        return None
    pk = cle_depuis_signature(bytes(sig), bytes(gp), AD_OTS_TX, msg32)
    if pk is None:
        return None
    return arbre_l(pk, bytes(gp), AD_L_TX)


def verifier(adresse20: bytes, msg32: bytes, temoin: Temoin) -> bool:
    """Vrai si la clé reconstruite depuis la signature donne l'adresse."""
    r = racine_depuis_temoin(temoin, msg32)
    return r is not None and adresse(bytes(temoin[0]), r) == adresse20


# ---------------------------------------------------------------------------
# 5. Dérivation du coffre (lamport.ts) : une graine maîtresse, un indice
# ---------------------------------------------------------------------------

def graine_de(maitre: str, indice: int) -> bytes:
    """``SHA-256("<maitre>/<indice>")`` — la graine de la clé d'indice ``indice``."""
    if not isinstance(maitre, str) or not maitre:
        raise ValueError("graine maîtresse : chaîne non vide attendue")
    if not isinstance(indice, int) or isinstance(indice, bool) or indice < 0:
        raise ValueError("indice ≥ 0 attendu")
    return sha256(f"{maitre}/{indice}".encode("utf-8"))


def adresse_de(maitre: str, indice: int) -> str:
    """L'adresse (20 octets, hex) de la clé d'indice ``indice`` du coffre."""
    return adresse_de_graine(graine_de(maitre, indice)).hex()


def empreinte_de(maitre: str, indice: int) -> str:
    """L'empreinte (32 octets, hex) — ce que ``clesUsees`` retient d'une clé brûlée."""
    return empreinte_de_graine(graine_de(maitre, indice)).hex()


def est_graine_hex256(maitre: object) -> bool:
    """La forme d'une graine tirée (ou dérivée) : 64 hexadécimaux minuscules."""
    return isinstance(maitre, str) and len(maitre) == 64 and all(
        c in "0123456789abcdef" for c in maitre)


__all__ = [
    "N", "W", "LEN", "OCTETS_SIG", "OCTETS_GRAINE", "OCTETS_TEMOIN",
    "TYPE_OTS", "TYPE_LTREE", "TYPE_ARBRE", "Temoin",
    "sha256", "adrs", "F", "H", "PRF", "chaine", "rand_hash", "base_w",
    "graine_publique", "cle_publique", "signer_wots", "cle_depuis_signature", "arbre_l",
    "AD_OTS_TX", "AD_L_TX", "racine", "adresse", "empreinte",
    "adresse_de_graine", "empreinte_de_graine", "signer", "racine_depuis_temoin", "verifier",
    "graine_de", "adresse_de", "empreinte_de", "est_graine_hex256",
]
