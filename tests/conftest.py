# tests/conftest.py
"""
Shared pytest fixtures for the agent test suite.

Provides mock LLM clients, in-memory memory stores, test skills,
and a fully-wired orchestrator for integration testing.
"""

import os
import sys
import tempfile
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm.base import BaseLLM, LLMResponse, ToolCall, TokenUsage
from core.skill_loader import SkillManifest
from core.skill_registry import AsyncSkillRegistry
from core.memory.working_memory import WorkingMemory


# ---------------------------------------------------------------------------
# Fake LLM for testing
# ---------------------------------------------------------------------------

class FakeLLM(BaseLLM):
    """
    A mock LLM that returns pre-configured responses.

    Usage:
        llm = FakeLLM(responses=[
            LLMResponse(stop_reason="end_turn", text="Hello!"),
        ])
    """

    def __init__(self, responses: list[LLMResponse] | None = None):
        self._responses = responses or [
            LLMResponse(
                stop_reason="end_turn",
                text="This is a test response.",
                usage=TokenUsage(input_tokens=10, output_tokens=20),
            )
        ]
        self._call_index = 0
        self.call_history: list[dict] = []

    async def chat(
        self,
        messages: list[dict],
        system: str = "",
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        self.call_history.append({
            "messages": messages,
            "system": system,
            "tools": tools,
            "max_tokens": max_tokens,
        })
        response = self._responses[min(self._call_index, len(self._responses) - 1)]
        self._call_index += 1
        return response

    def format_tool_result(self, tool_call_id: str, result: str) -> dict:
        return {
            "type": "tool_result",
            "tool_use_id": tool_call_id,
            "content": result,
        }

    def format_assistant_message(self, response: LLMResponse) -> dict:
        return {"role": "assistant", "content": response.text or ""}

    @property
    def provider_name(self) -> str:
        return "FakeLLM"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_llm():
    """A FakeLLM with a default response."""
    return FakeLLM()


@pytest.fixture
def fake_llm_with_tool_use():
    """A FakeLLM that first requests a tool call, then gives a final answer."""
    return FakeLLM(responses=[
        LLMResponse(
            stop_reason="tool_use",
            tool_calls=[ToolCall(id="tc_1", name="test_tool", input={"q": "hello"})],
            usage=TokenUsage(input_tokens=15, output_tokens=10),
        ),
        LLMResponse(
            stop_reason="end_turn",
            text="Tool result processed successfully.",
            usage=TokenUsage(input_tokens=25, output_tokens=30),
        ),
    ])


@pytest.fixture
def sample_skill_manifest(tmp_path) -> SkillManifest:
    """A sample SkillManifest for testing."""
    md_path = tmp_path / "test_skill" / "SKILL.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("# Test Skill\nThis is a test.", encoding="utf-8")
    return SkillManifest(
        name="TestSkill",
        description="A test skill for unit tests",
        triggers=["test action", "run test"],
        mcp_servers=["test_mcp"],
        md_path=md_path,
        full_content="# Test Skill\nThis is a test.",
    )


@pytest.fixture
def sample_skills(tmp_path) -> list[SkillManifest]:
    """Multiple sample skills for registry testing."""
    skills = [
        SkillManifest(
            name="FileOperations",
            description="Read, write, and edit files",
            triggers=["read file", "write file", "edit file", "list directory"],
            mcp_servers=["file_mcp"],
            md_path=tmp_path / "file" / "SKILL.md",
            full_content="# File skill",
        ),
        SkillManifest(
            name="WebSearch",
            description="Search the web and fetch URLs",
            triggers=["web search", "search the web", "fetch url", "browse page"],
            mcp_servers=["web_mcp"],
            md_path=tmp_path / "web" / "SKILL.md",
            full_content="# Web skill",
        ),
        SkillManifest(
            name="PDFGeneration",
            description="Generate PDF documents",
            triggers=["generate pdf", "create pdf", "export pdf", "pdf report"],
            mcp_servers=["pdf_mcp"],
            md_path=tmp_path / "pdf" / "SKILL.md",
            full_content="# PDF skill",
        ),
    ]
    return skills


@pytest.fixture
def skill_registry(sample_skills) -> AsyncSkillRegistry:
    """An AsyncSkillRegistry loaded with sample skills."""
    return AsyncSkillRegistry(sample_skills)


@pytest.fixture
def working_memory() -> WorkingMemory:
    """A fresh WorkingMemory instance."""
    return WorkingMemory()


@pytest.fixture
def temp_db_path(tmp_path) -> str:
    """Temporary SQLite database path for episodic store testing."""
    return str(tmp_path / "test_episodes.db")
