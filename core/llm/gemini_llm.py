# core/llm/gemini_llm.py
"""
Google Gemini LLM provider.

Wraps the google-genai SDK, translating tool definitions
from MCP/Anthropic format to Gemini function declarations.
"""

import uuid
import structlog
from google import genai
from google.genai import types

from core.llm.base import BaseLLM, LLMResponse, ToolCall, TokenUsage

logger = structlog.get_logger(__name__)


class GeminiLLM(BaseLLM):
    """Google Gemini provider (Gemini 2.0 Flash, Pro, etc.)."""

    def __init__(self, api_key: str = "", model: str = "gemini-2.0-flash"):
        self.model = model
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        logger.info("llm.initialized", provider="gemini", model=model)

    def _convert_tools(self, tools: list[dict]) -> list[types.Tool]:
        """
        Convert MCP/Anthropic tool format to Gemini function declarations.

        MCP format:
            {"name": "...", "description": "...", "input_schema": {...}}

        Gemini format:
            Tool(function_declarations=[FunctionDeclaration(...)])
        """
        declarations = []
        for tool in tools:
            schema = tool.get("input_schema", {})
            # Convert JSON Schema properties to Gemini Schema format
            parameters = None
            if schema and schema.get("properties"):
                parameters = types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        name: types.Schema(
                            type=self._map_json_type(prop.get("type", "string")),
                            description=prop.get("description", ""),
                        )
                        for name, prop in schema["properties"].items()
                    },
                    required=schema.get("required", []),
                )

            declarations.append(types.FunctionDeclaration(
                name=tool["name"],
                description=tool.get("description", ""),
                parameters=parameters,
            ))

        return [types.Tool(function_declarations=declarations)] if declarations else []

    @staticmethod
    def _map_json_type(json_type: str) -> types.Type:
        """Map JSON Schema type strings to Gemini Type enum."""
        mapping = {
            "string": types.Type.STRING,
            "number": types.Type.NUMBER,
            "integer": types.Type.INTEGER,
            "boolean": types.Type.BOOLEAN,
            "array": types.Type.ARRAY,
            "object": types.Type.OBJECT,
        }
        return mapping.get(json_type, types.Type.STRING)

    def _build_gemini_messages(
        self, messages: list[dict]
    ) -> list[types.Content]:
        """Convert standard message format to Gemini Content objects."""
        contents = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            content = msg.get("content", "")

            if isinstance(content, str):
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=content)],
                ))
            elif isinstance(content, list):
                # Handle tool results (list of result dicts)
                parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "tool_result":
                            parts.append(types.Part.from_function_response(
                                name=item.get("_tool_name", "tool"),
                                response={"result": item.get("content", "")},
                            ))
                        elif item.get("type") == "text":
                            parts.append(types.Part.from_text(text=item.get("text", "")))
                if parts:
                    contents.append(types.Content(role=role, parts=parts))
        return contents

    async def chat(
        self,
        messages: list[dict],
        system: str = "",
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        gemini_contents = self._build_gemini_messages(messages)
        gemini_tools = self._convert_tools(tools) if tools else None

        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            system_instruction=system if system else None,
            tools=gemini_tools,
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=gemini_contents,
            config=config,
        )

        # Parse response
        text = None
        tool_calls = []

        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.text:
                    text = (text or "") + part.text
                elif part.function_call:
                    tool_calls.append(ToolCall(
                        id=str(uuid.uuid4()),  # Gemini doesn't provide IDs
                        name=part.function_call.name,
                        input=dict(part.function_call.args) if part.function_call.args else {},
                    ))

        stop_reason = "tool_use" if tool_calls else "end_turn"

        # Extract usage
        usage_meta = getattr(response, "usage_metadata", None)
        usage = TokenUsage(
            input_tokens=getattr(usage_meta, "prompt_token_count", 0) if usage_meta else 0,
            output_tokens=getattr(usage_meta, "candidates_token_count", 0) if usage_meta else 0,
        )

        return LLMResponse(
            stop_reason=stop_reason,
            text=text,
            tool_calls=tool_calls,
            usage=usage,
            raw=response,
        )

    def format_tool_result(self, tool_call_id: str, result: str) -> dict:
        """Format tool result for Gemini (uses _tool_name for re-mapping)."""
        return {
            "type": "tool_result",
            "tool_use_id": tool_call_id,
            "content": result,
        }

    def format_assistant_message(self, response: LLMResponse) -> dict:
        """Format assistant message for conversation history."""
        content = []
        if response.text:
            content.append({"type": "text", "text": response.text})
        for tc in response.tool_calls:
            content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.input,
            })
        return {"role": "assistant", "content": content if content else response.text or ""}

    @property
    def provider_name(self) -> str:
        return "Gemini"
