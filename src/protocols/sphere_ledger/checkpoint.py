"""Point de contrôle : un arbre de Merkle à sommes sur les têtes de sphères.

La loi qu'il rend vérifiable est la conservation : frappé = détenu + brûlé,
rareté par rareté. Chaque feuille est une sphère (identifiant, rareté, tête,
vivante ou brûlée) et porte un compte de 1 dans sa rareté si elle est
vivante ; chaque nœud hache ses deux enfants ET la somme de leurs comptes.
La racine engage donc à la fois l'ensemble des têtes et les totaux. Une
preuve d'inclusion, logarithmique, situe une sphère dans l'état publié et
recompute les mêmes totaux ; quiconque compare les totaux aux plafonds moins
les brûlages, sans voir qui détient quoi.

La preuve porte la feuille elle-même (identifiant, rareté, tête, vivante) et
le vérifieur la rehache : c'est ce qui lie la preuve à *cette* sphère. Une
preuve qui ne transporterait que le hachage de feuille pourrait être
réétiquetée, ou présenter un nœud interne comme une feuille.

``Checkpoint`` est l'enregistrement signé par l'ancre (SLH-DSA) qui publie
la racine, les totaux et son numéro de séquence.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from . import slh_dsa

LEAF_DOMAIN = b"EIDOLON_SUMLEAF_V1:"
NODE_DOMAIN = b"EIDOLON_SUMNODE_V1:"
PAD_DOMAIN = b"EIDOLON_SUMPAD_V1"
RECORD_DOMAIN = b"EIDOLON_CHECKPOINT_V1:"


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


Sums = Dict[str, int]


def _add(a: Sums, b: Sums) -> Sums:
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + v
    return {k: v for k, v in out.items() if v}


@dataclass(frozen=True)
class SphereLeaf:
    sphere_id: str
    rarity: str
    head: str        # hex du dernier enregistrement
    alive: bool

    def sums(self) -> Sums:
        return {self.rarity: 1} if self.alive else {}

    def hash(self) -> bytes:
        body = {"sphere_id": self.sphere_id, "rarity": self.rarity, "head": self.head, "alive": self.alive}
        return hashlib.sha3_256(LEAF_DOMAIN + _canonical(body)).digest()

    def to_dict(self) -> dict:
        return {"sphere_id": self.sphere_id, "rarity": self.rarity, "head": self.head, "alive": self.alive}

    @classmethod
    def from_dict(cls, d: dict) -> "SphereLeaf":
        if not isinstance(d, dict):
            raise ValueError("feuille attendue sous forme d'objet")
        for k in ("sphere_id", "rarity", "head"):
            if not isinstance(d.get(k), str):
                raise ValueError(f"feuille : champ {k} manquant ou non textuel")
        if not isinstance(d.get("alive"), bool):
            raise ValueError("feuille : alive doit être un booléen")
        return cls(d["sphere_id"], d["rarity"], d["head"], d["alive"])


def _node_hash(left: bytes, right: bytes, sums: Sums) -> bytes:
    return hashlib.sha3_256(NODE_DOMAIN + left + right + _canonical(sums)).digest()


_PAD = hashlib.sha3_256(PAD_DOMAIN).digest()


@dataclass
class SumProof:
    leaf: SphereLeaf
    index: int
    siblings: List[Tuple[str, Sums, str]]   # (hash hex, sums, "L"|"R" position du frère)

    def to_dict(self) -> dict:
        return {"leaf": self.leaf.to_dict(), "index": self.index,
                "siblings": [[h, s, side] for h, s, side in self.siblings]}

    @classmethod
    def from_dict(cls, d: dict) -> "SumProof":
        if not isinstance(d, dict) or not isinstance(d.get("siblings"), list):
            raise ValueError("preuve attendue sous forme d'objet avec ses frères")
        siblings = []
        for item in d["siblings"]:
            if not (isinstance(item, (list, tuple)) and len(item) == 3 and isinstance(item[0], str)
                    and isinstance(item[1], dict) and item[2] in ("L", "R")):
                raise ValueError("preuve : frère mal formé")
            if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in item[1].values()):
                raise ValueError("preuve : sommes non entières ou négatives")
            siblings.append((item[0], dict(item[1]), item[2]))
        index = d.get("index", 0)
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ValueError("preuve : index invalide")
        return cls(SphereLeaf.from_dict(d.get("leaf")), index, siblings)


class SumTree:
    """Arbre construit sur des feuilles triées par ``sphere_id`` (ordre canonique)."""

    def __init__(self, leaves: Sequence[SphereLeaf]):
        self.leaves = sorted(leaves, key=lambda l: l.sphere_id)
        ids = [l.sphere_id for l in self.leaves]
        if len(set(ids)) != len(ids):
            raise ValueError("deux feuilles pour la même sphère : principe d'exclusion violé")
        level: List[Tuple[bytes, Sums]] = [(l.hash(), l.sums()) for l in self.leaves]
        self._levels: List[List[Tuple[bytes, Sums]]] = [level]
        if not level:
            level = [(_PAD, {})]
            self._levels = [level]
        while len(level) > 1:
            if len(level) % 2 == 1:
                level = level + [(_PAD, {})]
                self._levels[-1] = level
            nxt = [(_node_hash(level[i][0], level[i + 1][0], _add(level[i][1], level[i + 1][1])),
                    _add(level[i][1], level[i + 1][1])) for i in range(0, len(level), 2)]
            self._levels.append(nxt)
            level = nxt

    @property
    def root(self) -> bytes:
        return self._levels[-1][0][0]

    @property
    def totals(self) -> Sums:
        return dict(self._levels[-1][0][1])

    def prove(self, sphere_id: str) -> SumProof:
        idx = next((i for i, l in enumerate(self.leaves) if l.sphere_id == sphere_id), None)
        if idx is None:
            raise KeyError(sphere_id)
        leaf = self.leaves[idx]
        siblings: List[Tuple[str, Sums, str]] = []
        i = idx
        for level in self._levels[:-1]:
            j = i ^ 1
            sib = level[j] if j < len(level) else (_PAD, {})
            siblings.append((sib[0].hex(), dict(sib[1]), "L" if j < i else "R"))
            i //= 2
        return SumProof(leaf, idx, siblings)


def verify_proof(proof: SumProof, root: bytes, totals: Sums) -> bool:
    """Rehache la feuille annoncée (identifiant, rareté, tête, vivante), puis
    recalcule la racine ET les totaux : la preuve ne situe une sphère que si
    la feuille est recalculée, et l'un sans l'autre ne prouve pas la
    conservation. Le vérifieur compare ensuite ``proof.leaf`` à ce qu'il
    attend (l'identifiant, la tête du fichier de sphère, son état)."""
    try:
        h = proof.leaf.hash()           # LEAF_DOMAIN : un nœud interne ne passe pas pour une feuille
        sums = proof.leaf.sums()
        for sib_hex, sib_sums, side in proof.siblings:
            sib = bytes.fromhex(sib_hex)
            merged = _add(sums, sib_sums)
            h = _node_hash(sib, h, merged) if side == "L" else _node_hash(h, sib, merged)
            sums = merged
    except (ValueError, TypeError, AttributeError):
        return False
    return h == root and sums == {k: v for k, v in totals.items() if v}


def conservation_ok(totals: Sums, burned: Sums, caps: Dict[str, int]) -> Tuple[bool, List[str]]:
    """détenu + brûlé ≤ plafond, rareté par rareté ; toute rareté inconnue ou
    tout compte négatif est une erreur (un compte est un cardinal : jamais < 0,
    et un « brûlé = −1 » masquerait un dépassement)."""
    errors = []
    for label, sums in (("totaux", totals), ("brûlages", burned)):
        for r, n in sums.items():
            if r not in caps:
                errors.append(f"rareté inconnue dans les {label} : {r}")
            elif isinstance(n, bool) or not isinstance(n, int) or n < 0:
                errors.append(f"{r} : compte invalide dans les {label} ({n!r})")
    if errors:
        return (False, errors)
    for r, alive in totals.items():
        if alive + burned.get(r, 0) > caps[r]:
            errors.append(f"{r} : {alive} vivantes + {burned.get(r, 0)} brûlées > plafond {caps[r]}")
    return (not errors, errors)


@dataclass
class Checkpoint:
    anchor_id: str
    checkpoint_seq: int
    root: str            # hex
    totals: Sums
    burned: Sums
    issued_at: str
    anchor_pk: Optional[str] = None
    signature: Optional[str] = None
    kind: str = "checkpoint"
    version: int = 1

    def unsigned_fields(self) -> dict:
        return {"kind": self.kind, "version": self.version, "anchor_id": self.anchor_id,
                "checkpoint_seq": self.checkpoint_seq, "root": self.root, "totals": self.totals,
                "burned": self.burned, "issued_at": self.issued_at}

    @property
    def record_hash(self) -> bytes:
        return hashlib.sha3_256(RECORD_DOMAIN + _canonical(self.unsigned_fields())).digest()

    @classmethod
    def issue(cls, anchor: slh_dsa.SlhDsaKeyPair, anchor_id: str, seq: int, tree: SumTree,
              burned: Sums, issued_at: str) -> "Checkpoint":
        cp = cls(anchor_id=anchor_id, checkpoint_seq=seq, root=tree.root.hex(), totals=tree.totals,
                 burned=dict(burned), issued_at=issued_at)
        cp.anchor_pk = anchor.public_key.hex()
        cp.signature = anchor.sign("checkpoint", cp.record_hash).hex()
        return cp

    def verify(self, anchor_pk: bytes) -> bool:
        return (self.anchor_pk == anchor_pk.hex() and bool(self.signature)
                and slh_dsa.verify(anchor_pk, "checkpoint", self.record_hash, bytes.fromhex(self.signature)))

    def to_dict(self) -> dict:
        d = self.unsigned_fields()
        d["anchor_pk"] = self.anchor_pk
        d["signature"] = self.signature
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Checkpoint":
        if not isinstance(d, dict) or d.get("kind") != "checkpoint":
            raise ValueError("point de contrôle attendu")
        for k in ("anchor_id", "root", "issued_at"):
            if not isinstance(d.get(k), str):
                raise ValueError(f"point de contrôle : champ {k} manquant ou non textuel")
        seq = d.get("checkpoint_seq")
        if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
            raise ValueError("point de contrôle : checkpoint_seq invalide")
        for k in ("totals", "burned"):
            sums = d.get(k, {})
            if not isinstance(sums, dict) or any(isinstance(v, bool) or not isinstance(v, int) or v < 0
                                                 for v in sums.values()):
                raise ValueError(f"point de contrôle : {k} doit compter des cardinaux")
        return cls(anchor_id=d["anchor_id"], checkpoint_seq=seq, root=d["root"],
                   totals=dict(d.get("totals", {})), burned=dict(d.get("burned", {})), issued_at=d["issued_at"],
                   anchor_pk=d.get("anchor_pk"), signature=d.get("signature"), version=int(d.get("version", 1)))


__all__ = ["SphereLeaf", "SumTree", "SumProof", "verify_proof", "conservation_ok", "Checkpoint"]
