from __future__ import annotations
import base64

from interfaces.llm import LLMProvider
from src.pipeline.context import PipelineContext
from src.pipeline.stages.base import PipelineStage
from utils.logger import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a document classification specialist.
Analyze the provided document and determine its type.

Return ONLY a JSON object with this exact structure — no explanation, no markdown:
{
  "document_type": "<snake_case type name>",
  "confidence": <float 0.0–1.0>,
  "reasoning": "<one sentence>",
  "alternatives": [
    {"document_type": "<type>", "confidence": <float>}
  ]
}

Use generic, industry-agnostic type names such as:
  invoice, receipt, purchase_order, contract, identity_document,
  bank_statement, tax_form, report, form, letter, other, generic
"""

_PREVIEW_BYTES = 8_192  # first 8 KB is sufficient for classification


class ClassifyStage(PipelineStage):
    """Determines the document type using an LLM.

    A configurable confidence threshold controls when the result is trusted.
    Below the threshold the job continues with ``fallback_type`` so downstream
    stages can still attempt extraction rather than failing silently.
    """

    name = "classify"

    def __init__(
        self,
        llm: LLMProvider,
        model: str | None = None,
        confidence_threshold: float = 0.70,
        fallback_type: str = "generic",
    ) -> None:
        self._llm = llm
        self._model = model
        self._threshold = confidence_threshold
        self._fallback = fallback_type

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        user_prompt = self._build_prompt(ctx)
        result = await self._llm.complete_json(
            _SYSTEM_PROMPT, user_prompt, model=self._model
        )

        doc_type: str = result.get("document_type") or self._fallback
        confidence: float = float(result.get("confidence", 0.0))

        if confidence < self._threshold:
            logger.warning(
                "classify_low_confidence",
                job_id=ctx.job_id,
                detected=doc_type,
                confidence=confidence,
                using_fallback=self._fallback,
            )
            doc_type = self._fallback

        ctx.document_type = doc_type
        ctx.classification_confidence = confidence
        ctx.metadata["classification_reasoning"] = result.get("reasoning", "")
        ctx.metadata["classification_alternatives"] = result.get("alternatives", [])
        return ctx

    def _build_prompt(self, ctx: PipelineContext) -> str:
        preview = base64.b64encode(ctx.raw_bytes[:_PREVIEW_BYTES]).decode()
        known = ctx.metadata.get("known_types")
        hint = f"\nKnown types for this tenant: {', '.join(known)}" if known else ""
        return (
            f"Filename: {ctx.filename}\n"
            f"MIME type: {ctx.mime_type}\n"
            f"File preview (base64, first {_PREVIEW_BYTES} bytes): {preview}"
            f"{hint}\n\n"
            "Classify this document."
        )
