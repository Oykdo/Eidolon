"""Discovers all files belonging to a specific vault on this machine.

The inventory is the authoritative answer to "what do we need to move
to make this vault work on another machine".

Two kinds of artifacts are collected:

* Identity files (.psnx, .blend_data) - cryptographic credentials
* State files - persistent vault state, registry entry, escrows, etc.

Files outside the vault's scope (other vaults, system caches, machine
fingerprints) are intentionally excluded.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

try:
    from config.paths import (
        get_vaults_root,
        get_keys_dir,
        get_identities_dir,
        get_persistent_vaults_dir,
        get_identity_history_dir,
        get_vault_registry_path,
    )
except Exception:  # pragma: no cover
    def get_vaults_root() -> Path:
        return Path("data") / "vaults"

    def get_keys_dir() -> Path:
        return get_vaults_root() / "keys"

    def get_identities_dir() -> Path:
        return get_vaults_root() / "identities"

    def get_persistent_vaults_dir() -> Path:
        return get_vaults_root() / "persistent"

    def get_identity_history_dir() -> Path:
        return get_vaults_root() / "identity_history"

    def get_vault_registry_path() -> Path:
        return get_identities_dir() / "vault_registry.json"


@dataclass
class InventoryEntry:
    """A single file to be included in the archive."""

    archive_path: str   # path inside archive (forward slashes, normalized)
    source_path: Path   # absolute path on the source machine
    size: int
    sha256: str

    def to_dict(self) -> Dict:
        return {
            "archive_path": self.archive_path,
            "size": self.size,
            "sha256": self.sha256,
        }


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_entry(source: Path, archive_path: str) -> Optional[InventoryEntry]:
    if not source.is_file():
        return None
    return InventoryEntry(
        archive_path=archive_path,
        source_path=source,
        size=source.stat().st_size,
        sha256=_sha256_file(source),
    )


def _walk_dir(base: Path, archive_prefix: str) -> List[InventoryEntry]:
    out: List[InventoryEntry] = []
    if not base.is_dir():
        return out
    for f in sorted(base.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(base).as_posix()
        entry = _make_entry(f, f"{archive_prefix}/{rel}")
        if entry is not None:
            out.append(entry)
    return out


def collect_vault_inventory(
    *,
    vault_id: str,
    vault_number: int,
    vault_name: str,
    depositor_prefix: str,
    psnx_path: Optional[Path] = None,
    blend_path: Optional[Path] = None,
) -> List[InventoryEntry]:
    """Build the full list of files belonging to this vault.

    Args:
        vault_id: canonical vault id
        vault_number: vault numeric id
        vault_name: human-readable name (used for key filenames)
        depositor_prefix: 16-hex-char prefix of sha256(vault_key)
        psnx_path: explicit .psnx path (preferred over auto-discovery)
        blend_path: explicit .blend_data path (preferred over auto-discovery)
    """
    entries: List[InventoryEntry] = []
    seen_archive_paths: set = set()

    # 1. Identity files (always required)
    for source, kind in ((psnx_path, "psnx"), (blend_path, "blend_data")):
        if source is None:
            continue
        source = Path(source)
        if not source.is_file():
            continue
        archive_path = f"keys/{source.name}"
        entry = _make_entry(source, archive_path)
        if entry is not None and archive_path not in seen_archive_paths:
            entries.append(entry)
            seen_archive_paths.add(archive_path)

    # 2. Persistent vault state (per vault_id directory)
    persistent_root = get_persistent_vaults_dir()
    for candidate in (vault_id, vault_name, f"vault_{vault_number}"):
        if not candidate:
            continue
        sub = persistent_root / candidate
        if sub.is_dir():
            for entry in _walk_dir(sub, f"vault_state/persistent/{candidate}"):
                if entry.archive_path not in seen_archive_paths:
                    entries.append(entry)
                    seen_archive_paths.add(entry.archive_path)

    # 3. Identity history (per-vault audit trail)
    history_root = get_identity_history_dir()
    for candidate in (vault_id, vault_name):
        if not candidate:
            continue
        sub = history_root / candidate
        if sub.is_dir():
            for entry in _walk_dir(sub, f"vault_state/identity_history/{candidate}"):
                if entry.archive_path not in seen_archive_paths:
                    entries.append(entry)
                    seen_archive_paths.add(entry.archive_path)

    # 4. Escrows (partitioned by depositor prefix)
    if depositor_prefix:
        escrow_dir = get_vaults_root() / "escrows" / depositor_prefix.lower()
        if escrow_dir.is_dir():
            for entry in _walk_dir(
                escrow_dir, f"vault_state/escrows/{depositor_prefix.lower()}"
            ):
                if entry.archive_path not in seen_archive_paths:
                    entries.append(entry)
                    seen_archive_paths.add(entry.archive_path)

    # 5. Distribution / assignment caches (per vault_id)
    distrib_dir = get_vaults_root() / "distribution"
    if distrib_dir.is_dir():
        for f in distrib_dir.rglob("*"):
            if not f.is_file():
                continue
            name = f.name
            if vault_id and vault_id in name:
                rel = f.relative_to(distrib_dir).as_posix()
                archive_path = f"vault_state/distribution/{rel}"
                entry = _make_entry(f, archive_path)
                if entry is not None and archive_path not in seen_archive_paths:
                    entries.append(entry)
                    seen_archive_paths.add(archive_path)

    # 6. Registry slice (just this vault's entry, not the whole multi-vault file)
    registry_path = get_vault_registry_path()
    if registry_path.is_file():
        try:
            registry_data = json.loads(registry_path.read_text(encoding="utf-8"))
        except Exception:
            registry_data = None
        if isinstance(registry_data, dict):
            slice_data = _extract_registry_slice(
                registry_data, vault_id=vault_id, vault_number=vault_number
            )
            if slice_data:
                tmp_path = (
                    get_vaults_root().parent / ".migration_tmp_registry_slice.json"
                )
                tmp_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path.write_text(
                    json.dumps(slice_data, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
                archive_path = "vault_state/registry_slice.json"
                entry = _make_entry(tmp_path, archive_path)
                if entry is not None and archive_path not in seen_archive_paths:
                    entries.append(entry)
                    seen_archive_paths.add(archive_path)

    return entries


def _extract_registry_slice(
    registry: dict, *, vault_id: str, vault_number: int
) -> Optional[dict]:
    """Return a minimal registry entry for this vault only."""
    vaults_section = registry.get("vaults")
    if not isinstance(vaults_section, dict):
        return None
    for key, entry in vaults_section.items():
        if not isinstance(entry, dict):
            continue
        if entry.get("vault_id") == vault_id or entry.get("vault_number") == vault_number:
            return {
                "schema": registry.get("schema") or registry.get("schema_version"),
                "vault_entry_key": key,
                "vault_entry": entry,
            }
    return None
