import asyncio
from typing import List, Optional
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel
import tiktoken
from Backend.Utils.Logger import logger
from Query.DirectQuery import get_all_chunks
from LLM.Llm import generate_answer
from Backend.Middleware.auth import auth_middleware
from Utils.PickleReader import read_pickle_file
from Dbhelper.user_mapping_db_helper import (
    get_user_content_ids,
    get_user_feed_ids,
    get_user_sources_with_details,
    get_all_sources_with_details,
    get_all_active_source_ids,
)
from Dbhelper.query_db_helper import (
    save_user_query,
    get_user_queries,
    delete_user_query,
    clear_user_query_history,
)

class QueryRequest(BaseModel):
    question: str
    ids: list[str]
    fallback_threshold: float = 0.5
    fallback_provider: str = "both"
    max_web_results: int = 5


class UserQueryRequest(BaseModel):
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
    docstore, index_to_id = await read_pickle_file(source_id)
    parts = (
        docstore._dict[index_to_id[i]].page_content
        for i in range(len(index_to_id))
    )
    text = "\n\n".join(p for p in parts if p.strip())
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

    return answer

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
    return answer


async def user_query_endpoint(body: UserQueryRequest, user_id: str = Depends(auth_middleware)):
    """
    Auth-protected query endpoint for the RAG Playground.
    1. Validates selected sources ownership (content_ids & feed_ids).
    2. Runs hybrid RAG search (BM25 + Dense FAISS embeddings).
    3. Synthesizes response with LLM.
    4. Automatically logs query record with linked content_ids and feed_ids into the database.
    5. Returns answer along with retrieved chunks for inspection.
    """
    question = (body.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    selected_ids = body.selected_ids or []
    if not selected_ids:
        raise HTTPException(status_code=400, detail="Please select at least one document or source to query against")

    # Fetch user mapped content_ids and feed_ids, and all active system IDs
    user_content_ids = set(await get_user_content_ids(user_id))
    user_feed_ids = set(await get_user_feed_ids(user_id))
    all_user_ids = user_content_ids | user_feed_ids
    all_system_ids = set(await get_all_active_source_ids())
    allowed_ids = all_user_ids | all_system_ids

    # Validate that selected IDs exist in active system/user sources
    valid_ids = [sid for sid in selected_ids if sid in allowed_ids]
    if not valid_ids:
        raise HTTPException(status_code=403, detail="None of the selected sources are available or exist in your knowledge base")

    matched_content_ids = [sid for sid in valid_ids if sid in (user_content_ids | all_system_ids)]
    matched_feed_ids = [sid for sid in valid_ids if sid in (user_feed_ids | all_system_ids)]

    # Run RAG retrieval pipeline
    chunks = []
    try:
        chunks = await get_all_chunks(question, valid_ids)
    except FileNotFoundError as e:
        logger.warning("[user_query_endpoint] Missing index files: %s", e)
    except Exception as e:
        logger.exception("[user_query_endpoint] Retrieval failed: %s", e)

    inspectable_chunks = extract_inspectable_chunks(chunks)

    if not chunks:
        answer = (
            "No relevant chunks were matched in the selected documents for your query. "
            "Try selecting more documents, or rephrase your question with different keywords."
        )
    else:
        context = await build_context(chunks)
        try:
            answer = await generate_answer(question, context)
        except Exception as e:
            logger.exception("[user_query_endpoint] LLM answer generation failed: %s", e)
            raise HTTPException(status_code=502, detail=f"LLM answer generation failed: {e}")

    # Persist query in database linked with content_ids and feed_ids
    saved_record = await save_user_query(
        user_id=user_id,
        question=question,
        answer=answer,
        content_ids=matched_content_ids,
        feed_ids=matched_feed_ids,
        selected_ids=valid_ids,
        chunks_found=len(chunks),
    )

    return {
        **saved_record,
        "sources_queried": len(valid_ids),
        "chunks": inspectable_chunks,
    }


async def get_query_history_endpoint(limit: int = 50, user_id: str = Depends(auth_middleware)):
    """Fetch query evaluation history for the logged-in user."""
    history = await get_user_queries(user_id=user_id, limit=limit)
    return {"history": history}


async def delete_query_history_endpoint(query_id: str, user_id: str = Depends(auth_middleware)):
    """Delete a specific test query from history."""
    success = await delete_user_query(query_id=query_id, user_id=user_id)
    return {"success": success, "message": "Query record removed"}


async def clear_query_history_endpoint(user_id: str = Depends(auth_middleware)):
    """Clear all test query history for the user."""
    await clear_user_query_history(user_id=user_id)
    return {"success": True, "message": "Query history cleared"}


async def get_user_queryable_sources(user_id: str = Depends(auth_middleware)):
    """Return all sources owned by the user with details for the RAG Playground selector."""
    try:
        sources = await get_user_sources_with_details(user_id)
        return {"sources": sources}
    except Exception as e:
        logger.exception("[get_user_queryable_sources] Failed to fetch sources: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


async def get_all_queryable_sources(user_id: str = Depends(auth_middleware)):
    """Return all sources in the system with details for the RAG Playground selector."""
    try:
        sources = await get_all_sources_with_details(current_user_id=user_id)
        return {"sources": sources}
    except Exception as e:
        logger.exception("[get_all_queryable_sources] Failed to fetch all sources: %s", e)
        raise HTTPException(status_code=500, detail=str(e))