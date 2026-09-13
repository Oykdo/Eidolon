"""Racine UTXO et preuves d'inclusion — port de ``merkle.ts`` et ``utxo.py``.

Chaque bloc fédéré déclare la racine de Merkle du carnet entier après lui :
feuille = SHA-256d(txid ‖ rang(4) ‖ adresse(20) ‖ montant(8)), ordre
canonique (txid, rang), niveau impair complété par duplication du dernier
nœud, carnet vide = 32 octets nuls. Un témoin qui tient la tête signée juge
une sortie contre ``utxo_root`` sans rejouer la chaîne.

La preuve portable est celle de l'atelier :
``{"v": 1, "feuille": hex, "freres": [{"cote": "gauche"|"droite", "hash": hex}…], "racine": hex}``
— ``cote`` dit de quel côté se place le frère à ce niveau.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Sequence, Tuple

CODES_VERDICT = ("incluse", "etrangere", "rompue", "aveugle")

HEX32 = 64
HEX20 = 40


def sha256d(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def est_hex(s: Any, longueur: int) -> bool:
    return (isinstance(s, str) and len(s) == longueur
            and all(c in "0123456789abcdef" for c in s))


def est_entier(x: Any, minimum: int = 0) -> bool:
    return isinstance(x, int) and not isinstance(x, bool) and x >= minimum


# ---------------------------------------------------------------------------
# 1. Feuilles et racine
# ---------------------------------------------------------------------------

def feuille_sortie(txid: bytes, rang: int, adresse: bytes, montant: int) -> bytes:
    """SHA-256d(txid ‖ rang(4) ‖ adresse(20) ‖ montant(8)) — même règle que merkle.ts."""
    if len(txid) != 32 or len(adresse) != 20:
        raise ValueError("txid de 32 octets et adresse de 20 octets attendus")
    return sha256d(txid + rang.to_bytes(4, "big") + adresse + montant.to_bytes(8, "big"))


def feuille_de(sortie: Dict[str, Any]) -> bytes:
    """La feuille d'une sortie ``{"txid", "rang", "adresse", "montant"}`` (hex, int)."""
    return feuille_sortie(bytes.fromhex(sortie["txid"]), int(sortie["rang"]),
                          bytes.fromhex(sortie["adresse"]), int(sortie["montant"]))


def merkle_root(feuilles: Sequence[bytes]) -> bytes:
    if not feuilles:
        return bytes(32)
    lvl = list(feuilles)
    while len(lvl) > 1:
        if len(lvl) % 2:
            lvl.append(lvl[-1])
        lvl = [sha256d(lvl[i] + lvl[i + 1]) for i in range(0, len(lvl), 2)]
    return lvl[0]


def ordre_canonique(sorties: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """(txid, rang) croissants — l'hex minuscule se trie comme les octets."""
    return sorted(sorties, key=lambda s: (s["txid"], int(s["rang"])))


def utxo_root(sorties: Sequence[Dict[str, Any]]) -> bytes:
    """Racine du carnet entier, telle que le nœud l'inscrit dans l'en-tête signé."""
    return merkle_root([feuille_de(s) for s in ordre_canonique(sorties)])


# ---------------------------------------------------------------------------
# 2. Preuves
# ---------------------------------------------------------------------------

def niveaux_de(feuilles: Sequence[bytes]) -> List[List[bytes]]:
    """Tous les niveaux, du bas vers la racine, niveaux impairs complétés."""
    if not feuilles:
        return [[bytes(32)]]
    cur = list(feuilles)
    niveaux: List[List[bytes]] = [list(cur)]
    while len(cur) > 1:
        if len(cur) % 2:
            cur.append(cur[-1])
            niveaux[-1] = list(cur)
        cur = [sha256d(cur[i] + cur[i + 1]) for i in range(0, len(cur), 2)]
        niveaux.append(list(cur))
    return niveaux


def preuve_de(feuilles: Sequence[bytes], indice: int) -> Optional[Dict[str, Any]]:
    """La preuve portable de la feuille ``indice`` ; None hors bornes."""
    if not est_entier(indice) or indice >= len(feuilles):
        return None
    niveaux = niveaux_de(feuilles)
    freres: List[Dict[str, str]] = []
    i = indice
    for lvl in niveaux[:-1]:
        pair = i ^ 1
        sib = lvl[min(pair, len(lvl) - 1)]
        freres.append({"cote": "droite" if i % 2 == 0 else "gauche", "hash": sib.hex()})
        i //= 2
    return {"v": 1, "feuille": feuilles[indice].hex(), "freres": freres,
            "racine": niveaux[-1][0].hex()}


def preuve_reseau(sorties: Sequence[Dict[str, Any]], ref: str) -> Optional[Dict[str, Any]]:
    """Preuve d'une sortie ``"txid:rang"`` contre la racine UTXO, depuis la
    liste publiée (etat.json)."""
    ordre = ordre_canonique(sorties)
    for i, s in enumerate(ordre):
        if f"{s['txid']}:{int(s['rang'])}" == ref:
            return preuve_de([feuille_de(x) for x in ordre], i)
    return None


def racine_de_preuve(preuve: Dict[str, Any]) -> Optional[bytes]:
    """Remonte la feuille par ses frères ; None si la preuve est mal formée."""
    try:
        h = bytes.fromhex(preuve["feuille"])
        freres = preuve["freres"]
    except (KeyError, TypeError, ValueError):
        return None
    if len(h) != 32 or not isinstance(freres, list):
        return None
    for f in freres:
        try:
            sib = bytes.fromhex(f["hash"])
            cote = f["cote"]
        except (KeyError, TypeError, ValueError):
            return None
        if len(sib) != 32:
            return None
        if cote == "droite":
            h = sha256d(h + sib)
        elif cote == "gauche":
            h = sha256d(sib + h)
        else:
            return None
    return h


def verifier_preuve(preuve: Dict[str, Any]) -> bool:
    r = racine_de_preuve(preuve)
    return r is not None and est_hex(preuve.get("racine"), HEX32) and r.hex() == preuve["racine"]


def parser_preuve(o: Any) -> Tuple[Optional[Dict[str, Any]], str]:
    """(preuve, "") ou (None, motif) — la même sévérité que ``parserPreuve``."""
    if not isinstance(o, dict) or o.get("v") != 1:
        return None, "preuve illisible"
    if not est_hex(o.get("feuille"), HEX32) or not est_hex(o.get("racine"), HEX32):
        return None, "empreintes attendues sur 32 octets"
    if not isinstance(o.get("freres"), list):
        return None, "frères absents"
    freres = []
    for f in o["freres"]:
        if not isinstance(f, dict) or f.get("cote") not in ("gauche", "droite"):
            return None, "frère sans côté"
        if not est_hex(f.get("hash"), HEX32):
            return None, "frère mal formé"
        freres.append({"cote": f["cote"], "hash": f["hash"]})
    return {"v": 1, "feuille": o["feuille"], "freres": freres, "racine": o["racine"]}, ""


# ---------------------------------------------------------------------------
# 3. Le verdict, comme la page Témoin
# ---------------------------------------------------------------------------

def juger(racine_tete: Optional[str], preuve: Dict[str, Any]) -> Tuple[str, str]:
    """(code, détail) : ``aveugle`` sans tête, ``rompue`` si le chemin ne
    remonte pas à sa propre racine, ``etrangere`` si cette racine n'est pas
    celle de la tête, ``incluse`` sinon."""
    if not racine_tete:
        return "aveugle", "pas de tête — suivre d'abord"
    if not verifier_preuve(preuve):
        return "rompue", "chemin rompu"
    if preuve["racine"] != racine_tete:
        return "etrangere", "racine étrangère — pas cette tête"
    return "incluse", "incluse"


__all__ = [
    "CODES_VERDICT", "sha256d", "est_hex", "est_entier",
    "feuille_sortie", "feuille_de", "merkle_root", "ordre_canonique", "utxo_root",
    "niveaux_de", "preuve_de", "preuve_reseau", "racine_de_preuve", "verifier_preuve",
    "parser_preuve", "juger",
]
