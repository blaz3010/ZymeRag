import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from Dbhelper.db import AsyncDB

logger = logging.getLogger(__name__)

# In-memory fallback in case the database is temporarily unreachable
_IN_MEMORY_QUERY_STORE = []

_TABLE_ENSURED = False


async def ensure_queries_table() -> bool:
    """Ensure that the queries table exists in PostgreSQL."""
    global _TABLE_ENSURED
    if _TABLE_ENSURED:
        return True

    ddl_statements = [
        """
        CREATE TABLE IF NOT EXISTS queries (
            id           BIGSERIAL    PRIMARY KEY,
            query_id     VARCHAR(255) UNIQUE NOT NULL,
            question     TEXT         NOT NULL,
            answer       TEXT         NOT NULL,
            content_ids  TEXT         NOT NULL DEFAULT '[]',
            feed_ids     TEXT         NOT NULL DEFAULT '[]',
            selected_ids TEXT         NOT NULL DEFAULT '[]',
            chunks_found INTEGER      NOT NULL DEFAULT 0,
            created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_queries_created_at ON queries(created_at DESC)",
    ]

    try:
        async with AsyncDB() as s:
            for stmt in ddl_statements:
                await s.execute(text(stmt))
            await s.commit()
            _TABLE_ENSURED = True
            logger.info("[query_db_helper] queries table and indexes verified.")
            return True
    except Exception as e:
        logger.warning("[query_db_helper] Table creation check failed or already exists: %s", e)
        return False


def _parse_json_list(val) -> list:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
    return []


async def save_query(
    question: str,
    answer: str,
    content_ids: Optional[List[str]] = None,
    feed_ids: Optional[List[str]] = None,
    selected_ids: Optional[List[str]] = None,
    chunks_found: int = 0
) -> dict:
    """
    Save a query linked with content_ids and feed_ids to the database.
    Falls back gracefully if the database connection fails.
    """
    query_id = str(uuid.uuid4())
    content_ids = content_ids or []
    feed_ids = feed_ids or []
    selected_ids = selected_ids or (content_ids + feed_ids)
    now_iso = datetime.utcnow().isoformat()

    record = {
        "query_id": query_id,
        "question": question,
        "answer": answer,
        "content_ids": content_ids,
        "feed_ids": feed_ids,
        "selected_ids": selected_ids,
        "chunks_found": chunks_found,
        "created_at": now_iso,
    }

    try:
        await ensure_queries_table()
        async with AsyncDB() as s:
            await s.execute(
                text("""
                    INSERT INTO queries
                        (query_id, question, answer, content_ids, feed_ids, selected_ids, chunks_found)
                    VALUES
                        (:qid, :q, :a, :cids, :fids, :sids, :cf)
                """),
                {
                    "qid": query_id,
                    "q": question,
                    "a": answer,
                    "cids": json.dumps(content_ids),
                    "fids": json.dumps(feed_ids),
                    "sids": json.dumps(selected_ids),
                    "cf": chunks_found,
                },
            )
            await s.commit()
            logger.info("[query_db_helper] Successfully saved query %s", query_id)
            return record
    except SQLAlchemyError as sqle:
        logger.exception("[query_db_helper] Database error saving query: %s", sqle)
    except Exception as e:
        logger.exception("[query_db_helper] Unexpected error saving query: %s", e)

    # In-memory store fallback
    _IN_MEMORY_QUERY_STORE.insert(0, record)
    return record


async def get_queries(limit: int = 50) -> List[dict]:
    """
    Fetch historical queries ordered from newest to oldest.
    """
    try:
        await ensure_queries_table()
        async with AsyncDB() as s:
            rows = (
                await s.execute(
                    text("""
                        SELECT query_id, question, answer, content_ids, feed_ids, selected_ids, chunks_found, created_at
                        FROM queries
                        ORDER BY created_at DESC
                        LIMIT :lim
                    """),
                    {"lim": limit},
                )
            ).mappings().all()

            results = []
            for r in rows:
                results.append({
                    "query_id": r["query_id"],
                    "question": r["question"],
                    "answer": r["answer"],
                    "content_ids": _parse_json_list(r["content_ids"]),
                    "feed_ids": _parse_json_list(r["feed_ids"]),
                    "selected_ids": _parse_json_list(r["selected_ids"]),
                    "chunks_found": r["chunks_found"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                })
            return results
    except Exception as e:
        logger.warning("[query_db_helper] Falling back to in-memory store: %s", e)
        return list(_IN_MEMORY_QUERY_STORE[:limit])


async def get_query_by_id(query_id: str) -> Optional[dict]:
    """
    Fetch details for a specific query.
    """
    try:
        async with AsyncDB() as s:
            row = (
                await s.execute(
                    text("SELECT * FROM queries WHERE query_id = :qid"),
                    {"qid": query_id},
                )
            ).mappings().first()
            if row:
                return {
                    "query_id": row["query_id"],
                    "question": row["question"],
                    "answer": row["answer"],
                    "content_ids": _parse_json_list(row["content_ids"]),
                    "feed_ids": _parse_json_list(row["feed_ids"]),
                    "selected_ids": _parse_json_list(row["selected_ids"]),
                    "chunks_found": row["chunks_found"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                }
    except Exception as e:
        logger.warning("[query_db_helper] Lookup failed: %s", e)

    for q in _IN_MEMORY_QUERY_STORE:
        if q["query_id"] == query_id:
            return q
    return None


async def delete_query(query_id: str) -> bool:
    """
    Delete a query from history.
    """
    deleted = False
    try:
        async with AsyncDB() as s:
            res = await s.execute(
                text("DELETE FROM queries WHERE query_id = :qid"),
                {"qid": query_id},
            )
            await s.commit()
            deleted = (res.rowcount or 0) > 0
    except Exception as e:
        logger.warning("[query_db_helper] DB delete failed: %s", e)

    # Clean in-memory store
    global _IN_MEMORY_QUERY_STORE
    prev_len = len(_IN_MEMORY_QUERY_STORE)
    _IN_MEMORY_QUERY_STORE = [
        q for q in _IN_MEMORY_QUERY_STORE
        if q["query_id"] != query_id
    ]
    if len(_IN_MEMORY_QUERY_STORE) < prev_len:
        deleted = True

    return deleted


async def clear_query_history() -> bool:
    """
    Clear all past test queries.
    """
    try:
        async with AsyncDB() as s:
            await s.execute(text("DELETE FROM queries"))
            await s.commit()
    except Exception as e:
        logger.warning("[query_db_helper] DB clear failed: %s", e)

    global _IN_MEMORY_QUERY_STORE
    _IN_MEMORY_QUERY_STORE = []
    return True