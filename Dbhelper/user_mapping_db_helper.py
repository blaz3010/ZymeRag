import logging
from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from Dbhelper.db import AsyncDB

logger = logging.getLogger(__name__)


async def get_all_sources_with_details() -> List[dict]:
    """Fetch all active content and feed sources in the database with full details."""
    try:
        async with AsyncDB() as s:
            content_rows = (
                await s.execute(
                    text("""
                        SELECT DISTINCT c.content_id AS id, c.name, c.file_type AS type,
                               c.chunks, c.file_size, c.inserted_at
                        FROM contents c
                        WHERE c.deleted_at IS NULL
                        ORDER BY c.inserted_at DESC
                    """)
                )
            ).mappings().all()

            feed_rows = (
                await s.execute(
                    text("""
                        SELECT DISTINCT f.feed_id AS id, f.url AS name, 'website' AS type,
                               f.chunks, NULL AS file_size, f.inserted_at
                        FROM feeds f
                        WHERE f.deleted_at IS NULL
                        ORDER BY f.inserted_at DESC
                    """)
                )
            ).mappings().all()

            sources = []
            seen_ids = set()
            for r in content_rows:
                cid = r["id"]
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)
                sources.append({
                    "id": cid,
                    "name": r["name"],
                    "type": str(r["type"]).capitalize() if r["type"] != "website" else "Url",
                    "chunks": r["chunks"],
                    "file_size": r["file_size"],
                    "status": "Ingested",
                    "inserted_at": r["inserted_at"].isoformat() if r["inserted_at"] else None,
                    "is_mine": True,
                    "owner": "Public",
                })

            for r in feed_rows:
                fid = r["id"]
                if fid in seen_ids:
                    continue
                seen_ids.add(fid)
                sources.append({
                    "id": fid,
                    "name": r["name"],
                    "type": "Url",
                    "chunks": r["chunks"],
                    "file_size": None,
                    "status": "Ingested",
                    "inserted_at": r["inserted_at"].isoformat() if r["inserted_at"] else None,
                    "is_mine": True,
                    "owner": "Public",
                })

            return sources
    except SQLAlchemyError:
        logger.exception("[user_mapping_db_helper] Database error fetching all sources")
        return []
    except Exception:
        logger.exception("[user_mapping_db_helper] Unexpected error fetching all sources")
        return []


async def get_all_active_source_ids() -> List[str]:
    """Return all active content_ids and feed_ids across the platform."""
    try:
        async with AsyncDB() as s:
            c_rows = (await s.execute(text("SELECT content_id FROM contents WHERE deleted_at IS NULL"))).scalars().all()
            f_rows = (await s.execute(text("SELECT feed_id FROM feeds WHERE deleted_at IS NULL"))).scalars().all()
            return list(set(c_rows) | set(f_rows))
    except Exception:
        logger.exception("[user_mapping_db_helper] Error fetching all active source IDs")
        return []