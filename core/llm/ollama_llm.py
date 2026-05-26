# core/llm/ollama_llm.py
"""
Ollama LLM provider.

Ollama exposes an OpenAI-compatible API at localhost:11434/v1,
so this inherits from OpenAILLM with Ollama-specific defaults.
"""

import structlog

from core.llm.openai_llm import OpenAILLM

logger = structlog.get_logger(__name__)


class OllamaLLM(OpenAILLM):
    """
    Ollama provider — runs models locally.

    Inherits from OpenAILLM since Ollama's API is OpenAI-compatible.
    Defaults to localhost:11434/v1 and uses 'ollama' as a dummy API key.
    """

    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434/v1",
        api_key: str = "ollama",  # Ollama doesn't need a real key
    ):
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url,
            provider_label="Ollama",
        )
        logger.info(
            "llm.initialized",
            provider="ollama",
            model=model,
            base_url=base_url,
        )

    @property
    def provider_name(self) -> str:
        return "Ollama"
