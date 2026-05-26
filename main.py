# main.py
import asyncio
from core.memory.working_memory  import WorkingMemory
from core.memory.episodic_store  import EpisodicStore
from core.memory.semantic_store  import SemanticStore
from core.memory.procedural_store import ProceduralStore
from core.brain        import Brain
from core.reflection   import ReflectionEngine
from core.skill_loader import load_skills
from core.skill_registry import AsyncSkillRegistry
from core.mcp_dispatcher import AsyncMCPDispatcher
from core.orchestrator  import AsyncOrchestrator

async def build_agent() -> AsyncOrchestrator:
    # Memory tiers
    brain = Brain(
        working    = WorkingMemory(),
        episodic   = EpisodicStore("brain/episodes.db"),
        semantic   = SemanticStore("brain/chroma"),
        procedural = ProceduralStore("skills"),
    )
    await brain.init()

    # Skills
    skills   = load_skills("skills/")
    registry = AsyncSkillRegistry(skills)

    dispatcher = AsyncMCPDispatcher()
    reflection = ReflectionEngine(brain)

    return AsyncOrchestrator(registry, dispatcher, brain, reflection)

async def main():
    agent = await build_agent()
    while True:
        msg = input("You: ")
        result = await agent.run(msg)
        print("Agent:", result)

if __name__ == "__main__":
    asyncio.run(main())