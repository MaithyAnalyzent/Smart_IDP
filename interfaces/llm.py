from __future__ import annotations
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal contract for LLM completion providers.

    Two concrete implementations ship with this platform:
      - services/llm/openai_provider.py   (OpenAI / Azure OpenAI)
      - services/llm/anthropic_provider.py (Anthropic Claude)

    Add your own by implementing this protocol and registering it in
    services/llm/__init__.py's get_llm_provider() factory.
    """

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> str:
        """Return a plain-text completion."""
        ...

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Return a parsed JSON object from the LLM response."""
        ...
