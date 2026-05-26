# core/memory/episodic_store.py
import json, aiosqlite
from datetime import datetime, timezone
from dataclasses import dataclass

@dataclass
class Episode:
    intent: str
    skill_used: str
    tools_called: list[str]
    outcome: str
    result_summary: str
    lessons: str
    created_at: str = ""

class EpisodicStore:
    def __init__(self, db_path: str = "brain/episodes.db"):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at  TEXT,
                    intent      TEXT,
                    skill_used  TEXT,
                    tools_called TEXT,
                    outcome     TEXT,
                    result_summary TEXT,
                    lessons     TEXT
                )
            """)
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_intent ON episodes(intent)"
            )
            await db.commit()

    async def write(self, ep: Episode):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO episodes VALUES (NULL,?,?,?,?,?,?,?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    ep.intent, ep.skill_used,
                    json.dumps(ep.tools_called),
                    ep.outcome, ep.result_summary, ep.lessons,
                )
            )
            await db.commit()

    async def search(self, query: str, limit: int = 4) -> list[Episode]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                """SELECT intent,skill_used,tools_called,outcome,
                          result_summary,lessons,created_at
                   FROM episodes
                   WHERE intent LIKE ? OR lessons LIKE ? OR result_summary LIKE ?
                   ORDER BY created_at DESC LIMIT ?""",
                (f"%{query}%",) * 3 + (limit,),
            )
            rows = await cur.fetchall()
        return [
            Episode(
                intent=r["intent"], skill_used=r["skill_used"],
                tools_called=json.loads(r["tools_called"]),
                outcome=r["outcome"], result_summary=r["result_summary"],
                lessons=r["lessons"], created_at=r["created_at"],
            )
            for r in rows
        ]