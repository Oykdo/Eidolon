"""Registre de garde des sphères — une chaîne d'enregistrements par sphère.

Format public : ``docs/SPHERE_LEDGER_FORMAT.md``. Une sphère est un fichier
auto-vérifiable : son enregistrement de frappe (``MintRecord``, signé par
l'émetteur en SLH-DSA), puis ses enregistrements de garde (``CustodyRecord``,
chacun signé WOTS+ par le contrôleur courant, dont la racine a été engagée
dans l'enregistrement précédent), plus les reçus d'ancre (``AnchorReceipt``)
qui rendent une tête finale.

Principe d'exclusion : une instance, un contrôleur. Le fichier ne peut
contenir qu'un chemin ; deux fichiers qui divergent après un même
enregistrement sont une fourche (``detect_fork``), que seule l'ancre tranche
en ne recevant qu'une tête par état. Et seule l'ancre de rattachement de la
sphère — celle de la frappe, ou celle désignée par le dernier ``reanchor`` —
finalise : un reçu d'une autre ancre, même reconnue, est une erreur (§1.5).

Un fichier de sphère est une entrée non fiable (il arrive d'une autre
voûte) : les lecteurs sont typés et toute malformation est une
``LedgerError`` ou un verdict ``ok=False``, jamais une exception nue.

Rien ici ne parle réseau. Le hachage d'un enregistrement est
``SHA3-256("EIDOLON_CUSTODY_V1:" || JSON canonique)`` sur ses champs hors
signature. Les octets sont écrits en hexadécimal minuscule.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from . import hash_sig as wots
from . import slh_dsa
from .checkpoint import SphereLeaf, SumProof, verify_proof

RECORD_DOMAIN = b"EIDOLON_CUSTODY_V1:"
COMMIT_DOMAIN = b"EIDOLON_SPHERE_COMMIT_V1:"
GENESIS_DOMAIN = b"EIDOLON_GENESIS_V1:"
KEY_SECRET_DOMAIN = b"EIDOLON_WOTS_SECRET_V1:"
KEY_PUBLIC_DOMAIN = b"EIDOLON_WOTS_PUBLIC_V1:"
VERSION = 1

# Raisons d'un enregistrement de garde. « claim » est le premier saut d'une
# sphère frappée vers un trésor (§1.6) ; « burn » termine la chaîne ;
# « reanchor » et « reissue-key » restent dans la voûte du détenteur.
REASONS = ("transfer", "claim", "burn", "reanchor", "reissue-key")
_SAME_VAULT = ("reanchor", "reissue-key")


class LedgerError(ValueError):
    """Enregistrement mal formé ou chaîne invalide."""


def canonical(obj) -> bytes:
    try:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except (UnicodeEncodeError, TypeError, ValueError) as exc:
        # Un substitut isolé (\udc80) passe json.loads mais pas l'encodage UTF-8 :
        # on ne bascule pas en ensure_ascii, ça changerait les hachages non ASCII.
        raise LedgerError(f"contenu non canonisable : {exc}") from None


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hex(b: Optional[bytes]) -> Optional[str]:
    return None if b is None else b.hex()


def _field(d, key: str, kind: str, *, optional: bool = False):
    """Lecteur typé d'un champ venu d'un fichier : clé absente, mauvais type,
    hexadécimal impossible ou texte non encodable sont des ``LedgerError``."""
    if not isinstance(d, dict):
        raise LedgerError("enregistrement attendu sous forme d'objet")
    v = d.get(key)
    if v is None:
        if optional:
            return None
        raise LedgerError(f"champ manquant : {key}")
    if kind == "int":
        if isinstance(v, bool) or not isinstance(v, int):
            raise LedgerError(f"champ {key} : entier attendu")
        return v
    if not isinstance(v, str):
        raise LedgerError(f"champ {key} : texte attendu")
    if kind == "hex":
        try:
            bytes.fromhex(v)
        except ValueError:
            raise LedgerError(f"champ {key} : hexadécimal attendu") from None
    else:
        try:
            v.encode("utf-8")
        except UnicodeEncodeError:
            raise LedgerError(f"champ {key} : texte non encodable en UTF-8") from None
    return v


def sphere_commit(template: dict) -> bytes:
    """Engagement reproductible sur un gabarit : sans les champs d'horodatage.

    ``sphereHash`` du générateur inclut ``createdAt``, donc deux générations
    du même gabarit ne donnent pas le même hachage. Celui-ci ne dépend que du
    contenu.
    """
    body = {k: v for k, v in template.items() if k not in ("createdAt", "created_at", "sphereHash")}
    return hashlib.sha3_256(COMMIT_DOMAIN + canonical(body)).digest()


# Les plafonds de la genèse par rareté (21 186 sphères) : une donnée publiée, la
# racine de genèse les porte aussi (``GenesisRoot.caps``) et fait foi.
GENESIS_CAPS: Dict[str, int] = {"primordial": 11, "genesis": 58, "mythic": 360, "legendary": 720, "epic": 1440,
                                "rare": 2160, "uncommon": 3600, "common": 12837}


def _caps() -> Dict[str, int]:
    return dict(GENESIS_CAPS)


# ---------------------------------------------------------------------------
# Enregistrements
# ---------------------------------------------------------------------------

@dataclass
class MintRecord:
    sphere_id: str
    rarity: str
    index: int
    sphere_commit: str          # hex
    vault_id: str
    ots_root: str               # hex, racine WOTS+ du premier contrôleur
    anchor_id: str
    issued_at: str
    external_seal: Optional[str] = None    # hex du sceau Esoptron, ou None
    issuer_pk: Optional[str] = None        # hex
    signature: Optional[str] = None        # hex, SLH-DSA
    kind: str = "mint"
    version: int = VERSION

    def unsigned_fields(self) -> dict:
        return {
            "kind": self.kind, "version": self.version, "sphere_id": self.sphere_id,
            "rarity": self.rarity, "index": self.index, "sphere_commit": self.sphere_commit,
            "vault_id": self.vault_id, "ots_root": self.ots_root, "anchor_id": self.anchor_id,
            "issued_at": self.issued_at, "external_seal": self.external_seal,
        }

    @property
    def record_hash(self) -> bytes:
        return hashlib.sha3_256(RECORD_DOMAIN + canonical(self.unsigned_fields())).digest()

    def to_dict(self) -> dict:
        d = self.unsigned_fields()
        d["issuer_pk"] = self.issuer_pk
        d["signature"] = self.signature
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "MintRecord":
        if not isinstance(d, dict) or d.get("kind") != "mint":
            raise LedgerError("enregistrement de frappe attendu")
        return cls(sphere_id=_field(d, "sphere_id", "str"), rarity=_field(d, "rarity", "str"),
                   index=_field(d, "index", "int"), sphere_commit=_field(d, "sphere_commit", "hex"),
                   vault_id=_field(d, "vault_id", "hex"), ots_root=_field(d, "ots_root", "hex"),
                   anchor_id=_field(d, "anchor_id", "str"), issued_at=_field(d, "issued_at", "str"),
                   external_seal=_field(d, "external_seal", "hex", optional=True),
                   issuer_pk=_field(d, "issuer_pk", "hex", optional=True),
                   signature=_field(d, "signature", "hex", optional=True),
                   version=_field(d, "version", "int", optional=True) or VERSION)


@dataclass
class CustodyRecord:
    sphere_id: str
    seq: int
    prev_hash: str              # hex
    from_vault_id: str
    to_vault_id: Optional[str]  # None pour un burn ; = from_vault_id pour reanchor / reissue-key
    next_ots_root: Optional[str]  # hex ; None pour un burn
    reason: str
    issued_at: str
    anchor_id: Optional[str] = None     # nouvelle ancre de rattachement, pour un reanchor seulement
    signer_seed: Optional[str] = None   # hex, seed public WOTS+ du signataire
    signature: Optional[str] = None     # hex, 2 144 octets
    kind: str = "custody"
    version: int = VERSION

    def unsigned_fields(self) -> dict:
        return {
            "kind": self.kind, "version": self.version, "sphere_id": self.sphere_id, "seq": self.seq,
            "prev_hash": self.prev_hash, "from_vault_id": self.from_vault_id, "to_vault_id": self.to_vault_id,
            "next_ots_root": self.next_ots_root, "reason": self.reason, "issued_at": self.issued_at,
            "anchor_id": self.anchor_id,
        }

    @property
    def record_hash(self) -> bytes:
        return hashlib.sha3_256(RECORD_DOMAIN + canonical(self.unsigned_fields())).digest()

    def to_dict(self) -> dict:
        d = self.unsigned_fields()
        d["signer_seed"] = self.signer_seed
        d["signature"] = self.signature
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "CustodyRecord":
        if not isinstance(d, dict) or d.get("kind") != "custody":
            raise LedgerError("enregistrement de garde attendu")
        return cls(sphere_id=_field(d, "sphere_id", "str"), seq=_field(d, "seq", "int"),
                   prev_hash=_field(d, "prev_hash", "hex"), from_vault_id=_field(d, "from_vault_id", "hex"),
                   to_vault_id=_field(d, "to_vault_id", "hex", optional=True),
                   next_ots_root=_field(d, "next_ots_root", "hex", optional=True),
                   reason=_field(d, "reason", "str"), issued_at=_field(d, "issued_at", "str"),
                   anchor_id=_field(d, "anchor_id", "str", optional=True),
                   signer_seed=_field(d, "signer_seed", "hex", optional=True),
                   signature=_field(d, "signature", "hex", optional=True),
                   version=_field(d, "version", "int", optional=True) or VERSION)


@dataclass
class AnchorReceipt:
    sphere_id: str
    custody_head: str           # hex
    seq: int
    anchor_id: str
    received_at: str
    anchor_pk: Optional[str] = None
    signature: Optional[str] = None
    kind: str = "receipt"
    version: int = VERSION

    def unsigned_fields(self) -> dict:
        return {"kind": self.kind, "version": self.version, "sphere_id": self.sphere_id,
                "custody_head": self.custody_head, "seq": self.seq, "anchor_id": self.anchor_id,
                "received_at": self.received_at}

    @property
    def record_hash(self) -> bytes:
        return hashlib.sha3_256(RECORD_DOMAIN + canonical(self.unsigned_fields())).digest()

    def to_dict(self) -> dict:
        d = self.unsigned_fields()
        d["anchor_pk"] = self.anchor_pk
        d["signature"] = self.signature
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "AnchorReceipt":
        if not isinstance(d, dict) or d.get("kind") != "receipt":
            raise LedgerError("reçu d'ancre attendu")
        return cls(sphere_id=_field(d, "sphere_id", "str"), custody_head=_field(d, "custody_head", "hex"),
                   seq=_field(d, "seq", "int"), anchor_id=_field(d, "anchor_id", "str"),
                   received_at=_field(d, "received_at", "str"),
                   anchor_pk=_field(d, "anchor_pk", "hex", optional=True),
                   signature=_field(d, "signature", "hex", optional=True),
                   version=_field(d, "version", "int", optional=True) or VERSION)


# ---------------------------------------------------------------------------
# Émission, garde, reçus : les trois opérations
# ---------------------------------------------------------------------------

class ReceiverKey:
    """La clé à usage unique que le receveur fabrique AVANT le transfert.

    Il communique ``ots_root`` (et son seed public) à l'émetteur ; il garde
    ``keypair`` pour signer, une seule fois, le transfert suivant.
    """

    def __init__(self, keypair: Optional[wots.WotsKeyPair] = None) -> None:
        self.keypair = keypair or wots.WotsKeyPair()

    @classmethod
    def derive(cls, material: bytes, sphere_id: str, seq: int) -> "ReceiverKey":
        """La clé d'une voûte pour une sphère, dérivée de son matériel de clé
        (question 12) : rien à sauvegarder, restaurer la voûte restaure le droit
        de signer. ``seq`` est le numéro de l'enregistrement où la racine est
        engagée (0 pour la frappe, 1 pour une réclamation…) ; la clé signe
        l'enregistrement ``seq + 1``. Le risque d'une clé à état est tenu par
        la règle du client — lire la tête à l'ancre avant de signer — et par
        l'ancre, qui refuse une seconde tête.
        """
        if not isinstance(material, (bytes, bytearray)) or len(material) < 32:
            raise LedgerError("matériel de dérivation : 32 octets au moins")
        if seq < 0:
            raise LedgerError("seq ≥ 0")
        sid = sphere_id.encode("utf-8")
        tag = len(sid).to_bytes(2, "big") + sid + seq.to_bytes(8, "big")
        secret = hashlib.sha3_256(KEY_SECRET_DOMAIN + bytes(material) + b":" + tag).digest()
        public = hashlib.sha3_256(KEY_PUBLIC_DOMAIN + bytes(material) + b":" + tag).digest()
        return cls(wots.WotsKeyPair(secret_seed=secret, public_seed=public, ots_index=0))

    @property
    def ots_root(self) -> str:
        return self.keypair.public_key.root.hex()

    @property
    def seed(self) -> str:
        return self.keypair.public_seed.hex()


def mint(issuer: Optional[slh_dsa.SlhDsaKeyPair], *, sphere_id: str, rarity: str, index: int,
         template: dict, vault_id: str, first_key: ReceiverKey, anchor_id: str,
         external_seal: Optional[bytes] = None, issued_at: Optional[str] = None,
         caps: Optional[Dict[str, int]] = None) -> MintRecord:
    """Frappe une sphère. Refuse un index hors plafond : même l'émetteur ne
    frappe pas au-delà de la rareté.

    Sans ``issuer``, l'enregistrement n'est pas signé : il n'est authentifié
    que par sa preuve d'inclusion dans une racine de genèse signée
    (``GenesisRoot``, question 14) — c'est le régime de la genèse, 21 186
    frappes pour une signature.
    """
    caps = caps or _caps()
    if rarity not in caps:
        raise LedgerError(f"rareté inconnue : {rarity!r}")
    if not (0 <= index < caps[rarity]):
        raise LedgerError(f"index {index} hors plafond pour {rarity} (cap {caps[rarity]})")
    rec = MintRecord(sphere_id=sphere_id, rarity=rarity, index=index,
                     sphere_commit=sphere_commit(template).hex(), vault_id=vault_id,
                     ots_root=first_key.ots_root, anchor_id=anchor_id,
                     issued_at=issued_at or _now(), external_seal=_hex(external_seal))
    if issuer is not None:
        rec.issuer_pk = issuer.public_key.hex()
        rec.signature = issuer.sign("mint", rec.record_hash).hex()
    return rec


def _sums(d, key: str) -> Dict[str, int]:
    sums = d.get(key, {})
    if not isinstance(sums, dict) or any(not isinstance(k, str) or isinstance(v, bool) or not isinstance(v, int) or v < 0
                                         for k, v in sums.items()):
        raise LedgerError(f"champ {key} : des cardinaux par rareté attendus")
    return dict(sums)


@dataclass
class GenesisRoot:
    """La racine de genèse : l'arbre à sommes des frappes, signé une fois.

    Elle engage l'ensemble des ``MintRecord`` (par la racine), les totaux par
    rareté, les plafonds, l'empreinte du fichier de distribution figé
    (question 13), le trésor et l'ancre. ``genesis_seq`` et ``supersedes``
    sont le retour arrière (question 18) : une racine remplaçante porte le
    numéro suivant et le hachage de celle qu'elle remplace.
    """
    genesis_seq: int
    root: str                      # hex, racine du SumTree des frappes
    totals: Dict[str, int]
    caps: Dict[str, int]
    count: int
    distribution_sha256: str
    treasury_id: str
    anchor_id: str
    issued_at: str
    supersedes: Optional[str] = None       # hex du record_hash de la racine remplacée
    issuer_pk: Optional[str] = None
    signature: Optional[str] = None
    kind: str = "genesis"
    version: int = VERSION

    def unsigned_fields(self) -> dict:
        return {"kind": self.kind, "version": self.version, "genesis_seq": self.genesis_seq, "root": self.root,
                "totals": self.totals, "caps": self.caps, "count": self.count,
                "distribution_sha256": self.distribution_sha256, "treasury_id": self.treasury_id,
                "anchor_id": self.anchor_id, "issued_at": self.issued_at, "supersedes": self.supersedes}

    @property
    def record_hash(self) -> bytes:
        return hashlib.sha3_256(GENESIS_DOMAIN + canonical(self.unsigned_fields())).digest()

    @classmethod
    def issue(cls, issuer: slh_dsa.SlhDsaKeyPair, **fields) -> "GenesisRoot":
        g = cls(**fields)
        g.issuer_pk = issuer.public_key.hex()
        g.signature = issuer.sign("genesis", g.record_hash).hex()
        return g

    def verify(self, issuer_pk: bytes) -> bool:
        return (self.issuer_pk == issuer_pk.hex() and bool(self.signature)
                and slh_dsa.verify(issuer_pk, "genesis", self.record_hash, bytes.fromhex(self.signature)))

    def to_dict(self) -> dict:
        d = self.unsigned_fields()
        d["issuer_pk"] = self.issuer_pk
        d["signature"] = self.signature
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "GenesisRoot":
        if not isinstance(d, dict) or d.get("kind") != "genesis":
            raise LedgerError("racine de genèse attendue")
        seq = _field(d, "genesis_seq", "int")
        count = _field(d, "count", "int")
        if seq < 1 or count < 0:
            raise LedgerError("racine de genèse : genesis_seq ≥ 1, count ≥ 0")
        return cls(genesis_seq=seq, root=_field(d, "root", "hex"), totals=_sums(d, "totals"), caps=_sums(d, "caps"),
                   count=count, distribution_sha256=_field(d, "distribution_sha256", "hex"),
                   treasury_id=_field(d, "treasury_id", "hex"), anchor_id=_field(d, "anchor_id", "str"),
                   issued_at=_field(d, "issued_at", "str"), supersedes=_field(d, "supersedes", "hex", optional=True),
                   issuer_pk=_field(d, "issuer_pk", "hex", optional=True),
                   signature=_field(d, "signature", "hex", optional=True),
                   version=_field(d, "version", "int", optional=True) or VERSION)


def sign_custody(prev, controller: ReceiverKey, *, to_vault_id: Optional[str],
                 next_key_root: Optional[str], reason: str = "transfer",
                 issued_at: Optional[str] = None, anchor_id: Optional[str] = None) -> CustodyRecord:
    """Le contrôleur courant signe le saut suivant.

    ``prev`` est le dernier enregistrement (frappe ou garde). ``controller``
    est la clé dont la racine y est engagée : on le vérifie avant de signer,
    pour ne pas consommer une clé sur un enregistrement que personne ne
    pourra vérifier. Un ``reanchor`` désigne sa nouvelle ancre (``anchor_id``)
    et reste, comme ``reissue-key``, dans la voûte du détenteur.
    """
    if reason not in REASONS:
        raise LedgerError(f"raison inconnue : {reason!r}")
    committed = prev.ots_root if isinstance(prev, MintRecord) else prev.next_ots_root
    if committed is None:
        raise LedgerError("chaîne terminée : plus de contrôleur engagé")
    if controller.ots_root != committed:
        raise LedgerError("la clé du contrôleur ne correspond pas à la racine engagée")
    from_vault = prev.vault_id if isinstance(prev, MintRecord) else prev.to_vault_id
    if reason == "burn":
        if to_vault_id is not None or next_key_root is not None:
            raise LedgerError("un burn n'a ni destinataire ni clé suivante")
    elif to_vault_id is None or next_key_root is None:
        raise LedgerError("un transfert exige un destinataire et sa clé suivante")
    if reason in _SAME_VAULT and to_vault_id != from_vault:
        raise LedgerError(f"un {reason} ne déplace pas la sphère : destinataire = détenteur")
    if reason == "claim":
        if not isinstance(prev, MintRecord):
            raise LedgerError("une réclamation est le premier saut : elle part de la frappe")
        if to_vault_id == from_vault:
            raise LedgerError("une réclamation sort la sphère du trésor")
    if reason == "reanchor":
        if not anchor_id:
            raise LedgerError("un reanchor désigne la nouvelle ancre de rattachement")
    elif anchor_id is not None:
        raise LedgerError(f"un {reason} ne change pas d'ancre")
    seq = 1 if isinstance(prev, MintRecord) else prev.seq + 1
    rec = CustodyRecord(sphere_id=prev.sphere_id, seq=seq, prev_hash=prev.record_hash.hex(),
                        from_vault_id=from_vault, to_vault_id=to_vault_id, next_ots_root=next_key_root,
                        reason=reason, issued_at=issued_at or _now(), anchor_id=anchor_id,
                        signer_seed=controller.seed)
    rec.signature = controller.keypair.sign(rec.record_hash).to_bytes().hex()
    return rec


def issue_receipt(anchor: slh_dsa.SlhDsaKeyPair, anchor_id: str, record, *,
                  received_at: Optional[str] = None) -> AnchorReceipt:
    """L'ancre atteste qu'elle a reçu cette tête. Elle ne juge pas le contenu."""
    seq = 0 if isinstance(record, MintRecord) else record.seq
    r = AnchorReceipt(sphere_id=record.sphere_id, custody_head=record.record_hash.hex(), seq=seq,
                      anchor_id=anchor_id, received_at=received_at or _now())
    r.anchor_pk = anchor.public_key.hex()
    r.signature = anchor.sign("receipt", r.record_hash).hex()
    return r


# ---------------------------------------------------------------------------
# Le fichier de sphère et sa vérification
# ---------------------------------------------------------------------------

@dataclass
class SphereFile:
    mint: MintRecord
    custody: List[CustodyRecord] = field(default_factory=list)
    receipts: List[AnchorReceipt] = field(default_factory=list)
    genesis_proof: Optional[SumProof] = None    # inclusion de la frappe dans la racine de genèse
    template: Optional[dict] = None             # le gabarit révélé à la réclamation ; doit redonner sphere_commit

    @property
    def head(self):
        return self.custody[-1] if self.custody else self.mint

    @property
    def head_hash(self) -> str:
        return self.head.record_hash.hex()

    @property
    def owner(self) -> Optional[str]:
        h = self.head
        if isinstance(h, MintRecord):
            return h.vault_id
        return h.to_vault_id

    @property
    def burned(self) -> bool:
        # Un burn termine la chaîne : tout enregistrement après lui est invalide,
        # la sphère reste morte même si un fichier fabriqué ajoute une tête.
        return any(c.reason == "burn" for c in self.custody)

    @property
    def anchor_id(self) -> str:
        """L'ancre de rattachement courante : celle du dernier reanchor, sinon celle de la frappe."""
        for c in reversed(self.custody):
            if c.reason == "reanchor" and c.anchor_id:
                return c.anchor_id
        return self.mint.anchor_id

    def anchors_by_head(self) -> Dict[str, str]:
        """Pour chaque tête (hex), l'ancre qui l'ordonne : un reanchor est encore
        ordonné par l'ancienne ancre, le saut suivant par la nouvelle."""
        current = self.mint.anchor_id
        out = {self.mint.record_hash.hex(): current}
        for c in self.custody:
            out[c.record_hash.hex()] = current
            if c.reason == "reanchor" and c.anchor_id:
                current = c.anchor_id
        return out

    def to_dict(self) -> dict:
        return {"format": "EIDOLON_SPHERE", "version": VERSION, "mint": self.mint.to_dict(),
                "custody": [c.to_dict() for c in self.custody], "receipts": [r.to_dict() for r in self.receipts],
                "genesis_proof": self.genesis_proof.to_dict() if self.genesis_proof is not None else None,
                "template": self.template}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict) -> "SphereFile":
        if not isinstance(d, dict) or d.get("format") != "EIDOLON_SPHERE":
            raise LedgerError("fichier de sphère attendu")
        custody, receipts = d.get("custody", []), d.get("receipts", [])
        if not isinstance(custody, list) or not isinstance(receipts, list):
            raise LedgerError("custody et receipts doivent être des listes")
        proof = d.get("genesis_proof")
        if proof is not None:
            try:
                proof = SumProof.from_dict(proof)
            except ValueError as exc:
                raise LedgerError(f"preuve de genèse illisible : {exc}") from None
        template = d.get("template")
        if template is not None and not isinstance(template, dict):
            raise LedgerError("gabarit : objet attendu")
        return cls(mint=MintRecord.from_dict(d.get("mint")),
                   custody=[CustodyRecord.from_dict(c) for c in custody],
                   receipts=[AnchorReceipt.from_dict(r) for r in receipts],
                   genesis_proof=proof, template=template)

    @classmethod
    def from_json(cls, s: str) -> "SphereFile":
        try:
            d = json.loads(s)
        except (ValueError, TypeError) as exc:
            raise LedgerError(f"JSON illisible : {exc}") from None
        return cls.from_dict(d)


@dataclass
class Verification:
    ok: bool
    final: bool
    errors: List[str]
    head_hash: str
    owner: Optional[str]
    revealed: bool = False      # le gabarit est présent et redonne l'engagement de la frappe


def verify_sphere(sphere: SphereFile, *, issuer_pk: Optional[bytes] = None,
                  known_anchors: Optional[Dict[str, bytes]] = None,
                  caps: Optional[Dict[str, int]] = None,
                  genesis: Optional[GenesisRoot] = None,
                  treasury_ids: Optional[Set[str]] = None) -> Verification:
    """Vérifie une sphère de la frappe à la tête, hors ligne.

    ``issuer_pk`` : clé publique d'émetteur exigée (sans elle, la frappe n'est
    vérifiée que dans sa forme). ``genesis`` : la racine de genèse ; la frappe
    est alors authentifiée par sa preuve d'inclusion (``genesis_proof``), et sa
    signature, si elle en a une, doit tenir aussi. ``treasury_ids`` : les
    adresses de trésor ; un trésor ne fait que réclamer (``claim``, premier
    saut, vers une autre voûte) ou brûler. Le gabarit, s'il est révélé dans le
    fichier (``template``), doit redonner ``sphere_commit`` : sans lui, un
    vérifieur contrôle l'inclusion, la chaîne et les reçus, pas le contenu
    (``revealed`` le dit). ``known_anchors`` : ``anchor_id ->
    clé publique`` ; la tête est **finale** si un reçu de l'ancre de
    rattachement de cette tête (celle de la frappe, ou celle désignée par le
    dernier ``reanchor``), connue du vérifieur, la cite. Un reçu d'une autre
    ancre est une erreur : c'est la trace d'une finalisation hors ancre
    (§1.5). Un fichier illisible donne un verdict ``ok=False``, jamais une
    exception.
    """
    try:
        return _verify_sphere(sphere, issuer_pk=issuer_pk, known_anchors=known_anchors, caps=caps,
                              genesis=genesis, treasury_ids=treasury_ids)
    except (LedgerError, TypeError, ValueError, AttributeError) as exc:
        return Verification(ok=False, final=False, errors=[f"fichier illisible : {exc}"], head_hash="", owner=None)


def _verify_sphere(sphere: SphereFile, *, issuer_pk: Optional[bytes], known_anchors: Optional[Dict[str, bytes]],
                   caps: Optional[Dict[str, int]], genesis: Optional[GenesisRoot],
                   treasury_ids: Optional[Set[str]]) -> Verification:
    errors: List[str] = []
    caps = caps or (genesis.caps if genesis is not None else None) or _caps()
    m = sphere.mint

    # 1. La frappe
    if m.rarity not in caps or not (0 <= m.index < caps.get(m.rarity, 0)):
        errors.append(f"frappe hors plafond : {m.rarity} #{m.index}")
    if genesis is not None:
        if issuer_pk is not None and not genesis.verify(issuer_pk):
            errors.append("racine de genèse : signature d'émetteur invalide")
        proof = sphere.genesis_proof
        if proof is None:
            errors.append("frappe : preuve d'inclusion dans la racine de genèse absente")
        elif proof.leaf != SphereLeaf(m.sphere_id, m.rarity, m.record_hash.hex(), True):
            errors.append("frappe : la preuve d'inclusion ne porte pas sur cette frappe")
        elif not verify_proof(proof, bytes.fromhex(genesis.root), genesis.totals):
            errors.append("frappe : preuve d'inclusion invalide")
        if m.signature and issuer_pk is not None:
            if m.issuer_pk != issuer_pk.hex() or not slh_dsa.verify(issuer_pk, "mint", m.record_hash, bytes.fromhex(m.signature)):
                errors.append("frappe : signature d'émetteur invalide")
    elif issuer_pk is not None:
        if m.issuer_pk != issuer_pk.hex():
            errors.append("frappe : clé d'émetteur inattendue")
        elif not (m.signature and slh_dsa.verify(issuer_pk, "mint", m.record_hash, bytes.fromhex(m.signature))):
            errors.append("frappe : signature d'émetteur invalide")
    elif not m.signature:
        errors.append("frappe non signée")
    revealed = False
    if sphere.template is not None:
        if sphere_commit(sphere.template).hex() != m.sphere_commit:
            errors.append("gabarit : ne redonne pas l'engagement de la frappe")
        else:
            revealed = True

    # 2. La chaîne de garde
    prev = m
    committed = m.ots_root
    for i, c in enumerate(sphere.custody, start=1):
        expected_from = prev.vault_id if isinstance(prev, MintRecord) else prev.to_vault_id
        if c.sphere_id != m.sphere_id:
            errors.append(f"garde #{i} : autre sphère")
        if c.seq != i:
            errors.append(f"garde #{i} : seq {c.seq}, attendu {i}")
        if c.prev_hash != prev.record_hash.hex():
            errors.append(f"garde #{i} : ne lie pas l'enregistrement précédent")
        if c.from_vault_id != expected_from:
            errors.append(f"garde #{i} : émetteur {c.from_vault_id[:12]} n'est pas le détenteur {str(expected_from)[:12]}")
        if committed is None:
            errors.append(f"garde #{i} : enregistrement après un burn")
        if c.reason not in REASONS:
            errors.append(f"garde #{i} : raison inconnue {c.reason!r}")
        if c.reason == "burn":
            if c.to_vault_id is not None or c.next_ots_root is not None:
                errors.append(f"garde #{i} : un burn n'a ni destinataire ni clé suivante")
        elif c.to_vault_id is None or c.next_ots_root is None:
            errors.append(f"garde #{i} : transfert sans destinataire ou sans clé suivante")
        elif c.reason in _SAME_VAULT and c.to_vault_id != c.from_vault_id:
            errors.append(f"garde #{i} : un {c.reason} ne déplace pas la sphère "
                          f"(détenteur {str(c.from_vault_id)[:12]}, destinataire {str(c.to_vault_id)[:12]})")
        if c.reason == "claim":
            if i != 1:
                errors.append(f"garde #{i} : une réclamation est le premier saut")
            if c.from_vault_id != m.vault_id:
                errors.append(f"garde #{i} : une réclamation part de la voûte de frappe")
            if c.to_vault_id == c.from_vault_id:
                errors.append(f"garde #{i} : une réclamation sort la sphère du trésor")
            if treasury_ids is not None and c.from_vault_id not in treasury_ids:
                errors.append(f"garde #{i} : réclamation hors trésor")
        elif treasury_ids is not None and c.from_vault_id in treasury_ids and c.reason != "burn":
            errors.append(f"garde #{i} : le trésor ne fait que réclamer ou brûler, pas {c.reason}")
        if c.reason == "reanchor" and not c.anchor_id:
            errors.append(f"garde #{i} : reanchor sans nouvelle ancre")
        elif c.reason != "reanchor" and c.anchor_id is not None:
            errors.append(f"garde #{i} : ancre déclarée hors reanchor")
        # La signature WOTS+ doit reconstruire exactement la racine engagée.
        if committed is not None and c.signature and c.signer_seed:
            try:
                sig = wots.WotsSignature.from_bytes(bytes.fromhex(c.signature))
                pk = wots.WotsPublicKey(bytes.fromhex(c.signer_seed), 0, bytes.fromhex(committed))
                if not wots.verify(pk, c.record_hash, sig):
                    errors.append(f"garde #{i} : signature WOTS+ invalide pour la racine engagée")
            except (ValueError, TypeError, wots.HashSigError) as exc:
                errors.append(f"garde #{i} : signature illisible ({exc})")
        elif committed is not None:
            errors.append(f"garde #{i} : non signée")
        prev = c
        committed = c.next_ots_root

    # 3. Les reçus : seule l'ancre de rattachement de la tête citée finalise.
    known_anchors = known_anchors or {}
    anchor_for = sphere.anchors_by_head()
    final = False
    for j, r in enumerate(sphere.receipts, start=1):
        expected_anchor = anchor_for.get(r.custody_head)
        if r.sphere_id != m.sphere_id or expected_anchor is None:
            errors.append(f"reçu #{j} : cite une tête qui n'est pas dans ce fichier")
            continue
        if r.anchor_id != expected_anchor:
            errors.append(f"reçu #{j} : ancre {r.anchor_id!r} n'est pas l'ancre de rattachement "
                          f"{expected_anchor!r} de cette tête")
            continue
        pk = known_anchors.get(r.anchor_id)
        if pk is None:
            continue    # ancre inconnue du vérifieur : le reçu ne compte pas, sans être une erreur
        if r.anchor_pk != pk.hex() or not (r.signature and slh_dsa.verify(pk, "receipt", r.record_hash, bytes.fromhex(r.signature))):
            errors.append(f"reçu #{j} : signature d'ancre invalide")
            continue
        if r.custody_head == sphere.head_hash:
            final = True

    return Verification(ok=not errors, final=final and not errors, errors=errors,
                        head_hash=sphere.head_hash, owner=sphere.owner, revealed=revealed and not errors)


def detect_fork(a: SphereFile, b: SphereFile) -> Optional[Tuple[int, str, str]]:
    """Deux fichiers de la même sphère qui divergent après un même
    enregistrement : ``(seq, tête_a, tête_b)`` du premier désaccord, ou None.

    C'est la double dépense vue par un tiers. Le registre ne la tranche pas ;
    l'ancre le fait en n'acceptant qu'une tête par ``prev_hash``.
    """
    if a.mint.sphere_id != b.mint.sphere_id or a.mint.record_hash != b.mint.record_hash:
        return None
    for i, (x, y) in enumerate(zip(a.custody, b.custody), start=1):
        if x.record_hash != y.record_hash:
            if x.prev_hash == y.prev_hash:
                return (i, x.record_hash.hex(), y.record_hash.hex())
            return None
    return None


__all__ = ["MintRecord", "CustodyRecord", "AnchorReceipt", "GenesisRoot", "SphereFile", "Verification",
           "ReceiverKey", "mint", "sign_custody", "issue_receipt", "verify_sphere", "detect_fork", "sphere_commit",
           "canonical", "LedgerError", "REASONS", "GENESIS_CAPS"]
