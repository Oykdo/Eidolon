"""Bilan de flux : le théorème de la divergence appliqué au registre de garde.

Pour un volume V (un ensemble de voûtes) entre deux points de contrôle, et
rareté par rareté :

    détenu_après(V) − détenu_avant(V) = entrées(V) − sorties(V) + frappes(V) − brûlages(V)

Les frappes sont les seules sources, les brûlages les seuls puits ; un
transfert a une divergence nulle (ce qui sort d'une voûte entre dans une
autre). Tout écart est une source non déclarée — un « monopôle » : de
l'inflation, ou une fourche comptée deux fois. Sur le volume total d'une
ancre, la frontière est vide et il reste ``Δtotaux = frappes − brûlages``,
que ``sphere_checkpoint.conservation_ok`` borne ensuite par les plafonds.

C'est l'invariant du réconciliateur de l'ancre (I3), écrit une fois pour
toutes : il se vérifie sur le volume total à chaque point de contrôle, et
localement sur n'importe quel sous-ensemble de voûtes sans rien savoir du
reste. Rien ici ne parle réseau ni ne lit de fichier.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, Union

from .checkpoint import Checkpoint, conservation_ok
from .ledger import SphereFile

Sums = Dict[str, int]

# Ce qu'un enregistrement fait au bilan. Une réclamation (« claim », du trésor
# vers une voûte) est un mouvement comme un transfert ; « reanchor » et
# « reissue-key » ne déplacent rien : divergence nulle, frontière non traversée.
KINDS = ("mint", "claim", "transfer", "burn")


def _signed_add(a: Sums, b: Sums, sign: int = 1) -> Sums:
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + sign * v
    return {k: v for k, v in out.items() if v}


def _diff(after: Sums, before: Sums) -> Sums:
    return _signed_add(after, before, -1)


@dataclass(frozen=True)
class Event:
    """Un mouvement de sphère vu par le bilan : sa nature, sa rareté, d'où, vers où."""
    kind: str
    sphere_id: str
    rarity: str
    from_vault: Optional[str]
    to_vault: Optional[str]

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"nature inconnue : {self.kind}")


def events_from_sphere(sphere: SphereFile, *, after_seq: int = -1) -> List[Event]:
    """Les mouvements d'un fichier de sphère dont le ``seq`` dépasse ``after_seq``.

    ``after_seq=-1`` inclut la frappe (seq 0) ; ``after_seq=k`` ne rend que
    ce qui s'est passé depuis le point de contrôle qui avait vu ``seq=k``.
    Une raison hors de ``REASONS`` est une erreur, pas un mouvement vers soi.
    """
    rarity = sphere.mint.rarity
    out: List[Event] = []
    if after_seq < 0:
        out.append(Event("mint", sphere.mint.sphere_id, rarity, None, sphere.mint.vault_id))
    for rec in sphere.custody:
        if rec.seq <= after_seq:
            continue
        if rec.reason == "burn":
            out.append(Event("burn", rec.sphere_id, rarity, rec.from_vault_id, None))
        elif rec.reason in ("transfer", "claim"):
            out.append(Event(rec.reason, rec.sphere_id, rarity, rec.from_vault_id, rec.to_vault_id))
        elif rec.reason in ("reanchor", "reissue-key"):       # même voûte : divergence nulle
            out.append(Event("transfer", rec.sphere_id, rarity, rec.from_vault_id, rec.from_vault_id))
        else:
            raise ValueError(f"raison inconnue : {rec.reason!r}")
    return out


@dataclass
class Balance:
    """Le bilan d'un volume : ce qui a traversé sa frontière, ce qui y est né ou mort."""
    inflow: Sums = field(default_factory=dict)
    outflow: Sums = field(default_factory=dict)
    minted: Sums = field(default_factory=dict)
    burned: Sums = field(default_factory=dict)

    @property
    def divergence(self) -> Sums:
        """entrées − sorties + frappes − brûlages : la variation attendue du volume."""
        d = _signed_add(self.inflow, self.outflow, -1)
        d = _signed_add(d, self.minted, 1)
        return _signed_add(d, self.burned, -1)


def flux_balance(events: Iterable[Event], volume: Optional[Set[str]] = None) -> Balance:
    """Bilan des ``events`` pour le volume ``volume`` (``None`` : toutes les voûtes).

    Une sphère frappée deux fois dans le même bilan est refusée : c'est le
    principe d'exclusion, une frappe par instance.
    """
    inside = (lambda v: True) if volume is None else (lambda v: v in volume)
    b = Balance()
    minted_ids: Set[str] = set()
    for e in events:
        one = {e.rarity: 1}
        if e.kind == "mint":
            if e.sphere_id in minted_ids:
                raise ValueError(f"sphère {e.sphere_id} frappée deux fois : exclusion violée")
            minted_ids.add(e.sphere_id)
            if inside(e.to_vault):
                b.minted = _signed_add(b.minted, one)
        elif e.kind == "burn":
            if inside(e.from_vault):
                b.burned = _signed_add(b.burned, one)
        else:
            src_in, dst_in = inside(e.from_vault), inside(e.to_vault)
            if dst_in and not src_in:
                b.inflow = _signed_add(b.inflow, one)
            elif src_in and not dst_in:
                b.outflow = _signed_add(b.outflow, one)
    return b


def volume_totals(spheres: Iterable[SphereFile], volume: Optional[Set[str]] = None) -> Sums:
    """Sphères vivantes détenues par les voûtes de ``volume``, rareté par rareté."""
    totals: Sums = {}
    for s in spheres:
        if s.burned:
            continue
        if volume is None or s.owner in volume:
            totals = _signed_add(totals, {s.mint.rarity: 1})
    return totals


def divergence_ok(before: Sums, after: Sums, balance: Balance) -> Tuple[bool, List[str]]:
    """après − avant == entrées − sorties + frappes − brûlages, rareté par rareté.

    Une rareté qui apparaît d'un côté seulement compte pour zéro de l'autre.
    """
    expected = balance.divergence
    observed = _diff(after, before)
    errors = []
    for r in sorted(set(expected) | set(observed)):
        if expected.get(r, 0) != observed.get(r, 0):
            errors.append(f"{r} : variation observée {observed.get(r, 0):+d}, "
                          f"attendue {expected.get(r, 0):+d} (source non déclarée)")
    return (not errors, errors)


def anchor_invariant(prev: Checkpoint, nxt: Checkpoint, events: Sequence[Event], *,
                     genesis_ids: Union[Set[str], Mapping[str, str]], caps: Dict[str, int],
                     minted_before: Optional[Set[str]] = None,
                     treasury_id: Optional[str] = None,
                     claim_targets: Optional[Mapping[str, str]] = None) -> Tuple[bool, List[str]]:
    """L'invariant de l'ancre entre deux points de contrôle consécutifs.

    1. pas de monopôle : toute frappe est dans la racine de genèse, sous sa
       rareté de genèse quand ``genesis_ids`` est une table ``id → rareté``,
       et n'a pas déjà été comptée au point de contrôle précédent quand
       ``minted_before`` (les identifiants de l'arbre de ``prev``, que l'ancre
       possède puisqu'elle l'a construit) est fourni ;
    2. sur le volume total, Δtotaux = frappes − brûlages ;
    3. Δbrûlés = brûlages ;
    4. conservation : détenu + brûlé ≤ plafond, rareté par rareté, aux deux
       points de contrôle ;
    5. la séquence avance d'un, sous la même ancre ;
    6. le trésor (question 9), quand ``treasury_id`` est donné : toute
       réclamation en part, et il ne transfère jamais ; quand
       ``claim_targets`` (``sphere_id → vault_id`` du créneau) est donné,
       chaque réclamation mène à la voûte de son créneau.

    Les reçus sont supposés déjà vérifiés (signatures, première tête gagne) ;
    ici on ne compte que ce que les enregistrements déclarent.
    """
    errors: List[str] = []
    if nxt.anchor_id != prev.anchor_id:
        errors.append(f"ancre {prev.anchor_id} puis {nxt.anchor_id} : pas la même")
    if nxt.checkpoint_seq != prev.checkpoint_seq + 1:
        errors.append(f"séquence {prev.checkpoint_seq} puis {nxt.checkpoint_seq} : pas consécutifs")
    rarity_of = genesis_ids if isinstance(genesis_ids, Mapping) else None
    for e in events:
        if e.kind == "claim":
            if treasury_id is not None and e.from_vault != treasury_id:
                errors.append(f"réclamation de {e.sphere_id} qui ne part pas du trésor")
            if claim_targets is not None and claim_targets.get(e.sphere_id) != e.to_vault:
                errors.append(f"réclamation de {e.sphere_id} vers {str(e.to_vault)[:12]} : "
                              f"le créneau est {str(claim_targets.get(e.sphere_id))[:12]}")
            continue
        if e.kind == "transfer" and treasury_id is not None and e.from_vault == treasury_id:
            errors.append(f"transfert de {e.sphere_id} depuis le trésor : il réclame ou brûle, il ne transfère pas")
            continue
        if e.kind != "mint":
            continue
        if e.sphere_id not in genesis_ids:
            errors.append(f"frappe hors racine de genèse : {e.sphere_id} (monopôle)")
        elif rarity_of is not None and rarity_of[e.sphere_id] != e.rarity:
            errors.append(f"frappe {e.sphere_id} en {e.rarity} : la genèse la dit {rarity_of[e.sphere_id]} (monopôle)")
        if minted_before is not None and e.sphere_id in minted_before:
            errors.append(f"frappe {e.sphere_id} déjà comptée au point de contrôle {prev.checkpoint_seq} : exclusion violée")
    try:
        balance = flux_balance(events, None)
    except ValueError as exc:
        return (False, errors + [str(exc)])
    ok, errs = divergence_ok(prev.totals, nxt.totals, balance)
    errors += errs
    burned_delta = _diff(nxt.burned, prev.burned)
    if burned_delta != balance.burned:
        errors.append(f"brûlés : variation {burned_delta}, brûlages déclarés {balance.burned}")
    ok0, errs0 = conservation_ok(prev.totals, prev.burned, caps)
    errors += [f"point de contrôle précédent : {e}" for e in errs0]
    ok2, errs2 = conservation_ok(nxt.totals, nxt.burned, caps)
    errors += errs2
    return (not errors, errors)


__all__ = ["Event", "Balance", "events_from_sphere", "flux_balance", "volume_totals",
           "divergence_ok", "anchor_invariant", "KINDS"]
