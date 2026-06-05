"""Manifest format for vault migration archives.

The manifest is stored inside the encrypted ZIP payload as ``manifest.json``.
Its canonical bytes are signed by an HMAC over a domain-separated derivation
of the vault key. See ``archive.compute_integrity_mac``.

Per-schema mac_input functions are frozen forever to preserve backward
compatibility (same discipline as escrow_7d).
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from .format_version import (
    CURRENT_FORMAT_SUITE,
    CURRENT_SCHEMA_VERSION,
    FormatError,
    MINIMUM_READER_VERSION,
    PRODUCER_TAG,
    check_compatibility,
)


def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


_REQUIRED_FIELDS = (
    "schema_version",
    "min_reader_version",
    "format_suite",
    "exported_at",
    "vault_id",
    "vault_number",
    "vault_name",
    "depositor_prefix",
    "transfer_mode",
    "file_inventory",
    "archive_salt",
)


@dataclass
class FileEntry:
    archive_path: str
    size: int
    sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return {"archive_path": self.archive_path, "size": self.size, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileEntry":
        return cls(
            archive_path=str(data["archive_path"]),
            size=int(data["size"]),
            sha256=str(data["sha256"]),
        )


@dataclass
class Manifest:
    vault_id: str
    vault_number: int
    vault_name: str
    depositor_prefix: str
    exported_at: str
    archive_salt: bytes
    file_inventory: List[FileEntry] = field(default_factory=list)
    transfer_mode: str = "snapshot"
    schema_version: int = CURRENT_SCHEMA_VERSION
    min_reader_version: int = MINIMUM_READER_VERSION
    format_suite: str = CURRENT_FORMAT_SUITE
    producer: str = PRODUCER_TAG
    integrity_mac: bytes = b""
    notes: str = ""

    # ------------------------------------------------------------- MAC input

    def _mac_input_v1(self) -> bytes:
        payload = {
            "schema_version": self.schema_version,
            "min_reader_version": self.min_reader_version,
            "format_suite": self.format_suite,
            "producer": self.producer,
            "vault_id": self.vault_id,
            "vault_number": self.vault_number,
            "vault_name": self.vault_name,
            "depositor_prefix": self.depositor_prefix,
            "exported_at": self.exported_at,
            "transfer_mode": self.transfer_mode,
            "notes": self.notes,
            "archive_salt": _b64e(self.archive_salt),
            "file_inventory": [
                {"archive_path": e.archive_path, "size": e.size, "sha256": e.sha256}
                for e in self.file_inventory
            ],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def mac_input(self) -> bytes:
        fn = _MAC_INPUT_BY_VERSION.get(self.schema_version)
        if fn is None:
            raise FormatError(
                f"no mac_input function registered for migration schema v{self.schema_version}"
            )
        return fn(self)

    # --------------------------------------------------------------- (de)ser

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "min_reader_version": self.min_reader_version,
            "format_suite": self.format_suite,
            "producer": self.producer,
            "vault_id": self.vault_id,
            "vault_number": self.vault_number,
            "vault_name": self.vault_name,
            "depositor_prefix": self.depositor_prefix,
            "exported_at": self.exported_at,
            "transfer_mode": self.transfer_mode,
            "notes": self.notes,
            "archive_salt": _b64e(self.archive_salt),
            "file_inventory": [e.to_dict() for e in self.file_inventory],
            "integrity_mac": _b64e(self.integrity_mac),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Manifest":
        for required in _REQUIRED_FIELDS:
            if required not in data:
                raise FormatError(f"manifest missing required field: {required!r}")

        check_compatibility(
            schema_version=int(data["schema_version"]),
            min_reader_version=int(data.get("min_reader_version", 1)),
            format_suite=str(data["format_suite"]),
        )

        return cls(
            schema_version=int(data["schema_version"]),
            min_reader_version=int(data.get("min_reader_version", MINIMUM_READER_VERSION)),
            format_suite=str(data["format_suite"]),
            producer=str(data.get("producer", PRODUCER_TAG)),
            vault_id=str(data["vault_id"]),
            vault_number=int(data["vault_number"]),
            vault_name=str(data["vault_name"]),
            depositor_prefix=str(data["depositor_prefix"]),
            exported_at=str(data["exported_at"]),
            transfer_mode=str(data.get("transfer_mode", "snapshot")),
            notes=str(data.get("notes", "")),
            archive_salt=_b64d(str(data["archive_salt"])),
            file_inventory=[
                FileEntry.from_dict(e) for e in data.get("file_inventory", [])
            ],
            integrity_mac=_b64d(str(data.get("integrity_mac", ""))),
        )

    @classmethod
    def from_json(cls, text: str) -> "Manifest":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise FormatError(f"invalid manifest JSON: {exc}")
        return cls.from_dict(data)

    # ----------------------------------------------------------------- info

    def summary(self) -> Dict[str, Any]:
        return {
            "vault_id": self.vault_id,
            "vault_number": self.vault_number,
            "vault_name": self.vault_name,
            "exported_at": self.exported_at,
            "transfer_mode": self.transfer_mode,
            "file_count": len(self.file_inventory),
            "total_bytes": sum(e.size for e in self.file_inventory),
            "schema_version": self.schema_version,
            "format_suite": self.format_suite,
        }


# ---------------------------------------------------------------------------
# FROZEN per-version mac_input registry (same discipline as escrow_7d)
# ---------------------------------------------------------------------------

_MAC_INPUT_BY_VERSION: Dict[int, Callable[[Manifest], bytes]] = {
    1: Manifest._mac_input_v1,
}
