"""On-disk envelope format for 7D Escrow documents.

The envelope is a JSON document where binary fields are base64-encoded for
readability. Three independent version identifiers are baked in and bound
into the integrity MAC so they cannot be tampered with:

    schema_version       structure of the JSON envelope itself
    min_reader_version   lowest reader build that knows the layout
    crypto_suite         named cryptographic bundle (algos + parameters)

Backward-compatibility rule (CRITICAL)
--------------------------------------

The canonical bytes covered by the integrity MAC for a given ``schema_version``
are FROZEN forever. If we ever want to add a field, we MUST bump
``schema_version`` AND register a new ``_mac_input_v{N}`` method. Old envelopes
continue to be read with their own version's mac_input function, so their
recorded MAC keeps verifying. There is NO automatic migration of stored
envelopes: their cryptographic state is immutable. To "upgrade" an envelope
to a newer suite, call ``reseal()`` which decrypts with the original suite
and re-encrypts with the current one - this requires the vault key.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from .format_version import (
    CURRENT_CRYPTO_SUITE,
    CURRENT_SCHEMA_VERSION,
    FormatError,
    MINIMUM_READER_VERSION,
    PRODUCER_TAG,
    check_compatibility,
)

ESCROW_SCHEMA_VERSION = CURRENT_SCHEMA_VERSION
ESCROW_FILE_SUFFIX = ".escrow7d"

_REQUIRED_FIELDS = (
    "schema_version",
    "min_reader_version",
    "crypto_suite",
    "escrow_id",
    "deposited_at",
    "depositor_vault_id_prefix",
    "kdf_salt",
    "aes_nonce",
    "ciphertext",
    "aes_tag",
    "payload_size",
)


def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


@dataclass
class EscrowEnvelope:
    escrow_id: str
    deposited_at: str
    depositor_vault_id_prefix: str
    conditions: List[Dict] = field(default_factory=list)
    kdf_salt: bytes = b""
    aes_nonce: bytes = b""
    ciphertext: bytes = b""
    aes_tag: bytes = b""
    payload_size: int = 0
    integrity_mac: bytes = b""
    label: str = ""
    # version triple (defaults to current producer values)
    schema_version: int = CURRENT_SCHEMA_VERSION
    min_reader_version: int = MINIMUM_READER_VERSION
    crypto_suite: str = CURRENT_CRYPTO_SUITE
    producer: str = PRODUCER_TAG

    # ------------------------------------------------------------------ MAC
    # Each schema version has its OWN frozen mac_input function. Never modify
    # an existing _mac_input_vN: that would invalidate every envelope ever
    # produced with that version. To add a field, define _mac_input_v(N+1)
    # and register it in _MAC_INPUT_BY_VERSION below.

    def _mac_input_v1(self) -> bytes:
        payload = {
            "schema_version": self.schema_version,
            "min_reader_version": self.min_reader_version,
            "crypto_suite": self.crypto_suite,
            "producer": self.producer,
            "escrow_id": self.escrow_id,
            "deposited_at": self.deposited_at,
            "depositor_vault_id_prefix": self.depositor_vault_id_prefix,
            "label": self.label,
            "conditions": self.conditions,
            "kdf_salt": _b64e(self.kdf_salt),
            "aes_nonce": _b64e(self.aes_nonce),
            "ciphertext": _b64e(self.ciphertext),
            "aes_tag": _b64e(self.aes_tag),
            "payload_size": self.payload_size,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def mac_input(self) -> bytes:
        """Dispatch to the frozen mac_input function for self.schema_version."""
        fn = _MAC_INPUT_BY_VERSION.get(self.schema_version)
        if fn is None:
            raise FormatError(
                f"no mac_input function registered for schema v{self.schema_version}"
            )
        return fn(self)

    # ----------------------------------------------------------- (de)ser

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "min_reader_version": self.min_reader_version,
            "crypto_suite": self.crypto_suite,
            "producer": self.producer,
            "escrow_id": self.escrow_id,
            "deposited_at": self.deposited_at,
            "depositor_vault_id_prefix": self.depositor_vault_id_prefix,
            "label": self.label,
            "conditions": self.conditions,
            "kdf_salt": _b64e(self.kdf_salt),
            "aes_nonce": _b64e(self.aes_nonce),
            "ciphertext": _b64e(self.ciphertext),
            "aes_tag": _b64e(self.aes_tag),
            "payload_size": self.payload_size,
            "integrity_mac": _b64e(self.integrity_mac),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EscrowEnvelope":
        """Load an envelope WITHOUT mutating its schema.

        The envelope is instantiated with its own schema_version, so MAC
        verification later uses the matching frozen mac_input function.
        """
        for required in _REQUIRED_FIELDS:
            if required not in data:
                raise FormatError(f"envelope missing required field: {required!r}")

        check_compatibility(
            schema_version=int(data["schema_version"]),
            min_reader_version=int(data.get("min_reader_version", 1)),
            crypto_suite=str(data["crypto_suite"]),
        )

        return cls(
            schema_version=int(data["schema_version"]),
            min_reader_version=int(data.get("min_reader_version", MINIMUM_READER_VERSION)),
            crypto_suite=str(data["crypto_suite"]),
            producer=str(data.get("producer", PRODUCER_TAG)),
            escrow_id=str(data["escrow_id"]),
            deposited_at=str(data["deposited_at"]),
            depositor_vault_id_prefix=str(data["depositor_vault_id_prefix"]),
            label=str(data.get("label", "")),
            conditions=list(data.get("conditions", [])),
            kdf_salt=_b64d(data["kdf_salt"]),
            aes_nonce=_b64d(data["aes_nonce"]),
            ciphertext=_b64d(data["ciphertext"]),
            aes_tag=_b64d(data["aes_tag"]),
            payload_size=int(data["payload_size"]),
            integrity_mac=_b64d(data.get("integrity_mac", "")),
        )

    @classmethod
    def from_json(cls, text: str) -> "EscrowEnvelope":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise FormatError(f"invalid JSON: {exc}")
        return cls.from_dict(data)

    # ---------------------------------------------------------- summary

    def summary(self) -> Dict[str, Any]:
        return {
            "escrow_id": self.escrow_id,
            "label": self.label,
            "deposited_at": self.deposited_at,
            "payload_size": self.payload_size,
            "conditions": [c.get("type") for c in self.conditions],
            "depositor_vault_id_prefix": self.depositor_vault_id_prefix,
            "schema_version": self.schema_version,
            "crypto_suite": self.crypto_suite,
        }


# ---------------------------------------------------------------------------
# FROZEN per-version mac_input dispatcher.
# Adding a new schema means: write _mac_input_v(N+1) and add the row below.
# NEVER mutate or delete an existing row: that breaks every existing envelope.
# ---------------------------------------------------------------------------

_MAC_INPUT_BY_VERSION: Dict[int, Callable[[EscrowEnvelope], bytes]] = {
    1: EscrowEnvelope._mac_input_v1,
}
