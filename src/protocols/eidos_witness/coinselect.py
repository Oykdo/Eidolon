"""Sélection des sorties — port de ``coinselect.ts`` (les deux trous d'ARBRES.md).

1. Glouton borné : parmi les combinaisons d'au plus trois sorties, prendre
   les plus petites qui atteignent ``montant`` (préférer celles qui
   atteignent aussi ``montant + poussière``, pour ne pas fabriquer un rendu
   poussiéreux).
2. Poussière : si le rendu est strictement inférieur à 10 000 atomes, on
   n'ouvre pas de sortie de rendu ; l'écart devient frais.

Le validateur n'est pas modifié : un atome de rendu reste légal. C'est le
portefeuille qui refuse d'en créer un. Un témoin WOTS+ pèse 2 177 octets
(drapeau + 2 176) : trois entrées au plus par envoi.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import wots

ATOMES = 100_000_000
POUSSIERE_ATOMES = 10_000
MAX_ENTREES = 3
OCTETS_TEMOIN = 1 + wots.OCTETS_TEMOIN    # 2 177
MSG_FRAGMENTE = "solde suffisant mais fragmenté — regrouper d'abord"


@dataclass
class Selection:
    ok: bool
    code: str = ""                          # "" | montant | vide | insuffisant | fragmente
    message: str = ""
    solde: int = 0
    couverture_max: int = 0
    entrees: List[Dict[str, Any]] = field(default_factory=list)
    total_entrees: int = 0
    montant: int = 0
    rendu: int = 0
    frais: int = 0
    poussiere: bool = False
    octets_temoins: int = 0


def solde_de(sorties: Sequence[Dict[str, Any]]) -> int:
    return sum(int(o["montant"]) for o in sorties)


def couverture_max(sorties: Sequence[Dict[str, Any]], k: int = MAX_ENTREES) -> int:
    return sum(int(o["montant"]) for o in sorted(sorties, key=lambda o: -int(o["montant"]))[:k])


def _cle_refs(combo: Sequence[Dict[str, Any]]) -> str:
    return ",".join(sorted(str(o["ref"]) for o in combo))


def selectionner(sorties: Sequence[Dict[str, Any]], montant: Any,
                 poussiere: int = POUSSIERE_ATOMES, maximum: int = MAX_ENTREES) -> Selection:
    solde = solde_de(sorties)
    max_k = couverture_max(sorties, maximum)
    if not isinstance(montant, int) or isinstance(montant, bool) or montant <= 0:
        return Selection(False, "montant", "Montant invalide.", solde, max_k)
    if not sorties:
        return Selection(False, "vide", "Aucune sortie dépensable.", solde, 0)
    if solde < montant:
        return Selection(False, "insuffisant", "Solde insuffisant.", solde, max_k)

    meilleur: Optional[Selection] = None
    meilleure_cle: Optional[Tuple[int, int, int, str]] = None
    plafond = min(maximum, len(sorties))
    for k in range(1, plafond + 1):
        for combo in combinations(sorties, k):
            total = sum(int(o["montant"]) for o in combo)
            if total < montant:
                continue
            brut = total - montant
            est_poussiere = 0 < brut < poussiere
            cle = (1 if est_poussiere else 0, total, len(combo), _cle_refs(combo))
            if meilleure_cle is None or cle < meilleure_cle:
                meilleure_cle = cle
                entrees = sorted(combo, key=lambda o: (int(o["montant"]), str(o["ref"])))
                meilleur = Selection(
                    True, entrees=[dict(o) for o in entrees], total_entrees=total,
                    montant=montant, rendu=0 if est_poussiere else brut,
                    frais=brut if est_poussiere else 0, poussiere=est_poussiere,
                    octets_temoins=len(entrees) * OCTETS_TEMOIN, solde=solde,
                    couverture_max=max_k,
                )
    if meilleur is not None:
        return meilleur
    return Selection(False, "fragmente", MSG_FRAGMENTE, solde, max_k)


def choisir_regroupement(sorties: Sequence[Dict[str, Any]],
                         maximum: int = MAX_ENTREES) -> List[Dict[str, Any]]:
    """Les plus petites sorties, au plus ``maximum``, pour un regroupement."""
    if len(sorties) < 2:
        return []
    return [dict(o) for o in sorted(sorties, key=lambda o: (int(o["montant"]), str(o["ref"])))[
        :min(maximum, len(sorties))]]


def formater_atomes(atomes: int, digits: int = 6) -> str:
    signe = "-" if atomes < 0 else ""
    n = abs(atomes)
    return f"{signe}{n // ATOMES}.{str(n % ATOMES).zfill(8)[:digits]}"


__all__ = [
    "ATOMES", "POUSSIERE_ATOMES", "MAX_ENTREES", "OCTETS_TEMOIN", "MSG_FRAGMENTE",
    "Selection", "solde_de", "couverture_max", "selectionner", "choisir_regroupement",
    "formater_atomes",
]
