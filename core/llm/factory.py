# core/llm/factory.py
"""
LLM client factory.

Creates the appropriate LLM provider instance based on Settings.
"""

import structlog

from config import Settings
from core.llm.base import BaseLLM

logger = structlog.get_logger(__name__)


def get_llm_client(settings: Settings) -> BaseLLM:
    """
    Create an LLM client from application settings.

    Supports: anthropic, openai, gemini, ollama, deepseek.

    Args:
        settings: Application settings with provider/model/key config.

    Returns:
        A BaseLLM implementation for the configured provider.

    Raises:
        ValueError: If the provider is not recognized.
    """
    provider = settings.llm_provider.lower().strip()

    match provider:
        case "anthropic":
            from core.llm.anthropic_llm import AnthropicLLM
            return AnthropicLLM(
                api_key=settings.llm_api_key,
                model=settings.llm_model,
            )

        case "openai":
            from core.llm.openai_llm import OpenAILLM
            return OpenAILLM(
                api_key=settings.llm_api_key,
                model=settings.llm_model,
                base_url=settings.llm_base_url or None,
                provider_label="OpenAI",
            )

        case "deepseek":
            from core.llm.openai_llm import OpenAILLM
            return OpenAILLM(
                api_key=settings.llm_api_key,
                model=settings.llm_model or "deepseek-chat",
                base_url=settings.llm_base_url or "https://api.deepseek.com",
                provider_label="DeepSeek",
            )

        case "gemini":
            from core.llm.gemini_llm import GeminiLLM
            return GeminiLLM(
                api_key=settings.llm_api_key,
                model=settings.llm_model or "gemini-2.0-flash",
            )

        case "ollama":
            from core.llm.ollama_llm import OllamaLLM
            return OllamaLLM(
                model=settings.llm_model or "llama3",
                base_url=settings.llm_base_url or "http://localhost:11434/v1",
            )

        case _:
            raise ValueError(
                f"Unknown LLM provider: '{provider}'. "
                f"Supported: anthropic, openai, gemini, ollama, deepseek"
            )


def get_reflection_llm(settings: Settings) -> BaseLLM:
    """
    Create an LLM client for the reflection engine.

    Uses reflection-specific overrides if configured,
    otherwise falls back to the main LLM settings.
    """
    if settings.reflection_provider:
        reflection_settings = settings.model_copy(update={
            "llm_provider": settings.reflection_provider,
            "llm_model": settings.reflection_model or settings.llm_model,
        })
        logger.info(
            "llm.reflection_override",
            provider=settings.reflection_provider,
            model=reflection_settings.llm_model,
        )
        return get_llm_client(reflection_settings)

    return get_llm_client(settings)
