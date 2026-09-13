"""Un actif Eidos rangé dans une voûte — le dossier et son jugement.

Ce qui compte dans Eidos est ancré : une pièce est une sortie non dépensée
prouvée contre la racine UTXO d'une tête signée. Une relique récupérée est
une pièce (la dépense de la relique vers le coffre) ; un sceau d'âge est la
lecture d'une relique récupérée. Le dossier range donc **la même chose** dans
tous les cas : une tête signée, une sortie, sa preuve d'inclusion.

  {"format": "EIDOLON_EIDOS_ACTIF", "version": 1,
   "genre": "piece" | "relique",
   "reseau": <federation.reseau ou null>,
   "tete": TeteSignee (etat.json.tete_signee),
   "sortie": {"txid", "rang", "adresse", "montant"},
   "preuve": {"v": 1, "feuille", "freres", "racine"},
   "indice": <indice de la clé du coffre, ou null>,
   "age": <nom d'âge pour une relique, ou null>,
   "note": <texte libre, hors jugement>}

``juger_actif`` refait ce que fait la page Témoin : la tête est signée par un
validateur de la fédération donnée, la feuille est celle de la sortie, la
preuve remonte à la racine UTXO de cette tête. Une tête plus récente peut
montrer la pièce dépensée : le dossier prouve qu'elle **était** là au bloc
``tete.hauteur``, jamais qu'elle y est encore — c'est l'état qui le dit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from . import preuve as P
from . import tete as T
from .carnet import NOMS_AGES

FORMAT_ACTIF = "EIDOLON_EIDOS_ACTIF"
VERSION_ACTIF = 1
GENRES = ("piece", "relique")


class ActifError(ValueError):
    """Dossier mal formé."""


@dataclass(frozen=True)
class VerdictActif:
    ok: bool
    code: str          # "incluse" | "etrangere" | "rompue" | "aveugle" | "tete" | "forme"
    detail: str
    hauteur: Optional[int] = None


def _sortie_valide(s: Any) -> bool:
    return (isinstance(s, dict) and P.est_hex(s.get("txid"), 64) and P.est_entier(s.get("rang"))
            and P.est_hex(s.get("adresse"), 40) and P.est_entier(s.get("montant"), 1))


def dossier(*, tete: Dict[str, Any], sortie: Dict[str, Any], preuve: Dict[str, Any],
            genre: str = "piece", reseau: Optional[str] = None, indice: Optional[int] = None,
            age: Optional[str] = None, note: str = "") -> Dict[str, Any]:
    """Assemble un dossier ; lève ActifError si la forme est fausse. Ne juge pas."""
    if genre not in GENRES:
        raise ActifError(f"genre {genre!r} inconnu")
    if not _sortie_valide(sortie):
        raise ActifError("sortie : txid, rang, adresse, montant attendus")
    T.TeteSignee.depuis(tete)   # forme seulement
    p, motif = P.parser_preuve(preuve)
    if p is None:
        raise ActifError(f"preuve : {motif}")
    if age is not None and age not in NOMS_AGES:
        raise ActifError(f"âge {age!r} inconnu")
    if indice is not None and not P.est_entier(indice):
        raise ActifError("indice ≥ 0 ou null")
    return {
        "format": FORMAT_ACTIF, "version": VERSION_ACTIF, "genre": genre,
        "reseau": reseau,
        "tete": dict(tete),
        "sortie": {"txid": sortie["txid"], "rang": int(sortie["rang"]),
                   "adresse": sortie["adresse"], "montant": int(sortie["montant"])},
        "preuve": p, "indice": indice, "age": age, "note": str(note or ""),
    }


def dossier_depuis_etat(etat_brut: Dict[str, Any], ref: str, **kw: Any) -> Dict[str, Any]:
    """Le dossier d'une sortie ``"txid:rang"`` d'un ``etat.json`` chargé : tête
    signée et preuve prises dans l'état publié."""
    from .etat import parser_etat
    e = parser_etat(etat_brut)
    if e.tete_signee is None:
        raise ActifError("etat.json sans tête signée")
    sortie = next((s for s in e.sorties if f"{s['txid']}:{s['rang']}" == ref), None)
    if sortie is None:
        raise ActifError(f"sortie {ref} absente de l'état")
    pr = P.preuve_reseau(e.sorties, ref)
    if pr is None:
        raise ActifError(f"pas de preuve pour {ref}")
    return dossier(tete=e.tete_signee, sortie=sortie, preuve=pr,
                   reseau=kw.pop("reseau", e.reseau), **kw)


def juger_actif(d: Dict[str, Any], fed: T.Federation,
                verifier_proposant: bool = True) -> VerdictActif:
    """Ne lève jamais : un dossier mal formé rend ``forme``."""
    if not isinstance(d, dict) or d.get("format") != FORMAT_ACTIF or d.get("version") != VERSION_ACTIF:
        return VerdictActif(False, "forme", "dossier inconnu")
    if d.get("genre") not in GENRES or not _sortie_valide(d.get("sortie")):
        return VerdictActif(False, "forme", "genre ou sortie mal formés")
    try:
        brut_tete = d.get("tete")
        tete = T.TeteSignee.depuis(brut_tete if isinstance(brut_tete, dict) else {})
    except T.TeteError as e:
        return VerdictActif(False, "forme", str(e))
    p, motif = P.parser_preuve(d.get("preuve"))
    if p is None:
        return VerdictActif(False, "forme", f"preuve : {motif}")
    v = T.verifier_tete(tete, fed, verifier_proposant=verifier_proposant)
    if not v.ok:
        return VerdictActif(False, "tete", v.detail, tete.hauteur)
    if p["feuille"] != P.feuille_de(d["sortie"]).hex():
        return VerdictActif(False, "rompue", "la feuille n'est pas celle de la sortie", tete.hauteur)
    code, detail = P.juger(tete.utxo_root.hex(), p)
    if code != "incluse":
        return VerdictActif(False, code, detail, tete.hauteur)
    return VerdictActif(True, "incluse", f"incluse · bloc {tete.hauteur}", tete.hauteur)


def identifiant(d: Dict[str, Any]) -> str:
    """``txid:rang`` — ce qui nomme un dossier dans la voûte."""
    s = d["sortie"]
    return f"{s['txid']}:{int(s['rang'])}"


__all__ = [
    "FORMAT_ACTIF", "VERSION_ACTIF", "GENRES", "ActifError", "VerdictActif",
    "dossier", "dossier_depuis_etat", "juger_actif", "identifiant",
]
