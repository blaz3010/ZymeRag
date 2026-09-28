import asyncio
import logging
from functools import lru_cache
from pathlib import Path

import faiss
from langchain_community.vectorstores import FAISS

from Embeddings.Embeddingmaker import embedder

BASE_DIR = Path("Data").resolve()
logger = logging.getLogger(__name__)


class SemanticQuery:
    @staticmethod
    @lru_cache(maxsize=32)
    def load_vectorstore(path: str):
        return FAISS.load_local(
            path,
            embedder,
            allow_dangerous_deserialization=True,
        )

    @staticmethod
    @lru_cache(maxsize=512)
    def _embed(query: str) -> tuple:
        return tuple(embedder.embed_query(query))

    @staticmethod
    def _resolve(folder: str, uuid: str) -> str | None:
        path = (BASE_DIR / folder / uuid).resolve()
        if not path.is_relative_to(BASE_DIR):
            raise ValueError(f"Invalid uuid: {uuid!r}")
        if not path.is_dir():
            logger.warning("Skipping missing index: %s", path)
            return None
        return str(path)

    def _search(self, path: str, query_vec: list[float], k: int):
        vs = self.load_vectorstore(path)
        hits = vs.similarity_search_with_score_by_vector(query_vec, k=k)
        if vs.index.metric_type == faiss.METRIC_INNER_PRODUCT:
            return hits
        return [(doc, 1 - score / 2) for doc, score in hits]

    async def _search_many(
        self, folder: str, query: str, uuids: list[str], top_k: int
    ):
        paths = [p for u in uuids if (p := self._resolve(folder, u)) is not None]
        if not paths:
            return []
        query_vec = list(await asyncio.to_thread(self._embed, query))
        results = await asyncio.gather(
            *(asyncio.to_thread(self._search, p, query_vec, top_k) for p in paths)
        )
        merged = [hit for hits in results for hit in hits]
        merged.sort(key=lambda x: x[1], reverse=True)
        return merged[:top_k]

    async def get_semantic_chunks_fromFeed(
        self, query: str, uuids: list[str], top_k: int = 5
    ):
        return await self._search_many("Feed", query, uuids, top_k)

    async def get_semantic_chunks_fromContent(
        self, query: str, uuids: list[str], top_k: int = 5
    ):
        return await self._search_many("Content", query, uuids, top_k)