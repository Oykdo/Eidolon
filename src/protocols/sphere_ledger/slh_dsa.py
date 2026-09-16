"""SLH-DSA (FIPS 205, SPHINCS+-SHA2-128s) : la signature de l'émetteur et des ancres.

Sans état et par hachage pur, donc du même métal que WOTS+ ; là où WOTS+
signe une fois, SLH-DSA signe autant qu'on veut, au prix d'une signature de
7 856 octets et d'environ deux secondes par signature sur ce poste. C'est
sans importance pour ce qu'elle signe : la racine de genèse (une fois), les
reçus et points de contrôle d'ancre (quelques-uns par jour).

Chaque signature porte sur ``SHA3-256("EIDOLON_SLH_V1:" || usage || charge)`` :
le même octet ne peut pas valoir à la fois pour une frappe, un reçu et un
point de contrôle.

Implémentation : ``pqcrypto.sign.sphincs_sha2_128s_simple``, le même paquet
que la cérémonie. Clé publique 32 octets, clé secrète 64 octets.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pqcrypto.sign import sphincs_sha2_128s_simple as _slh

ALGORITHM = "SLH-DSA-SHA2-128s"
PUBLIC_KEY_SIZE = _slh.PUBLIC_KEY_SIZE
SECRET_KEY_SIZE = _slh.SECRET_KEY_SIZE
SIGNATURE_SIZE = _slh.SIGNATURE_SIZE

_DOMAIN = b"EIDOLON_SLH_V1:"


def tagged_message(purpose: str, payload: bytes) -> bytes:
    """Ce qui est réellement signé : un condensat séparé par usage."""
    return hashlib.sha3_256(_DOMAIN + purpose.encode("utf-8") + b":" + payload).digest()


@dataclass
class SlhDsaKeyPair:
    public_key: bytes
    _secret_key: bytes

    @classmethod
    def generate(cls) -> "SlhDsaKeyPair":
        pk, sk = _slh.generate_keypair()
        return cls(public_key=bytes(pk), _secret_key=bytes(sk))

    def sign(self, purpose: str, payload: bytes) -> bytes:
        return bytes(_slh.sign(self._secret_key, tagged_message(purpose, payload)))

    # Sérialisation de la clé secrète : à écrire dans un fichier protégé,
    # jamais dans un enregistrement.
    def to_secret_dict(self) -> dict:
        return {"algorithm": ALGORITHM, "public_key": self.public_key.hex(), "secret_key": self._secret_key.hex()}

    @classmethod
    def from_secret_dict(cls, d: dict) -> "SlhDsaKeyPair":
        if d.get("algorithm") != ALGORITHM:
            raise ValueError(f"algorithme inattendu : {d.get('algorithm')!r}")
        return cls(bytes.fromhex(d["public_key"]), bytes.fromhex(d["secret_key"]))


def verify(public_key: bytes, purpose: str, payload: bytes, signature: bytes) -> bool:
    """Vrai si ``signature`` est celle de ``public_key`` sur (usage, charge)."""
    if len(public_key) != PUBLIC_KEY_SIZE or len(signature) != SIGNATURE_SIZE:
        return False
    try:
        return bool(_slh.verify(public_key, tagged_message(purpose, payload), signature))
    except Exception:
        return False


__all__ = ["ALGORITHM", "PUBLIC_KEY_SIZE", "SECRET_KEY_SIZE", "SIGNATURE_SIZE",
           "SlhDsaKeyPair", "verify", "tagged_message"]
