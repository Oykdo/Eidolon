"""Interactive CLI for 7D Escrow, wired into the Eidolon launcher.

Exposes ``escrow_menu(vault_key, vault_label)`` which paints a small sub-menu
(Deposit / List / Retrieve / Verify / Delete / Back) and dispatches to the
high-level api functions.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from . import api
from .conditions import Condition, TimeLock
from .sealer import SealError, UnsealError


# ---------------------------------------------------------------------------
# Soft import of launcher's colored helpers; fall back to no-color if absent.
# ---------------------------------------------------------------------------

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


def _prompt_int(message: str, default: int) -> int:
    raw = _prompt(message, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "..."


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def _action_deposit(vault_key: bytes, vault_label: str) -> None:
    print_section("7D ESCROW - DEPOSIT")
    src = _prompt("Path of the file to escrow (leave empty for inline text)")
    payload: bytes
    if src:
        path = Path(src).expanduser()
        if not path.is_file():
            print_status(f"file not found: {path}", "error")
            return
        payload = path.read_bytes()
        default_label = path.name
    else:
        text = _prompt("Inline secret text")
        if not text:
            print_status("empty payload, aborting", "warn")
            return
        payload = text.encode("utf-8")
        default_label = "inline"

    label = _prompt("Label (free text)", default_label)

    # Ownership is enforced cryptographically: the AES key, the HMAC,
    # and the on-disk partitioning are all derived from the vault key.
    # No explicit "owner match" condition is needed in Phase 1.
    conditions: List[Condition] = []
    days = _prompt_int("Time lock in days (0 = no lock)", 0)
    if days > 0:
        release_after = datetime.now(timezone.utc) + timedelta(days=days)
        conditions.append(TimeLock(release_after=release_after))
        print_status(f"time lock set until {release_after.isoformat()}", "info")

    combined_conditions: List[Condition] = conditions

    try:
        escrow_id = api.deposit_document(
            payload=payload,
            vault_key=vault_key,
            conditions=combined_conditions,
            label=label,
        )
    except SealError as exc:
        print_status(f"sealing failed: {exc}", "error")
        return

    print_status(f"deposited as {escrow_id} ({len(payload)} bytes)", "ok")
    print(f"    {Colors.DIM}tip: use [2] List to see all escrows or [3] Retrieve with this id{Colors.RESET}")


def _action_list(vault_key: bytes, vault_label: str) -> None:
    print_section("7D ESCROW - LIST")
    summaries = api.list_escrows(vault_key)
    if not summaries:
        print_status("no escrows in this vault", "info")
        return

    header = f"    {'ID':<24} {'LABEL':<24} {'SIZE':>10}  CONDITIONS  DEPOSITED"
    print(f"{Colors.BOLD}{header}{Colors.RESET}")
    print("    " + "-" * (len(header) - 4))
    for s in summaries:
        cond_repr = ",".join(s["conditions"]) if s["conditions"] else "owner"
        print(
            f"    {_truncate(s['escrow_id'], 24):<24} "
            f"{_truncate(s['label'] or '-', 24):<24} "
            f"{s['payload_size']:>10}  "
            f"{_truncate(cond_repr, 10):<10}  "
            f"{s['deposited_at']}"
        )
    print(f"\n    {Colors.DIM}Total: {len(summaries)} escrow(s){Colors.RESET}")


def _resolve_escrow_id(vault_key: bytes, raw: str) -> Optional[str]:
    """Resolve a user input to a full escrow_id.

    Accepts: empty (lists and lets user pick by number), a number (1-based index
    from list_escrows), or any unique id prefix. The picker loops until the
    user supplies something valid or explicitly cancels with 'Q'.
    Returns the full id, or None if cancelled / no escrows.
    """
    summaries = api.list_escrows(vault_key)
    if not summaries:
        print_status("no escrows in this vault", "info")
        return None

    def _match(value: str) -> Optional[str]:
        """Match a non-empty value against the summaries; print error and return None on miss."""
        if value.isdigit():
            idx = int(value)
            if 1 <= idx <= len(summaries):
                return summaries[idx - 1]["escrow_id"]
            print_status(f"index {idx} out of range (1..{len(summaries)})", "warn")
            return None
        exact = [s for s in summaries if s["escrow_id"] == value]
        if exact:
            return exact[0]["escrow_id"]
        prefix_matches = [s for s in summaries if s["escrow_id"].startswith(value)]
        if len(prefix_matches) == 1:
            return prefix_matches[0]["escrow_id"]
        if len(prefix_matches) > 1:
            print_status(f"prefix '{value}' is ambiguous ({len(prefix_matches)} matches)", "warn")
            return None
        print_status(f"no escrow matches '{value}'", "warn")
        return None

    if raw:
        result = _match(raw)
        if result:
            return result
        # Fall through to interactive picker so the user isn't kicked back.

    print()
    print(f"    {Colors.BOLD}Available escrows:{Colors.RESET}")
    for i, s in enumerate(summaries, 1):
        label = _truncate(s["label"] or "-", 30)
        short_id = _truncate(s["escrow_id"], 18)
        print(f"    {Colors.YELLOW}[{i}]{Colors.RESET} {short_id}  {Colors.DIM}{label}  {s['payload_size']}B{Colors.RESET}")
    print()

    while True:
        choice = _prompt("Pick a number, paste the full id, or 'Q' to cancel").strip()
        if not choice:
            print_status("empty input - type a number, an id, or 'Q' to cancel", "warn")
            continue
        if choice.lower() in ("q", "quit", "cancel", "back"):
            print_status("cancelled", "info")
            return None
        result = _match(choice)
        if result:
            return result
        # _match already printed the warning; loop again.


_MAGIC_EXTENSIONS = [
    (b"\x89PNG\r\n\x1a\n",   ".png"),
    (b"\xff\xd8\xff",        ".jpg"),
    (b"GIF87a",              ".gif"),
    (b"GIF89a",              ".gif"),
    (b"%PDF-",               ".pdf"),
    (b"PK\x03\x04",          ".zip"),
    (b"PK\x05\x06",          ".zip"),
    (b"BM",                  ".bmp"),
    (b"\x1f\x8b",            ".gz"),
    (b"7z\xbc\xaf\x27\x1c",  ".7z"),
    (b"Rar!\x1a\x07",        ".rar"),
    (b"ID3",                 ".mp3"),
    (b"OggS",                ".ogg"),
    (b"RIFF",                ".wav"),  # also webp/avi - close enough as default
    (b"\x00\x00\x00\x18ftyp", ".mp4"),
    (b"\x00\x00\x00\x1cftyp", ".mp4"),
]


def _guess_extension(payload: bytes, label: str) -> str:
    """Best-effort: derive an extension from magic bytes, then label, else .bin."""
    head = payload[:16]
    for magic, ext in _MAGIC_EXTENSIONS:
        if head.startswith(magic):
            return ext
    # If label already has an extension, use it.
    suffix = Path(label).suffix
    if suffix and 1 < len(suffix) <= 5:
        return suffix
    # Plain UTF-8 text?
    try:
        payload[:4096].decode("utf-8")
        return ".txt"
    except UnicodeDecodeError:
        return ".bin"


def _sanitize_stem(label: str) -> str:
    stem = Path(label).stem or "escrow"
    cleaned = "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in stem)
    return cleaned or "escrow"


def _action_retrieve(vault_key: bytes, vault_label: str) -> None:
    print_section("7D ESCROW - RETRIEVE")
    raw = _prompt("Escrow ID (number, prefix, or leave empty to list)")
    escrow_id = _resolve_escrow_id(vault_key, raw)
    if not escrow_id:
        return

    # Look up the label before unsealing so we can pre-fill a sensible save path.
    summaries = api.list_escrows(vault_key)
    label = next((s["label"] for s in summaries if s["escrow_id"] == escrow_id), "") or "escrow"

    try:
        payload = api.retrieve_document(escrow_id, vault_key)
    except KeyError:
        print_status(f"escrow {escrow_id} not found", "error")
        return
    except UnsealError as exc:
        print_status(f"unable to retrieve: {exc}", "error")
        return

    ext = _guess_extension(payload, label)
    stem = _sanitize_stem(label)
    default_dir = Path.home() / "Downloads"
    if not default_dir.is_dir():
        default_dir = Path.cwd()
    default_path = default_dir / f"{stem}{ext}"

    print()
    print(f"    {Colors.DIM}Detected format: {ext} ({len(payload):,} bytes){Colors.RESET}")
    print(f"    {Colors.DIM}Default save path: {default_path}{Colors.RESET}")
    out_path_str = _prompt("Save path (Enter = default, or type 'preview' to see content)").strip()

    if out_path_str.lower() == "preview":
        preview = payload[:512]
        try:
            text = preview.decode("utf-8")
            print(f"\n    {Colors.DIM}--- preview (first {len(preview)} bytes) ---{Colors.RESET}")
            print(f"    {text}")
            print(f"    {Colors.DIM}--- end preview ---{Colors.RESET}")
        except UnicodeDecodeError:
            print(f"\n    {Colors.DIM}(binary content, hex preview){Colors.RESET}")
            print(f"    {preview[:64].hex()}")
        print_status(f"retrieved {len(payload):,} bytes (not saved)", "info")
        return

    out_path = Path(out_path_str).expanduser() if out_path_str else default_path

    # If the user pointed at a directory (existing or ending with a separator),
    # append the default filename so the write doesn't fail with "permission denied".
    if out_path.is_dir() or out_path_str.endswith(("/", "\\")):
        out_path = out_path / default_path.name

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(payload)
    except OSError as exc:
        print_status(f"could not write to {out_path}: {exc}", "error")
        return
    print_status(f"{len(payload):,} bytes written to {out_path}", "ok")


def _action_verify(vault_key: bytes, vault_label: str) -> None:
    print_section("7D ESCROW - VERIFY")
    raw = _prompt("Escrow ID (number, prefix, or 'all' for full sweep)").strip()
    if raw.lower() in ("all", "*"):
        summaries = api.list_escrows(vault_key)
        ok_count = bad_count = 0
        for s in summaries:
            ok, reason = api.verify_integrity(s["escrow_id"], vault_key)
            if ok:
                ok_count += 1
            else:
                bad_count += 1
                print_status(f"{s['escrow_id']}: {reason}", "warn")
        print_status(f"verified {ok_count} ok / {bad_count} failed", "ok" if bad_count == 0 else "warn")
        return

    escrow_id = _resolve_escrow_id(vault_key, raw)
    if not escrow_id:
        return
    ok, reason = api.verify_integrity(escrow_id, vault_key)
    if ok:
        print_status(f"{escrow_id}: integrity ok", "ok")
    else:
        print_status(f"{escrow_id}: {reason}", "error")


def _action_delete(vault_key: bytes, vault_label: str) -> None:
    print_section("7D ESCROW - DELETE")
    raw = _prompt("Escrow ID (number, prefix, or leave empty to list)")
    escrow_id = _resolve_escrow_id(vault_key, raw)
    if not escrow_id:
        return
    confirm = _prompt(f"Type DELETE to confirm removal of {escrow_id}").upper()
    if confirm != "DELETE":
        print_status("aborted", "info")
        return
    if api.delete_escrow(escrow_id, vault_key):
        print_status(f"{escrow_id} removed", "ok")
    else:
        print_status(f"{escrow_id} not found", "warn")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

_ACTIONS = (
    ("1", "Deposit document",  _action_deposit),
    ("2", "List escrows",      _action_list),
    ("3", "Retrieve document", _action_retrieve),
    ("4", "Verify integrity",  _action_verify),
    ("5", "Delete escrow",     _action_delete),
)


def escrow_menu(vault_key: bytes, vault_label: str = "") -> None:
    """Interactive sub-menu invoked from launcher [X]."""
    if not vault_key or len(vault_key) < 32:
        print_status("invalid vault key (auth required first)", "error")
        return

    while True:
        print_section("7D ESCROW")
        if vault_label:
            print(f"    {Colors.DIM}vault: {vault_label}{Colors.RESET}")
        print()
        for key, label, _ in _ACTIONS:
            print(f"    {Colors.YELLOW}[{key}]{Colors.RESET}  {label}")
        print(f"    {Colors.YELLOW}[Q]{Colors.RESET}  Back to main menu")
        print()

        choice = _prompt("Choice", "Q").upper()
        if choice in ("Q", "QUIT", "EXIT", "B", "BACK", ""):
            return

        for key, _, handler in _ACTIONS:
            if choice == key:
                try:
                    handler(vault_key, vault_label)
                except Exception as exc:  # pragma: no cover - last-chance UI safety
                    print_status(f"unexpected error: {exc}", "error")
                input(f"\n    {Colors.DIM}Press Enter to continue...{Colors.RESET}")
                break
        else:
            print_status("invalid choice", "warn")
