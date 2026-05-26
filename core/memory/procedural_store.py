# core/memory/procedural_store.py
import re, aiofiles
from pathlib import Path
from datetime import datetime, timezone

class ProceduralStore:
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)

    async def patch_skill(self, skill_name: str, lesson: str):
        md_path = self.skills_dir / skill_name / "SKILL.md"
        if not md_path.exists():
            return

        async with aiofiles.open(md_path, "r") as f:
            content = await f.read()

        marker = "## Lessons learned"
        if marker not in content:
            content += f"\n\n{marker}\n"

        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        line = f"- [{date}] {lesson}\n"
        content = content.replace(marker, f"{marker}\n{line}", 1)

        async with aiofiles.open(md_path, "w") as f:
            await f.write(content)

    async def read_lessons(self, skill_name: str) -> str:
        md_path = self.skills_dir / skill_name / "SKILL.md"
        if not md_path.exists():
            return ""

        async with aiofiles.open(md_path, "r") as f:
            content = await f.read()

        match = re.search(
            r"## Lessons learned\n(.*?)(\n##|$)", content, re.DOTALL
        )
        return match.group(1).strip() if match else ""