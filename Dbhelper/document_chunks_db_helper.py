import json
import logging
import math
from typing import Literal, Optional

from sqlalchemy import (
    BigInteger, Column, DateTime, Float, Integer, MetaData, String, Table,
    Text, bindparam, cast, delete, func, insert, literal, literal_column,
    or_, select, text, union_all,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.types import UserDefinedType

from Dbhelper.db import AsyncDB

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1024
BATCH_SIZE = 200

OwnerColumn = Literal["content_id", "feed_id"]


class Vector(UserDefinedType):
    cache_ok = True

    def __init__(self, dim: Optional[int] = None):
        self.dim = dim

    def get_col_spec(self, **kw):
        return "extensions.vector" + (f"({self.dim})" if self.dim else "")


metadata_obj = MetaData()

document_chunks = Table(
    "document_chunks",
    metadata_obj,
    Column("id", BigInteger, primary_key=True),
    Column("content_id", String),
    Column("feed_id", String),
    Column("chunk_index", Integer, nullable=False),
    Column("content", Text, nullable=False),
    Column("embedding", Vector(EMBEDDING_DIM)),
    Column("metadata", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True)),
    Column("search_vector", TSVECTOR), 
)
t = document_chunks.c


_RESULT_COLUMNS = (
    t.id.label("chunk_id"),
    t.content_id,
    t.feed_id,
    t.chunk_index,
    t.content,
    t["metadata"],
)


def _valid_owner(content_id: Optional[str], feed_id: Optional[str]) -> bool:
    if (content_id is None) == (feed_id is None):
        logger.error("Exactly one of content_id or feed_id must be provided")
        return False
    return True


def _owner_col(column: OwnerColumn):
    if column not in ("content_id", "feed_id"):
        raise ValueError(f"Invalid column: {column!r}")
    return t[column]


def _owner_filter(content_id: Optional[str], feed_id: Optional[str]):
    if content_id is not None:
        return t.content_id == content_id
    return t.feed_id == feed_id


def _owner_in(ids: list[str], column: Optional[OwnerColumn] = None):
    if column is not None:
        return _owner_col(column).in_(ids)
    return or_(t.content_id.in_(ids), t.feed_id.in_(ids))


def _clean_ids(ids) -> list[str]:
    return list(dict.fromkeys(i for i in (ids or []) if i))


def _vector_literal(embedding) -> str:
    if hasattr(embedding, "tolist"):  # numpy / tensor
        embedding = embedding.tolist()
    values = [float(v) for v in embedding]
    if len(values) != EMBEDDING_DIM:
        raise ValueError(f"Expected {EMBEDDING_DIM} dims, got {len(values)}")
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Embedding contains NaN or inf")
    return "[" + ",".join(map(str, values)) + "]"


def _vector_param(embedding):
    # Bound as text and cast server-side, so the driver needs no vector codec.
    return cast(literal(_vector_literal(embedding), Text), Vector())




async def save_chunks_to_database(
    chunks,
    embeddings,
    content_id: Optional[str] = None,
    feed_id: Optional[str] = None,
) -> bool:
    if not _valid_owner(content_id, feed_id):
        return False

    if len(chunks) != len(embeddings):
        logger.error("Chunks and embeddings count mismatch")
        return False

    try:
        records = [
            {
                "p_content_id": content_id,
                "p_feed_id": feed_id,
                "p_chunk_index": index,
                "p_content": chunk.page_content.replace("\x00", ""),
                "p_embedding": _vector_literal(embedding),
                "p_metadata": json.loads(
                    json.dumps(chunk.metadata or {}, default=str)
                ),
            }
            for index, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]

        insert_stmt = insert(document_chunks).values({
            "content_id": bindparam("p_content_id"),
            "feed_id": bindparam("p_feed_id"),
            "chunk_index": bindparam("p_chunk_index"),
            "content": bindparam("p_content"),
            "embedding": cast(bindparam("p_embedding", type_=Text), Vector()),
            "metadata": bindparam("p_metadata", type_=JSONB),
        })

        async with AsyncDB() as s:
            await s.execute(
                delete(document_chunks).where(_owner_filter(content_id, feed_id))
            )
            for i in range(0, len(records), BATCH_SIZE):
                await s.execute(insert_stmt, records[i:i + BATCH_SIZE])
            await s.commit()

        logger.info(
            "Saved %s chunks for content_id=%s feed_id=%s",
            len(records), content_id, feed_id,
        )
        return True

    except ValueError:
        logger.exception("Invalid chunk/embedding data")
        return False
    except SQLAlchemyError:
        logger.exception(
            "Database error saving chunks for content_id=%s feed_id=%s",
            content_id, feed_id,
        )
        return False
    except Exception:
        logger.exception(
            "Unexpected error saving chunks for content_id=%s feed_id=%s",
            content_id, feed_id,
        )
        return False


async def delete_chunks_from_database(
    content_id: Optional[str] = None,
    feed_id: Optional[str] = None,
) -> bool:
    if not _valid_owner(content_id, feed_id):
        return False

    try:
        async with AsyncDB() as s:
            await s.execute(
                delete(document_chunks).where(_owner_filter(content_id, feed_id))
            )
            await s.commit()
        return True

    except SQLAlchemyError:
        logger.exception("Database error deleting document chunks")
        return False
    except Exception:
        logger.exception("Unexpected error deleting document chunks")
        return False




async def get_chunks_from_database(
    content_id: Optional[str] = None,
    feed_id: Optional[str] = None,
) -> list[dict]:
    if not _valid_owner(content_id, feed_id):
        return []

    try:
        stmt = (
            select(t.id, *_RESULT_COLUMNS)
            .where(_owner_filter(content_id, feed_id))
            .order_by(t.chunk_index)
        )
        async with AsyncDB() as s:
            result = await s.execute(stmt)
            return [dict(row) for row in result.mappings().all()]

    except SQLAlchemyError:
        logger.exception("Database error retrieving document chunks")
        return []
    except Exception:
        logger.exception("Unexpected error retrieving document chunks")
        return []



async def get_semantic_chunks_by_ids(
    query_embedding,
    ids: list[str],
    column: Optional[OwnerColumn] = None,   # None = match content_id OR feed_id
    top_k: int = 6,
    iterative_scan: bool = False,
) -> list[dict]:
    ids = _clean_ids(ids)
    if (
        query_embedding is None
        or len(query_embedding) == 0
        or not ids
        or top_k <= 0
    ):
        return []

    try:
        qvec = _vector_param(query_embedding)
        distance = t.embedding.op("<=>", return_type=Float)(qvec)

        stmt = (
            select(*_RESULT_COLUMNS, (1 - distance).label("similarity"))
            .where(_owner_in(ids, column))
            .where(t.embedding.is_not(None))
            .order_by(distance, t.id)
            .limit(top_k)
        )
        async with AsyncDB() as s:
            if iterative_scan:
                await s.execute(
                    text("SET LOCAL hnsw.iterative_scan = relaxed_order")
                )
                await s.execute(text("SET LOCAL hnsw.ef_search = 100"))
            result = await s.execute(stmt)
            return [dict(r) for r in result.mappings().all()]

    except ValueError:
        logger.exception("Invalid query embedding")
        return []
    except SQLAlchemyError:
        logger.exception("Database error during semantic chunk retrieval")
        return []
    except Exception:
        logger.exception("Unexpected error during semantic chunk retrieval")
        return []


async def get_keyword_chunks_by_ids(
    query: str,
    ids: list[str],
    column: Optional[OwnerColumn] = None,   # None = match content_id OR feed_id
    top_k: int = 6,
    websearch: bool = False,
) -> list[dict]:
    ids = _clean_ids(ids)
    if not query or not query.strip() or not ids or top_k <= 0:
        return []

    try:
        ts_func = func.websearch_to_tsquery if websearch else func.to_tsquery
        tsq = ts_func(literal_column("'english'::regconfig"), query)
        rank = func.ts_rank_cd(t.search_vector, tsq)

        stmt = (
            select(*_RESULT_COLUMNS, rank.label("rank"))
            .where(_owner_in(ids, column))
            .where(t.search_vector.op("@@", is_comparison=True)(tsq))
            .order_by(rank.desc(), t.id)
            .limit(top_k)
        )
        async with AsyncDB() as s:
            result = await s.execute(stmt)
            return [dict(r) for r in result.mappings().all()]

    except SQLAlchemyError:
        logger.exception("Database error during keyword chunk retrieval")
        return []
    except Exception:
        logger.exception("Unexpected error during keyword chunk retrieval")
        return []


async def get_semantic_based_chunks(
    query_embedding: list[float],
    content_id: Optional[str] = None,
    feed_id: Optional[str] = None,
    top_k: int = 6,
) -> list[dict]:
    if not _valid_owner(content_id, feed_id):
        return []
    column: OwnerColumn = "content_id" if content_id is not None else "feed_id"
    owner = content_id if content_id is not None else feed_id
    return await get_semantic_chunks_by_ids(
        query_embedding, [owner], column, top_k
    )


async def get_keyword_based_chunks(
    query: str,
    content_id: Optional[str] = None,
    feed_id: Optional[str] = None,
    top_k: int = 6,
) -> list[dict]:
    if not _valid_owner(content_id, feed_id):
        return []
    column: OwnerColumn = "content_id" if content_id is not None else "feed_id"
    owner = content_id if content_id is not None else feed_id
    return await get_keyword_chunks_by_ids(
        query, [owner], column, top_k, websearch=True
    )

async def get_chunks_by_source_id(source_id: str) -> list[dict]:
    try:
        by_content = select(*_RESULT_COLUMNS).where(t.content_id == source_id)
        by_feed = select(*_RESULT_COLUMNS).where(t.feed_id == source_id)
        u = union_all(by_content, by_feed).subquery()
        stmt = select(u).order_by(u.c.chunk_index, u.c.id)
        async with AsyncDB() as s:
            result = await s.execute(stmt)
            return [dict(row) for row in result.mappings().all()]

    except SQLAlchemyError:
        logger.exception("Database error retrieving chunks (source_id=%s)", source_id)
        return []
    except Exception:
        logger.exception("Unexpected error retrieving chunks (source_id=%s)", source_id)
        return []