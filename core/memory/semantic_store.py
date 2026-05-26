# core/memory/semantic_store.py
import uuid
import chromadb
from chromadb.config import Settings

class SemanticStore:
    def __init__(self, persist_dir: str = "brain/chroma"):
        # AsyncHttpClient if you run chroma as a server,
        # or PersistentClient wrapped in run_in_executor for local
        self._client = chromadb.AsyncHttpClient(
            host="localhost", port=8000,
            settings=Settings(anonymized_telemetry=False),
        )
        self._col = None

    async def init(self):
        self._col = await self._client.get_or_create_collection(
            "agent_knowledge",
            metadata={"hnsw:space": "cosine"},
        )

    async def write(self, text: str, metadata: dict):
        await self._col.add(
            documents=[text],
            metadatas=[metadata],
            ids=[str(uuid.uuid4())],
        )

    async def search(self, query: str, n: int = 4) -> list[dict]:
        results = await self._col.query(
            query_texts=[query],
            n_results=n,
        )
        docs  = results["documents"][0]
        metas = results["metadatas"][0]
        return [{"text": d, "meta": m} for d, m in zip(docs, metas)]