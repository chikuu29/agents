# core/reflection.py
import json
from anthropic import AsyncAnthropic

class ReflectionEngine:
    def __init__(self, brain):
        self.brain = brain
        self.client = AsyncAnthropic()

    async def reflect(
        self,
        intent: str,
        skill_used: str,
        tools_called: list[str],
        full_trace: str,
        final_result: str,
        success: bool,
    ):
        prompt = f"""
You are a reflection system for an AI agent. Analyse this task execution.

Task: {intent}
Skill: {skill_used}
Tools used: {tools_called}
Success: {success}

Trace (condensed):
{full_trace[:3000]}

Result:
{final_result[:500]}

Respond ONLY with valid JSON (no markdown fences):
{{
  "outcome": "success" | "partial" | "fail",
  "result_summary": "<one sentence>",
  "lessons": "<what to remember for future similar tasks, max 2 sentences>",
  "facts": ["<fact 1>", "<fact 2>"],
  "skill_patch": "<one-line SKILL.md improvement, or empty string>"
}}
"""
        resp = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(resp.content[0].text)

        await self.brain.write_experience(
            intent=intent,
            skill=skill_used,
            tools=tools_called,
            outcome=data["outcome"],
            summary=data["result_summary"],
            lessons=data["lessons"],
            facts=data.get("facts", []),
            skill_patch=data.get("skill_patch", ""),
        )
        return data