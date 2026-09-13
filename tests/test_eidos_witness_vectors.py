"""Témoin Eidos : les vecteurs partagés d'Eidos, rejoués ici à l'octet.

``tests/vectors/eidos_vecteurs.json`` est ``vecteurs.json`` d'Oykdo/Eidos
(``eidos-vecteurs/1``, écrit par ``vecteurs.py``, lu par Python et par
l'atelier TypeScript). Ce que ces tests prouvent : le port du témoin donne
les mêmes graines, adresses, signatures, racines et têtes que le nœud —
donc un envoi signé par une voûte Eidolon est un envoi Eidos, et une tête
jugée ici est jugée comme par la page Témoin.

``tests/vectors/eidos_croises.json`` : WOTS+ signé par l'original d'Eidos
vérifié par ``sphere_ledger.hash_sig``, et l'inverse.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.protocols.eidos_witness import envoi as EN
from src.protocols.eidos_witness import preuve as P
from src.protocols.eidos_witness import tete as T
from src.protocols.eidos_witness import wots as W
from src.protocols.eidos_witness import xmss as X
from src.protocols.eidos_witness import actif as A
from src.protocols.sphere_ledger import hash_sig as HS

VECTEURS = Path(__file__).resolve().parent / "vectors" / "eidos_vecteurs.json"
CROISES = Path(__file__).resolve().parent / "vectors" / "eidos_croises.json"


@pytest.fixture(scope="module")
def v():
    return json.loads(VECTEURS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def croises():
    return json.loads(CROISES.read_text(encoding="utf-8"))


def h(s: str) -> bytes:
    return bytes.fromhex(s)


# ---------------------------------------------------------------------------
# spec et paramètres
# ---------------------------------------------------------------------------

def test_spec_et_parametres(v):
    assert v["spec"] == "eidos-vecteurs/1"
    p = v["parametres"]
    assert (p["n"], p["w"], p["len"]) == (W.N, W.W, W.LEN)
    assert p["octets_signature"] == W.OCTETS_SIG == HS.LEN * HS.N
    assert p["octets_temoin"] == W.OCTETS_TEMOIN
    assert p["version_tx"] == EN.VERSION_TX


# ---------------------------------------------------------------------------
# wots : dérivation, adresse, signature, empreinte
# ---------------------------------------------------------------------------

def test_wots_derivation_et_adresse(v):
    w = v["wots"]
    g = W.graine_de(w["maitre"], w["indice"])
    assert g.hex() == w["graine"]
    gp, r = W.racine(g)
    assert gp.hex() == w["graine_publique"]
    assert r.hex() == w["racine_l"]
    assert W.adresse(gp, r).hex() == w["adresse"]
    assert W.empreinte(gp, r).hex() == w["empreinte"]
    assert W.adresse_de(w["maitre"], w["indice"]) == w["adresse"]
    assert W.empreinte_de(w["maitre"], w["indice"]) == w["empreinte"]
    assert W.adresse_de(w["maitre"], 1) == w["adresse_indice_1"]


def test_wots_signature_identique(v):
    w = v["wots"]
    g = W.graine_de(w["maitre"], w["indice"])
    gp, sig = W.signer(g, h(w["message"]))
    assert gp.hex() == w["graine_publique"]
    assert sig.hex() == w["signature"]
    assert W.verifier(h(w["adresse"]), h(w["message"]), (gp, sig))


def test_wots_refus(v):
    w = v["wots"]
    m, adr = h(w["message"]), h(w["adresse"])
    temoin = (h(w["graine_publique"]), h(w["signature"]))
    assert W.verifier(adr, m, temoin)
    faux = bytearray(temoin[1])
    faux[100] ^= 1
    assert not W.verifier(adr, m, (temoin[0], bytes(faux)))
    assert not W.verifier(adr, m, (temoin[0], temoin[1][:-1]))
    assert not W.verifier(adr, hashlib.sha256(b"autre").digest(), temoin)
    assert not W.verifier(adr, m, (hashlib.sha256(b"autre graine").digest(), temoin[1]))
    assert not W.verifier(h(w["adresse_indice_1"]), m, temoin)
    assert W.racine_depuis_temoin(("court", temoin[1]), m) is None
    assert W.racine_depuis_temoin(None, m) is None


def test_graine_de_refuse_les_formes_fausses():
    with pytest.raises(ValueError):
        W.graine_de("", 0)
    with pytest.raises(ValueError):
        W.graine_de("x", -1)
    with pytest.raises(ValueError):
        W.graine_de("x", True)
    assert W.est_graine_hex256("ab" * 32)
    assert not W.est_graine_hex256("AB" * 32)
    assert not W.est_graine_hex256("eidos-atelier-reseau-essai-v1")


# ---------------------------------------------------------------------------
# WOTS+ croisé : Eidos ↔ sphere_ledger.hash_sig
# ---------------------------------------------------------------------------

def test_croise_eidos_signe_hash_sig_verifie(croises):
    f = croises["eidos_signe_eidolon_verifie"]
    pk = HS.WotsPublicKey(seed=h(f["graine_publique"]), ots_index=0, root=h(f["racine_l"]))
    sig = HS.WotsSignature.from_bytes(h(f["signature"]))
    assert HS.verify(pk, h(f["message"]), sig)
    assert HS.public_key_from_signature(sig, h(f["message"]), pk.seed, 0) == pk.root
    # et le port en refait autant, à partir de la graine
    g = W.graine_de(f["maitre"], f["indice"])
    assert g.hex() == f["graine"]
    assert W.signer(g, h(f["message"]))[1].hex() == f["signature"]


def test_croise_hash_sig_signe_eidos_verifie(croises):
    f = croises["eidolon_signe_eidos_verifie"]
    kp = HS.WotsKeyPair(secret_seed=h(f["secret_seed"]), public_seed=h(f["public_seed"]),
                        ots_index=f["ots_index"])
    assert kp.public_key.root.hex() == f["root"]
    assert kp.sign(h(f["message"])).to_bytes().hex() == f["signature"]
    temoin = (h(f["public_seed"]), h(f["signature"]))
    assert W.adresse(temoin[0], h(f["root"])).hex() == f["adresse"]
    assert W.verifier(h(f["adresse"]), h(f["message"]), temoin)


def test_croise_a_la_volee():
    """Sans vecteur figé : une signature hash_sig se vérifie par le port, et
    une signature du port par hash_sig, sur des clés fraîches."""
    m = hashlib.sha256(b"a la volee").digest()
    kp = HS.WotsKeyPair(secret_seed=b"\x07" * 32, public_seed=b"\x08" * 32)
    s = kp.sign(m)
    assert W.verifier(W.adresse(kp.public_seed, kp.public_key.root), m, (kp.public_seed, s.to_bytes()))
    g = W.graine_de("volee", 5)
    gp, r = W.racine(g)
    gp2, sig = W.signer(g, m)
    assert HS.verify(HS.WotsPublicKey(seed=gp, ots_index=0, root=r), m, HS.WotsSignature.from_bytes(sig))


# ---------------------------------------------------------------------------
# xmss
# ---------------------------------------------------------------------------

def test_xmss_vecteur(v):
    x = v["xmss"]
    s = x["signature"]
    sig = (s["indice"], h(s["wots"]), [h(c) for c in s["chemin"]])
    assert X.verifier_mss(h(x["racine"]), h(x["graine_publique"]), x["hauteur"], h(x["message"]), sig)
    # feuille 0 : arbre L de la clé impliquée
    pk = W.cle_depuis_signature(h(s["wots"]), h(x["graine_publique"]), X.ad_ots(0), h(x["message"]))
    assert W.arbre_l(pk, h(x["graine_publique"]), X.ad_l(0)).hex() == x["feuille_0"]


def test_xmss_refus(v):
    x = v["xmss"]
    s = x["signature"]
    racine, gp, hauteur, m = h(x["racine"]), h(x["graine_publique"]), x["hauteur"], h(x["message"])
    chemin = [h(c) for c in s["chemin"]]
    assert not X.verifier_mss(racine, gp, hauteur, m, (s["indice"] + 1, h(s["wots"]), chemin))
    assert not X.verifier_mss(racine, gp, hauteur, m, (s["indice"], h(s["wots"]), chemin[:-1]))
    assert not X.verifier_mss(racine, gp, hauteur, m, (1 << hauteur, h(s["wots"]), chemin))
    assert not X.verifier_mss(racine, gp, hauteur, hashlib.sha256(b"x").digest(), (s["indice"], h(s["wots"]), chemin))
    faux = list(chemin)
    faux[0] = bytes(32)
    assert not X.verifier_mss(racine, gp, hauteur, m, (s["indice"], h(s["wots"]), faux))
    assert not X.verifier_mss(racine, gp, hauteur, m, "pas une signature")
    assert not X.verifier_mss(racine, gp, hauteur, m, (True, h(s["wots"]), chemin))


# ---------------------------------------------------------------------------
# carnet (racine UTXO) et preuves
# ---------------------------------------------------------------------------

def test_utxo_root_vecteur(v):
    c = v["carnet"]
    assert [P.feuille_de(s).hex() for s in c["sorties"]] == c["feuilles"]
    assert P.utxo_root(c["sorties"]).hex() == c["utxo_root"]
    assert P.merkle_root([]) == bytes(32)


def test_preuves_de_toutes_les_feuilles(v):
    c = v["carnet"]
    feuilles = [P.feuille_de(s) for s in P.ordre_canonique(c["sorties"])]
    for i in range(len(feuilles)):
        pr = P.preuve_de(feuilles, i)
        assert pr is not None and pr["racine"] == c["utxo_root"]
        assert P.verifier_preuve(pr)
        assert P.juger(c["utxo_root"], pr) == ("incluse", "incluse")
    assert P.preuve_de(feuilles, len(feuilles)) is None
    assert P.preuve_de(feuilles, -1) is None


def test_preuve_refus(v):
    c = v["carnet"]
    pr = P.preuve_reseau(c["sorties"], f"{c['sorties'][0]['txid']}:0")
    assert pr is not None
    assert P.juger(None, pr)[0] == "aveugle"
    assert P.juger("ff" * 32, pr)[0] == "etrangere"
    rompue = json.loads(json.dumps(pr))
    rompue["freres"][0]["cote"] = "gauche" if rompue["freres"][0]["cote"] == "droite" else "droite"
    assert P.juger(c["utxo_root"], rompue)[0] == "rompue"
    assert P.parser_preuve({"v": 2})[0] is None
    assert P.parser_preuve({"v": 1, "feuille": "00", "racine": "00" * 32, "freres": []})[0] is None
    assert P.parser_preuve({"v": 1, "feuille": "00" * 32, "racine": "00" * 32, "freres": [{"cote": "haut", "hash": "00" * 32}]})[0] is None
    assert P.preuve_reseau(c["sorties"], "ff" * 32 + ":0") is None


# ---------------------------------------------------------------------------
# tête signée
# ---------------------------------------------------------------------------

def test_tete_vecteur(v):
    te = v["tete"]
    fed = T.Federation.depuis(te["federation"])
    tete = T.TeteSignee.depuis(te["tete_signee"])
    assert T.id_bloc(tete) == tete.id_bloc
    assert len(T.entete_federe(tete)) == 120
    verdict = T.verifier_tete(tete, fed)
    assert verdict.ok, verdict.detail
    assert P.utxo_root(te["sorties"]).hex() == te["tete_signee"]["utxo_root"]
    assert tete.to_dict() == te["tete_signee"]


def test_tete_refus(v):
    te = v["tete"]
    fed = T.Federation.depuis(te["federation"])
    base = te["tete_signee"]
    for champ, valeur in (("hauteur", base["hauteur"] + 1), ("ts", base["ts"] + 1),
                          ("utxo_root", "00" * 32), ("prev", "11" * 32), ("merkle", "22" * 32)):
        t = T.TeteSignee.depuis({**base, champ: valeur})
        assert not T.verifier_tete(t, fed).ok, champ
    # id_bloc recomposé mais signature d'un autre validateur
    t = T.TeteSignee.depuis({**base, "validateur": (base["validateur"] + 1) % fed.n})
    assert "signature" in T.verifier_tete(t, fed).detail
    t = T.TeteSignee.depuis({**base, "validateur": 99})
    assert "hors" in T.verifier_tete(t, fed).detail
    t = T.TeteSignee.depuis({**base, "indice": base["indice"] + 1})
    assert not T.verifier_tete(t, fed).ok
    with pytest.raises(T.TeteError):
        T.TeteSignee.depuis({**base, "signature": "00"})
    with pytest.raises(T.TeteError):
        T.TeteSignee.depuis({**base, "chemin": ["zz"]})


def test_federation_refus(v):
    f = dict(v["tete"]["federation"])
    with pytest.raises(T.TeteError):
        T.Federation.depuis({**f, "racines": f["racines"][:1] + f["racines"][:2]})   # n = 3
    with pytest.raises(T.TeteError):
        T.Federation.depuis({**f, "graines_publiques": f["graines_publiques"][:-1]})
    with pytest.raises(T.TeteError):
        T.Federation.depuis({**f, "hauteur_mss": 0})
    with pytest.raises(T.TeteError):
        T.Federation.depuis("non")


def test_proposant_du_creneau(v):
    """Avec t0 et créneau, le validateur doit être le proposant V[(3·s) mod n]."""
    te = v["tete"]
    base = te["tete_signee"]
    f = dict(te["federation"])
    s = 5
    f.update({"t0_unix": base["ts"] - s * 600, "creneau_s": 600, "pas_rotation": 3})
    fed = T.Federation.depuis(f)
    assert fed.creneau(base["ts"]) == s
    attendu = fed.proposant(s)
    tete = T.TeteSignee.depuis(base)
    verdict = T.verifier_tete(tete, fed)
    if attendu == base["validateur"]:
        assert verdict.ok
    else:
        assert not verdict.ok and "proposant" in verdict.detail
        assert T.verifier_tete(tete, fed, verifier_proposant=False).ok


# ---------------------------------------------------------------------------
# transaction
# ---------------------------------------------------------------------------

def test_tx_vecteur(v):
    tx, w = v["tx"], v["wots"]
    core = EN.core_tx([(h(e["txid"]), e["vout"]) for e in tx["entrees"]],
                      [(h(s["adresse"]), s["atomes"]) for s in tx["sorties"]])
    assert core.hex() == tx["core"]
    assert EN.txid_core(core).hex() == tx["txid"]
    assert EN.sighash(h(tx["txid"]), 0).hex() == tx["sighash_0"]
    entrees = [{"ref": tx["entrees"][0]["txid"] + ":0", "txid": tx["entrees"][0]["txid"], "rang": 0,
                "adresse": w["adresse"], "indice": w["indice"], "montant": 1234}]
    signe = EN.signer_entrees(w["maitre"], entrees, h(tx["sorties"][0]["adresse"]),
                              tx["sorties"][0]["atomes"], tx["sorties"][1]["atomes"], 1)
    assert signe.txid == tx["txid"]
    assert signe.adresse_rendu == tx["sorties"][1]["adresse"] == w["adresse_indice_1"]
    assert signe.temoins[0][0].hex() == tx["temoin_0"]["graine_publique"]
    assert signe.temoins[0][1].hex() == tx["temoin_0"]["signature"]
    assert signe.empreintes == [w["empreinte"]]
    assert len(signe.octets) == tx["ser_tx_longueur"]
    assert hashlib.sha256(signe.octets).hexdigest() == tx["ser_tx_sha256"]
    assert signe.texte.startswith(EN.DEBUT + "\n") and signe.texte.endswith(EN.FIN + "\n")
    assert all(len(ligne) <= 76 for ligne in signe.texte.splitlines())
    assert EN.desencapsuler(signe.texte) == signe.octets
    assert EN.deser_tx(signe.octets) == (core, signe.temoins)
    assert EN.verifier_envoi(signe.octets, [w["adresse"]]) == (True, tx["txid"])


def test_tx_refus(v):
    tx, w = v["tx"], v["wots"]
    entrees = [{"txid": tx["entrees"][0]["txid"], "rang": 0, "adresse": w["adresse_indice_1"],
                "indice": w["indice"], "montant": 1234}]
    with pytest.raises(EN.EnvoiError):      # clé d'indice 0 pour l'adresse d'indice 1
        EN.signer_entrees(w["maitre"], entrees, h(tx["sorties"][0]["adresse"]), 10)
    with pytest.raises(EN.EnvoiError):
        EN.signer_entrees(w["maitre"], [], h(tx["sorties"][0]["adresse"]), 10)
    with pytest.raises(EN.EnvoiError):
        EN.desencapsuler("rien")
    with pytest.raises(EN.EnvoiError):
        EN.deser_tx(b"\x00\x00\x00\x10abc")
    bon = EN.signer_entrees(w["maitre"], [{**entrees[0], "adresse": w["adresse"]}],
                            h(tx["sorties"][0]["adresse"]), 10)
    assert EN.verifier_envoi(bon.octets, [w["adresse_indice_1"]])[0] is False
    altere = bytearray(bon.octets)
    altere[-1] ^= 1
    assert EN.verifier_envoi(bytes(altere), [w["adresse"]])[0] is False


# ---------------------------------------------------------------------------
# dossier d'actif, depuis la famille tete
# ---------------------------------------------------------------------------

def test_actif_depuis_vecteur_tete(v):
    te = v["tete"]
    fed = T.Federation.depuis(te["federation"])
    for so in te["sorties"]:
        ref = f"{so['txid']}:{so['rang']}"
        pr = P.preuve_reseau(te["sorties"], ref)
        d = A.dossier(tete=te["tete_signee"], sortie=so, preuve=pr, genre="piece", indice=None)
        assert A.identifiant(d) == ref
        verdict = A.juger_actif(d, fed)
        assert verdict.ok and verdict.code == "incluse" and verdict.hauteur == te["tete_signee"]["hauteur"]
        # sortie changée : la feuille n'est plus celle de la sortie
        assert A.juger_actif({**d, "sortie": {**so, "montant": so["montant"] + 1}}, fed).code == "rompue"
        # racine étrangère
        assert A.juger_actif({**d, "preuve": {**pr, "racine": "ff" * 32}}, fed).code in ("rompue", "etrangere")
        # tête d'une autre fédération
        autre = dict(te["federation"])
        autre["racines"] = autre["racines"][1:] + autre["racines"][:1]   # tourne, ne renverse pas
        assert A.juger_actif(d, T.Federation.depuis(autre)).code == "tete"
        assert A.juger_actif({**d, "format": "AUTRE"}, fed).code == "forme"
        assert A.juger_actif("non", fed).code == "forme"
