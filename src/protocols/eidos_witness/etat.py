"""Lecture d'``etat.json`` — l'état publié du réseau d'essai (``eidos-etat/1``).

Le nœud publie après chaque bloc : hauteur, tête, racine UTXO, tête signée,
sorties non dépensées (``"txid:rang" → {adresse, montant}``), soldes par
adresse, invariant. Ce module le lit avec la sévérité de ``parserEtatTestnet``
(envoi.ts) et retrouve les pièces d'un coffre : celles dont l'adresse dérive
de sa graine maîtresse aux indices ``0 … n + marge − 1`` — le robinet verse
sur l'indice ``n``, pas encore consommé localement.

Rien ici ne parle au réseau : le JSON lui est donné.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import wots
from .preuve import est_entier, est_hex

MARGE_INDICES = 8


@dataclass
class Etat:
    hauteur: int
    tete: Optional[str]
    maj_unix: Optional[int]
    invariant: Optional[bool]
    sorties: List[Dict[str, Any]]          # {txid, rang, adresse, montant}, ordre publié
    soldes: Dict[str, int]
    utxo_root: Optional[str] = None
    tete_signee: Optional[Dict[str, Any]] = None
    spec: Optional[str] = None
    reseau: Optional[str] = None
    reliques: List[Dict[str, Any]] = field(default_factory=list)


def parser_etat(raw: Any) -> Etat:
    """Ne lève pas : ce qui est mal formé est ignoré, sortie par sortie."""
    o = raw if isinstance(raw, dict) else {}
    sorties: List[Dict[str, Any]] = []
    brut = o.get("sorties")
    if isinstance(brut, dict):
        for cle, v in brut.items():
            if not isinstance(cle, str) or ":" not in cle or not isinstance(v, dict):
                continue
            txid, _, rang_texte = cle.partition(":")
            try:
                rang = int(rang_texte)
            except ValueError:
                continue
            if (est_hex(txid, 64) and rang >= 0 and str(rang) == rang_texte
                    and est_hex(v.get("adresse"), 40)
                    and est_entier(v.get("montant"), 1)):
                sorties.append({"txid": txid, "rang": rang,
                                "adresse": v["adresse"], "montant": v["montant"]})
    soldes: Dict[str, int] = {}
    if isinstance(o.get("soldes"), dict):
        for a, m in o["soldes"].items():
            if est_hex(a, 40) and est_entier(m):
                soldes[a] = m
    hauteur = o.get("hauteur")
    tete = o.get("tete")
    maj = o.get("maj_unix")
    inv = o.get("invariant")
    reliques = o.get("reliques")
    return Etat(
        hauteur=hauteur if isinstance(hauteur, int) and est_entier(hauteur) else -1,
        tete=tete if est_hex(tete, 64) else None,
        maj_unix=maj if est_entier(maj) else None,
        invariant=inv if isinstance(inv, bool) else None,
        sorties=sorties,
        soldes=soldes,
        utxo_root=o["utxo_root"] if est_hex(o.get("utxo_root"), 64) else None,
        tete_signee=o.get("tete_signee") if isinstance(o.get("tete_signee"), dict) else None,
        spec=o.get("spec") if isinstance(o.get("spec"), str) else None,
        reseau=o.get("reseau") if isinstance(o.get("reseau"), str) else None,
        reliques=[r for r in reliques if isinstance(r, dict)] if isinstance(reliques, list) else [],
    )


def adresses_du_coffre(maitre: str, n: int, marge: int = MARGE_INDICES) -> Dict[str, int]:
    """adresse → indice, pour les indices ``0 … n + marge − 1``."""
    if not est_entier(n) or not est_entier(marge):
        raise ValueError("n et marge : entiers ≥ 0")
    return {wots.adresse_de(maitre, i): i for i in range(n + marge)}


def sorties_du_coffre(etat: Etat, maitre: str, n: int,
                      marge: int = MARGE_INDICES) -> List[Dict[str, Any]]:
    """Les pièces du réseau dont l'adresse dérive de la graine du coffre,
    dans l'ordre publié. Chaque sortie : ref, txid, rang, adresse, indice, montant."""
    indices = adresses_du_coffre(maitre, n, marge)
    out: List[Dict[str, Any]] = []
    for s in etat.sorties:
        indice = indices.get(s["adresse"])
        if indice is None:
            continue
        out.append({
            "ref": f"{s['txid']}:{s['rang']}",
            "txid": s["txid"],
            "rang": s["rang"],
            "adresse": s["adresse"],
            "indice": indice,
            "montant": s["montant"],
        })
    return out


def solde(sorties: List[Dict[str, Any]]) -> int:
    return sum(int(s["montant"]) for s in sorties)


def prochain_indice(sorties: List[Dict[str, Any]], n: int) -> int:
    """``chargerTestnet`` : n = max(n, plus grand indice reçu + 1)."""
    return max([n] + [int(s["indice"]) + 1 for s in sorties])


__all__ = [
    "MARGE_INDICES", "Etat", "parser_etat", "adresses_du_coffre", "sorties_du_coffre",
    "solde", "prochain_indice",
]
