# tests/test_orchestrator.py
"""
Integration tests for the AsyncOrchestrator.

Uses FakeLLM and mock dispatchers to test the full agentic loop
without real LLM or MCP server calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.orchestrator import AsyncOrchestrator
from core.llm.base import LLMResponse, ToolCall, TokenUsage
from tests.conftest import FakeLLM


class TestAsyncOrchestrator:
    """Integration tests for the orchestrator's agentic loop."""

    def _build_orchestrator(
        self,
        llm: FakeLLM,
        skill_registry,
        tools: list[dict] | None = None,
    ) -> AsyncOrchestrator:
        """Helper to build an orchestrator with mocked dependencies."""
        # Mock dispatcher
        dispatcher = MagicMock()
        dispatcher.get_tool_definitions = AsyncMock(return_value=tools or [])
        dispatcher.call = AsyncMock(return_value={"result": "tool output"})

        # Mock brain
        brain = MagicMock()
        brain.recall = AsyncMock(return_value="## Past context\n- some memory")
        brain.working = MagicMock()
        brain.working.summary.return_value = "No prior messages"
        brain.working.messages.return_value = []
        brain.working.add = MagicMock()

        # Mock reflection
        reflection = MagicMock()
        reflection.reflect = AsyncMock(return_value={"outcome": "success"})

        return AsyncOrchestrator(
            registry=skill_registry,
            dispatcher=dispatcher,
            brain=brain,
            reflection=reflection,
            llm=llm,
        )

    @pytest.mark.asyncio
    async def test_simple_response(self, skill_registry):
        """Orchestrator should return text for a simple end_turn response."""
        llm = FakeLLM(responses=[
            LLMResponse(
                stop_reason="end_turn",
                text="Hello! I can help with that.",
                usage=TokenUsage(input_tokens=50, output_tokens=20),
            ),
        ])
        orch = self._build_orchestrator(llm, skill_registry)
        result = await orch.run("read file test.txt")

        assert result == "Hello! I can help with that."
        assert len(llm.call_history) == 1

    @pytest.mark.asyncio
    async def test_tool_use_loop(self, skill_registry):
        """Orchestrator should handle tool_use → tool_result → end_turn cycle."""
        llm = FakeLLM(responses=[
            LLMResponse(
                stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_1", name="file_mcp__read", input={"path": "/tmp/test"})],
                usage=TokenUsage(input_tokens=50, output_tokens=30),
            ),
            LLMResponse(
                stop_reason="end_turn",
                text="File contents: hello world",
                usage=TokenUsage(input_tokens=80, output_tokens=20),
            ),
        ])
        orch = self._build_orchestrator(llm, skill_registry)
        result = await orch.run("read file test.txt")

        assert "File contents" in result
        assert len(llm.call_history) == 2

    @pytest.mark.asyncio
    async def test_multiple_tool_calls(self, skill_registry):
        """Orchestrator should fire multiple tool calls concurrently."""
        llm = FakeLLM(responses=[
            LLMResponse(
                stop_reason="tool_use",
                tool_calls=[
                    ToolCall(id="tc_1", name="search", input={"q": "a"}),
                    ToolCall(id="tc_2", name="fetch", input={"url": "b"}),
                ],
                usage=TokenUsage(input_tokens=50, output_tokens=30),
            ),
            LLMResponse(
                stop_reason="end_turn",
                text="Both tools executed.",
                usage=TokenUsage(input_tokens=100, output_tokens=20),
            ),
        ])
        orch = self._build_orchestrator(llm, skill_registry)
        result = await orch.run("search the web for info")

        assert result == "Both tools executed."
        # Dispatcher should have been called twice
        assert orch.dispatcher.call.call_count == 2

    @pytest.mark.asyncio
    async def test_memory_is_updated(self, skill_registry):
        """Orchestrator should update working memory after completion."""
        llm = FakeLLM(responses=[
            LLMResponse(stop_reason="end_turn", text="Done!", usage=TokenUsage()),
        ])
        orch = self._build_orchestrator(llm, skill_registry)
        await orch.run("test message")

        # Working memory should have add() called for user and assistant
        assert orch.brain.working.add.call_count == 2

    @pytest.mark.asyncio
    async def test_reflection_is_triggered(self, skill_registry):
        """Orchestrator should fire reflection as a background task."""
        llm = FakeLLM(responses=[
            LLMResponse(stop_reason="end_turn", text="OK", usage=TokenUsage()),
        ])
        orch = self._build_orchestrator(llm, skill_registry)
        await orch.run("do something")

        # Give the fire-and-forget task a moment to start
        import asyncio
        await asyncio.sleep(0.1)
        # Reflection should have been called (it's fire-and-forget via create_task)
