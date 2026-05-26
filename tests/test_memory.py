# tests/test_memory.py
"""
Unit tests for memory subsystems.

Tests working memory, episodic store, and procedural store
with real (temporary) databases.
"""

import pytest
import asyncio
from pathlib import Path

from core.memory.working_memory import WorkingMemory
from core.memory.episodic_store import EpisodicStore, Episode
from core.memory.procedural_store import ProceduralStore


class TestWorkingMemory:
    """Tests for the sliding-window working memory."""

    def test_add_and_retrieve(self, working_memory):
        working_memory.add("user", "Hello")
        working_memory.add("assistant", "Hi there!")
        messages = working_memory.messages()
        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "Hello"}
        assert messages[1] == {"role": "assistant", "content": "Hi there!"}

    def test_sliding_window_truncation(self, working_memory):
        for i in range(25):
            working_memory.add("user", f"Message {i}")
        messages = working_memory.messages()
        assert len(messages) == 20  # Window size is 20
        assert messages[0]["content"] == "Message 5"  # First 5 dropped
        assert messages[-1]["content"] == "Message 24"

    def test_summary_uses_last_three(self, working_memory):
        working_memory.add("user", "first")
        working_memory.add("assistant", "second")
        working_memory.add("user", "third")
        working_memory.add("assistant", "fourth")
        summary = working_memory.summary()
        assert "second" in summary
        assert "third" in summary
        assert "fourth" in summary

    def test_empty_summary(self, working_memory):
        summary = working_memory.summary()
        assert summary == ""

    def test_messages_returns_copy(self, working_memory):
        working_memory.add("user", "test")
        msgs = working_memory.messages()
        msgs.append({"role": "user", "content": "injected"})
        assert len(working_memory.messages()) == 1  # Original unchanged


class TestEpisodicStore:
    """Tests for the SQLite-backed episodic memory."""

    @pytest.mark.asyncio
    async def test_init_creates_table(self, temp_db_path):
        store = EpisodicStore(temp_db_path)
        await store.init()
        # Should not raise; table is created

    @pytest.mark.asyncio
    async def test_write_and_search(self, temp_db_path):
        store = EpisodicStore(temp_db_path)
        await store.init()

        ep = Episode(
            intent="read the config file",
            skill_used="FileOperations",
            tools_called=["file_mcp__read"],
            outcome="success",
            result_summary="Read config.yaml successfully",
            lessons="Config files are in the root directory",
        )
        await store.write(ep)

        results = await store.search("config", limit=5)
        assert len(results) >= 1
        assert results[0].intent == "read the config file"
        assert results[0].skill_used == "FileOperations"
        assert results[0].outcome == "success"

    @pytest.mark.asyncio
    async def test_search_no_results(self, temp_db_path):
        store = EpisodicStore(temp_db_path)
        await store.init()

        results = await store.search("nonexistent query xyz", limit=5)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_limit(self, temp_db_path):
        store = EpisodicStore(temp_db_path)
        await store.init()

        for i in range(10):
            await store.write(Episode(
                intent=f"test task {i}",
                skill_used="TestSkill",
                tools_called=[],
                outcome="success",
                result_summary=f"Result {i}",
                lessons="lesson",
            ))

        results = await store.search("test task", limit=3)
        assert len(results) == 3


class TestProceduralStore:
    """Tests for the SKILL.md patching and lesson reading."""

    @pytest.mark.asyncio
    async def test_read_lessons_from_skill(self, tmp_path):
        skill_dir = tmp_path / "skills"
        test_skill = skill_dir / "TestSkill"
        test_skill.mkdir(parents=True)
        (test_skill / "SKILL.md").write_text("""---
name: TestSkill
---

# Test Skill

## Lessons learned
- [2024-01-01] Always check file encoding
- [2024-01-02] Handle empty files gracefully
""", encoding="utf-8")

        store = ProceduralStore(str(skill_dir))
        lessons = await store.read_lessons("TestSkill")
        assert "check file encoding" in lessons
        assert "Handle empty files" in lessons

    @pytest.mark.asyncio
    async def test_read_lessons_no_section(self, tmp_path):
        skill_dir = tmp_path / "skills"
        test_skill = skill_dir / "TestSkill"
        test_skill.mkdir(parents=True)
        (test_skill / "SKILL.md").write_text("""---
name: TestSkill
---

# Test Skill
No lessons section here.
""", encoding="utf-8")

        store = ProceduralStore(str(skill_dir))
        lessons = await store.read_lessons("TestSkill")
        assert lessons == ""

    @pytest.mark.asyncio
    async def test_read_lessons_missing_skill(self, tmp_path):
        store = ProceduralStore(str(tmp_path / "nonexistent"))
        lessons = await store.read_lessons("NonExistent")
        assert lessons == ""

    @pytest.mark.asyncio
    async def test_patch_skill_adds_lesson(self, tmp_path):
        skill_dir = tmp_path / "skills"
        test_skill = skill_dir / "TestSkill"
        test_skill.mkdir(parents=True)
        md_path = test_skill / "SKILL.md"
        md_path.write_text("""# Test Skill

## Lessons learned
- [2024-01-01] Existing lesson
""", encoding="utf-8")

        store = ProceduralStore(str(skill_dir))
        await store.patch_skill("TestSkill", "New lesson about error handling")

        content = md_path.read_text(encoding="utf-8")
        assert "New lesson about error handling" in content
        assert "Existing lesson" in content
