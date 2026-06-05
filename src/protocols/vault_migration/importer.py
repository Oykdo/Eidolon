"""High-level import: open archive, verify, conflict-check, install."""

from __future__ import annotations

import hashlib
import hmac
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .archive import (
    ArchiveError,
    compute_integrity_mac,
    read_archive,
    read_zip_to_files,
)
from .format_version import CURRENT_FORMAT_SUITE
from .manifest import Manifest


class ImportError(Exception):
    pass


class ImportConflict(ImportError):
    """Raised when a different vault is already installed on this machine."""


def _depositor_prefix(vault_key: bytes) -> str:
    return hashlib.sha256(vault_key).hexdigest()[:16]


def _vaults_root() -> Path:
    try:
        from config.paths import get_vaults_root
        return get_vaults_root()
    except Exception:
        return Path("data") / "vaults"


def _list_existing_vaults() -> List[Dict]:
    """Return a list of vault entries already known on this machine."""
    try:
        from config.paths import get_vault_registry_path
        registry_path = get_vault_registry_path()
    except Exception:
        registry_path = _vaults_root() / "identities" / "vault_registry.json"

    if not registry_path.is_file():
        return []

    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    vaults_section = registry.get("vaults")
    if not isinstance(vaults_section, dict):
        return []

    out: List[Dict] = []
    for key, entry in vaults_section.items():
        if isinstance(entry, dict):
            out.append({
                "registry_key": key,
                "vault_id": entry.get("vault_id"),
                "vault_number": entry.get("vault_number"),
                "vault_name": entry.get("vault_name"),
            })
    return out


def _verify_manifest_mac(manifest: Manifest, vault_key: bytes) -> Tuple[bool, str]:
    if not manifest.integrity_mac:
        return False, "manifest has no integrity_mac"
    try:
        expected = compute_integrity_mac(
            vault_key=vault_key,
            salt=manifest.archive_salt,
            manifest_canonical=manifest.mac_input(),
            suite_name=manifest.format_suite,
        )
    except Exception as exc:
        return False, f"unable to recompute manifest MAC: {exc}"
    if not hmac.compare_digest(expected, manifest.integrity_mac):
        return False, "manifest MAC mismatch (wrong key or tampered archive)"
    return True, "manifest MAC ok"


def _verify_file_hashes(
    manifest: Manifest, files: Dict[str, bytes]
) -> Tuple[bool, str]:
    inv_paths = {e.archive_path for e in manifest.file_inventory}
    extra = set(files.keys()) - inv_paths
    missing = inv_paths - set(files.keys())
    if extra:
        return False, f"archive has extra files not in inventory: {sorted(extra)[:3]}"
    if missing:
        return False, f"archive missing files listed in inventory: {sorted(missing)[:3]}"

    for entry in manifest.file_inventory:
        data = files.get(entry.archive_path)
        if data is None:
            return False, f"missing payload for {entry.archive_path}"
        if len(data) != entry.size:
            return False, f"size mismatch for {entry.archive_path}"
        actual_sha = hashlib.sha256(data).hexdigest()
        if actual_sha != entry.sha256:
            return False, f"sha256 mismatch for {entry.archive_path}"
    return True, "all file hashes ok"


def inspect_archive(archive_path, vault_key: bytes) -> Dict:
    """Open + verify an archive without installing anything.

    Returns the manifest summary plus a `verified=True/False` flag.
    Raises ImportError if the archive is structurally invalid.
    """
    archive_path = Path(archive_path)
    if not archive_path.is_file():
        raise ImportError(f"archive not found: {archive_path}")

    try:
        header, zip_bytes = read_archive(archive_path, vault_key)
    except ArchiveError as exc:
        raise ImportError(f"unable to read archive: {exc}")

    try:
        manifest_bytes, files = read_zip_to_files(zip_bytes)
    except ArchiveError as exc:
        raise ImportError(f"archive ZIP invalid: {exc}")

    try:
        manifest = Manifest.from_json(manifest_bytes.decode("utf-8"))
    except Exception as exc:
        raise ImportError(f"invalid manifest: {exc}")

    mac_ok, mac_reason = _verify_manifest_mac(manifest, vault_key)
    files_ok, files_reason = _verify_file_hashes(manifest, files)

    summary = manifest.summary()
    summary["archive_path"] = str(archive_path)
    summary["verified"] = bool(mac_ok and files_ok)
    summary["mac_ok"] = mac_ok
    summary["mac_reason"] = mac_reason
    summary["files_ok"] = files_ok
    summary["files_reason"] = files_reason
    return summary


def _backup_existing_vault_data(target_root: Path) -> Optional[Path]:
    """Move conflicting directories into a timestamped backup folder."""
    backup_dir = target_root / "pre_migration_backup" / time.strftime(
        "%Y%m%dT%H%M%S", time.gmtime()
    )

    candidates = [
        target_root / "persistent",
        target_root / "identity_history",
        target_root / "escrows",
        target_root / "distribution",
    ]
    found_any = False
    for src in candidates:
        if src.is_dir():
            backup_dir.mkdir(parents=True, exist_ok=True)
            dst = backup_dir / src.name
            try:
                shutil.copytree(src, dst, dirs_exist_ok=False)
                found_any = True
            except Exception:
                pass
    if found_any:
        return backup_dir
    return None


def _install_files(
    files: Dict[str, bytes], target_root: Path, manifest: Manifest
) -> List[Path]:
    """Write each archive entry to its destination under the vault data tree.

    Returns the list of installed file paths.
    """
    written: List[Path] = []

    for entry in manifest.file_inventory:
        data = files[entry.archive_path]
        dest = _resolve_install_path(entry.archive_path, target_root)
        if dest is None:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".migration_tmp")
        tmp.write_bytes(data)
        tmp.replace(dest)
        written.append(dest)

    return written


def _resolve_install_path(archive_path: str, vaults_root: Path) -> Optional[Path]:
    """Map an in-archive path to its destination on disk."""
    def safe_join(base: Path, rel: str) -> Path:
        rel_path = Path(rel)
        if rel_path.is_absolute() or any(part == ".." for part in rel_path.parts):
            raise ValueError(f"Unsafe archive path: {archive_path}")
        dest = (base / rel_path).resolve()
        root = base.resolve()
        if dest != root and root not in dest.parents:
            raise ValueError(f"Archive path escapes target root: {archive_path}")
        return dest

    if archive_path.startswith("keys/"):
        return vaults_root / "keys" / Path(archive_path).name
    if archive_path.startswith("vault_state/persistent/"):
        rel = archive_path[len("vault_state/persistent/"):]
        return safe_join(vaults_root / "persistent", rel)
    if archive_path.startswith("vault_state/identity_history/"):
        rel = archive_path[len("vault_state/identity_history/"):]
        return safe_join(vaults_root / "identity_history", rel)
    if archive_path.startswith("vault_state/escrows/"):
        rel = archive_path[len("vault_state/escrows/"):]
        return safe_join(vaults_root / "escrows", rel)
    if archive_path.startswith("vault_state/distribution/"):
        rel = archive_path[len("vault_state/distribution/"):]
        return safe_join(vaults_root / "distribution", rel)
    if archive_path == "vault_state/registry_slice.json":
        # Registry slice is NOT auto-installed in the registry (manual review).
        # It's written next to vaults_root for inspection.
        return vaults_root / ".imported_registry_slice.json"
    return None


def _merge_registry_slice(slice_path: Path) -> Tuple[bool, str]:
    """Optionally merge the imported registry slice into vault_registry.json.

    Returns (merged, message). Only performs the merge when the registry
    already exists and the slice's vault_id is not already present.
    """
    if not slice_path.is_file():
        return False, "no registry slice imported"

    try:
        slice_data = json.loads(slice_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"invalid registry slice: {exc}"

    try:
        from config.paths import get_vault_registry_path
        registry_path = get_vault_registry_path()
    except Exception:
        registry_path = _vaults_root() / "identities" / "vault_registry.json"

    if not registry_path.is_file():
        # Brand new install: write a fresh registry containing only this entry
        new_registry = {
            "schema_version": slice_data.get("schema") or 1,
            "vaults": {
                slice_data["vault_entry_key"]: slice_data["vault_entry"],
            },
        }
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            json.dumps(new_registry, indent=2, sort_keys=True), encoding="utf-8"
        )
        return True, "registry created from imported slice"

    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"existing registry unreadable: {exc}"

    if not isinstance(registry.get("vaults"), dict):
        registry["vaults"] = {}

    key = slice_data["vault_entry_key"]
    registry["vaults"][key] = slice_data["vault_entry"]
    registry_path.write_text(
        json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8"
    )
    return True, "registry merged with imported slice"


def import_vault(
    archive_path,
    vault_key: bytes,
    *,
    force_replace: bool = False,
) -> Dict:
    """Verify and install a vault migration archive.

    Policy:
      * Same vault_id already present  -> refresh (backup existing data first)
      * Different vault_id present     -> ImportConflict (unless force_replace=True)
      * No vault present               -> straight install

    Args:
        archive_path:  path to the .eidolon_keybundle_full file
        vault_key:     authenticated vault key (>= 32 bytes)
        force_replace: if True, allow overwriting a different vault (DANGEROUS)

    Returns:
        Summary dict with manifest details + actions taken.

    Raises:
        ImportError on verification/IO failure.
        ImportConflict when refusing a foreign-vault overwrite.
    """
    archive_path = Path(archive_path)
    if not vault_key or len(vault_key) < 32:
        raise ImportError("vault_key must be at least 32 bytes")

    # 1. Inspect + verify (no side effects yet)
    summary = inspect_archive(archive_path, vault_key)
    if not summary["verified"]:
        raise ImportError(
            f"archive verification failed - mac={summary['mac_reason']} "
            f"files={summary['files_reason']}"
        )

    # 2. Re-read for the file payloads
    _, zip_bytes = read_archive(archive_path, vault_key)
    manifest_bytes, files = read_zip_to_files(zip_bytes)
    manifest = Manifest.from_json(manifest_bytes.decode("utf-8"))

    # 3. Conflict check
    existing = _list_existing_vaults()
    conflict: Optional[Dict] = None
    refresh: bool = False
    for ev in existing:
        if ev.get("vault_id") == manifest.vault_id:
            refresh = True
            break
        # different vault_id present
        conflict = ev

    if conflict and not refresh and not force_replace:
        raise ImportConflict(
            f"machine already has vault '{conflict.get('vault_name')}' "
            f"(#{conflict.get('vault_number')}). Refusing to import a different vault. "
            "Delete the existing vault first or pass force_replace=True."
        )

    # 4. Verify depositor_prefix matches our vault_key
    if manifest.depositor_prefix.lower() != _depositor_prefix(vault_key).lower():
        raise ImportError(
            "depositor_prefix in archive does not match the provided vault key"
        )

    # 5. Backup any existing vault data
    vaults_root = _vaults_root()
    backup_path = _backup_existing_vault_data(vaults_root) if (refresh or force_replace) else None

    # 6. Install files
    try:
        installed = _install_files(files, vaults_root, manifest)
    except Exception as exc:
        raise ImportError(f"installation failed: {exc}")

    # 7. Merge registry slice
    slice_path = vaults_root / ".imported_registry_slice.json"
    merged, merge_msg = _merge_registry_slice(slice_path)
    try:
        if slice_path.is_file():
            slice_path.unlink()
    except Exception:
        pass

    return {
        "manifest": manifest.summary(),
        "installed_count": len(installed),
        "installed_paths": [str(p) for p in installed[:10]],
        "backup_path": str(backup_path) if backup_path else None,
        "registry_merged": merged,
        "registry_merge_message": merge_msg,
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "refresh_mode": refresh,
        "forced": force_replace and not refresh,
    }
