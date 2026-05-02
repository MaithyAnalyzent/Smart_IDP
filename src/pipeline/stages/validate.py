from __future__ import annotations
import json

from interfaces.llm import LLMProvider
from src.pipeline.context import PipelineContext
from src.pipeline.stages.base import PipelineStage
from utils.logger import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a document validation specialist.

You will receive extracted fields from a document and a list of validation rules.
Evaluate each rule against the extracted data.

Return ONLY a JSON object with this exact structure:
{
  "overall_status": "passed" | "failed" | "warning",
  "score": <float 0.0–1.0>,
  "issues": [
    {
      "field": "<field_name or 'general'>",
      "rule": "<rule description>",
      "message": "<what failed and why>",
      "severity": "error" | "warning"
    }
  ]
}

- "passed"  → no error-level issues found
- "warning" → only warning-level issues found
- "failed"  → at least one error-level issue found
- Return an empty issues array if everything passes.
"""


class ValidateStage(PipelineStage):
    """Validates extracted fields against tenant-configured processing rules.

    Rules are plain-English strings stored in ProcessingRule records and
    loaded into ctx.metadata["validation_rules"] before the pipeline runs.
    The LLM interprets each rule and checks whether the extracted fields satisfy it.

    If no rules are configured for the detected document type, this stage is
    skipped gracefully (validation_status = "skipped").
    """

    name = "validate"

    def __init__(self, llm: LLMProvider, model: str | None = None) -> None:
        self._llm = llm
        self._model = model

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        rules: list[dict] = ctx.metadata.get("validation_rules", [])
        if not rules:
            ctx.validation_status = "skipped"
            logger.info("validate_skipped_no_rules", job_id=ctx.job_id)
            return ctx

        user_prompt = self._build_prompt(ctx, rules)
        result = await self._llm.complete_json(_SYSTEM_PROMPT, user_prompt, model=self._model)

        ctx.validation_status = result.get("overall_status", "failed")
        ctx.validation_issues = result.get("issues", [])
        ctx.metadata["validation_score"] = float(result.get("score", 0.0))

        logger.info(
            "validate_ok",
            job_id=ctx.job_id,
            status=ctx.validation_status,
            issues=len(ctx.validation_issues),
        )
        return ctx

    @staticmethod
    def _build_prompt(ctx: PipelineContext, rules: list[dict]) -> str:
        rules_text = "\n".join(
            f"{i + 1}. [{r.get('severity', 'error').upper()}] {r.get('rule_description', '')}"
            for i, r in enumerate(rules)
        )
        fields_json = json.dumps(ctx.extracted_fields, indent=2, default=str)
        return (
            f"Document type: {ctx.document_type}\n\n"
            f"Extracted fields:\n{fields_json}\n\n"
            f"Validation rules:\n{rules_text}\n\n"
            "Evaluate each rule and return your findings."
        )
