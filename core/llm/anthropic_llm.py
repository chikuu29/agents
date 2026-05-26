# core/llm/anthropic_llm.py
"""
Anthropic Claude LLM provider.

Wraps the official anthropic SDK's AsyncAnthropic client,
translating responses to the unified LLMResponse format.
"""

import structlog
from anthropic import AsyncAnthropic

from core.llm.base import BaseLLM, LLMResponse, ToolCall, TokenUsage

logger = structlog.get_logger(__name__)


class AnthropicLLM(BaseLLM):
    """Anthropic Claude provider (Claude Sonnet, Opus, Haiku, etc.)."""

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-20250514"):
        self.model = model
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        # Falls back to ANTHROPIC_API_KEY env var if api_key is empty
        self.client = AsyncAnthropic(**kwargs)
        logger.info("llm.initialized", provider="anthropic", model=model)

    async def chat(
        self,
        messages: list[dict],
        system: str = "",
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools
        if temperature is not None:
            kwargs["temperature"] = temperature

        response = await self.client.messages.create(**kwargs)

        # Parse response
        text = None
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text = block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    input=block.input,
                ))

        stop_reason = "tool_use" if response.stop_reason == "tool_use" else "end_turn"
        usage = TokenUsage(
            input_tokens=getattr(response.usage, "input_tokens", 0),
            output_tokens=getattr(response.usage, "output_tokens", 0),
        )

        return LLMResponse(
            stop_reason=stop_reason,
            text=text,
            tool_calls=tool_calls,
            usage=usage,
            raw=response,
        )

    def format_tool_result(self, tool_call_id: str, result: str) -> dict:
        """Anthropic expects tool results in a specific block format."""
        return {
            "type": "tool_result",
            "tool_use_id": tool_call_id,
            "content": result,
        }

    def format_assistant_message(self, response: LLMResponse) -> dict:
        """Anthropic stores the raw content blocks as the assistant message."""
        return {"role": "assistant", "content": response.raw.content}

    @property
    def provider_name(self) -> str:
        return "Anthropic"
