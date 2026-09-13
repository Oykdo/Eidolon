"""Arbre à sommes : la conservation, prouvable feuille par feuille."""
from __future__ import annotations

import pytest

from src.protocols.sphere_ledger import slh_dsa
from src.protocols.sphere_ledger import checkpoint as cp

CAPS = {"common": 5, "rare": 2, "mythic": 1}


def _leaves(burn_one=False):
    ls = [cp.SphereLeaf(f"COMMON_{i}", "common", f"{i:064x}", True) for i in range(5)]
    ls += [cp.SphereLeaf("RARE_0", "rare", "a" * 64, True), cp.SphereLeaf("RARE_1", "rare", "b" * 64, not burn_one)]
    ls += [cp.SphereLeaf("MYTHIC_0", "mythic", "c" * 64, True)]
    return ls


def test_totals_equal_caps_when_everything_is_alive():
    t = cp.SumTree(_leaves())
    assert t.totals == CAPS
    ok, errs = cp.conservation_ok(t.totals, {}, CAPS)
    assert ok, errs


def test_burn_moves_a_unit_from_alive_to_burned():
    t = cp.SumTree(_leaves(burn_one=True))
    assert t.totals == {"common": 5, "rare": 1, "mythic": 1}
    assert cp.conservation_ok(t.totals, {"rare": 1}, CAPS)[0]
    # Oublier de compter le brûlage ne casse rien ; en inventer un de trop, si.
    assert not cp.conservation_ok(t.totals, {"rare": 2}, CAPS)[0]


def test_inflation_is_caught():
    extra = _leaves() + [cp.SphereLeaf("MYTHIC_1", "mythic", "d" * 64, True)]
    t = cp.SumTree(extra)
    ok, errs = cp.conservation_ok(t.totals, {}, CAPS)
    assert not ok and "mythic" in errs[0]


def test_duplicate_sphere_is_refused():
    with pytest.raises(ValueError):
        cp.SumTree(_leaves() + [cp.SphereLeaf("RARE_0", "rare", "z" * 64, True)])


def test_proof_recomputes_root_and_totals():
    t = cp.SumTree(_leaves())
    for leaf in t.leaves:
        p = t.prove(leaf.sphere_id)
        assert cp.verify_proof(p, t.root, t.totals), leaf.sphere_id
    # Mêmes feuilles, une tête différente : autre racine, la preuve ne passe plus.
    other = cp.SumTree([cp.SphereLeaf(l.sphere_id, l.rarity, l.head if l.sphere_id != "RARE_0" else "e" * 64, l.alive)
                        for l in _leaves()])
    assert other.root != t.root
    assert not cp.verify_proof(t.prove("RARE_0"), other.root, other.totals)
    # Une preuve valide contre des totaux gonflés échoue : la somme fait partie de la preuve.
    assert not cp.verify_proof(t.prove("RARE_0"), t.root, {**t.totals, "mythic": 2})


def test_negative_counts_are_refused():
    assert not cp.conservation_ok({"mythic": 2}, {"mythic": -1}, CAPS)[0], "un brûlé négatif masquerait un dépassement"
    assert not cp.conservation_ok({"mythic": -3}, {}, CAPS)[0]
    assert cp.conservation_ok({"mythic": 0}, {"rare": 0}, CAPS)[0]


def test_proof_is_bound_to_the_leaf_it_names():
    t = cp.SumTree(_leaves())
    p = t.prove("RARE_0")
    assert p.leaf.sphere_id == "RARE_0" and cp.verify_proof(p, t.root, t.totals)
    # Réétiqueter la preuve (autre identifiant, autre rareté, autre tête, brûlée) : refusée,
    # parce que le vérifieur rehache la feuille annoncée au lieu de croire un hachage fourni.
    for changed in (cp.SphereLeaf("RARE_9", "rare", p.leaf.head, True),
                    cp.SphereLeaf("RARE_0", "mythic", p.leaf.head, True),
                    cp.SphereLeaf("RARE_0", "rare", "e" * 64, True),
                    cp.SphereLeaf("RARE_0", "rare", p.leaf.head, False)):
        assert not cp.verify_proof(cp.SumProof(changed, p.index, p.siblings), t.root, t.totals), changed
    # Un nœud interne présenté comme feuille : le domaine de hachage des feuilles l'exclut.
    inner_hash, _ = t._levels[1][0]
    fake = cp.SumProof(cp.SphereLeaf("X", "rare", inner_hash.hex(), True), 0, p.siblings[1:])
    assert not cp.verify_proof(fake, t.root, t.totals)
    # Aller-retour JSON, et une preuve malformée est refusée sans exception.
    assert cp.verify_proof(cp.SumProof.from_dict(p.to_dict()), t.root, t.totals)
    with pytest.raises(ValueError):
        cp.SumProof.from_dict({"leaf": p.leaf.to_dict(), "index": 0, "siblings": [["zz", {"rare": -1}, "L"]]})
    assert not cp.verify_proof(cp.SumProof(p.leaf, p.index, [("zz", {}, "L")]), t.root, t.totals)


def test_checkpoint_round_trip_refuses_negative_or_missing_counts():
    anchor = slh_dsa.SlhDsaKeyPair.generate()
    t = cp.SumTree(_leaves())
    c = cp.Checkpoint.issue(anchor, "eidolon-vps", 1, t, {}, "2026-09-12T12:00:00Z")
    again = cp.Checkpoint.from_dict(c.to_dict())
    assert again.verify(anchor.public_key) and again.record_hash == c.record_hash
    with pytest.raises(ValueError):
        cp.Checkpoint.from_dict({**c.to_dict(), "burned": {"rare": -1}})
    with pytest.raises(ValueError):
        cp.Checkpoint.from_dict({**c.to_dict(), "checkpoint_seq": "1"})


def test_order_of_input_does_not_change_the_root():
    a = cp.SumTree(_leaves())
    b = cp.SumTree(list(reversed(_leaves())))
    assert a.root == b.root


def test_checkpoint_is_signed_and_verifiable():
    anchor = slh_dsa.SlhDsaKeyPair.generate()
    t = cp.SumTree(_leaves(burn_one=True))
    c = cp.Checkpoint.issue(anchor, "eidolon-vps", 1, t, {"rare": 1}, "2026-09-12T12:00:00Z")
    assert c.verify(anchor.public_key)
    assert c.totals == t.totals and c.root == t.root.hex()
    c.totals = {**c.totals, "mythic": 2}
    assert not c.verify(anchor.public_key), "les totaux font partie de ce qui est signé"
