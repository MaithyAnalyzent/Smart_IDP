from __future__ import annotations
from interfaces.llm import LLMProvider
from configs.settings import get_settings
from core.exceptions import ConfigurationError


def get_llm_provider() -> LLMProvider:
    """Factory that returns the active LLM provider based on LLM_PROVIDER env var.

    Supported values:
      openai     → OpenAIProvider  (requires OPENAI_API_KEY)
      anthropic  → AnthropicProvider (requires ANTHROPIC_API_KEY)

    Add a new provider by:
      1. Creating services/llm/your_provider.py implementing LLMProvider protocol.
      2. Adding a branch below.
    """
    settings = get_settings()
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        from services.llm.openai_provider import OpenAIProvider
        return OpenAIProvider()

    if provider == "anthropic":
        from services.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider()

    raise ConfigurationError(
        f"Unknown LLM_PROVIDER '{provider}'. Supported: openai, anthropic."
    )
