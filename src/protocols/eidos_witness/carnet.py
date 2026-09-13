"""``eidos.carnet`` — le format d'échange avec l'atelier (``eidos-carnet/1``).

Le carnet est l'unique fichier d'Eidos : le feuillet du coffre (graine
maîtresse, indice courant, sorties, historique, clés brûlées, reliques,
objets…) et, à côté, la jauge de la Tour (``tour``), hors empreinte. Il n'est
**pas signé** — signer une sauvegarde brûlerait une clé WOTS+ — mais porte
une trace SHA-256d liée à l'adresse courante :

  corps     = {v: 1, kind, alg: "sha256d", sig: "lamport-sha256", feuillet, adresse}
  empreinte = SHA-256d("eidos-carnet/1" ‖ JSON.stringify(corps))
  fichier   = {…corps, empreinte, tour}

Pour que l'empreinte soit la même des deux côtés, ce module sérialise comme
``JSON.stringify`` : sans espaces, clés dans l'ordre d'insertion, UTF-8 sans
échappement ASCII, entiers sans partie décimale. Un carnet écrit ici s'ouvre
dans l'atelier ; un carnet écrit par l'atelier se relit ici, à l'octet.

Ce que ce module ne fait pas : renormaliser ``objets`` et ``tour`` comme
l'atelier (``normaliserObjets``, ``normaliserTour``). Un carnet écrit par
l'atelier est déjà normalisé, et la vérification d'empreinte porte sur le
feuillet tel qu'il est lu ; un carnet écrit ici porte ``objets: []`` et une
Tour vide. Les lectures de jeu ne sont pas des preuves (Eidos, § « Figures
≠ preuves »).

Ici, le carnet est un **format d'échange**, pas le stockage : la voûte Eidolon
range l'état du coffre ailleurs et redérive la graine maîtresse, qui
n'apparaît que dans le carnet exporté.
"""
from __future__ import annotations

import json
import math
from typing import Any, Dict, Union

from . import wots
from .preuve import est_entier, sha256d

KIND_CARNET = "eidos-carnet/1"
TAG_CARNET = "eidos-carnet/1"
EXT_CARNET = ".carnet"
NOM_CARNET = "eidos.carnet"
NOMS_CARNET = ("eidos.carnet", "carnet.eidos", "eidos.carnet.json")
SIG_CARNET = "lamport-sha256"
ALG_CARNET = "sha256d"

NOMS_AGES = ("Satya", "Treta", "Dvapara", "Kali")

# Bloc de genèse du journal local (genesis.json, bloc_genese) — le premier
# bloc de la chaîne locale de chaque coffre (chaine.ts, blocGenese).
BLOC_GENESE: Dict[str, Any] = {
    "hauteur": 0,
    "prev": "0" * 64,
    "merkle": "0cd32557985be5c07e3a085862cb951c2f5f1cc46684283a5ed98e9e48ef6d0a",
    "ts": 1756540680,
    "nonce": 470448,
    "bits": 18,
    "hash": "00003d32ffa7a1dc7f1ace8ec08d0c739126ad4449fe004ea772710baec2c7b6",
    "glyphes": ("··· ··· ··· ✚✚○ ·✚· ☽✚✚ ✚✚☽ ☽○✚ ☽☽· ○✚○ ✚·○ ✚✚✚ ·○☽ ☽✚· ✚☽☽ ·✚☽ "
                "✚·· ·☽· ✚○· ·✚· ○✚· ✚☽○ ·○· ☽○☽ ☽☽✚ ○○· ○·○ ·☽○ ✚✚✚ ☽·· ··○ ·✚☽ "
                "☽☽○ ✚○✚ ·☽○ ✚·○ ··☽ ✚☽☽ ✚☽✚ ··☽ ✚·○ ✚☽✚ ○☽·"),
    "motif": "genese",
}


class CarnetError(ValueError):
    """Carnet illisible, rompu ou étranger."""


# ---------------------------------------------------------------------------
# 1. JSON comme JSON.stringify
# ---------------------------------------------------------------------------

def _js(x: Any) -> Any:
    """Prépare une valeur pour une sérialisation identique à JSON.stringify :
    flottants entiers → int, NaN/∞ → null, tuples → listes."""
    if isinstance(x, bool) or x is None or isinstance(x, (str, int)):
        return x
    if isinstance(x, float):
        if math.isnan(x) or math.isinf(x):
            return None
        return int(x) if x == int(x) else x
    if isinstance(x, dict):
        return {str(k): _js(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_js(v) for v in x]
    raise CarnetError(f"valeur non sérialisable : {type(x).__name__}")


def json_js(x: Any) -> str:
    return json.dumps(_js(x), separators=(",", ":"), ensure_ascii=False)


# ---------------------------------------------------------------------------
# 2. Le coffre
# ---------------------------------------------------------------------------

def tour_vide() -> Dict[str, Any]:
    return {
        "etage": 0, "sommet": 0, "depuis": 0,
        "dons": [], "echos": [], "antres": [], "alcoves": [], "bus": [], "elixirs": [],
        "portes": [], "captures": [], "fouilles": [], "liberee": None, "porte": None,
        "capsules": [], "coffres": [], "ascension": None, "veillee": None,
    }


def bloc_genese() -> Dict[str, Any]:
    return dict(BLOC_GENESE)


def coffre_vide(maitre: str, nature: str = "personnel", scenario: str = "vide") -> Dict[str, Any]:
    """Un coffre neuf, dans l'ordre de clés de ``coffreVide`` (wallet.ts)."""
    if nature not in ("atelier", "personnel"):
        raise CarnetError("nature : atelier ou personnel")
    return {
        "maitre": maitre,
        "n": 0,
        "sorties": [],
        "historique": [],
        "scenario": scenario,
        "nature": nature,
        "clesUsees": [],
        "derniereSig": None,
        "chaine": [bloc_genese()],
        "reliques": [],
        "objets": [],
        "philosophale": None,
        "tour": tour_vide(),
    }


def coffre_valide(c: Any) -> bool:
    return (isinstance(c, dict) and isinstance(c.get("maitre"), str)
            and isinstance(c.get("sorties"), list) and est_entier(c.get("n")))


def normaliser(c: Dict[str, Any]) -> Dict[str, Any]:
    """``normaliser`` de carnet.ts, sans renormaliser ``objets`` : les quatre
    champs prennent leur valeur par défaut s'ils manquent, à leur place."""
    out = dict(c)
    out["clesUsees"] = list(c["clesUsees"]) if isinstance(c.get("clesUsees"), list) else []
    out["reliques"] = ([r for r in c["reliques"] if r in NOMS_AGES]
                       if isinstance(c.get("reliques"), list) else [])
    out["objets"] = list(c["objets"]) if isinstance(c.get("objets"), list) else []
    out["philosophale"] = c.get("philosophale", None)
    return out


def feuillet_de(c: Dict[str, Any]) -> Dict[str, Any]:
    """Le feuillet porte tout ce qui engage le coffre ; la jauge voyage à côté."""
    return {k: v for k, v in c.items() if k != "tour"}


def corps_carnet(coffre: Dict[str, Any]) -> Dict[str, Any]:
    f = feuillet_de(normaliser(coffre))
    return {
        "v": 1,
        "kind": KIND_CARNET,
        "alg": ALG_CARNET,
        "sig": SIG_CARNET,
        "feuillet": f,
        "adresse": wots.adresse_de(f["maitre"], f["n"]),
    }


def empreinte_carnet(coffre: Dict[str, Any]) -> str:
    return sha256d((TAG_CARNET + json_js(corps_carnet(coffre))).encode("utf-8")).hex()


def exporter_carnet(coffre: Dict[str, Any]) -> str:
    if not coffre_valide(coffre):
        raise CarnetError("coffre incomplet : maitre, n, sorties")
    corps = corps_carnet(coffre)
    tour = coffre.get("tour")
    return json_js({**corps, "empreinte": empreinte_carnet(coffre),
                    "tour": tour if isinstance(tour, dict) else tour_vide()})


# ---------------------------------------------------------------------------
# 3. Lecture
# ---------------------------------------------------------------------------

Ouverture = Dict[str, Any]   # {coffre, adresse, empreinte} — ou CarnetError


def parser_carnet(raw: Union[str, bytes]) -> Ouverture:
    """Relit un carnet avec la même sévérité que ``parserCarnet`` : version,
    algorithme, signature, feuillet, adresse dérivée, empreinte recomposée."""
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = bytes(raw).decode("utf-8")
        except UnicodeDecodeError:
            raise CarnetError("carnet illisible")
    try:
        j = json.loads(raw)
    except (TypeError, ValueError):
        raise CarnetError("carnet illisible")
    if not isinstance(j, dict):
        raise CarnetError("carnet illisible")
    if j.get("kind") != KIND_CARNET:
        raise CarnetError("ce n'est pas un carnet Eidos")
    if j.get("v") != 1 or j.get("alg") != ALG_CARNET:
        raise CarnetError("version de carnet inconnue")
    if j.get("sig") != SIG_CARNET:
        raise CarnetError("ce carnet n'est pas Lamport-SHA256")
    if not coffre_valide(j.get("feuillet")):
        raise CarnetError("feuillet incomplet")
    feuillet = normaliser(j["feuillet"])
    adresse = wots.adresse_de(feuillet["maitre"], feuillet["n"])
    if j.get("adresse") != adresse:
        raise CarnetError("adresse Lamport rompue — graine et indice ne correspondent pas")
    attendu = empreinte_carnet(feuillet)
    if j.get("empreinte") != attendu:
        raise CarnetError("empreinte rompue — carnet altéré")
    tour = j.get("tour")
    coffre = {**feuillet, "tour": tour if isinstance(tour, dict) else tour_vide()}
    return {"coffre": coffre, "adresse": adresse, "empreinte": attendu}


def est_nom_carnet(nom: str) -> bool:
    n = nom.lower()
    return n in NOMS_CARNET or n.endswith(EXT_CARNET) or n.endswith(".eidos")


__all__ = [
    "KIND_CARNET", "TAG_CARNET", "EXT_CARNET", "NOM_CARNET", "NOMS_CARNET",
    "SIG_CARNET", "ALG_CARNET", "NOMS_AGES", "BLOC_GENESE", "CarnetError",
    "json_js", "tour_vide", "bloc_genese", "coffre_vide", "coffre_valide", "normaliser",
    "feuillet_de", "corps_carnet", "empreinte_carnet", "exporter_carnet", "parser_carnet",
    "est_nom_carnet",
]
