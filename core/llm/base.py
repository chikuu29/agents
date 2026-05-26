# core/llm/base.py
"""
Abstract base class and unified data types for LLM providers.

All provider implementations must inherit from BaseLLM and return
LLMResponse objects, ensuring the orchestrator is provider-agnostic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """A single tool-use request from the LLM."""
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class TokenUsage:
    """Token consumption for a single LLM call."""
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class LLMResponse:
    """
    Unified response from any LLM provider.

    Attributes:
        stop_reason: Why the LLM stopped — "end_turn" or "tool_use".
        text:        Final text output (None if the response is tool_use only).
        tool_calls:  List of tool-use blocks (empty if stop_reason is end_turn).
        usage:       Token consumption stats.
        raw:         Provider-specific raw response for debugging.
    """
    stop_reason: str
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    raw: Any = field(default=None, repr=False)


class BaseLLM(ABC):
    """
    Abstract LLM client interface.

    Every provider implementation must:
    1. Accept provider-specific config in __init__
    2. Implement chat() returning a unified LLMResponse
    3. Translate tool definitions from MCP format to provider format
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        system: str = "",
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Send a chat completion request.

        Args:
            messages:    List of {"role": ..., "content": ...} dicts.
            system:      System prompt string.
            tools:       List of tool definitions in MCP/Anthropic format.
            max_tokens:  Maximum tokens in the response.
            temperature: Sampling temperature.

        Returns:
            Unified LLMResponse.
        """
        ...

    @abstractmethod
    def format_tool_result(
        self, tool_call_id: str, result: str
    ) -> dict:
        """
        Format a tool result message for this provider.

        Different providers expect tool results in different shapes.
        This method ensures the orchestrator can construct the right
        message format regardless of provider.
        """
        ...

    @abstractmethod
    def format_assistant_message(self, response: LLMResponse) -> dict:
        """
        Format the assistant's response as a message for the conversation history.

        This is needed because each provider has a different representation
        for assistant messages containing tool calls.
        """
        ...

    @property
    def provider_name(self) -> str:
        """Human-readable provider name."""
        return self.__class__.__name__
