import asyncio
from Query.BM25Query import BM25
from Query.SemanticQuery import SemanticQuery
from Query.WebSearchFallback import WebSearchFallback

from pathlib import Path

BASE_DIR = Path("Data").resolve()
bm25 = BM25()
semantic = SemanticQuery()
web_fallback = WebSearchFallback()


async def get_all_chunks(query: str, ids: list[str]):
    content_ids = [uid for uid in ids if (BASE_DIR / "Content" / uid).is_dir()]
    feed_ids = [uid for uid in ids if (BASE_DIR / "Feed" / uid).is_dir()]

    tasks = []
    if content_ids:
        tasks.append(bm25.get_keyword_chunks_From_Content(query, content_ids))
        tasks.append(semantic.get_semantic_chunks_fromContent(query, content_ids))
    if feed_ids:
        tasks.append(bm25.get_keyword_chunks_From_Feed(query, feed_ids))
        tasks.append(semantic.get_semantic_chunks_fromFeed(query, feed_ids))

    results = await asyncio.gather(*tasks) if tasks else []
    all_chunks = [hit for group in results for hit in group]
    return all_chunks



async def get_all_chunks_with_fallback(
    query: str,
    ids: list[str],
    fallback_threshold: float = 0.5,
    fallback_provider: str = "both",
    max_web_results: int = 5
):

    kb_chunks = await get_all_chunks(query, ids)
    return await web_fallback.evaluate_and_fallback(
        query=query,
        kb_chunks=kb_chunks,
        threshold=fallback_threshold,
        provider=fallback_provider,
        max_results=max_web_results
    )

