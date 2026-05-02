from __future__ import annotations
import base64

from interfaces.llm import LLMProvider
from src.pipeline.context import PipelineContext
from src.pipeline.stages.base import PipelineStage
from utils.logger import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a document data extraction specialist.

Extract all relevant structured fields from the provided document.

Rules:
- Return ONLY a valid JSON object. Keys must be snake_case strings.
- Values must be the verbatim extracted data (preserve original formatting).
- If a field is not present in the document, omit it entirely — do not use null.
- For lists (e.g. line items), use a JSON array of objects.
- Do not invent data. Only extract what is explicitly present.
"""

_CONTENT_WINDOW = 32_768  # 32 KB of base64-encoded content sent to the LLM


class ExtractStage(PipelineStage):
    """Extracts structured fields from the classified document using an LLM.

    Field hints from the tenant's DocumentSchema (if one matches the detected
    document_type) are injected into the prompt so the LLM focuses on the
    fields that matter to that tenant.
    """

    name = "extract"

    def __init__(
        self,
        llm: LLMProvider,
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> None:
        self._llm = llm
        self._model = model
        self._max_tokens = max_tokens

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        user_prompt = self._build_prompt(ctx)
        extracted = await self._llm.complete_json(
            _SYSTEM_PROMPT,
            user_prompt,
            model=self._model,
            max_tokens=self._max_tokens,
        )
        ctx.extracted_fields = extracted
        logger.info(
            "extract_ok",
            job_id=ctx.job_id,
            doc_type=ctx.document_type,
            fields=len(extracted),
        )
        return ctx

    def _build_prompt(self, ctx: PipelineContext) -> str:
        encoded = base64.b64encode(ctx.raw_bytes[:_CONTENT_WINDOW]).decode()
        field_hints: list[str] = ctx.metadata.get("field_hints", [])
        hint_text = (
            f"\n\nFocus on extracting these fields: {', '.join(field_hints)}"
            if field_hints
            else ""
        )
        return (
            f"Document type: {ctx.document_type}\n"
            f"Filename: {ctx.filename}\n"
            f"MIME type: {ctx.mime_type}\n"
            f"Content (base64, up to {_CONTENT_WINDOW} bytes): {encoded}"
            f"{hint_text}\n\n"
            "Extract all structured fields from this document."
        )
