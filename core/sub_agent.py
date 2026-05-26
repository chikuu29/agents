# core/sub_agent.py
import asyncio
from dataclasses import dataclass

@dataclass
class SubTask:
    intent: str

class SubAgentCoordinator:
    def __init__(self, orchestrator_factory):
        self.factory = orchestrator_factory   # () -> AsyncOrchestrator

    async def run_parallel(self, tasks: list[SubTask]) -> list[str]:
        return await asyncio.gather(
            *[self.factory().run(t.intent) for t in tasks]
        )