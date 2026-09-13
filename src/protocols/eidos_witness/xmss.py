"""XMSS des validateurs Eidos — la vérification seule (``federation.py``).

Une clé de validateur est un arbre de Merkle tweaké de 2^h clés WOTS+ ;
la clé publique est (racine, graine publique). Une signature de bloc est
``(indice, signature WOTS+, chemin)`` : la feuille ``i`` est reconstruite
depuis la signature (arbre L de la clé impliquée, ADRS OTS i / L i), puis
remontée jusqu'à la racine par ``rand_hash`` aux ADRS (arbre, hauteur k,
indice parent).

Signer est hors de ce paquet : le compteur d'indice d'un validateur est un
état que seul le nœud tient. Ici on juge.
"""
from __future__ import annotations

from typing import Sequence, Tuple

from . import wots as W

Signature = Tuple[int, bytes, Sequence[bytes]]   # (indice, sig WOTS+, chemin)


def ad_ots(i: int) -> bytes:
    return W.adrs(W.TYPE_OTS, a=i)


def ad_l(i: int) -> bytes:
    return W.adrs(W.TYPE_LTREE, a=i)


def ad_arbre(hauteur: int, indice: int) -> bytes:
    return W.adrs(W.TYPE_ARBRE, b=hauteur, c=indice)


def verifier_mss(racine: bytes, graine_pub: bytes, hauteur: int, msg32: bytes,
                 sig: Signature) -> bool:
    """Vrai si la feuille reconstruite depuis ``sig`` remonte à ``racine``."""
    try:
        i, ots, chemin = sig
    except (TypeError, ValueError):
        return False
    if not isinstance(i, int) or isinstance(i, bool):
        return False
    if not isinstance(hauteur, int) or isinstance(hauteur, bool) or hauteur < 0:
        return False
    if not (0 <= i < (1 << hauteur)) or len(chemin) != hauteur:
        return False
    if len(racine) != W.N or len(graine_pub) != W.N or len(msg32) != W.N:
        return False
    if any(not isinstance(f, (bytes, bytearray)) or len(f) != W.N for f in chemin):
        return False
    pk = W.cle_depuis_signature(bytes(ots), graine_pub, ad_ots(i), msg32)
    if pk is None:
        return False
    n = W.arbre_l(pk, graine_pub, ad_l(i))
    idx = i
    for k, frere in enumerate(chemin):
        parent = idx >> 1
        if idx % 2 == 0:
            n = W.rand_hash(n, bytes(frere), graine_pub, ad_arbre(k, parent))
        else:
            n = W.rand_hash(bytes(frere), n, graine_pub, ad_arbre(k, parent))
        idx = parent
    return n == racine


__all__ = ["Signature", "ad_ots", "ad_l", "ad_arbre", "verifier_mss"]
