from __future__ import annotations
import json
from typing import Any

import anthropic

from core.exceptions import ConfigurationError
from configs.settings import get_settings
from utils.logger import get_logger
from utils.retry import with_retry

logger = get_logger(__name__)


class AnthropicProvider:
    """LLM provider backed by the Anthropic API (Claude model family).

    Swap the default model by setting the model parameter on each call,
    or update _default_model for a platform-wide default.
    """

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.ANTHROPIC_API_KEY:
            raise ConfigurationError(
                "ANTHROPIC_API_KEY must be set when LLM_PROVIDER=anthropic"
            )
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._default_model = "claude-sonnet-4-6"

    @with_retry(max_attempts=3, min_wait=2.0, max_wait=15.0)
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> str:
        message = await self._client.messages.create(
            model=model or self._default_model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature,
        )
        return message.content[0].text if message.content else ""

    @with_retry(max_attempts=3, min_wait=2.0, max_wait=15.0)
    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        # Anthropic does not have a native JSON mode — instruct via system prompt
        json_system = (
            f"{system_prompt}\n\n"
            "IMPORTANT: Respond ONLY with valid JSON. "
            "No markdown fences, no explanation, no surrounding text."
        )
        text = await self.complete(
            json_system, user_prompt,
            model=model, temperature=temperature, max_tokens=max_tokens,
        )
        # Strip any accidental markdown code fences
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(text)
