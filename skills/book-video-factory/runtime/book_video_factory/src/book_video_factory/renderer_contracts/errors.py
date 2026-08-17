"""Structured, stable error objects for contract validation."""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from types import MappingProxyType
from typing import Any, Mapping

from .enums import RendererErrorCode


@dataclass(frozen=True)
class RenderIssue:
    code: RendererErrorCode
    message: str
    field: str = "$"
    details: Mapping[str, Any] = dataclass_field(default_factory=dict)
    stage: str = "validate"

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "field": self.field,
            "details": dict(self.details),
            "stage": self.stage,
        }


class ContractValidationError(ValueError):
    """Raised when deserialization cannot produce a valid contract object."""

    def __init__(self, issues: tuple[RenderIssue, ...] | list[RenderIssue]):
        self.issues = tuple(issues)
        summary = "; ".join(
            f"{issue.code.value} at {issue.field}: {issue.message}"
            for issue in self.issues
        )
        super().__init__(summary or "contract validation failed")


class SnapshotWriteError(RuntimeError):
    """Raised when an immutable release snapshot cannot be safely persisted."""
