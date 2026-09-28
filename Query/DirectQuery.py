import asyncio
import logging
import pickle
import re
from functools import lru_cache
from pathlib import Path

import numpy as np

BASE_DIR = Path("Data").resolve()
logger = logging.getLogger(__name__)
_TOKEN_RE = re.compile(r"\b\w+\b")


class BM25:
    def __init__(self, top_k: int = 6):
        self.top_k = top_k

    @staticmethod
    def tokenize(text: str) -> list[str]:
        return _TOKEN_RE.findall(text.lower())

    @staticmethod
    @lru_cache(maxsize=128)
    def load_bm25(path: str):
        with open(path, "rb") as f:
            return pickle.load(f)

    @staticmethod
    def _resolve(folder: str, uuid: str) -> str | None:
        base = (BASE_DIR / folder / uuid).resolve()
        if not base.is_relative_to(BASE_DIR):
            raise ValueError(f"Invalid uuid: {uuid!r}")
        bm25_path = base / "bm25.pkl"
        if not bm25_path.is_file():
            logger.warning("Skipping missing BM25 file: %s", bm25_path)
            return None
        return str(bm25_path)

    def loadandquery(self, path: str, query_tokens: list[str], k: int):
        data = self.load_bm25(path)
        documents = data["documents"]
        scores = data["bm25"].get_scores(query_tokens)
        top_indices = np.argsort(scores)[::-1][:k]
        return [
            (documents[i], float(scores[i]))
            for i in top_indices
            if scores[i] > 0
        ]

    async def _search_many(
        self, folder: str, query: str, uuids: list[str], top_k: int
    ):
        paths = [p for u in uuids if (p := self._resolve(folder, u)) is not None]
        if not paths:
            return []

        query_tokens = self.tokenize(query)

        results = await asyncio.gather(
            *(
                asyncio.to_thread(self.loadandquery, p, query_tokens, top_k)
                for p in paths
            )
        )
        merged = [hit for hits in results for hit in hits]
        merged.sort(key=lambda x: x[1], reverse=True)
        return merged[:top_k]

    async def get_keyword_chunks_From_Feed(self, query: str, uuids: list[str]):
        return await self._search_many("Feed", query, uuids, self.top_k)

    async def get_keyword_chunks_From_Content(self, query: str, uuids: list[str]):
        return await self._search_many("Content", query, uuids, self.top_k)