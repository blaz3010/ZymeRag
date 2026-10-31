import asyncio
import logging

from langchain_core.documents import Document

from Query.BM25Query import BM25
from Query.SemanticQuery import SemanticQuery
from Query.WebSearchFallback import WebSearchFallback

logger = logging.getLogger(__name__)

CANDIDATES = 10
RRF_K = 60

bm25 = BM25(top_k=CANDIDATES)
semantic = SemanticQuery()
web_fallback = WebSearchFallback()


def _rrf(
    semantic_rows: list[dict],
    keyword_rows: list[dict],
    top_k: int,
) -> list[dict]:
    scores: dict = {}
    by_id: dict = {}
    for rows in (semantic_rows, keyword_rows):
        for rank, row in enumerate(rows):
            cid = row["chunk_id"]
            by_id[cid] = {**by_id.get(cid, {}), **row}
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
    ranked = sorted(scores, key=scores.get, reverse=True)[:top_k]
    return [by_id[c] for c in ranked]


def _to_hit(row: dict) -> tuple[Document, float]:
    doc = Document(
        page_content=row["content"],
        metadata={
            **(row.get("metadata") or {}),
            "chunk_id": row["chunk_id"],
            "chunk_index": row["chunk_index"],
            "content_id": row["content_id"],
            "feed_id": row["feed_id"],
        },
    )
    return doc, float(row.get("similarity") or 0.0)


async def get_all_chunks(
    query: str, ids: list[str], top_k: int = 6
) -> list[tuple[Document, float]]:
    ids = list(dict.fromkeys(i for i in ids if i))
    if not query.strip() or not ids:
        return []
    (
        kw_content, sem_content, kw_feed, sem_feed,
    ) = await asyncio.gather(
        bm25.get_keyword_chunks_From_Content(query, ids, as_rows=True),
        semantic.get_semantic_chunks_fromContent(
            query, ids, top_k=CANDIDATES, as_rows=True
        ),
        bm25.get_keyword_chunks_From_Feed(query, ids, as_rows=True),
        semantic.get_semantic_chunks_fromFeed(
            query, ids, top_k=CANDIDATES, as_rows=True
        ),
    )
    semantic_rows = sorted(
        sem_content + sem_feed, key=lambda r: r["similarity"], reverse=True
    )[:CANDIDATES]
    keyword_rows = sorted(
        kw_content + kw_feed, key=lambda r: r["rank"], reverse=True
    )[:CANDIDATES]

    return [_to_hit(r) for r in _rrf(semantic_rows, keyword_rows, top_k)]


async def get_all_chunks_with_fallback(
    query: str,
    ids: list[str],
    fallback_threshold: float = 0.5,
    fallback_provider: str = "both",
    max_web_results: int = 5,
    top_k: int = 6,
):
    kb_chunks = await get_all_chunks(query, ids, top_k=top_k)
    return await web_fallback.evaluate_and_fallback(
        query=query,
        kb_chunks=kb_chunks,
        threshold=fallback_threshold,
        provider=fallback_provider,
        max_results=max_web_results,
    )