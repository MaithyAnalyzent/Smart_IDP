from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineContext:
    """Immutable-by-convention state bag that threads through every pipeline stage.

    A single PipelineContext is created when a job starts and passed to each
    stage in sequence. Stages read from it, write their outputs back into it,
    and return it. No stage communicates with another except through this object.

    Control flow
    ------------
    Set ``should_abort = True`` (via ``abort()``) to stop the pipeline cleanly
    without raising an exception. Remaining stages will be skipped and the job
    will be persisted with whatever partial state was accumulated.
    """

    # ── Identity ─────────────────────────────────────────────────────────────
    job_id: str
    tenant_id: str

    # ── Raw input ────────────────────────────────────────────────────────────
    raw_bytes: bytes
    filename: str
    mime_type: str

    # ── Populated by IngestStage ─────────────────────────────────────────────
    storage_key: str | None = None

    # ── Populated by ClassifyStage ───────────────────────────────────────────
    document_type: str | None = None
    classification_confidence: float = 0.0

    # ── Populated by ExtractStage ────────────────────────────────────────────
    extracted_fields: dict[str, Any] = field(default_factory=dict)

    # ── Populated by ValidateStage ───────────────────────────────────────────
    validation_status: str = "pending"
    validation_issues: list[dict[str, Any]] = field(default_factory=list)

    # ── Cross-stage metadata ─────────────────────────────────────────────────
    stage_timings: dict[str, float] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    should_abort: bool = False

    # Free-form bag for inter-stage hints (e.g. field_hints, validation_rules)
    metadata: dict[str, Any] = field(default_factory=dict)

    # ── Helpers ──────────────────────────────────────────────────────────────
    def record_error(self, stage: str, message: str) -> None:
        self.errors.append({"stage": stage, "message": message})

    def abort(self, stage: str, reason: str) -> None:
        """Halt the pipeline gracefully after the current stage returns."""
        self.record_error(stage, reason)
        self.should_abort = True
