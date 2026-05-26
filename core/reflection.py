# core/reflection.py
"""
Reflection engine — post-task self-analysis.

After each task completes, analyzes the execution trace to
extract lessons, facts, and skill improvements. Writes findings
back to episodic, semantic, and procedural memory.
"""

import json
import structlog

from core.llm.base import BaseLLM

logger = structlog.get_logger(__name__)


class ReflectionEngine:
    def __init__(self, brain, llm: BaseLLM):
        self.brain = brain
        self.llm = llm

    async def reflect(
        self,
        intent: str,
        skill_used: str,
        tools_called: list[str],
        full_trace: str,
        final_result: str,
        success: bool,
    ):
        logger.info(
            "reflection.started",
            intent=intent[:100],
            skill=skill_used,
            tools_count=len(tools_called),
            success=success,
        )

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
        try:
            response = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.3,
            )

            raw_text = response.text or ""
            # Strip markdown fences if model includes them despite instructions
            raw_text = raw_text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1]
            if raw_text.endswith("```"):
                raw_text = raw_text.rsplit("```", 1)[0]
            raw_text = raw_text.strip()

            data = json.loads(raw_text)

            logger.info(
                "reflection.completed",
                outcome=data.get("outcome"),
                summary=data.get("result_summary", "")[:100],
                facts_count=len(data.get("facts", [])),
                has_patch=bool(data.get("skill_patch")),
            )

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

        except json.JSONDecodeError as e:
            logger.error(
                "reflection.parse_error",
                error=str(e),
                raw_response=raw_text[:500] if 'raw_text' in dir() else "N/A",
            )
            return {"outcome": "fail", "result_summary": "Reflection parse failed"}

        except Exception as e:
            logger.error(
                "reflection.error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return {"outcome": "fail", "result_summary": f"Reflection error: {e}"}