# tests/test_skill_loader.py
"""
Unit tests for the skill loader module.

Tests YAML frontmatter parsing, SKILL.md discovery, and
SkillManifest construction.
"""

import pytest
from pathlib import Path
from core.skill_loader import load_skills, _parse_frontmatter, SkillManifest


class TestParseFrontmatter:
    """Tests for the _parse_frontmatter function."""

    def test_valid_yaml_frontmatter(self):
        text = """---
name: TestSkill
description: A test skill
triggers:
  - trigger one
  - trigger two
mcp_servers:
  - test_mcp
---

# Skill content here
"""
        result = _parse_frontmatter(text)
        assert result["name"] == "TestSkill"
        assert result["description"] == "A test skill"
        assert result["triggers"] == ["trigger one", "trigger two"]
        assert result["mcp_servers"] == ["test_mcp"]

    def test_no_frontmatter(self):
        text = "# Just a normal markdown file\nNo frontmatter."
        result = _parse_frontmatter(text)
        assert result == {}

    def test_empty_frontmatter(self):
        text = "---\n---\nContent"
        result = _parse_frontmatter(text)
        assert result == {} or result is None or not result

    def test_missing_optional_fields(self):
        text = """---
name: MinimalSkill
---

# Content
"""
        result = _parse_frontmatter(text)
        assert result.get("name") == "MinimalSkill"

    def test_single_trigger_as_string(self):
        text = """---
name: SingleTrigger
description: Test
triggers: single trigger
mcp_servers:
  - test_mcp
---
"""
        result = _parse_frontmatter(text)
        # May be string or list depending on parser
        triggers = result.get("triggers")
        assert triggers is not None


class TestLoadSkills:
    """Tests for the load_skills function."""

    def test_load_from_directory(self, tmp_path):
        # Create a skill directory structure
        skill_dir = tmp_path / "skills"
        file_skill = skill_dir / "file"
        file_skill.mkdir(parents=True)
        (file_skill / "SKILL.md").write_text("""---
name: FileOps
description: File operations
triggers:
  - read file
  - write file
mcp_servers:
  - file_mcp
---

# File Operations
""", encoding="utf-8")

        skills = load_skills(str(skill_dir))
        assert len(skills) == 1
        assert skills[0].name == "FileOps"
        assert "read file" in skills[0].triggers

    def test_load_empty_directory(self, tmp_path):
        skill_dir = tmp_path / "empty_skills"
        skill_dir.mkdir()
        skills = load_skills(str(skill_dir))
        assert len(skills) == 0

    def test_load_multiple_skills(self, tmp_path):
        skill_dir = tmp_path / "skills"
        for name in ["alpha", "beta", "gamma"]:
            d = skill_dir / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(f"""---
name: {name.title()}
description: {name} skill
triggers:
  - {name} action
mcp_servers:
  - {name}_mcp
---

# {name.title()} Skill
""", encoding="utf-8")

        skills = load_skills(str(skill_dir))
        assert len(skills) == 3
        names = {s.name for s in skills}
        assert names == {"Alpha", "Beta", "Gamma"}

    def test_malformed_skill_skipped(self, tmp_path):
        skill_dir = tmp_path / "skills"
        good = skill_dir / "good"
        good.mkdir(parents=True)
        (good / "SKILL.md").write_text("""---
name: GoodSkill
description: Works fine
triggers:
  - good action
mcp_servers:
  - good_mcp
---
""", encoding="utf-8")

        bad = skill_dir / "bad"
        bad.mkdir(parents=True)
        (bad / "SKILL.md").write_text("No frontmatter here", encoding="utf-8")

        skills = load_skills(str(skill_dir))
        assert len(skills) == 1
        assert skills[0].name == "GoodSkill"
