# core/memory/working_memory.py
from dataclasses import dataclass, field

@dataclass
class WorkingMemory:
    _turns: list = field(default_factory=list)

    def add(self, role: str, content: str):
        self._turns.append({"role": role, "content": content})
        if len(self._turns) > 20:
            self._turns = self._turns[-20:]

    def messages(self) -> list:
        return list(self._turns)

    def summary(self) -> str:
        recent = self._turns[-3:]
        return "\n".join(f"{t['role']}: {t['content'][:120]}" for t in recent)