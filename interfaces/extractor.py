from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class ExtractionResult:
    """Structured output produced by any extractor implementation."""
    fields: dict[str, Any]
    confidence: float
    raw_text: str
    extractor_id: str
    page_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class IExtractor(Protocol):
    """Contract every document extractor must satisfy.

    Implementations are registered against MIME types via the extractor
    registry in services/extractor_registry.py — no subclassing required.
    """

    @property
    def supported_mime_types(self) -> list[str]:
        """MIME types this extractor can handle."""
        ...

    async def extract(
        self,
        file_bytes: bytes,
        mime_type: str,
        document_type: str,
        field_hints: list[str] | None = None,
    ) -> ExtractionResult:
        """Extract structured fields from raw file bytes."""
        ...
