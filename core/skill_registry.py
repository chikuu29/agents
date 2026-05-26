# core/skill_registry.py
"""
Async skill registry with keyword-based intent routing.

Routes user messages to the most relevant skill by matching
trigger keywords defined in each SKILL.md frontmatter.
"""

import re
import structlog
from dataclasses import dataclass
from core.skill_loader import SkillManifest

logger = structlog.get_logger(__name__)


@dataclass
class RouteResult:
    """Result of skill routing with confidence score."""
    skill_name: str
    confidence: float
    matched_triggers: list[str]


class AsyncSkillRegistry:
    """
    Registry that holds loaded skills and routes user intents
    to the best-matching skill via keyword overlap scoring.
    """

    def __init__(self, skills: list[SkillManifest]):
        self.skills: dict[str, SkillManifest] = {s.name: s for s in skills}
        self._default_skill: str | None = None
        if skills:
            self._default_skill = skills[0].name
        logger.info(
            "skill_registry.initialized",
            skill_count=len(skills),
            skill_names=list(self.skills.keys()),
        )

    async def route(self, user_message: str) -> tuple[str, float]:
        """
        Route a user message to the best-matching skill.

        Scoring strategy:
        1. Tokenize the user message into lowercase words.
        2. For each skill, check how many of its trigger phrases
           appear as substrings in the message.
        3. Boost score if the skill description also matches.
        4. Return the skill with the highest score and confidence.

        Returns:
            (skill_name, confidence) where confidence is 0.0-1.0.
        """
        msg_lower = user_message.lower().strip()
        msg_words = set(re.findall(r"\w+", msg_lower))

        best_skill = self._default_skill
        best_score = 0.0
        best_triggers: list[str] = []

        for name, skill in self.skills.items():
            score = 0.0
            matched: list[str] = []

            # Check trigger phrase matches (substring match)
            for trigger in skill.triggers:
                trigger_lower = trigger.lower().strip()
                if trigger_lower in msg_lower:
                    score += 2.0  # Strong match: full trigger phrase found
                    matched.append(trigger)
                else:
                    # Partial: check individual trigger words
                    trigger_words = set(re.findall(r"\w+", trigger_lower))
                    overlap = trigger_words & msg_words
                    if overlap:
                        score += len(overlap) / len(trigger_words)
                        matched.append(trigger)

            # Boost from description keyword overlap
            if skill.description:
                desc_words = set(re.findall(r"\w+", skill.description.lower()))
                desc_overlap = desc_words & msg_words
                score += len(desc_overlap) * 0.3

            if score > best_score:
                best_score = score
                best_skill = name
                best_triggers = matched

        # Normalize confidence to 0.0 - 1.0 range
        max_possible = max(
            (len(s.triggers) * 2.0 + len(re.findall(r"\w+", s.description or "")) * 0.3)
            for s in self.skills.values()
        ) if self.skills else 1.0
        confidence = min(best_score / max(max_possible, 1.0), 1.0)

        logger.info(
            "skill_registry.routed",
            user_message=user_message[:100],
            selected_skill=best_skill,
            confidence=round(confidence, 3),
            matched_triggers=best_triggers,
        )

        return best_skill, confidence

    def get(self, name: str) -> SkillManifest:
        """Retrieve a skill manifest by name."""
        if name not in self.skills:
            available = list(self.skills.keys())
            raise KeyError(
                f"Skill '{name}' not found. Available: {available}"
            )
        return self.skills[name]

    def list_skills(self) -> list[str]:
        """Return list of all registered skill names."""
        return list(self.skills.keys())
