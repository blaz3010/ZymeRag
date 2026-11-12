import asyncio
from typing import List, Optional
from fastapi import HTTPException, Query
from pydantic import BaseModel
import tiktoken
from Backend.Utils.Logger import logger
from Query.DirectQuery import get_all_chunks
from LLM.Llm import generate_answer
from Utils.PickleReader import read_pickle_file
from Dbhelper.user_mapping_db_helper import (
    get_all_sources_with_details,
    get_all_active_source_ids,
)
from Dbhelper.query_db_helper import (
    save_query,
    get_queries,
    delete_query,
    clear_query_history,
)
from Dbhelper.document_chunks_db_helper import get_chunks_by_source_id
from Query.WebSearchFallback import web_search_fallback

class QueryRequest(BaseModel):
    question: str
    ids: list[str]
    fallback_threshold: float = 0.5
    fallback_provider: str = "both"
    max_web_results: int = 5


class QueryBodyRequest(BaseModel):
    question: str
    selected_ids: List[str]


async def build_context(chunks: list[tuple]) -> str:
    texts = []
    for doc, _score in chunks:
        if hasattr(doc, "page_content"):
            texts.append(doc.page_content)
        else:
            texts.append(str(doc))
    return "\n\n".join(texts)


MAX_FULLCONTEXT_TOKENS = 6000
_tokenizer = tiktoken.get_encoding("cl100k_base")


async def _load_source_text(source_id: str, max_tokens: int = MAX_FULLCONTEXT_TOKENS) -> str:
    chunks = await get_chunks_by_source_id(source_id)
    text = "\n".join(c.get("content") or c.get("page_content") or "" for c in chunks)
    tokens = _tokenizer.encode(text)
    if len(tokens) <= max_tokens:
        return text
    truncated = _tokenizer.decode(tokens[:max_tokens])
    return truncated + "\n\n[...truncated to fit token limit...]"



def extract_inspectable_chunks(chunks: list[tuple], max_items: int = 8) -> list:
    """Format chunk tuples into inspectable payload for UI RAG testing."""
    result = []
    for item in chunks[:max_items]:
        if isinstance(item, tuple) and len(item) >= 2:
            doc, score = item[0], item[1]
        elif isinstance(item, tuple) and len(item) == 1:
            doc, score = item[0], 0.0
        else:
            doc, score = item, 0.0

        content = doc.page_content if hasattr(doc, "page_content") else str(doc)
        meta = getattr(doc, "metadata", {}) or {}

        score_val = None
        if isinstance(score, (int, float)):
            score_val = round(float(score), 4)

        result.append({
            "snippet": content[:320] + ("..." if len(content) > 320 else ""),
            "full_snippet": content[:1200],
            "score": score_val,
            "source": meta.get("source") or meta.get("content_id") or "Document Chunk",
            "metadata": {
                k: v for k, v in meta.items() if isinstance(v, (str, int, float, bool))
            },
        })
    return result


async def query_endpoint(question: str = Query(...), ids: list[str] = Query(...)):
    """Legacy/Direct query endpoint without authentication."""
    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    try:
        chunks = await get_all_chunks(question, ids)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not chunks:
        raise HTTPException(status_code=404, detail="No relevant chunks found for this query")

    context = await build_context(chunks)

    try:
        answer = await generate_answer(question, context)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {e}")
    print(answer)
    return {"answer": answer}

async def query_endpoint_fullcontext(question: str = Query(...), ids: list[str] = Query(...)):
    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    results = await asyncio.gather(
        *(_load_source_text(sid) for sid in ids),
        return_exceptions=True,
    )

    texts = []
    for sid, res in zip(ids, results):
        if isinstance(res, Exception):
            logger.warning("[query_endpoint_fullcontext] Failed to load %s: %s", sid, res)
        elif res:
            texts.append(res)
    context = "\n\n".join(texts)
    logger.info("[query_fullcontext] sources=%d chars=%d words=%d",len(texts),len(context),len(context.split()),)
    if not context.strip():
        raise HTTPException(status_code=404, detail="No content found for the given source IDs")
    try:
        answer = await generate_answer(question, context)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {e}")
    logger.info(
    "[query_fullcontext] answer_type=%s answer_length=%d",
    type(answer).__name__,
    len(answer) if isinstance(answer, str) else 0,)
    logger.info("[query_fullcontext] answer=%s", answer)
    return {"answer":answer}



async def get_query_history_endpoint(limit: int = 50):
    """Fetch query evaluation history."""
    history = await get_queries(limit=limit)
    return {"history": history}


async def delete_query_history_endpoint(query_id: str):
    """Delete a specific test query from history."""
    success = await delete_query(query_id=query_id)
    return {"success": success, "message": "Query record removed"}


async def clear_query_history_endpoint():
    """Clear all test query history."""
    await clear_query_history()
    return {"success": True, "message": "Query history cleared"}


async def get_queryable_sources():
    """Return all sources in the system with details for the RAG Playground selector."""
    try:
        sources = await get_all_sources_with_details()
        return {"sources": sources}
    except Exception as e:
        logger.exception("[get_queryable_sources] Failed to fetch all sources: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


async def web_search_query_endpoint(question: str = Query(...), max_results: int = Query(5)):
    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    try:
        chunks = await web_search_fallback(question.strip(), max_results=max_results)
        if not chunks:
            return {"question": question, "chunks": [], "answer": "No web results found."}
        context = "\n\n".join(c.get("content", "") for c in chunks if c.get("content"))
        try:
            answer = await generate_answer(question.strip(), context)
        except Exception as e:
            logger.exception("[web_search_query_endpoint] LLM failed: %s", e)
            answer = "\n\n".join(f"[{i+1}] {c.get('content')}\nSource: {c.get('url')}" for i, c in enumerate(chunks))
        return {"question": question, "chunks": chunks, "answer": answer}
    except Exception as e:
        logger.exception("[web_search_query_endpoint] Failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))