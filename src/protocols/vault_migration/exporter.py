"""High-level export: build manifest, ZIP files, encrypt, write archive."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .archive import (
    ArchiveError,
    build_zip_from_files,
    compute_integrity_mac,
    write_archive,
)
from .format_version import CURRENT_FORMAT_SUITE, get_suite, MIGRATION_FILE_SUFFIX
from .inventory import InventoryEntry, collect_vault_inventory
from .manifest import FileEntry, Manifest


class ExportError(Exception):
    pass


def _depositor_prefix(vault_key: bytes) -> str:
    return hashlib.sha256(vault_key).hexdigest()[:16]


def export_vault(
    *,
    vault_key: bytes,
    vault_id: str,
    vault_number: int,
    vault_name: str,
    output_path,
    psnx_path: Optional[Path] = None,
    blend_path: Optional[Path] = None,
    notes: str = "",
    suite_name: str = CURRENT_FORMAT_SUITE,
) -> dict:
    """Export this vault into a portable .eidolon_keybundle_full archive.

    Args:
        vault_key:      authenticated vault key (>= 32 bytes)
        vault_id:       canonical vault id
        vault_number:   numeric vault id
        vault_name:     human-readable name
        output_path:    destination file path
        psnx_path:      .psnx file source (if missing, identity files are skipped)
        blend_path:     .blend_data file source (if missing, idem)
        notes:          optional free-text note stored in manifest
        suite_name:     crypto suite name (default: current)

    Returns:
        A summary dict (manifest summary + output_path + total size).

    Raises:
        ExportError on any failure.
    """
    if not vault_key or len(vault_key) < 32:
        raise ExportError("vault_key must be at least 32 bytes")
    if not vault_id:
        raise ExportError("vault_id is required")

    output_path = Path(output_path)
    if output_path.exists() and output_path.is_dir():
        raise ExportError(f"output_path must be a file, not a directory: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    depositor_prefix = _depositor_prefix(vault_key)

    # 1. Discover inventory
    try:
        inventory: list = collect_vault_inventory(
            vault_id=vault_id,
            vault_number=vault_number,
            vault_name=vault_name,
            depositor_prefix=depositor_prefix,
            psnx_path=Path(psnx_path) if psnx_path else None,
            blend_path=Path(blend_path) if blend_path else None,
        )
    except Exception as exc:
        raise ExportError(f"inventory collection failed: {exc}")

    if not inventory:
        raise ExportError(
            "no files discovered for export - check vault_id/name/depositor_prefix"
        )

    # 2. Build manifest (without MAC yet)
    suite = get_suite(suite_name)
    archive_salt = os.urandom(suite.salt_len)

    manifest = Manifest(
        vault_id=vault_id,
        vault_number=vault_number,
        vault_name=vault_name,
        depositor_prefix=depositor_prefix,
        exported_at=datetime.now(timezone.utc).isoformat(),
        archive_salt=archive_salt,
        file_inventory=[
            FileEntry(
                archive_path=e.archive_path, size=e.size, sha256=e.sha256
            )
            for e in inventory
        ],
        transfer_mode="snapshot",
        notes=notes or "",
        format_suite=suite_name,
    )

    # 3. Compute the integrity MAC over canonical manifest bytes
    try:
        manifest.integrity_mac = compute_integrity_mac(
            vault_key=vault_key,
            salt=archive_salt,
            manifest_canonical=manifest.mac_input(),
            suite_name=suite_name,
        )
    except ArchiveError as exc:
        raise ExportError(f"failed to compute integrity MAC: {exc}")

    manifest_bytes = manifest.to_json().encode("utf-8")

    # 4. Read each file's content (small enough to fit in RAM for an MVP)
    payload_entries = []
    for inv in inventory:
        try:
            content = inv.source_path.read_bytes()
        except Exception as exc:
            raise ExportError(f"unable to read {inv.source_path}: {exc}")
        payload_entries.append((inv.archive_path, content))

    # 5. Build encrypted ZIP and write
    try:
        zip_bytes = build_zip_from_files(payload_entries, manifest_bytes)
        write_archive(
            output_path,
            vault_key=vault_key,
            zip_bytes=zip_bytes,
            suite_name=suite_name,
        )
    except ArchiveError as exc:
        raise ExportError(f"failed to write archive: {exc}")

    # 6. Cleanup registry slice tmp file (created by inventory.py)
    try:
        from config.paths import get_vaults_root
        tmp_registry = get_vaults_root().parent / ".migration_tmp_registry_slice.json"
        if tmp_registry.exists():
            tmp_registry.unlink()
    except Exception:
        pass

    summary = manifest.summary()
    summary["output_path"] = str(output_path)
    summary["archive_size_bytes"] = output_path.stat().st_size
    return summary
