from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ClassificationResult:
    """Output of a document classification operation."""
    document_type: str
    confidence: float
    alternative_types: list[dict] = field(default_factory=list)
    reasoning: str = ""


@runtime_checkable
class IClassifier(Protocol):
    """Contract every document classifier must satisfy."""

    async def classify(
        self,
        file_bytes: bytes,
        mime_type: str,
        known_types: list[str] | None = None,
    ) -> ClassificationResult:
        """Determine the document type from raw file bytes."""
        ...
