# core/llm/openai_llm.py
"""
OpenAI-compatible LLM provider.

Works with OpenAI, DeepSeek, and any OpenAI-API-compatible endpoint.
Also serves as the base for the Ollama provider.
"""

import json
import uuid
import structlog
from openai import AsyncOpenAI

from core.llm.base import BaseLLM, LLMResponse, ToolCall, TokenUsage

logger = structlog.get_logger(__name__)


class OpenAILLM(BaseLLM):
    """
    OpenAI-compatible provider.

    Supports: OpenAI (gpt-4o, etc.), DeepSeek (deepseek-chat),
    and any server exposing the OpenAI chat completions API.
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = "gpt-4o",
        base_url: str | None = None,
        provider_label: str = "OpenAI",
    ):
        self.model = model
        self._provider_label = provider_label
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        self.client = AsyncOpenAI(**kwargs)
        logger.info(
            "llm.initialized",
            provider=provider_label.lower(),
            model=model,
            base_url=base_url or "default",
        )

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """
        Convert MCP/Anthropic tool format to OpenAI function-calling format.

        MCP format:
            {"name": "...", "description": "...", "input_schema": {...}}

        OpenAI format:
            {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}
        """
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                },
            })
        return openai_tools

    async def chat(
        self,
        messages: list[dict],
        system: str = "",
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        # Prepend system message if provided
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": full_messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        # Parse tool calls
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    input=args,
                ))

        stop_reason = "tool_use" if tool_calls else "end_turn"
        usage_data = response.usage
        usage = TokenUsage(
            input_tokens=getattr(usage_data, "prompt_tokens", 0) if usage_data else 0,
            output_tokens=getattr(usage_data, "completion_tokens", 0) if usage_data else 0,
        )

        return LLMResponse(
            stop_reason=stop_reason,
            text=message.content,
            tool_calls=tool_calls,
            usage=usage,
            raw=response,
        )

    def format_tool_result(self, tool_call_id: str, result: str) -> dict:
        """OpenAI expects tool results as a message with role=tool."""
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result,
        }

    def format_assistant_message(self, response: LLMResponse) -> dict:
        """Format assistant message for OpenAI conversation history."""
        msg: dict = {"role": "assistant", "content": response.text or ""}
        if response.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.input),
                    },
                }
                for tc in response.tool_calls
            ]
            # OpenAI requires content to be null when there are tool calls
            if not response.text:
                msg["content"] = None
        return msg

    @property
    def provider_name(self) -> str:
        return self._provider_label
