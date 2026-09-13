"""``eidos.carnet`` : écrit ici, lu par l'atelier ; écrit par l'atelier, lu ici.

Les deux fixtures de ``tests/fixtures/eidos/`` ont été produites le 2026-09-13 :
``carnet_eidolon.json`` par ``exporter_carnet`` et **ouvert sans refus par
``ouvrirFichier`` de l'atelier** (carnet.ts, commit 2637c97), qui l'a
réexporté à l'octet identique ; ``carnet_atelier.json`` par ``exporterCarnet``
de l'atelier, avec un objet porté et une Tour entamée. Les tests ci-dessous
rejouent ces deux sens sans Node.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.protocols.eidos_witness import carnet as C
from src.protocols.eidos_witness import etat as ET
from src.protocols.eidos_witness import wots as W

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "eidos"
MAITRE = "ab" * 32


def _coffre_fixture():
    c = C.coffre_vide(MAITRE)
    c["n"] = 2
    c["sorties"] = [{"ref": "aa" * 32 + ":0", "txid": "aa" * 32, "rang": 0,
                     "adresse": "11" * 20, "indice": 0, "montant": 5}]
    c["clesUsees"] = ["cc" * 32]
    c["reliques"] = ["Kali", "Bidon"]
    return c


def test_export_reproduit_la_fixture_eidolon():
    attendu = (FIXTURES / "carnet_eidolon.json").read_text(encoding="utf-8")
    assert C.exporter_carnet(_coffre_fixture()) == attendu


def test_fixture_atelier_se_relit_et_se_reexporte_a_l_octet():
    raw = (FIXTURES / "carnet_atelier.json").read_text(encoding="utf-8")
    o = C.parser_carnet(raw)
    coffre = o["coffre"]
    assert coffre["maitre"] == "cd" * 32
    assert coffre["n"] == 8 and len(coffre["sorties"]) == 8
    assert len(coffre["objets"]) == 1 and coffre["objets"][0]["archetype"] == "lune"
    assert coffre["tour"]["etage"] == 5 and coffre["tour"]["sommet"] == 9
    assert coffre["reliques"] == ["Satya"]
    assert o["adresse"] == W.adresse_de(coffre["maitre"], coffre["n"])
    assert C.exporter_carnet(coffre) == raw
    assert C.parser_carnet(raw.encode("utf-8"))["empreinte"] == o["empreinte"]


def test_fixture_eidolon_se_relit():
    raw = (FIXTURES / "carnet_eidolon.json").read_text(encoding="utf-8")
    o = C.parser_carnet(raw)
    assert o["coffre"]["reliques"] == ["Kali"]          # « Bidon » filtré à l'écriture
    assert o["coffre"]["chaine"][0] == C.BLOC_GENESE
    assert o["coffre"]["tour"] == C.tour_vide()


@pytest.mark.parametrize("altere", [
    lambda j: j["feuillet"].__setitem__("n", 99),
    lambda j: j["feuillet"]["sorties"][0].__setitem__("montant", 6),
    lambda j: j["feuillet"].__setitem__("maitre", "ef" * 32),
    lambda j: j["feuillet"]["clesUsees"].append("dd" * 32),
    lambda j: j.__setitem__("empreinte", "00" * 32),
    lambda j: j.__setitem__("adresse", "00" * 20),
])
def test_alteration_refusee(altere):
    j = json.loads((FIXTURES / "carnet_atelier.json").read_text(encoding="utf-8"))
    altere(j)
    with pytest.raises(C.CarnetError):
        C.parser_carnet(json.dumps(j))


def test_la_tour_est_hors_empreinte():
    j = json.loads((FIXTURES / "carnet_atelier.json").read_text(encoding="utf-8"))
    j["tour"]["etage"] = 77
    o = C.parser_carnet(json.dumps(j))
    assert o["coffre"]["tour"]["etage"] == 77


@pytest.mark.parametrize("raw, motif", [
    ("pas du json", "illisible"),
    ("[]", "illisible"),
    ('{"kind": "autre"}', "pas un carnet"),
    ('{"kind": "eidos-carnet/1", "v": 2, "alg": "sha256d"}', "version"),
    ('{"kind": "eidos-carnet/1", "v": 1, "alg": "sha256d", "sig": "ecdsa"}', "Lamport"),
    ('{"kind": "eidos-carnet/1", "v": 1, "alg": "sha256d", "sig": "lamport-sha256", "feuillet": {}}', "incomplet"),
])
def test_formes_refusees(raw, motif):
    with pytest.raises(C.CarnetError, match=motif):
        C.parser_carnet(raw)


def test_json_comme_javascript():
    assert C.json_js({"a": 1.0, "b": [1, 2.5, None, True], "c": "é ☽"}) == '{"a":1,"b":[1,2.5,null,true],"c":"é ☽"}'
    assert C.json_js(float("nan")) == "null"
    with pytest.raises(C.CarnetError):
        C.json_js({"x": object()})


def test_normaliser_garde_l_ordre_des_cles():
    c = {"maitre": "m", "n": 0, "sorties": [], "clesUsees": ["x"], "autre": 1}
    n = C.normaliser(c)
    assert list(n.keys()) == ["maitre", "n", "sorties", "clesUsees", "autre", "reliques", "objets", "philosophale"]
    assert n["clesUsees"] == ["x"] and n["philosophale"] is None


def test_coffre_vide_a_la_forme_de_l_atelier():
    c = C.coffre_vide(MAITRE)
    assert list(c.keys()) == ["maitre", "n", "sorties", "historique", "scenario", "nature",
                              "clesUsees", "derniereSig", "chaine", "reliques", "objets",
                              "philosophale", "tour"]
    assert c["nature"] == "personnel" and c["chaine"][0]["motif"] == "genese"
    with pytest.raises(C.CarnetError):
        C.coffre_vide(MAITRE, nature="autre")
    o = C.parser_carnet(C.exporter_carnet(c))
    assert o["adresse"] == W.adresse_de(MAITRE, 0)
    assert C.est_nom_carnet("eidos.carnet") and C.est_nom_carnet("X.EIDOS") and not C.est_nom_carnet("a.psnx")


# ---------------------------------------------------------------------------
# etat.json → sorties d'un coffre
# ---------------------------------------------------------------------------

def test_sorties_du_coffre_depuis_un_etat():
    a0, a1, a9 = W.adresse_de(MAITRE, 0), W.adresse_de(MAITRE, 1), W.adresse_de(MAITRE, 9)
    brut = {
        "spec": "eidos-etat/1", "hauteur": 12, "tete": "ab" * 32, "maj_unix": 1, "invariant": True,
        "sorties": {
            "aa" * 32 + ":0": {"adresse": a0, "montant": 5},
            "aa" * 32 + ":1": {"adresse": "ff" * 20, "montant": 7},
            "bb" * 32 + ":0": {"adresse": a1, "montant": 9},
            "cc" * 32 + ":0": {"adresse": a9, "montant": 1},            # au-delà de n + marge
            "dd" * 32 + ":x": {"adresse": a0, "montant": 1},            # rang illisible
            "ee" * 32 + ":0": {"adresse": a0, "montant": 0},            # montant nul
            "zz" * 32 + ":0": {"adresse": a0, "montant": 1},            # txid non hex
        },
        "soldes": {a0: 5, "bad": 1},
    }
    e = ET.parser_etat(brut)
    assert e.hauteur == 12 and e.invariant is True and len(e.sorties) == 4
    assert e.soldes == {a0: 5}
    s = ET.sorties_du_coffre(e, MAITRE, 0)
    assert [x["indice"] for x in s] == [0, 1]
    assert s[0]["ref"] == "aa" * 32 + ":0" and ET.solde(s) == 14
    assert ET.prochain_indice(s, 0) == 2
    assert [x["indice"] for x in ET.sorties_du_coffre(e, MAITRE, 2, marge=8)] == [0, 1, 9]
    assert ET.parser_etat("rien").hauteur == -1
