from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class ValidationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ValidationIssue:
    """A single rule violation found during validation."""
    field: str
    rule: str
    message: str
    severity: str = "error"


@dataclass
class ValidationResult:
    """Aggregated outcome of running all validation rules."""
    status: ValidationStatus
    issues: list[ValidationIssue] = field(default_factory=list)
    score: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class IValidator(Protocol):
    """Contract every document validator must satisfy."""

    async def validate(
        self,
        extracted_fields: dict[str, Any],
        document_type: str,
        rules: list[dict] | None = None,
    ) -> ValidationResult:
        """Validate extracted fields and return a structured result."""
        ...
