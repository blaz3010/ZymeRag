import asyncio
import logging
from functools import lru_cache
from typing import Optional, Union

from langchain_core.documents import Document

from Embeddings.Embeddingmaker import embedder
from Dbhelper.document_chunks_db_helper import get_semantic_chunks_by_ids  # adjust to your helper's module name

logger = logging.getLogger(__name__)

# Qwen3-Embedding is instruction-aware: queries get an instruction, documents don't.
# Set to None if `embedder` already applies a query prompt.
QUERY_INSTRUCTION: Optional[str] = (
    "Given a question, retrieve passages that answer it"
)

# True only on pgvector >= 0.8 with an HNSW index.
USE_ITERATIVE_SCAN = False


class SemanticQuery:
    _COLUMNS = {"Feed": "feed_id", "Content": "content_id"}

    @staticmethod
    @lru_cache(maxsize=512)
    def _embed(query: str) -> tuple:
        if QUERY_INSTRUCTION:
            query = f"Instruct: {QUERY_INSTRUCTION}\nQuery: {query}"
        return tuple(embedder.embed_query(query))

    async def _search_many(
        self, kind: str, query: str, ids: list[str], top_k: int
    ) -> list[dict]:
        if not query.strip() or not ids or top_k <= 0:
            return []

        try:
            query_vec = await asyncio.to_thread(self._embed, query)
        except Exception:
            logger.exception("Failed to embed query for %s search", kind)
            return []

        # Dimension / NaN validation and error handling live in the helper.
        return await get_semantic_chunks_by_ids(
            query_vec,
            ids,
            self._COLUMNS[kind],
            top_k,
            iterative_scan=USE_ITERATIVE_SCAN,
        )

    @staticmethod
    def _format(
        rows: list[dict], as_rows: bool
    ) -> Union[list[dict], list[tuple[Document, float]]]:
        if as_rows:
            return rows
        return [
            (
                Document(
                    page_content=r["content"],
                    metadata={
                        **(r["metadata"] or {}),
                        "chunk_id": r["chunk_id"],
                        "chunk_index": r["chunk_index"],
                        "content_id": r["content_id"],
                        "feed_id": r["feed_id"],
                    },
                ),
                float(r["similarity"]),
            )
            for r in rows
        ]

    async def get_semantic_chunks(self, query, uuids, top_k=5, as_rows=False):
        embedding = await asyncio.to_thread(self._embed, query)
        logger.info("embed returned type=%s len=%s", type(embedding), len(embedding))
        rows = await get_semantic_chunks_by_ids(embedding, uuids, top_k=top_k)
        return self._format(rows, as_rows)