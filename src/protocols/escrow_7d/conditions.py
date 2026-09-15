"""Release conditions for escrowed documents.

Conditions are evaluated at retrieve time. Each condition implements
``is_satisfied(context)`` and serializes to/from a JSON-friendly dict so the
envelope can be reloaded across processes.
"""

from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Iterator, List, Tuple

from .errors import EscrowError


class ConditionError(EscrowError):
    """Raised when a condition cannot be evaluated or its data is malformed."""


MAX_CONDITION_DEPTH: int = 32
"""Deepest nesting of composite conditions accepted, at seal and at unseal.

A fixed bound makes the decision independent of the reader's call stack: an
envelope accepted by ``seal()`` is never refused later as "too deep".
"""


class Condition(ABC):
    type_id: str = ""

    @abstractmethod
    def is_satisfied(self, context: Dict) -> Tuple[bool, str]:
        """Return (ok, reason). ``reason`` is human readable on failure."""

    @abstractmethod
    def to_dict(self) -> Dict:
        ...

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict) -> "Condition":
        ...

    def walk(self) -> Iterator["Condition"]:
        """Yield this condition and, for composites, every descendant."""
        yield self

    @staticmethod
    def deserialize(data: Dict, _depth: int = 0) -> "Condition":
        if not isinstance(data, dict):
            raise ConditionError(
                f"condition entry must be an object, got {type(data).__name__}"
            )
        if _depth > MAX_CONDITION_DEPTH:
            raise ConditionError(
                f"condition tree deeper than {MAX_CONDITION_DEPTH} levels"
            )
        type_id = data.get("type")
        for klass in _ALL_CONDITION_CLASSES:
            if klass.type_id == type_id:
                if issubclass(klass, _Composite):
                    return klass.from_dict(data, _depth)
                return klass.from_dict(data)
        raise ConditionError(f"Unknown condition type: {type_id!r}")


class TimeLock(Condition):
    """Released only after a specific UTC datetime."""

    type_id = "time_lock"

    def __init__(self, release_after: datetime):
        if release_after.tzinfo is None:
            release_after = release_after.replace(tzinfo=timezone.utc)
        self.release_after = release_after.astimezone(timezone.utc)

    def is_satisfied(self, context: Dict) -> Tuple[bool, str]:
        now = datetime.now(timezone.utc)
        if now >= self.release_after:
            return True, "time lock passed"
        delta = self.release_after - now
        return False, f"locked for {delta} more"

    def to_dict(self) -> Dict:
        return {"type": self.type_id, "release_after": self.release_after.isoformat()}

    @classmethod
    def from_dict(cls, data: Dict) -> "TimeLock":
        try:
            return cls(datetime.fromisoformat(data["release_after"]))
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise ConditionError(f"Invalid TimeLock payload: {exc}")


_VAULT_ID_RE = re.compile(r"[0-9a-f]{64}")
_VAULT_ID_PREFIX_RE = re.compile(r"[0-9a-f]{16}")


def vault_id_from_key(vault_key: bytes) -> str:
    """The public identity of a vault key: ``sha256(vault_key)`` in hex.

    The envelope records its first 16 characters as ``depositor_vault_id_prefix``.
    """
    return hashlib.sha256(vault_key).hexdigest()


class OwnerSignature(Condition):
    """Released only to the vault that made the deposit.

    ``expected_vault_id`` is either the full 64-hex vault id
    (:func:`vault_id_from_key`) or the 16-hex prefix the envelope records and
    lists as ``depositor_vault_id_prefix``; both designate the same vault.
    At unseal time the requester identity is derived from the key that opens
    the envelope and cannot be supplied through ``context``.

    Phase 1 has a single trust root, the vault key, so the depositor always
    satisfies its own OwnerSignature and nobody else can even reach the
    condition (the integrity MAC fails first). ``seal()`` refuses an
    OwnerSignature naming another vault: such an envelope could never be
    opened. Inside ``CombinedAny`` it therefore releases immediately for the
    owner - combine it with a TimeLock through ``CombinedAll``.
    """

    type_id = "owner_signature"

    def __init__(self, expected_vault_id: str):
        if not isinstance(expected_vault_id, str):
            raise ConditionError("OwnerSignature: expected_vault_id must be a string")
        expected = expected_vault_id.strip().lower()
        if not (_VAULT_ID_RE.fullmatch(expected) or _VAULT_ID_PREFIX_RE.fullmatch(expected)):
            raise ConditionError(
                "OwnerSignature: expected_vault_id must be the 64-hex vault id "
                "or its 16-hex prefix"
            )
        self.expected_vault_id = expected

    @classmethod
    def for_vault_key(cls, vault_key: bytes) -> "OwnerSignature":
        """The condition satisfied by the vault that owns ``vault_key``."""
        return cls(vault_id_from_key(vault_key))

    def matches(self, vault_id: str) -> bool:
        """True if the 64-hex ``vault_id`` is the vault this condition names."""
        vault_id = (vault_id or "").lower()
        if len(self.expected_vault_id) == 64:
            return vault_id == self.expected_vault_id
        return vault_id.startswith(self.expected_vault_id)

    def is_satisfied(self, context: Dict) -> Tuple[bool, str]:
        actual = context.get("requester_vault_id") or ""
        if not actual:
            return False, "no requester vault id in context"
        if not self.matches(actual):
            return False, "requester vault id does not match depositor"
        return True, "requester is the depositor"

    def to_dict(self) -> Dict:
        return {"type": self.type_id, "expected_vault_id": self.expected_vault_id}

    @classmethod
    def from_dict(cls, data: Dict) -> "OwnerSignature":
        expected = data.get("expected_vault_id")
        if not isinstance(expected, str):
            raise ConditionError(
                "Invalid OwnerSignature payload: expected_vault_id must be a string"
            )
        return cls(expected_vault_id=expected)


class _Composite(Condition):
    def __init__(self, *children: Condition):
        if not children:
            raise ConditionError(f"{type(self).__name__} requires at least one child")
        self.children: List[Condition] = list(children)

    def walk(self) -> Iterator[Condition]:
        yield self
        for child in self.children:
            yield from child.walk()

    def to_dict(self) -> Dict:
        return {
            "type": self.type_id,
            "children": [c.to_dict() for c in self.children],
        }

    @classmethod
    def from_dict(cls, data: Dict, _depth: int = 0) -> "_Composite":
        raw_children = data.get("children", [])
        if not isinstance(raw_children, list):
            raise ConditionError(f"{cls.__name__} children must be a list")
        children = [Condition.deserialize(c, _depth + 1) for c in raw_children]
        return cls(*children)


class CombinedAll(_Composite):
    """All children must be satisfied."""

    type_id = "combined_all"

    def is_satisfied(self, context: Dict) -> Tuple[bool, str]:
        for child in self.children:
            ok, reason = child.is_satisfied(context)
            if not ok:
                return False, reason
        return True, "all child conditions satisfied"


class CombinedAny(_Composite):
    """At least one child must be satisfied."""

    type_id = "combined_any"

    def is_satisfied(self, context: Dict) -> Tuple[bool, str]:
        reasons: List[str] = []
        for child in self.children:
            ok, reason = child.is_satisfied(context)
            if ok:
                return True, reason
            reasons.append(reason)
        return False, "no child condition satisfied: " + " | ".join(reasons)


_ALL_CONDITION_CLASSES = (
    TimeLock,
    OwnerSignature,
    CombinedAll,
    CombinedAny,
)
