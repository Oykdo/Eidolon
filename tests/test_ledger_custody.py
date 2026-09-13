"""Registre de garde : ce qui passe, et surtout ce qui doit échouer.

Une chaîne valide de trois sauts passe. Puis chaque attaque que le registre
promet de refuser est jouée : rejeu, réordonnancement, double dépense vue
comme fourche, racine suivante alterée, mauvais signataire, trou de seq,
enregistrement apres un burn, frappe hors plafond, frappe non signée par
l'émetteur, reçu d'une ancre inconnue (en attente) contre reçu d'une ancre
connue (final).

SLH-DSA signe en ~2 s : une seule clé d'émetteur et une seule d'ancre pour
tout le module.
"""
from __future__ import annotations

import copy

import pytest

from src.protocols.sphere_ledger import slh_dsa
from src.protocols.sphere_ledger import ledger as sl

CAPS = {"common": 10, "rare": 3, "mythic": 1}
TEMPLATE = {"sphereId": "RARE_007", "index": 7, "rank": 3, "theme": "verre", "rarity": "rare",
            "baseRewardRatio": 1.4, "evolutionCycles": 6, "createdAt": "2026-09-12T10:00:00Z"}
A, B, C = "aa" * 32, "bb" * 32, "cc" * 32


@pytest.fixture(scope="module")
def issuer():
    return slh_dsa.SlhDsaKeyPair.generate()


@pytest.fixture(scope="module")
def anchor():
    return slh_dsa.SlhDsaKeyPair.generate()


@pytest.fixture(scope="module")
def minted(issuer):
    """Une sphère frappée pour A, avec la clé qui permet à A de la céder."""
    key_a = sl.ReceiverKey()
    m = sl.mint(issuer, sphere_id="RARE_007", rarity="rare", index=1, template=TEMPLATE,
                vault_id=A, first_key=key_a, anchor_id="eidolon-vps", caps=CAPS,
                issued_at="2026-09-12T10:00:00Z")
    return m, key_a


@pytest.fixture(scope="module")
def chain(minted):
    """A -> B -> C, construite UNE fois : chaque clé WOTS+ ne signe qu'une fois,
    donc un test qui veut muter la chaîne en prend une copie."""
    m, key_a = minted
    key_b, key_c = sl.ReceiverKey(), sl.ReceiverKey()
    c1 = sl.sign_custody(m, key_a, to_vault_id=B, next_key_root=key_b.ots_root, issued_at="2026-09-12T11:00:00Z")
    c2 = sl.sign_custody(c1, key_b, to_vault_id=C, next_key_root=key_c.ots_root, issued_at="2026-09-12T12:00:00Z")
    return sl.SphereFile(mint=m, custody=[c1, c2]), key_c


def _chain_three(chain):
    sphere, key_c = chain
    return copy.deepcopy(sphere), key_c


def test_sphere_commit_ignores_timestamps():
    a = sl.sphere_commit(TEMPLATE)
    b = sl.sphere_commit({**TEMPLATE, "createdAt": "1999-01-01T00:00:00Z", "sphereHash": "x"})
    assert a == b
    assert a != sl.sphere_commit({**TEMPLATE, "theme": "acier"})


def test_three_hops_verify_and_owner_is_last_receiver(issuer, chain):
    sphere, _ = _chain_three(chain)
    v = sl.verify_sphere(sphere, issuer_pk=issuer.public_key, caps=CAPS)
    assert v.ok, v.errors
    assert v.owner == C and not v.final


def test_json_round_trip_preserves_head(issuer, chain):
    sphere, _ = _chain_three(chain)
    again = sl.SphereFile.from_json(sphere.to_json())
    assert again.head_hash == sphere.head_hash
    assert sl.verify_sphere(again, issuer_pk=issuer.public_key, caps=CAPS).ok


def test_receipt_from_known_anchor_makes_head_final(issuer, anchor, chain):
    sphere, _ = _chain_three(chain)
    sphere.receipts.append(sl.issue_receipt(anchor, "eidolon-vps", sphere.head, received_at="2026-09-12T12:01:00Z"))
    known = {"eidolon-vps": anchor.public_key}
    assert sl.verify_sphere(sphere, issuer_pk=issuer.public_key, known_anchors=known, caps=CAPS).final
    # La même ancre, inconnue du vérifieur : la tête reste en attente, sans erreur.
    v = sl.verify_sphere(sphere, issuer_pk=issuer.public_key, known_anchors={}, caps=CAPS)
    assert v.ok and not v.final
    # Un reçu pour une tête plus ancienne ne finalise pas la tête courante.
    old = sl.SphereFile(mint=sphere.mint, custody=[sphere.custody[0]],
                        receipts=[sl.issue_receipt(anchor, "eidolon-vps", sphere.custody[0])])
    old.custody.append(sphere.custody[1])
    assert not sl.verify_sphere(old, issuer_pk=issuer.public_key, known_anchors=known, caps=CAPS).final


def test_forged_receipt_is_an_error(issuer, anchor, chain):
    sphere, _ = _chain_three(chain)
    r = sl.issue_receipt(anchor, "eidolon-vps", sphere.head)
    r.custody_head = sphere.custody[0].record_hash.hex()      # signé pour une autre tête
    sphere.receipts.append(r)
    v = sl.verify_sphere(sphere, issuer_pk=issuer.public_key, known_anchors={"eidolon-vps": anchor.public_key}, caps=CAPS)
    assert not v.ok and any("reçu" in e for e in v.errors)


def test_tampered_next_root_breaks_the_signature(issuer, chain):
    sphere, _ = _chain_three(chain)
    sphere.custody[0].next_ots_root = "ff" * 32
    v = sl.verify_sphere(sphere, issuer_pk=issuer.public_key, caps=CAPS)
    assert not v.ok
    assert any("signature WOTS+" in e for e in v.errors), v.errors
    assert any("ne lie pas" in e for e in v.errors), "le hachage du #1 a changé, le #2 ne le lie plus"


def test_wrong_signer_is_rejected(issuer, minted):
    m, key_a = minted
    intruder = sl.ReceiverKey()
    with pytest.raises(sl.LedgerError):
        sl.sign_custody(m, intruder, to_vault_id=B, next_key_root=sl.ReceiverKey().ots_root)


def test_replayed_record_is_rejected(issuer, chain):
    sphere, _ = _chain_three(chain)
    sphere.custody.append(copy.deepcopy(sphere.custody[1]))
    v = sl.verify_sphere(sphere, issuer_pk=issuer.public_key, caps=CAPS)
    assert not v.ok and any("seq 2, attendu 3" in e for e in v.errors)


def test_reordered_records_are_rejected(issuer, chain):
    sphere, _ = _chain_three(chain)
    sphere.custody.reverse()
    assert not sl.verify_sphere(sphere, issuer_pk=issuer.public_key, caps=CAPS).ok


def test_gap_in_seq_is_rejected(issuer, chain):
    sphere, _ = _chain_three(chain)
    del sphere.custody[0]
    v = sl.verify_sphere(sphere, issuer_pk=issuer.public_key, caps=CAPS)
    assert not v.ok and any("seq 2, attendu 1" in e for e in v.errors)


def test_double_spend_is_a_fork_between_two_files(issuer, minted):
    m, key_a = minted
    # A cède la même sphère à B et à C avec la même clé : deux fichiers, un seul état de départ.
    key_a1 = sl.ReceiverKey()
    m1 = sl.mint(issuer, sphere_id="RARE_008", rarity="rare", index=2, template=TEMPLATE, vault_id=A,
                 first_key=key_a1, anchor_id="eidolon-vps", caps=CAPS, issued_at="2026-09-12T10:00:00Z")
    # Une clé WOTS+ ne signe qu'une fois : il faut ruser pour produire la seconde.
    kp_copy = copy.deepcopy(key_a1)
    to_b = sl.sign_custody(m1, key_a1, to_vault_id=B, next_key_root=sl.ReceiverKey().ots_root)
    to_c = sl.sign_custody(m1, kp_copy, to_vault_id=C, next_key_root=sl.ReceiverKey().ots_root)
    fa, fb = sl.SphereFile(mint=m1, custody=[to_b]), sl.SphereFile(mint=m1, custody=[to_c])
    assert sl.verify_sphere(fa, issuer_pk=issuer.public_key, caps=CAPS).ok
    assert sl.verify_sphere(fb, issuer_pk=issuer.public_key, caps=CAPS).ok, "chaque fichier seul est valide"
    fork = sl.detect_fork(fa, fb)
    assert fork and fork[0] == 1, "vus ensemble, ils divergent au saut 1 : c'est la double dépense"
    assert sl.detect_fork(fa, fa) is None


def test_burn_terminates_the_chain(issuer, chain):
    sphere, key_c = _chain_three(chain)
    burn = sl.sign_custody(sphere.custody[1], key_c, to_vault_id=None, next_key_root=None, reason="burn")
    sphere.custody.append(burn)
    v = sl.verify_sphere(sphere, issuer_pk=issuer.public_key, caps=CAPS)
    assert v.ok and sphere.burned
    with pytest.raises(sl.LedgerError):
        sl.sign_custody(burn, sl.ReceiverKey(), to_vault_id=A, next_key_root=sl.ReceiverKey().ots_root)
    forged = copy.deepcopy(sphere)
    forged.custody.append(copy.deepcopy(sphere.custody[1]))
    assert forged.burned, "un burn reste un burn, même si un fichier fabriqué ajoute une tête"
    assert not sl.verify_sphere(forged, issuer_pk=issuer.public_key, caps=CAPS).ok


def _fresh(issuer, sphere_id, vault=A):
    key = sl.ReceiverKey()
    m = sl.mint(issuer, sphere_id=sphere_id, rarity="rare", index=0, template=TEMPLATE, vault_id=vault,
                first_key=key, anchor_id="eidolon-vps", caps=CAPS, issued_at="2026-09-12T10:00:00Z")
    return m, key


def test_receipt_from_a_foreign_anchor_neither_finalizes_nor_passes(issuer, anchor, chain):
    other = slh_dsa.SlhDsaKeyPair.generate()
    sphere, _ = _chain_three(chain)
    sphere.receipts.append(sl.issue_receipt(other, "esoptron", sphere.head, received_at="2026-09-12T12:01:00Z"))
    known = {"eidolon-vps": anchor.public_key, "esoptron": other.public_key}
    v = sl.verify_sphere(sphere, issuer_pk=issuer.public_key, known_anchors=known, caps=CAPS)
    assert not v.ok and not v.final and any("rattachement" in e for e in v.errors), v.errors


def test_reanchor_designates_the_new_anchor_and_only_it_finalizes_afterwards(issuer, anchor):
    other = slh_dsa.SlhDsaKeyPair.generate()
    m, key_a = _fresh(issuer, "RARE_010")
    with pytest.raises(sl.LedgerError):        # change de voûte
        sl.sign_custody(m, key_a, to_vault_id=B, next_key_root=sl.ReceiverKey().ots_root,
                        reason="reanchor", anchor_id="esoptron")
    with pytest.raises(sl.LedgerError):        # sans nouvelle ancre
        sl.sign_custody(m, key_a, to_vault_id=A, next_key_root=sl.ReceiverKey().ots_root, reason="reanchor")
    with pytest.raises(sl.LedgerError):        # une ancre sur un transfert
        sl.sign_custody(m, key_a, to_vault_id=B, next_key_root=sl.ReceiverKey().ots_root, anchor_id="esoptron")
    key_a2 = sl.ReceiverKey()
    re = sl.sign_custody(m, key_a, to_vault_id=A, next_key_root=key_a2.ots_root, reason="reanchor", anchor_id="esoptron")
    sphere = sl.SphereFile(mint=m, custody=[re])
    assert sphere.anchor_id == "esoptron" and sphere.owner == A
    known = {"eidolon-vps": anchor.public_key, "esoptron": other.public_key}
    # Le reanchor lui-même est ordonné par l'ancienne ancre ; le saut suivant par la nouvelle.
    sphere.receipts.append(sl.issue_receipt(anchor, "eidolon-vps", re))
    v = sl.verify_sphere(sphere, issuer_pk=issuer.public_key, known_anchors=known, caps=CAPS)
    assert v.ok and v.final, v.errors
    nxt = sl.sign_custody(re, key_a2, to_vault_id=B, next_key_root=sl.ReceiverKey().ots_root)
    sphere.custody.append(nxt)
    sphere.receipts.append(sl.issue_receipt(anchor, "eidolon-vps", nxt))       # l'ancienne ancre n'ordonne plus
    v = sl.verify_sphere(sphere, issuer_pk=issuer.public_key, known_anchors=known, caps=CAPS)
    assert not v.ok and not v.final
    sphere.receipts.pop()
    sphere.receipts.append(sl.issue_receipt(other, "esoptron", nxt))
    v = sl.verify_sphere(sphere, issuer_pk=issuer.public_key, known_anchors=known, caps=CAPS)
    assert v.ok and v.final and v.owner == B, v.errors
    again = sl.SphereFile.from_json(sphere.to_json())
    assert again.anchor_id == "esoptron" and sl.verify_sphere(again, issuer_pk=issuer.public_key, known_anchors=known, caps=CAPS).final


def test_reissue_key_cannot_move_the_sphere(issuer):
    m, key = _fresh(issuer, "RARE_011")
    with pytest.raises(sl.LedgerError):
        sl.sign_custody(m, key, to_vault_id=B, next_key_root=sl.ReceiverKey().ots_root, reason="reissue-key")
    rec = sl.sign_custody(m, key, to_vault_id=A, next_key_root=sl.ReceiverKey().ots_root, reason="reissue-key")
    assert sl.verify_sphere(sl.SphereFile(mint=m, custody=[rec]), issuer_pk=issuer.public_key, caps=CAPS).ok
    forged = copy.deepcopy(rec)
    forged.to_vault_id = B
    v = sl.verify_sphere(sl.SphereFile(mint=m, custody=[forged]), issuer_pk=issuer.public_key, caps=CAPS)
    assert not v.ok and any("ne déplace pas" in e for e in v.errors), v.errors


def test_hostile_files_yield_a_verdict_never_a_crash(issuer, chain):
    sphere, _ = _chain_three(chain)
    base = sphere.to_dict()

    def mut(path, value):
        d = copy.deepcopy(base)
        cur = d
        for k in path[:-1]:
            cur = cur[k]
        cur[path[-1]] = value
        return d

    hostile = [mut(("mint", "index"), "7"), mut(("mint", "index"), True), mut(("mint", "sphere_commit"), "zz"),
               mut(("custody", 0, "seq"), None), mut(("custody", 0, "signature"), 12),
               mut(("custody", 0, "prev_hash"), "\udc80"), mut(("mint", "rarity"), ["rare"]),
               mut(("custody",), {"a": 1}), mut(("receipts",), "x"), mut(("mint",), None),
               mut(("mint", "issued_at"), "\udc80"), {"format": "EIDOLON_SPHERE"}, {"format": "nope"}, []]
    for h in hostile:
        try:
            s = sl.SphereFile.from_dict(h)
        except sl.LedgerError:
            continue
        v = sl.verify_sphere(s, issuer_pk=issuer.public_key, caps=CAPS)
        assert not v.ok, h
    with pytest.raises(sl.LedgerError):
        sl.SphereFile.from_json("{not json")
    # Un enregistrement construit hors de from_dict avec un texte non encodable : verdict, pas plantage.
    s, _ = _chain_three(chain)
    s.custody[0].reason = "\udc80"
    v = sl.verify_sphere(s, issuer_pk=issuer.public_key, caps=CAPS)
    assert not v.ok and v.errors


def test_mint_beyond_cap_is_refused_even_for_the_issuer(issuer):
    with pytest.raises(sl.LedgerError):
        sl.mint(issuer, sphere_id="MYTHIC_001", rarity="mythic", index=1, template=TEMPLATE, vault_id=A,
                first_key=sl.ReceiverKey(), anchor_id="eidolon-vps", caps=CAPS)


def test_mint_signed_by_another_key_is_rejected(issuer, minted):
    other = slh_dsa.SlhDsaKeyPair.generate()
    m = sl.mint(other, sphere_id="RARE_009", rarity="rare", index=0, template=TEMPLATE, vault_id=A,
                first_key=sl.ReceiverKey(), anchor_id="eidolon-vps", caps=CAPS)
    v = sl.verify_sphere(sl.SphereFile(mint=m), issuer_pk=issuer.public_key, caps=CAPS)
    assert not v.ok and any("émetteur" in e for e in v.errors)
    m.issuer_pk = issuer.public_key.hex()      # usurper l'identité ne suffit pas
    v = sl.verify_sphere(sl.SphereFile(mint=m), issuer_pk=issuer.public_key, caps=CAPS)
    assert not v.ok and any("signature d'émetteur invalide" in e for e in v.errors)
