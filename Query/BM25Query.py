import logging
import re
from typing import Union

from Dbhelper.document_chunks_db_helper import get_keyword_chunks_by_ids  # adjust to your helper's module name

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"\b\w+\b")
MAX_QUERY_TOKENS = 32


class BM25:
    """
    Keyword retrieval over document_chunks using Postgres full-text search.
    (Name kept for compatibility; ranking is ts_rank_cd, not true BM25.)
    """

    _COLUMNS = {"Feed": "feed_id", "Content": "content_id"}

    def __init__(self, top_k: int = 6):
        self.top_k = top_k

    @staticmethod
    def tokenize(value: str) -> list[str]:
        return _TOKEN_RE.findall(value.lower())

    @classmethod
    def build_or_query(cls, query: str) -> str:
        """
        OR-join the query terms for to_tsquery, so any matching term counts.
        websearch_to_tsquery would AND every term and often return nothing
        for natural-language questions. Tokens are \\w+ only, so they're
        safe to pass to to_tsquery.
        """
        tokens = [
            tok for tok in cls.tokenize(query)
            if any(c.isalnum() for c in tok)
        ]
        tokens = list(dict.fromkeys(tokens))[:MAX_QUERY_TOKENS]
        return " | ".join(tokens)

    async def _search_many(
        self, kind: str, query: str, ids: list[str], top_k: int
    ) -> list[dict]:
        ts_query = self.build_or_query(query)
        if not ts_query or not ids or top_k <= 0:
            return []

        return await get_keyword_chunks_by_ids(
            ts_query,
            ids,
            self._COLUMNS[kind],
            top_k,
            websearch=False,  # ts_query is already a to_tsquery expression
        )

    @staticmethod
    def _format(
        rows: list[dict], as_rows: bool
    ) -> Union[list[dict], list[tuple[str, float]]]:
        if as_rows:
            return rows
        return [(r["content"], float(r["rank"])) for r in rows]

    async def get_keyword_chunks(self, query, uuids, top_k=None, as_rows=False):
        rows = await get_keyword_chunks_by_ids(
            self._build_query(query), uuids, top_k=top_k or self.top_k
        )
        return self._format(rows, as_rows)