# tests/test_skill_registry.py
"""
Unit tests for the async skill registry.

Tests keyword-based routing accuracy, confidence scoring,
fallback behavior, and multi-skill resolution.
"""

import pytest
from core.skill_registry import AsyncSkillRegistry


class TestAsyncSkillRegistry:
    """Tests for skill routing and registry operations."""

    @pytest.mark.asyncio
    async def test_exact_trigger_match(self, skill_registry):
        """Exact trigger phrase should route to the correct skill."""
        skill_name, confidence = await skill_registry.route("read file from disk")
        assert skill_name == "FileOperations"
        assert confidence > 0

    @pytest.mark.asyncio
    async def test_web_search_routing(self, skill_registry):
        """Web-related intents should route to WebSearch skill."""
        skill_name, _ = await skill_registry.route("search the web for Python tutorials")
        assert skill_name == "WebSearch"

    @pytest.mark.asyncio
    async def test_pdf_routing(self, skill_registry):
        """PDF-related intents should route to PDFGeneration skill."""
        skill_name, _ = await skill_registry.route("generate pdf report from this data")
        assert skill_name == "PDFGeneration"

    @pytest.mark.asyncio
    async def test_partial_keyword_match(self, skill_registry):
        """Partial keyword overlap should still find a match."""
        skill_name, confidence = await skill_registry.route("I need to edit a file")
        assert skill_name == "FileOperations"
        assert confidence > 0

    @pytest.mark.asyncio
    async def test_unknown_intent_uses_fallback(self, skill_registry):
        """Completely unrelated input should fallback to the default skill."""
        skill_name, confidence = await skill_registry.route("tell me a joke about elephants")
        # Should still return something (the default/first skill)
        assert skill_name is not None
        # Confidence should be low
        assert confidence < 0.5

    @pytest.mark.asyncio
    async def test_confidence_ordering(self, skill_registry):
        """Higher trigger overlap should produce higher confidence."""
        _, conf_exact = await skill_registry.route("generate pdf")
        _, conf_partial = await skill_registry.route("maybe a pdf thing")
        # Exact match should have higher or equal confidence
        assert conf_exact >= conf_partial

    def test_get_existing_skill(self, skill_registry):
        """get() should return the skill manifest for a valid name."""
        skill = skill_registry.get("FileOperations")
        assert skill.name == "FileOperations"
        assert "read file" in skill.triggers

    def test_get_missing_skill_raises(self, skill_registry):
        """get() should raise KeyError for unknown skill names."""
        with pytest.raises(KeyError, match="NonExistent"):
            skill_registry.get("NonExistent")

    def test_list_skills(self, skill_registry):
        """list_skills() should return all registered skill names."""
        names = skill_registry.list_skills()
        assert set(names) == {"FileOperations", "WebSearch", "PDFGeneration"}

    @pytest.mark.asyncio
    async def test_empty_registry_handling(self):
        """Empty registry should handle routing gracefully."""
        registry = AsyncSkillRegistry([])
        # Should return None as default with 0 confidence
        skill_name, confidence = await registry.route("do something")
        assert skill_name is None
        assert confidence == 0.0
