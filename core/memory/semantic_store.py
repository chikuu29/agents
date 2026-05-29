# core/memory/semantic_store.py
import uuid
import chromadb
from chromadb.config import Settings

class SemanticStore:
    def __init__(self, persist_dir: str = "brain/chroma"):
        # Store the persistence path; client will be created in async init
        self.persist_dir = persist_dir
        self._client = None  # Will be set in async init
        self._col = None

    async def init(self):
        # Initialize a persistent client in a background thread to avoid blocking the event loop
        import asyncio
        self._client = await asyncio.to_thread(lambda: chromadb.PersistentClient(path=self.persist_dir))
        # get_or_create_collection is also synchronous, wrap it similarly
        self._col = await asyncio.to_thread(lambda: self._client.get_or_create_collection(
            "agent_knowledge",
            metadata={"hnsw:space": "cosine"},
        ))

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