"""Local filesystem persistence for 7D Escrow envelopes.

Layout::

    <vaults_root>/escrows/<depositor_prefix>/<escrow_id>.escrow7d

The depositor prefix is the first 16 hex chars of sha256(vault_key) — same as
``EscrowEnvelope.depositor_vault_id_prefix``. This keeps escrows from
different vaults isolated on disk without exposing the vault key.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, List, Optional

from .envelope import EscrowEnvelope, ESCROW_FILE_SUFFIX

try:
    from config.paths import get_vaults_root
except Exception:  # pragma: no cover - fallback for unconfigured envs
    def get_vaults_root() -> Path:
        return Path("data") / "vaults"


class EscrowStoreError(Exception):
    pass


class EscrowStore:
    """File-backed escrow store scoped to one depositor vault."""

    def __init__(self, depositor_prefix: str, base_dir: Optional[Path] = None):
        if not depositor_prefix:
            raise EscrowStoreError("depositor_prefix is required")
        if base_dir is None:
            base_dir = get_vaults_root() / "escrows"
        self.base_dir = Path(base_dir)
        self.dir = self.base_dir / depositor_prefix.lower()
        self.dir.mkdir(parents=True, exist_ok=True)
        self.depositor_prefix = depositor_prefix.lower()

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
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(envelope.to_json(), encoding="utf-8")
        tmp.replace(path)
        return path

    def load(self, escrow_id: str) -> Optional[EscrowEnvelope]:
        path = self._path_for(escrow_id)
        if not path.exists():
            return None
        try:
            return EscrowEnvelope.from_json(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError) as exc:
            raise EscrowStoreError(f"corrupt envelope at {path}: {exc}")

    def delete(self, escrow_id: str) -> bool:
        path = self._path_for(escrow_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def iter_envelopes(self) -> Iterator[EscrowEnvelope]:
        for path in sorted(self.dir.glob(f"*{ESCROW_FILE_SUFFIX}")):
            try:
                yield EscrowEnvelope.from_json(path.read_text(encoding="utf-8"))
            except Exception:
                continue

    def list_summaries(self) -> List[dict]:
        return [env.summary() for env in self.iter_envelopes()]

    def __len__(self) -> int:
        return sum(1 for _ in self.dir.glob(f"*{ESCROW_FILE_SUFFIX}"))
