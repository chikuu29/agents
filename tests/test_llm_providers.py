# tests/test_llm_providers.py
"""
Unit tests for the LLM abstraction layer.

Tests LLMResponse dataclass, factory function, and
provider response translation (using mocks).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.llm.base import BaseLLM, LLMResponse, ToolCall, TokenUsage
from core.llm.factory import get_llm_client


class TestLLMDataclasses:
    """Tests for LLM data types."""

    def test_token_usage_total(self):
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.total_tokens == 150

    def test_token_usage_defaults(self):
        usage = TokenUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0

    def test_tool_call_creation(self):
        tc = ToolCall(id="tc_1", name="search", input={"query": "test"})
        assert tc.id == "tc_1"
        assert tc.name == "search"
        assert tc.input == {"query": "test"}

    def test_llm_response_end_turn(self):
        resp = LLMResponse(
            stop_reason="end_turn",
            text="Hello, world!",
            usage=TokenUsage(input_tokens=5, output_tokens=10),
        )
        assert resp.stop_reason == "end_turn"
        assert resp.text == "Hello, world!"
        assert resp.tool_calls == []
        assert resp.usage.total_tokens == 15

    def test_llm_response_tool_use(self):
        resp = LLMResponse(
            stop_reason="tool_use",
            tool_calls=[
                ToolCall(id="tc_1", name="search", input={"q": "test"}),
                ToolCall(id="tc_2", name="fetch", input={"url": "http://example.com"}),
            ],
        )
        assert resp.stop_reason == "tool_use"
        assert len(resp.tool_calls) == 2
        assert resp.text is None


class TestLLMFactory:
    """Tests for the LLM factory function."""

    def test_anthropic_provider(self):
        from config import Settings
        settings = Settings(llm_provider="anthropic", llm_api_key="test-key")
        llm = get_llm_client(settings)
        assert llm.provider_name == "Anthropic"

    def test_openai_provider(self):
        from config import Settings
        settings = Settings(llm_provider="openai", llm_api_key="test-key")
        llm = get_llm_client(settings)
        assert llm.provider_name == "OpenAI"

    def test_deepseek_provider(self):
        from config import Settings
        settings = Settings(llm_provider="deepseek", llm_api_key="test-key")
        llm = get_llm_client(settings)
        assert llm.provider_name == "DeepSeek"

    def test_ollama_provider(self):
        from config import Settings
        settings = Settings(llm_provider="ollama", llm_model="llama3")
        llm = get_llm_client(settings)
        assert llm.provider_name == "Ollama"

    def test_gemini_provider(self):
        from config import Settings
        settings = Settings(llm_provider="gemini", llm_api_key="test-key")
        llm = get_llm_client(settings)
        assert llm.provider_name == "Gemini"

    def test_unknown_provider_raises(self):
        from config import Settings
        settings = Settings(llm_provider="unknown_provider", llm_api_key="test")
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_client(settings)

    def test_case_insensitive_provider(self):
        from config import Settings
        settings = Settings(llm_provider="ANTHROPIC", llm_api_key="test-key")
        llm = get_llm_client(settings)
        assert llm.provider_name == "Anthropic"


class TestFakeLLM:
    """Tests for the FakeLLM fixture itself."""

    @pytest.mark.asyncio
    async def test_fake_llm_default_response(self, fake_llm):
        response = await fake_llm.chat(
            messages=[{"role": "user", "content": "hello"}]
        )
        assert response.stop_reason == "end_turn"
        assert response.text == "This is a test response."

    @pytest.mark.asyncio
    async def test_fake_llm_records_history(self, fake_llm):
        await fake_llm.chat(
            messages=[{"role": "user", "content": "test 1"}],
            system="sys prompt",
        )
        await fake_llm.chat(
            messages=[{"role": "user", "content": "test 2"}],
        )
        assert len(fake_llm.call_history) == 2
        assert fake_llm.call_history[0]["system"] == "sys prompt"

    @pytest.mark.asyncio
    async def test_fake_llm_tool_use_response(self, fake_llm_with_tool_use):
        # First call: tool_use
        resp1 = await fake_llm_with_tool_use.chat(
            messages=[{"role": "user", "content": "use a tool"}]
        )
        assert resp1.stop_reason == "tool_use"
        assert len(resp1.tool_calls) == 1

        # Second call: end_turn
        resp2 = await fake_llm_with_tool_use.chat(
            messages=[{"role": "user", "content": "done"}]
        )
        assert resp2.stop_reason == "end_turn"
        assert resp2.text == "Tool result processed successfully."
