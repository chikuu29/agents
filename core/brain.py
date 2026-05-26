# core/brain.py
import asyncio

class Brain:
    def __init__(self, working, episodic, semantic, procedural):
        self.working    = working
        self.episodic   = episodic
        self.semantic   = semantic
        self.procedural = procedural

    async def init(self):
        """Call once at startup to initialise all async stores."""
        await asyncio.gather(
            self.episodic.init(),
            self.semantic.init(),
        )

    async def recall(self, intent: str, skill_name: str) -> str:
        """Fan out to all tiers in parallel, merge results."""
        episodes, facts, lessons = await asyncio.gather(
            self.episodic.search(intent, limit=3),
            self.semantic.search(intent, n=4),
            self.procedural.read_lessons(skill_name),
        )

        parts: list[str] = []

        if episodes:
            parts.append("## Relevant past experience")
            for ep in episodes:
                parts.append(
                    f"- [{ep.created_at[:10]}] \"{ep.intent[:80]}\" "
                    f"→ {ep.outcome} via {ep.skill_used}. {ep.lessons}"
                )

        if facts:
            parts.append("\n## Known relevant facts")
            for f in facts:
                parts.append(f"- {f['text']}")

        if lessons:
            parts.append(f"\n## Past {skill_name} skill lessons")
            parts.append(lessons)

        return "\n".join(parts)

    async def write_experience(
        self, intent: str, skill: str, tools: list[str],
        outcome: str, summary: str, lessons: str,
        facts: list[str], skill_patch: str,
    ):
        """Write all tiers in parallel after task completes."""
        from .memory.episodic_store import Episode
        tasks = [
            self.episodic.write(Episode(
                intent=intent, skill_used=skill, tools_called=tools,
                outcome=outcome, result_summary=summary, lessons=lessons,
            )),
            *[self.semantic.write(f, {"intent": intent, "skill": skill}) for f in facts],
        ]
        if skill_patch:
            tasks.append(self.procedural.patch_skill(skill, skill_patch))

        await asyncio.gather(*tasks)