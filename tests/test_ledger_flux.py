"""Théorème de la divergence : ce qui traverse la frontière égale ce qui naît dedans.

Un petit monde de trois voûtes et quatre sphères, des vrais enregistrements
(frappe SLH-DSA, garde WOTS+) : le bilan d'un volume prédit exactement la
variation de ses avoirs, sur le volume total comme sur n'importe quelle
voûte seule ; une frappe hors racine est un monopôle ; une sphère comptée
deux fois viole l'exclusion ; un burn est un puits, un transfert ne crée
rien.

SLH-DSA signe en ~2 s : une clé d'émetteur et une clé d'ancre pour le module.
"""
from __future__ import annotations

import copy

import pytest

from src.protocols.sphere_ledger import slh_dsa
from src.protocols.sphere_ledger import checkpoint as cp
from src.protocols.sphere_ledger import flux as fx
from src.protocols.sphere_ledger import ledger as sl

CAPS = {"common": 4, "rare": 2, "mythic": 1}
A, B, C = "aa" * 32, "bb" * 32, "cc" * 32
T0 = "2026-09-13T10:00:00Z"


def _template(sphere_id, rarity):
    return {"sphereId": sphere_id, "rarity": rarity, "theme": "verre", "createdAt": T0}


@pytest.fixture(scope="module")
def issuer():
    return slh_dsa.SlhDsaKeyPair.generate()


@pytest.fixture(scope="module")
def anchor():
    return slh_dsa.SlhDsaKeyPair.generate()


@pytest.fixture(scope="module")
def world(issuer):
    """Quatre sphères frappées : deux communes pour A, une rare pour A, une mythic pour B.
    Puis : la rare va de A à B, une commune de A à C, la mythic est brûlée par B."""
    keys = {}
    spheres = {}
    for sid, rarity, idx, vault in (("COMMON_0", "common", 0, A), ("COMMON_1", "common", 1, A),
                                    ("RARE_0", "rare", 0, A), ("MYTHIC_0", "mythic", 0, B)):
        k = sl.ReceiverKey()
        m = sl.mint(issuer, sphere_id=sid, rarity=rarity, index=idx, template=_template(sid, rarity),
                    vault_id=vault, first_key=k, anchor_id="eidolon-vps", caps=CAPS, issued_at=T0)
        keys[sid] = k
        spheres[sid] = sl.SphereFile(mint=m)
    genesis_ids = set(spheres)
    # mouvements
    kb = sl.ReceiverKey()
    spheres["RARE_0"].custody.append(sl.sign_custody(spheres["RARE_0"].mint, keys["RARE_0"], to_vault_id=B,
                                                     next_key_root=kb.ots_root, issued_at=T0))
    kc = sl.ReceiverKey()
    spheres["COMMON_1"].custody.append(sl.sign_custody(spheres["COMMON_1"].mint, keys["COMMON_1"], to_vault_id=C,
                                                       next_key_root=kc.ots_root, issued_at=T0))
    spheres["MYTHIC_0"].custody.append(sl.sign_custody(spheres["MYTHIC_0"].mint, keys["MYTHIC_0"], to_vault_id=None,
                                                       next_key_root=None, reason="burn", issued_at=T0))
    return spheres, genesis_ids


def _events(spheres, after_seq=-1):
    return [e for s in spheres.values() for e in fx.events_from_sphere(s, after_seq=after_seq)]


def test_total_volume_variation_is_mints_minus_burns(world):
    spheres, _ = world
    events = _events(spheres)
    b = fx.flux_balance(events, None)
    assert b.inflow == {} and b.outflow == {}, "le volume total n'a pas de frontière"
    assert b.minted == {"common": 2, "rare": 1, "mythic": 1}
    assert b.burned == {"mythic": 1}
    after = fx.volume_totals(spheres.values(), None)
    assert after == {"common": 2, "rare": 1}
    assert fx.divergence_ok({}, after, b) == (True, [])


def test_each_vault_alone_satisfies_the_theorem(world):
    spheres, _ = world
    events = _events(spheres)
    expected = {A: {"common": 1}, B: {"rare": 1}, C: {"common": 1}}
    for v in (A, B, C):
        b = fx.flux_balance(events, {v})
        after = fx.volume_totals(spheres.values(), {v})
        assert after == expected[v], v
        ok, errs = fx.divergence_ok({}, after, b)
        assert ok, (v, errs)
    # Le bilan de A dit précisément ce qui s'est passé : 3 frappées, 2 sorties, 0 entrée.
    b = fx.flux_balance(events, {A})
    assert b.minted == {"common": 2, "rare": 1} and b.outflow == {"common": 1, "rare": 1} and b.inflow == {}


def test_union_of_volumes_is_the_sum_of_balances(world):
    spheres, _ = world
    events = _events(spheres)
    ab = fx.flux_balance(events, {A, B})
    # A→B est intérieur au volume {A, B} : ni entrée ni sortie ; seule la commune vers C sort.
    assert ab.outflow == {"common": 1} and ab.inflow == {}
    assert ab.divergence == {"common": 1, "rare": 1}
    assert fx.volume_totals(spheres.values(), {A, B}) == {"common": 1, "rare": 1}


def test_undeclared_source_is_caught(world):
    spheres, _ = world
    b = fx.flux_balance(_events(spheres), None)
    inflated = {"common": 2, "rare": 1, "mythic": 1}     # une mythic de plus que le bilan
    ok, errs = fx.divergence_ok({}, inflated, b)
    assert not ok and "mythic" in errs[0] and "source non déclarée" in errs[0]


def test_double_mint_violates_exclusion(world):
    spheres, _ = world
    events = _events(spheres)
    dup = events + [fx.Event("mint", "RARE_0", "rare", None, C)]
    with pytest.raises(ValueError, match="exclusion"):
        fx.flux_balance(dup, None)


def test_transfer_has_zero_divergence_and_reanchor_moves_nothing(world, issuer):
    spheres, _ = world
    only_moves = [e for e in _events(spheres) if e.kind == "transfer"]
    assert fx.flux_balance(only_moves, None).divergence == {}
    # Un vrai « reanchor » : le registre le refuse s'il change de voûte ; sinon le flux voit
    # la même voûte des deux côtés, donc aucune traversée — registre et flux disent pareil.
    k1 = sl.ReceiverKey()
    m1 = sl.mint(issuer, sphere_id="RARE_1", rarity="rare", index=1, template=_template("RARE_1", "rare"),
                 vault_id=A, first_key=k1, anchor_id="eidolon-vps", caps=CAPS, issued_at=T0)
    with pytest.raises(sl.LedgerError):
        sl.sign_custody(m1, k1, to_vault_id=B, next_key_root=sl.ReceiverKey().ots_root, reason="reanchor",
                        anchor_id="esoptron", issued_at=T0)
    re = sl.sign_custody(m1, k1, to_vault_id=A, next_key_root=sl.ReceiverKey().ots_root, reason="reanchor",
                         anchor_id="esoptron", issued_at=T0)
    s1 = sl.SphereFile(mint=m1, custody=[re])
    assert sl.verify_sphere(s1, issuer_pk=issuer.public_key, caps=CAPS).ok
    ev = fx.events_from_sphere(s1, after_seq=0)
    assert ev == [fx.Event("transfer", "RARE_1", "rare", A, A)] and s1.owner == A
    assert fx.flux_balance(ev, {A}).divergence == {}
    # Une raison inconnue n'est pas un mouvement vers soi : c'est une erreur.
    forged = copy.deepcopy(s1)
    forged.custody[0].reason = "gift"
    with pytest.raises(ValueError):
        fx.events_from_sphere(forged, after_seq=0)
    assert fx.events_from_sphere(spheres["RARE_0"], after_seq=1) == [], "rien après le dernier seq"


def test_remint_of_a_genesis_id_and_wrong_rarity_are_refused(world, anchor):
    spheres, _ = world
    leaves = [cp.SphereLeaf(s.mint.sphere_id, s.mint.rarity, s.head_hash, not s.burned) for s in spheres.values()]
    cp1 = cp.Checkpoint.issue(anchor, "eidolon-vps", 1, cp.SumTree(leaves), {"mythic": 1}, T0)
    cp2 = cp.Checkpoint.issue(anchor, "eidolon-vps", 2, cp.SumTree(leaves), {"mythic": 1}, T0)
    rarity_of = {s.mint.sphere_id: s.mint.rarity for s in spheres.values()}
    assert fx.anchor_invariant(cp1, cp2, [], genesis_ids=rarity_of, caps=CAPS) == (True, [])
    # Re-frapper COMMON_0 dans un intervalle ultérieur, compensé par un brûlage pour tromper
    # Δtotaux : sans mémoire des identifiants déjà comptés, l'invariant passerait.
    remint = [fx.Event("mint", "COMMON_0", "common", None, C), fx.Event("burn", "COMMON_1", "common", A, None)]
    cp2b = cp.Checkpoint.issue(anchor, "eidolon-vps", 2, cp.SumTree(leaves), {"mythic": 1, "common": 1}, T0)
    ok, errs = fx.anchor_invariant(cp1, cp2b, remint, genesis_ids=rarity_of, caps=CAPS,
                                   minted_before=set(rarity_of))
    assert not ok and any("exclusion" in e for e in errs)
    # Sous une autre rareté : la genèse la dit common.
    ok, errs = fx.anchor_invariant(cp1, cp2, [fx.Event("mint", "COMMON_0", "mythic", None, C)],
                                   genesis_ids=rarity_of, caps=CAPS)
    assert not ok and any("monopôle" in e for e in errs)
    # Un point de contrôle précédent qui viole déjà la conservation est refusé aussi.
    cp0 = cp.Checkpoint(anchor_id="eidolon-vps", checkpoint_seq=0, root="00" * 32,
                        totals={"mythic": 2}, burned={}, issued_at=T0)
    ok, errs = fx.anchor_invariant(cp0, cp1, [], genesis_ids=rarity_of, caps=CAPS)
    assert not ok and any("précédent" in e for e in errs)


def test_burn_then_forged_transfer_stays_burned(world):
    spheres, _ = world
    forged = copy.deepcopy(spheres["MYTHIC_0"])
    forged.custody.append(copy.deepcopy(spheres["RARE_0"].custody[0]))
    forged.custody[-1].sphere_id = "MYTHIC_0"
    assert forged.burned, "un burn reste un burn, même si un fichier fabriqué ajoute une tête"
    assert fx.volume_totals([forged], None) == {}


def test_anchor_invariant_between_two_checkpoints(world, anchor):
    spheres, genesis_ids = world
    # Point de contrôle 1 : juste après les frappes (tout vivant, rien brûlé).
    leaves0 = [cp.SphereLeaf(s.mint.sphere_id, s.mint.rarity, s.mint.record_hash.hex(), True) for s in spheres.values()]
    cp1 = cp.Checkpoint.issue(anchor, "eidolon-vps", 1, cp.SumTree(leaves0), {}, T0)
    # Point de contrôle 2 : après les mouvements.
    leaves1 = [cp.SphereLeaf(s.mint.sphere_id, s.mint.rarity, s.head_hash, not s.burned) for s in spheres.values()]
    cp2 = cp.Checkpoint.issue(anchor, "eidolon-vps", 2, cp.SumTree(leaves1), {"mythic": 1}, T0)
    between = _events(spheres, after_seq=0)          # les gardes seulement, la frappe est dans cp1
    ok, errs = fx.anchor_invariant(cp1, cp2, between, genesis_ids=genesis_ids, caps=CAPS)
    assert ok, errs
    # Une frappe hors racine de genèse entre les deux : monopôle.
    rogue = between + [fx.Event("mint", "MYTHIC_1", "mythic", None, C)]
    ok, errs = fx.anchor_invariant(cp1, cp2, rogue, genesis_ids=genesis_ids, caps=CAPS)
    assert not ok and any("monopôle" in e for e in errs)
    # Le point de contrôle 2 qui « oublie » le brûlage : Δbrûlés ≠ brûlages déclarés.
    cp2b = cp.Checkpoint.issue(anchor, "eidolon-vps", 2, cp.SumTree(leaves1), {}, T0)
    ok, errs = fx.anchor_invariant(cp1, cp2b, between, genesis_ids=genesis_ids, caps=CAPS)
    assert not ok and any("brûlés" in e for e in errs)
    # Séquence qui saute : refusé.
    cp3 = cp.Checkpoint.issue(anchor, "eidolon-vps", 3, cp.SumTree(leaves1), {"mythic": 1}, T0)
    ok, errs = fx.anchor_invariant(cp1, cp3, between, genesis_ids=genesis_ids, caps=CAPS)
    assert not ok and any("consécutifs" in e for e in errs)


def test_inflation_beyond_caps_fails_even_with_a_consistent_balance(world, anchor):
    spheres, genesis_ids = world
    caps_small = {"common": 1, "rare": 2, "mythic": 1}      # deux communes frappées : c'est trop
    leaves = [cp.SphereLeaf(s.mint.sphere_id, s.mint.rarity, s.head_hash, not s.burned) for s in spheres.values()]
    cp0 = cp.Checkpoint.issue(anchor, "eidolon-vps", 0, cp.SumTree([]), {}, T0)
    cp1 = cp.Checkpoint.issue(anchor, "eidolon-vps", 1, cp.SumTree(leaves), {"mythic": 1}, T0)
    ok, errs = fx.anchor_invariant(cp0, cp1, _events(spheres), genesis_ids=genesis_ids, caps=caps_small)
    assert not ok and any("plafond" in e for e in errs)
