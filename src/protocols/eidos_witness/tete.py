"""La tête signée du réseau d'essai — ``etat.json.tete_signee`` contre ``federation.json``.

Un bloc fédéré d'Eidos est identifié par
``id_bloc = SHA-256d(E.header ‖ utxo_root)`` avec
``E.header = height(8) prev(32) merkle(32) ts(8) nonce(8)`` (gelé, nonce = 0
en fédéré). Le proposant du créneau le signe en XMSS. Le nœud publie de quoi
juger sans rejouer : hauteur, prev, merkle, ts, utxo_root, id_bloc,
validateur, indice, signature, chemin.

Le témoin recompose ``id_bloc``, vérifie la signature contre la racine et la
graine publique du validateur déclaré, et — quand ``federation.json`` donne
``t0_unix``, ``creneau_s`` et ``pas_rotation`` — que ce validateur était bien
le proposant du créneau : ``V[(pas · s) mod n]``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from . import wots, xmss
from .preuve import est_entier, est_hex, sha256d

HAUTEUR_MSS_DEFAUT = 10   # federation.py ; le testnet publie 12 dans federation.json
PAS_DEFAUT = 3


class TeteError(ValueError):
    """Tête ou fédération mal formée."""


@dataclass(frozen=True)
class Federation:
    racines: Tuple[bytes, ...]
    graines_pub: Tuple[bytes, ...]
    hauteur_mss: int
    t0: Optional[int] = None
    creneau_s: Optional[int] = None
    pas: int = PAS_DEFAUT
    reseau: Optional[str] = None
    spec: Optional[str] = None

    @property
    def n(self) -> int:
        return len(self.racines)

    def creneau(self, ts: int) -> Optional[int]:
        if self.t0 is None or not self.creneau_s:
            return None
        return (ts - self.t0) // self.creneau_s

    def proposant(self, creneau: int) -> int:
        return (self.pas * creneau) % self.n

    @classmethod
    def depuis(cls, f: Dict[str, Any]) -> "Federation":
        """Lit un ``federation.json`` (ou la famille ``tete.federation`` des vecteurs)."""
        if not isinstance(f, dict):
            raise TeteError("fédération : objet attendu")
        racines = f.get("racines")
        graines = f.get("graines_publiques")
        if not isinstance(racines, list) or not racines or not isinstance(graines, list):
            raise TeteError("fédération : racines et graines_publiques attendues")
        if len(racines) != len(graines):
            raise TeteError("fédération : une graine publique par racine")
        if any(not est_hex(r, 64) for r in racines) or any(not est_hex(g, 64) for g in graines):
            raise TeteError("fédération : racines et graines sur 32 octets hex")
        hauteur = f.get("hauteur_mss", HAUTEUR_MSS_DEFAUT)
        if not est_entier(hauteur, 1) or hauteur > 30:
            raise TeteError("fédération : hauteur_mss invalide")
        pas = f.get("pas_rotation", PAS_DEFAUT)
        if not est_entier(pas, 1):
            raise TeteError("fédération : pas_rotation invalide")
        if len(racines) % pas == 0:
            raise TeteError(f"fédération : n = {len(racines)} divisible par {pas}")
        t0 = f.get("t0_unix")
        creneau_s = f.get("creneau_s")
        return cls(
            racines=tuple(bytes.fromhex(r) for r in racines),
            graines_pub=tuple(bytes.fromhex(g) for g in graines),
            hauteur_mss=hauteur,
            t0=t0 if est_entier(t0) else None,
            creneau_s=creneau_s if est_entier(creneau_s, 1) else None,
            pas=pas,
            reseau=f.get("reseau") if isinstance(f.get("reseau"), str) else None,
            spec=f.get("spec") if isinstance(f.get("spec"), str) else None,
        )


@dataclass(frozen=True)
class TeteSignee:
    hauteur: int
    prev: bytes
    merkle: bytes
    ts: int
    utxo_root: bytes
    id_bloc: bytes
    validateur: int
    indice: int
    signature: bytes
    chemin: Tuple[bytes, ...]

    @classmethod
    def depuis(cls, t: Dict[str, Any]) -> "TeteSignee":
        if not isinstance(t, dict):
            raise TeteError("tête : objet attendu")
        for champ in ("prev", "merkle", "utxo_root", "id_bloc"):
            if not est_hex(t.get(champ), 64):
                raise TeteError(f"tête : {champ} sur 32 octets hex attendu")
        for champ in ("hauteur", "ts", "validateur", "indice"):
            if not est_entier(t.get(champ)):
                raise TeteError(f"tête : {champ} entier ≥ 0 attendu")
        sig = t.get("signature")
        if not est_hex(sig, 2 * wots.OCTETS_SIG):
            raise TeteError("tête : signature WOTS+ de 2 144 octets hex attendue")
        chemin = t.get("chemin")
        if not isinstance(chemin, list) or any(not est_hex(c, 64) for c in chemin):
            raise TeteError("tête : chemin de 32 octets hex attendu")
        return cls(
            hauteur=t["hauteur"], prev=bytes.fromhex(t["prev"]),
            merkle=bytes.fromhex(t["merkle"]), ts=t["ts"],
            utxo_root=bytes.fromhex(t["utxo_root"]), id_bloc=bytes.fromhex(t["id_bloc"]),
            validateur=t["validateur"], indice=t["indice"],
            signature=bytes.fromhex(str(sig)), chemin=tuple(bytes.fromhex(c) for c in chemin),
        )

    def to_dict(self) -> Dict[str, Any]:
        """La forme publiée (``etat.json.tete_signee``), à l'identique."""
        return {
            "hauteur": self.hauteur, "prev": self.prev.hex(), "merkle": self.merkle.hex(),
            "ts": self.ts, "utxo_root": self.utxo_root.hex(), "id_bloc": self.id_bloc.hex(),
            "validateur": self.validateur, "indice": self.indice,
            "signature": self.signature.hex(), "chemin": [c.hex() for c in self.chemin],
        }


def header(height: int, prev: bytes, merkle: bytes, ts: int, nonce: int) -> bytes:
    """E.header (gelé, 88 octets) — ``eonis.header``."""
    return (height.to_bytes(8, "big") + prev + merkle
            + ts.to_bytes(8, "big") + nonce.to_bytes(8, "big"))


def entete_federe(t: TeteSignee) -> bytes:
    """E.header suivi de la racine UTXO : 120 octets, nonce = 0 en fédéré."""
    return header(t.hauteur, t.prev, t.merkle, t.ts, 0) + t.utxo_root


def id_bloc(t: TeteSignee) -> bytes:
    return sha256d(entete_federe(t))


@dataclass(frozen=True)
class Verdict:
    ok: bool
    detail: str


def verifier_tete(t: TeteSignee, fed: Federation, verifier_proposant: bool = True) -> Verdict:
    """Recompose ``id_bloc``, vérifie la signature XMSS du validateur déclaré,
    et le créneau si la fédération le permet. Ne lève jamais."""
    if not (0 <= t.validateur < fed.n):
        return Verdict(False, f"validateur {t.validateur} hors de la fédération ({fed.n})")
    if id_bloc(t) != t.id_bloc:
        return Verdict(False, "id_bloc ne correspond pas à l'en-tête fédéré")
    sig = (t.indice, t.signature, list(t.chemin))
    if not xmss.verifier_mss(fed.racines[t.validateur], fed.graines_pub[t.validateur],
                             fed.hauteur_mss, t.id_bloc, sig):
        return Verdict(False, "signature de validateur invalide")
    if verifier_proposant:
        s = fed.creneau(t.ts)
        if s is not None:
            if s < 0:
                return Verdict(False, "créneau antérieur à la genèse")
            attendu = fed.proposant(s)
            if attendu != t.validateur:
                return Verdict(False, f"créneau {s} : proposant {attendu} attendu, "
                                      f"{t.validateur} reçu")
    return Verdict(True, f"tête signée · bloc {t.hauteur} · validateur {t.validateur}")


def tete_depuis_etat(etat: Dict[str, Any]) -> Optional[TeteSignee]:
    """La tête signée d'un ``etat.json`` déjà chargé ; None si absente."""
    t = etat.get("tete_signee") if isinstance(etat, dict) else None
    if t is None:
        return None
    return TeteSignee.depuis(t)


__all__ = [
    "TeteError", "Federation", "TeteSignee", "Verdict",
    "header", "entete_federe", "id_bloc", "verifier_tete", "tete_depuis_etat",
]
