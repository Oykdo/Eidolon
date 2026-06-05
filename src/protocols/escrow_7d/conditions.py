"""Release conditions for escrowed documents.

Conditions are evaluated at retrieve time. Each condition implements
``is_satisfied(context)`` and serializes to/from a JSON-friendly dict so the
envelope can be reloaded across processes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Tuple


class ConditionError(Exception):
    """Raised when a condition cannot be evaluated or its data is malformed."""


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

    @staticmethod
    def deserialize(data: Dict) -> "Condition":
        type_id = data.get("type")
        for klass in _ALL_CONDITION_CLASSES:
            if klass.type_id == type_id:
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
        except (KeyError, ValueError) as exc:
            raise ConditionError(f"Invalid TimeLock payload: {exc}")


class OwnerSignature(Condition):
    """Released only if the requester proves possession of the vault key.

    In Phase 1 ownership is implicit: the unseal operation can only succeed if
    the caller provides the correct vault key (the MAC and the wrapped session
    key both depend on it). This condition therefore checks the public vault
    id matches the recorded depositor.
    """

    type_id = "owner_signature"

    def __init__(self, expected_vault_id: str):
        self.expected_vault_id = (expected_vault_id or "").lower()

    def is_satisfied(self, context: Dict) -> Tuple[bool, str]:
        actual = (context.get("requester_vault_id") or "").lower()
        if not actual:
            return False, "no requester vault id in context"
        if actual != self.expected_vault_id:
            return False, "requester vault id does not match depositor"
        return True, "owner signature ok"

    def to_dict(self) -> Dict:
        return {"type": self.type_id, "expected_vault_id": self.expected_vault_id}

    @classmethod
    def from_dict(cls, data: Dict) -> "OwnerSignature":
        return cls(expected_vault_id=data.get("expected_vault_id", ""))


class _Composite(Condition):
    def __init__(self, *children: Condition):
        if not children:
            raise ConditionError(f"{type(self).__name__} requires at least one child")
        self.children: List[Condition] = list(children)

    def to_dict(self) -> Dict:
        return {
            "type": self.type_id,
            "children": [c.to_dict() for c in self.children],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "_Composite":
        raw_children = data.get("children", [])
        children = [Condition.deserialize(c) for c in raw_children]
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
