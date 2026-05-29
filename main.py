# main.py
"""
Entry point for the agent system.

Initializes all components (memory, skills, LLM, MCP, observability)
and runs the interactive agent loop.
"""

import asyncio
import structlog

from config import Settings
from core.memory.working_memory  import WorkingMemory
from core.memory.episodic_store  import EpisodicStore
from core.memory.semantic_store  import SemanticStore
from core.memory.procedural_store import ProceduralStore
from core.brain        import Brain
from core.reflection   import ReflectionEngine
from core.skill_loader import load_skills_async
from core.skill_registry import AsyncSkillRegistry
from core.mcp_dispatcher import AsyncMCPDispatcher
from core.orchestrator  import AsyncOrchestrator
from core.llm.factory import get_llm_client, get_reflection_llm
from core.logging_config import setup_logging
from core.observability import setup_observability

logger = structlog.get_logger(__name__)


async def build_agent(settings: Settings) -> AsyncOrchestrator:
    """Build and wire all agent components from settings."""

    # Memory tiers
    brain = Brain(
        working    = WorkingMemory(),
        episodic   = EpisodicStore(settings.brain_db_path),
        semantic   = SemanticStore(settings.brain_chroma_path),
        procedural = ProceduralStore(settings.skills_dir),
    )
    await brain.init()

    # Skills
    skills   = await load_skills_async(settings.skills_dir)
    registry = AsyncSkillRegistry(skills)

    # MCP
    dispatcher = AsyncMCPDispatcher(settings.mcp_registry_path)

    # LLM clients
    main_llm = get_llm_client(settings)
    reflection_llm = get_reflection_llm(settings)

    # Reflection
    reflection = ReflectionEngine(brain, reflection_llm)

    logger.info(
        "agent.built",
        llm_provider=main_llm.provider_name,
        skill_count=len(skills),
        skills=registry.list_skills(),
    )

    return AsyncOrchestrator(registry, dispatcher, brain, reflection, main_llm)


async def main():
    # Load configuration
    settings = Settings()

    # Setup logging and observability
    setup_logging(settings)
    setup_observability(settings)

    logger.info(
        "agent.starting",
        provider=settings.llm_provider,
        model=settings.llm_model,
        log_level=settings.log_level,
    )

    agent = await build_agent(settings)

    print(f"\n🤖 Agent ready! (LLM: {settings.llm_provider}/{settings.llm_model})")
    print("Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            msg = input("You: ")
            if msg.strip().lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break
            if not msg.strip():
                continue
            result = await agent.run(msg)
            print(f"Agent: {result}\n")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            logger.error("agent.error", error=str(e), error_type=type(e).__name__)
            print(f"Error: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())