"""Une transaction Eidos : cœur canonique, témoins, sérialisation, encapsulation.

Port de ``utxo.py`` (Tx) et ``envoi.ts``. Le cœur (``VERSION = 2``) exclut
les témoins, comme segwit : le txid ne bouge pas quand on signe.

  core    VERSION(4)=2 n_in(2) [txid(32) vout(4)]* n_out(2) [addr(20) atomes(8)]*
  txid    SHA-256d(core)
  sighash SHA-256(txid ‖ i(4))                 — signé par la clé de l'entrée i
  tx      len_core(4) core n_temoins(2) [flag(1) (graine_pub(32) sig(2144))?]*

Encapsulée en base64 (lignes de 76) entre ``-----EIDOS-----`` et
``-----FIN-----``, elle se colle dans une issue GitHub titrée « envoi » ; le
nœud la rejoue sur une copie du carnet et l'inclut ou la refuse. Rien ici
n'engage : seul le carnet du nœud tranche.

``signer_entrees`` fait ce que fait l'atelier : une clé par entrée, et le
même contrôle que le carnet — la clé reconstruite depuis la signature doit
donner l'adresse dépensée. La graine maîtresse n'entre qu'en octets opaques.
"""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import wots
from .preuve import est_entier, est_hex, sha256d

VERSION_TX = 2
DEBUT = "-----EIDOS-----"
FIN = "-----FIN-----"
LARGEUR_LIGNE = 76
MAX_CARACTERES_ISSUE = 65_536      # corps d'une issue GitHub
MAX_CARACTERES_ROBINET = 80_000    # robinet.py refuse au-delà
COINBASE_TXID = bytes(32)


class EnvoiError(ValueError):
    """Transaction mal formée."""


# ---------------------------------------------------------------------------
# 1. Cœur, txid, sighash
# ---------------------------------------------------------------------------

def core_tx(entrees: Sequence[Tuple[bytes, int]], sorties: Sequence[Tuple[bytes, int]]) -> bytes:
    if not (0 <= len(entrees) < 1 << 16) or not (0 <= len(sorties) < 1 << 16):
        raise EnvoiError("trop d'entrées ou de sorties")
    b = VERSION_TX.to_bytes(4, "big") + len(entrees).to_bytes(2, "big")
    for txid, vout in entrees:
        if len(txid) != 32 or not est_entier(vout) or vout >= 1 << 32:
            raise EnvoiError("entrée : txid de 32 octets et vout sur 4 octets")
        b += txid + vout.to_bytes(4, "big")
    b += len(sorties).to_bytes(2, "big")
    for addr, atomes in sorties:
        if len(addr) != 20 or not est_entier(atomes) or atomes >= 1 << 64:
            raise EnvoiError("sortie : adresse de 20 octets et montant sur 8 octets")
        b += addr + atomes.to_bytes(8, "big")
    return b


def txid_core(core: bytes) -> bytes:
    return sha256d(core)


def sighash(txid: bytes, index: int) -> bytes:
    return wots.sha256(txid + index.to_bytes(4, "big"))


# ---------------------------------------------------------------------------
# 2. Sérialisation et encapsulation
# ---------------------------------------------------------------------------

def ser_tx(core: bytes, temoins: Sequence[Optional[wots.Temoin]]) -> bytes:
    parts = [len(core).to_bytes(4, "big"), core, len(temoins).to_bytes(2, "big")]
    for w in temoins:
        if w is None:
            parts.append(b"\x00")
        else:
            gp, sig = w
            if len(gp) != wots.OCTETS_GRAINE or len(sig) != wots.OCTETS_SIG:
                raise EnvoiError("témoin de taille inattendue")
            parts += [b"\x01", bytes(gp), bytes(sig)]
    return b"".join(parts)


def deser_tx(octets: bytes) -> Tuple[bytes, List[Optional[wots.Temoin]]]:
    """(core, témoins) ; EnvoiError si la forme n'est pas exactement celle attendue."""
    if len(octets) < 6:
        raise EnvoiError("transaction tronquée")
    lc = int.from_bytes(octets[:4], "big")
    core = octets[4:4 + lc]
    if len(core) != lc:
        raise EnvoiError("cœur tronqué")
    p = 4 + lc
    if len(octets) < p + 2:
        raise EnvoiError("compte de témoins absent")
    nt = int.from_bytes(octets[p:p + 2], "big")
    p += 2
    temoins: List[Optional[wots.Temoin]] = []
    for _ in range(nt):
        if p >= len(octets):
            raise EnvoiError("témoin tronqué")
        flag = octets[p]
        p += 1
        if flag == 0:
            temoins.append(None)
        elif flag == 1:
            gp = octets[p:p + wots.OCTETS_GRAINE]
            sig = octets[p + wots.OCTETS_GRAINE:p + wots.OCTETS_TEMOIN]
            if len(sig) != wots.OCTETS_SIG:
                raise EnvoiError("témoin tronqué")
            temoins.append((gp, sig))
            p += wots.OCTETS_TEMOIN
        else:
            raise EnvoiError(f"drapeau de témoin {flag} inconnu")
    if p != len(octets):
        raise EnvoiError("octets en trop après les témoins")
    return core, temoins


def encapsuler(octets: bytes, largeur: int = LARGEUR_LIGNE) -> str:
    b64 = base64.b64encode(octets).decode("ascii")
    lignes = [DEBUT] + [b64[i:i + largeur] for i in range(0, len(b64), largeur)] + [FIN]
    return "\n".join(lignes) + "\n"


_LIGNE_B64 = re.compile(r"^[A-Za-z0-9+/=]{4,}$")


def desencapsuler(texte: str) -> bytes:
    """Entre les marqueurs, seules les lignes entièrement base64 sont retenues."""
    lignes = [ligne.rstrip("\r") for ligne in texte.split("\n")]
    d = next((i for i, ligne in enumerate(lignes) if DEBUT in ligne), -1)
    f = next((i for i, ligne in enumerate(lignes) if i > d and FIN in ligne), -1) if d >= 0 else -1
    if d < 0 or f < 0:
        raise EnvoiError("marqueurs -----EIDOS----- / -----FIN----- absents")
    morceaux = [ligne.strip() for ligne in lignes[d + 1:f]]
    morceaux = [ligne for ligne in morceaux if _LIGNE_B64.match(ligne)]
    if not morceaux:
        raise EnvoiError("aucune transaction entre les marqueurs")
    s = "".join(morceaux)
    if len(s) % 4 or not re.match(r"^[A-Za-z0-9+/]*={0,2}$", s):
        raise EnvoiError("base64 invalide")
    return base64.b64decode(s, validate=True)


# ---------------------------------------------------------------------------
# 3. Signer des entrées du coffre
# ---------------------------------------------------------------------------

@dataclass
class EnvoiSigne:
    txid: str
    core: bytes
    temoins: List[wots.Temoin]
    empreintes: List[str]                 # clés brûlées, à noter dans clesUsees
    adresse_rendu: Optional[str]
    octets: bytes = b""
    texte: str = ""
    caracteres: int = 0
    transmissible_issue: bool = True
    transmissible_robinet: bool = True
    erreurs: List[str] = field(default_factory=list)


def signer_entrees(maitre: str, entrees: Sequence[Dict[str, Any]], dest: bytes, montant: int,
                   rendu: int = 0, indice_rendu: Optional[int] = None) -> EnvoiSigne:
    """Une clé par entrée (``entrees[i]["indice"]``), une sortie vers ``dest``,
    un rendu vers l'adresse d'indice ``indice_rendu`` si ``rendu > 0``.
    Lève EnvoiError si une clé ne correspond pas à l'adresse dépensée."""
    if len(dest) != 20:
        raise EnvoiError("destination de 20 octets attendue")
    if not entrees:
        raise EnvoiError("aucune entrée")
    if not est_entier(montant, 1):
        raise EnvoiError("montant ≥ 1 atome")
    inputs = []
    for e in entrees:
        if not est_hex(e.get("txid"), 64) or not est_entier(e.get("rang")):
            raise EnvoiError("entrée : txid et rang attendus")
        if not est_hex(e.get("adresse"), 40) or not est_entier(e.get("indice")):
            raise EnvoiError("entrée : adresse et indice attendus")
        inputs.append((bytes.fromhex(e["txid"]), int(e["rang"])))
    outputs = [(bytes(dest), montant)]
    adresse_rendu: Optional[str] = None
    if rendu > 0 and indice_rendu is not None:
        adresse_rendu = wots.adresse_de(maitre, indice_rendu)
        outputs.append((bytes.fromhex(adresse_rendu), rendu))
    core = core_tx(inputs, outputs)
    txid = txid_core(core)
    empreintes: List[str] = []
    temoins: List[wots.Temoin] = []
    for i, e in enumerate(entrees):
        h = sighash(txid, i)
        temoin = wots.signer(wots.graine_de(maitre, int(e["indice"])), h)
        r = wots.racine_depuis_temoin(temoin, h)
        if r is None or wots.adresse(temoin[0], r).hex() != e["adresse"]:
            raise EnvoiError(f"entrée {i} : la clé ne correspond pas à l'adresse")
        empreintes.append(wots.empreinte(temoin[0], r).hex())
        temoins.append(temoin)
    octets = ser_tx(core, temoins)
    texte = encapsuler(octets)
    return EnvoiSigne(
        txid=txid.hex(), core=core, temoins=temoins, empreintes=empreintes,
        adresse_rendu=adresse_rendu, octets=octets, texte=texte, caracteres=len(texte),
        transmissible_issue=len(texte) <= MAX_CARACTERES_ISSUE,
        transmissible_robinet=len(texte) <= MAX_CARACTERES_ROBINET,
    )


def verifier_envoi(octets: bytes, adresses_depensees: Sequence[str]) -> Tuple[bool, str]:
    """Le contrôle du carnet, hors contexte : chaque témoin reconstruit
    l'adresse de l'entrée qu'il dépense (données par l'appelant, dans l'ordre)."""
    try:
        core, temoins = deser_tx(octets)
    except EnvoiError as e:
        return False, str(e)
    if len(core) < 6 or int.from_bytes(core[:4], "big") != VERSION_TX:
        return False, "version de transaction inattendue"
    n_in = int.from_bytes(core[4:6], "big")
    if n_in != len(temoins) or n_in != len(adresses_depensees):
        return False, "un témoin et une adresse par entrée"
    txid = txid_core(core)
    for i, (w, a) in enumerate(zip(temoins, adresses_depensees)):
        if w is None:
            return False, f"entrée {i} : témoin absent"
        if not est_hex(a, 40) or not wots.verifier(bytes.fromhex(a), sighash(txid, i), w):
            return False, f"entrée {i} : témoin invalide pour {a[:12]}…"
    return True, txid.hex()


__all__ = [
    "VERSION_TX", "DEBUT", "FIN", "LARGEUR_LIGNE", "MAX_CARACTERES_ISSUE",
    "MAX_CARACTERES_ROBINET", "COINBASE_TXID", "EnvoiError", "EnvoiSigne",
    "core_tx", "txid_core", "sighash", "ser_tx", "deser_tx", "encapsuler", "desencapsuler",
    "signer_entrees", "verifier_envoi",
]
