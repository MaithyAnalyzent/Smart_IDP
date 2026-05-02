from __future__ import annotations
import json
from typing import Any

from openai import AsyncOpenAI

from core.exceptions import ConfigurationError
from configs.settings import get_settings
from utils.logger import get_logger
from utils.retry import with_retry

logger = get_logger(__name__)


class OpenAIProvider:
    """LLM provider backed by the OpenAI API (or any OpenAI-compatible endpoint).

    Set OPENAI_BASE_URL in .env to point at Azure OpenAI, Ollama, or any
    OpenAI-compatible server without changing this file.
    """

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            raise ConfigurationError(
                "OPENAI_API_KEY must be set when LLM_PROVIDER=openai"
            )
        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL or None,
        )
        self._default_model = "gpt-4o"

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
        response = await self._client.chat.completions.create(
            model=model or self._default_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

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
        response = await self._client.chat.completions.create(
            model=model or self._default_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)
