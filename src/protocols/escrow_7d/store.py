"""Local filesystem persistence for 7D Escrow envelopes.

Layout::

    <vaults_root>/escrows/<depositor_prefix>/<escrow_id>.escrow7d

The directory is created by ``save()`` only: listing, loading or verifying
for a vault that never deposited anything leaves no trace on disk.

The depositor prefix is the first 16 hex chars of sha256(vault_key) — same as
``EscrowEnvelope.depositor_vault_id_prefix``. This keeps escrows from
different vaults isolated on disk without exposing the vault key.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

from .envelope import EscrowEnvelope, ESCROW_FILE_SUFFIX
from .errors import EscrowError
from .format_version import FormatError

try:
    from config.paths import get_vaults_root
except Exception:  # pragma: no cover - fallback for unconfigured envs
    def get_vaults_root() -> Path:
        return Path("data") / "vaults"


class EscrowStoreError(EscrowError):
    """Bad escrow id, unreadable file, or envelope outside this store's scope."""


_PREFIX_RE = re.compile(r"[0-9a-f]{16}")


class EscrowStore:
    """File-backed escrow store scoped to one depositor vault."""

    def __init__(self, depositor_prefix: str, base_dir: Optional[Path] = None):
        if not depositor_prefix or not _PREFIX_RE.fullmatch(depositor_prefix.lower()):
            raise EscrowStoreError(
                f"depositor_prefix must be 16 hex characters, got {depositor_prefix!r}"
            )
        if base_dir is None:
            base_dir = get_vaults_root() / "escrows"
        self.base_dir = Path(base_dir)
        self.depositor_prefix = depositor_prefix.lower()
        self.dir = self.base_dir / self.depositor_prefix

    # ------------------------------------------------------------------ paths

    def _path_for(self, escrow_id: str) -> Path:
        if not escrow_id or "/" in escrow_id or "\\" in escrow_id:
            raise EscrowStoreError(f"invalid escrow_id: {escrow_id!r}")
        return self.dir / f"{escrow_id}{ESCROW_FILE_SUFFIX}"

    # ----------------------------------------------------------------- CRUD

    def save(self, envelope: EscrowEnvelope) -> Path:
        if envelope.depositor_vault_id_prefix.lower() != self.depositor_prefix:
            raise EscrowStoreError(
                "envelope depositor prefix does not match this store's scope"
            )
        path = self._path_for(envelope.escrow_id)
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(envelope.to_json())
                fh.flush()
                os.fsync(fh.fileno())
            tmp.replace(path)
        except OSError as exc:
            raise EscrowStoreError(f"cannot write {path}: {exc}") from exc
        return path

    def _read(self, path: Path) -> EscrowEnvelope:
        """Parse one envelope file; every failure becomes EscrowStoreError.

        The file name is part of the contract: an envelope whose inner
        ``escrow_id`` differs from its file name is a copy or a forgery and is
        reported as unreadable rather than listed under either id.
        """
        try:
            envelope = EscrowEnvelope.from_json(path.read_text(encoding="utf-8"))
        except (FormatError, UnicodeDecodeError, OSError) as exc:
            raise EscrowStoreError(f"corrupt envelope at {path}: {exc}") from exc
        except Exception as exc:  # backstop: no raw exception leaves the store
            raise EscrowStoreError(f"corrupt envelope at {path}: {exc!r}") from exc
        expected_id = path.name[: -len(ESCROW_FILE_SUFFIX)]
        if envelope.escrow_id != expected_id:
            raise EscrowStoreError(
                f"corrupt envelope at {path}: escrow_id {envelope.escrow_id!r} "
                f"does not match the file name"
            )
        if envelope.depositor_vault_id_prefix.lower() != self.depositor_prefix:
            raise EscrowStoreError(
                f"envelope at {path} belongs to another vault "
                f"({envelope.depositor_vault_id_prefix})"
            )
        return envelope

    def load(self, escrow_id: str) -> Optional[EscrowEnvelope]:
        """Return the envelope, None if absent, EscrowStoreError if unreadable."""
        path = self._path_for(escrow_id)
        if not path.is_file():
            return None
        return self._read(path)

    def delete(self, escrow_id: str) -> bool:
        """Remove the file (readable or not). True if something was removed."""
        path = self._path_for(escrow_id)
        if not path.is_file():
            return False
        try:
            path.unlink()
        except OSError as exc:
            raise EscrowStoreError(f"cannot delete {path}: {exc}") from exc
        return True

    def scan(self) -> Iterator[Tuple[Path, Optional[EscrowEnvelope], Optional[str]]]:
        """Yield ``(path, envelope, error)`` for every ``.escrow7d`` file.

        Exactly one of ``envelope`` / ``error`` is set. Unreadable files are
        reported, never hidden: a corrupt or newer-format escrow must stay
        visible to the owner.
        """
        if not self.dir.is_dir():
            return
        for path in sorted(self.dir.glob(f"*{ESCROW_FILE_SUFFIX}")):
            if not path.is_file():
                continue
            try:
                yield path, self._read(path), None
            except EscrowStoreError as exc:
                yield path, None, str(exc)

    def iter_envelopes(self) -> Iterator[EscrowEnvelope]:
        for _path, env, _error in self.scan():
            if env is not None:
                yield env

    def list_summaries(self) -> List[dict]:
        return [env.summary() for env in self.iter_envelopes()]

    def list_unreadable(self) -> List[dict]:
        """``[{"escrow_id": ..., "error": ...}]`` for files that cannot be parsed."""
        return [
            {"escrow_id": path.name[: -len(ESCROW_FILE_SUFFIX)], "error": error}
            for path, _env, error in self.scan()
            if error is not None
        ]

    def __len__(self) -> int:
        return sum(1 for _ in self.scan())
