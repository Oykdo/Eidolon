"""Interactive CLI for vault migration, wired into the Eidolon launcher.

Exposes ``migration_menu(vault_key, identity, psnx_path, blend_path)``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .exporter import export_vault, ExportError
from .importer import import_vault, inspect_archive, ImportConflict
from .importer import ImportError as MigrationImportError


try:
    from src.ui.launcher import Colors, print_section, print_status  # type: ignore
except Exception:  # pragma: no cover
    class _PlainColors:
        RESET = BOLD = DIM = ""
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = ""
    Colors = _PlainColors()  # type: ignore

    def print_section(title: str) -> None:
        print(f"\n=== {title} ===\n")

    def print_status(message: str, status: str = "info") -> None:
        prefix = {"ok": "[OK]", "error": "[X]", "warn": "[!]"}.get(status, "[i]")
        print(f"    {prefix} {message}")


def _prompt(message: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        raw = input(f"    {message}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""
    return raw or default


def _action_export(
    vault_key: bytes,
    vault_id: str,
    vault_number: int,
    vault_name: str,
    psnx_path: Optional[Path],
    blend_path: Optional[Path],
) -> None:
    print_section("VAULT MIGRATION - EXPORT (SNAPSHOT)")
    print(f"    {Colors.DIM}This produces a portable .eidolon_keybundle_full file{Colors.RESET}")
    print(f"    {Colors.DIM}containing everything needed to restore this vault elsewhere.{Colors.RESET}")
    print()
    print(f"    {Colors.YELLOW}!{Colors.RESET} {Colors.BOLD}Snapshot mode warning:{Colors.RESET}")
    print(f"    {Colors.DIM}  - This machine remains fully usable after export.{Colors.RESET}")
    print(f"    {Colors.DIM}  - If you also use the imported vault on another machine,{Colors.RESET}")
    print(f"    {Colors.DIM}    progression will diverge between machines (no auto-sync).{Colors.RESET}")
    print()

    default_dir = Path.home() / "Documents"
    if not default_dir.exists():
        default_dir = Path.home()
    safe_name = "".join(c for c in vault_name if c.isalnum() or c in "-_")
    default_name = f"{safe_name or 'vault'}_snapshot.eidolon_keybundle_full"
    default_path = default_dir / default_name

    target_str = _prompt(
        "Output path",
        default=str(default_path),
    )
    if not target_str:
        print_status("aborted", "info")
        return

    out_path = Path(target_str).expanduser()
    if out_path.is_dir():
        out_path = out_path / default_name

    if out_path.exists():
        overwrite = _prompt(
            f"File exists ({out_path.name}). Overwrite? (y/N)", "n"
        ).lower()
        if overwrite != "y":
            print_status("aborted", "info")
            return

    notes = _prompt("Notes (optional, stored in archive)", "")

    try:
        summary = export_vault(
            vault_key=vault_key,
            vault_id=vault_id,
            vault_number=vault_number,
            vault_name=vault_name,
            output_path=out_path,
            psnx_path=psnx_path,
            blend_path=blend_path,
            notes=notes,
        )
    except ExportError as exc:
        print_status(f"export failed: {exc}", "error")
        return

    print()
    print_status(f"exported successfully", "ok")
    print(f"    {Colors.DIM}Path:        {summary['output_path']}{Colors.RESET}")
    print(f"    {Colors.DIM}Archive size: {summary['archive_size_bytes']:,} bytes{Colors.RESET}")
    print(f"    {Colors.DIM}File count:   {summary['file_count']}{Colors.RESET}")
    print(f"    {Colors.DIM}Total payload: {summary['total_bytes']:,} bytes{Colors.RESET}")
    print()
    print(f"    {Colors.YELLOW}!{Colors.RESET} Keep this file safe; possession is enough to restore the vault.")


def _action_inspect(vault_key: bytes) -> None:
    print_section("VAULT MIGRATION - INSPECT")
    target = _prompt("Path to archive (.eidolon_keybundle_full)")
    if not target:
        return

    archive_path = Path(target).expanduser()
    if not archive_path.is_file():
        print_status(f"file not found: {archive_path}", "error")
        return

    try:
        summary = inspect_archive(archive_path, vault_key)
    except MigrationImportError as exc:
        print_status(f"inspection failed: {exc}", "error")
        return

    print()
    print(f"    {Colors.BOLD}Vault ID:{Colors.RESET}     {summary['vault_id']}")
    print(f"    {Colors.BOLD}Vault number:{Colors.RESET} #{summary['vault_number']}")
    print(f"    {Colors.BOLD}Vault name:{Colors.RESET}   {summary['vault_name']}")
    print(f"    {Colors.BOLD}Exported at:{Colors.RESET}  {summary['exported_at']}")
    print(f"    {Colors.BOLD}Mode:{Colors.RESET}         {summary['transfer_mode']}")
    print(f"    {Colors.BOLD}Files:{Colors.RESET}        {summary['file_count']} ({summary['total_bytes']:,} bytes)")
    print(f"    {Colors.BOLD}Schema:{Colors.RESET}       v{summary['schema_version']} / suite={summary['format_suite']}")
    print()
    if summary["verified"]:
        print_status("integrity verified - archive is genuine", "ok")
    else:
        print_status("integrity NOT verified", "error")
        if not summary["mac_ok"]:
            print(f"    {Colors.RED}    MAC: {summary['mac_reason']}{Colors.RESET}")
        if not summary["files_ok"]:
            print(f"    {Colors.RED}    Files: {summary['files_reason']}{Colors.RESET}")


def _action_import(vault_key: bytes) -> None:
    print_section("VAULT MIGRATION - IMPORT")
    target = _prompt("Path to archive (.eidolon_keybundle_full)")
    if not target:
        return

    archive_path = Path(target).expanduser()
    if not archive_path.is_file():
        print_status(f"file not found: {archive_path}", "error")
        return

    # Inspect first
    try:
        summary = inspect_archive(archive_path, vault_key)
    except MigrationImportError as exc:
        print_status(f"archive unreadable: {exc}", "error")
        return

    print()
    print(f"    Vault to import: {Colors.BOLD}{summary['vault_name']}{Colors.RESET} (#{summary['vault_number']})")
    print(f"    Vault ID:        {summary['vault_id']}")
    print(f"    Exported at:     {summary['exported_at']}")
    print(f"    Files:           {summary['file_count']} ({summary['total_bytes']:,} bytes)")
    print()

    if not summary["verified"]:
        print_status("archive failed verification - aborting", "error")
        return

    confirm = _prompt(
        "Type IMPORT to confirm installation", default=""
    ).strip().upper()
    if confirm != "IMPORT":
        print_status("aborted", "info")
        return

    try:
        result = import_vault(archive_path, vault_key, force_replace=False)
    except ImportConflict as exc:
        print()
        print_status(f"{exc}", "warn")
        print()
        forced = _prompt(
            "Force replace anyway? (creates backup of existing data) Type REPLACE",
            default="",
        ).strip().upper()
        if forced != "REPLACE":
            print_status("aborted", "info")
            return
        try:
            result = import_vault(archive_path, vault_key, force_replace=True)
        except MigrationImportError as exc2:
            print_status(f"import failed: {exc2}", "error")
            return
    except MigrationImportError as exc:
        print_status(f"import failed: {exc}", "error")
        return

    print()
    print_status(
        f"imported {result['installed_count']} file(s)",
        "ok",
    )
    print(f"    {Colors.DIM}refresh_mode={result['refresh_mode']}, forced={result.get('forced', False)}{Colors.RESET}")
    if result.get("backup_path"):
        print(f"    {Colors.DIM}Pre-import backup: {result['backup_path']}{Colors.RESET}")
    print(f"    {Colors.DIM}Registry merge: {result['registry_merge_message']}{Colors.RESET}")
    print()
    print_status("Re-authenticate (.psnx + .blend_data) to load this vault.", "info")


_ACTIONS = (
    ("1", "Export vault (snapshot)", "_export"),
    ("2", "Inspect archive (no install)", "_inspect"),
    ("3", "Import archive into this machine", "_import"),
)


def migration_menu(
    *,
    vault_key: bytes,
    vault_id: str,
    vault_number: int,
    vault_name: str,
    psnx_path: Optional[Path] = None,
    blend_path: Optional[Path] = None,
) -> None:
    """Interactive sub-menu for vault export/import."""
    if not vault_key or len(vault_key) < 32:
        print_status("invalid vault key (auth required first)", "error")
        return

    while True:
        print_section("VAULT MIGRATION")
        print(f"    {Colors.DIM}vault: {vault_name} #{vault_number}{Colors.RESET}")
        print()
        for key, label, _ in _ACTIONS:
            print(f"    {Colors.YELLOW}[{key}]{Colors.RESET}  {label}")
        print(f"    {Colors.YELLOW}[Q]{Colors.RESET}  Back to main menu")
        print()

        choice = _prompt("Choice", "Q").upper()
        if choice in ("Q", "QUIT", "EXIT", "B", "BACK", ""):
            return

        if choice == "1":
            _action_export(vault_key, vault_id, vault_number, vault_name, psnx_path, blend_path)
        elif choice == "2":
            _action_inspect(vault_key)
        elif choice == "3":
            _action_import(vault_key)
        else:
            print_status("invalid choice", "warn")
            continue

        input(f"\n    {Colors.DIM}Press Enter to continue...{Colors.RESET}")
