import logging
from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from Dbhelper.db import AsyncDB

logger = logging.getLogger(__name__)


async def link_user_to_content(user_id: str, content_id: str) -> bool:
    """Map a user to a document content record (feed_id = NULL). Idempotent via ON CONFLICT DO NOTHING."""
    try:
        async with AsyncDB() as s:
            result = await s.execute(
                text("""
                    INSERT INTO user_mappings (user_id, content_id)
                    VALUES (:uid, :cid)
                    ON CONFLICT DO NOTHING
                """),
                {"uid": user_id, "cid": content_id},
            )
            await s.commit()
            return (result.rowcount or 0) > 0
    except SQLAlchemyError:
        logger.exception("[user_mapping_db_helper] Database error linking user_id=%s to content_id=%s", user_id, content_id)
        return False
    except Exception:
        logger.exception("[user_mapping_db_helper] Unexpected error linking user_id=%s to content_id=%s", user_id, content_id)
        return False


async def link_user_to_feed(user_id: str, feed_id: str) -> bool:
    """Map a user to a website feed record (content_id = NULL). Idempotent via ON CONFLICT DO NOTHING."""
    try:
        async with AsyncDB() as s:
            result = await s.execute(
                text("""
                    INSERT INTO user_mappings (user_id, feed_id)
                    VALUES (:uid, :fid)
                    ON CONFLICT DO NOTHING
                """),
                {"uid": user_id, "fid": feed_id},
            )
            await s.commit()
            return (result.rowcount or 0) > 0
    except SQLAlchemyError:
        logger.exception("[user_mapping_db_helper] Database error linking user_id=%s to feed_id=%s", user_id, feed_id)
        return False
    except Exception:
        logger.exception("[user_mapping_db_helper] Unexpected error linking user_id=%s to feed_id=%s", user_id, feed_id)
        return False


async def get_user_mappings(user_id: str) -> List[dict]:
    """Fetch all content and feed mappings for a user."""
    try:
        async with AsyncDB() as s:
            rows = (
                await s.execute(
                    text("SELECT * FROM user_mappings WHERE user_id = :uid"),
                    {"uid": user_id},
                )
            ).mappings().all()
            return [dict(r) for r in rows]
    except SQLAlchemyError:
        logger.exception("[user_mapping_db_helper] Database error fetching mappings for user_id=%s", user_id)
        return []
    except Exception:
        logger.exception("[user_mapping_db_helper] Unexpected error fetching mappings for user_id=%s", user_id)
        return []


async def get_user_content_ids(user_id: str) -> List[str]:
    """Fetch the content_ids a user is mapped to (including unmapped active content)."""
    try:
        async with AsyncDB() as s:
            rows = (
                await s.execute(
                    text("""
                        SELECT DISTINCT c.content_id FROM contents c
                        LEFT JOIN user_mappings um ON c.content_id = um.content_id
                        WHERE (um.user_id = :uid OR um.user_id IS NULL)
                          AND c.deleted_at IS NULL
                    """),
                    {"uid": user_id},
                )
            ).mappings().all()
            return [r["content_id"] for r in rows]
    except SQLAlchemyError:
        logger.exception("[user_mapping_db_helper] Database error fetching content_ids for user_id=%s", user_id)
        return []
    except Exception:
        logger.exception("[user_mapping_db_helper] Unexpected error fetching content_ids for user_id=%s", user_id)
        return []


async def get_user_feed_ids(user_id: str) -> List[str]:
    """Fetch the feed_ids a user is mapped to (including unmapped active feeds)."""
    try:
        async with AsyncDB() as s:
            rows = (
                await s.execute(
                    text("""
                        SELECT DISTINCT f.feed_id FROM feeds f
                        LEFT JOIN user_mappings um ON f.feed_id = um.feed_id
                        WHERE (um.user_id = :uid OR um.user_id IS NULL)
                          AND f.deleted_at IS NULL
                    """),
                    {"uid": user_id},
                )
            ).mappings().all()
            return [r["feed_id"] for r in rows]
    except SQLAlchemyError:
        logger.exception("[user_mapping_db_helper] Database error fetching feed_ids for user_id=%s", user_id)
        return []
    except Exception:
        logger.exception("[user_mapping_db_helper] Unexpected error fetching feed_ids for user_id=%s", user_id)
        return []


async def get_users_for_content(content_id: str) -> List[str]:
    """Reverse lookup: fetch the user_ids mapped to a given content_id."""
    try:
        async with AsyncDB() as s:
            rows = (
                await s.execute(
                    text("SELECT user_id FROM user_mappings WHERE content_id = :cid"),
                    {"cid": content_id},
                )
            ).mappings().all()
            return [r["user_id"] for r in rows]
    except SQLAlchemyError:
        logger.exception("[user_mapping_db_helper] Database error fetching users for content_id=%s", content_id)
        return []
    except Exception:
        logger.exception("[user_mapping_db_helper] Unexpected error fetching users for content_id=%s", content_id)
        return []


async def get_users_for_feed(feed_id: str) -> List[str]:
    """Reverse lookup: fetch the user_ids mapped to a given feed_id."""
    try:
        async with AsyncDB() as s:
            rows = (
                await s.execute(
                    text("SELECT user_id FROM user_mappings WHERE feed_id = :fid"),
                    {"fid": feed_id},
                )
            ).mappings().all()
            return [r["user_id"] for r in rows]
    except SQLAlchemyError:
        logger.exception("[user_mapping_db_helper] Database error fetching users for feed_id=%s", feed_id)
        return []
    except Exception:
        logger.exception("[user_mapping_db_helper] Unexpected error fetching users for feed_id=%s", feed_id)
        return []


async def user_has_content_mapping(user_id: str, content_id: str) -> bool:
    """Check whether a user-content mapping already exists."""
    try:
        async with AsyncDB() as s:
            row = (
                await s.execute(
                    text("""
                        SELECT 1 FROM user_mappings
                        WHERE user_id = :uid AND content_id = :cid
                    """),
                    {"uid": user_id, "cid": content_id},
                )
            ).first()
            return row is not None
    except SQLAlchemyError:
        logger.exception("[user_mapping_db_helper] Database error checking mapping user_id=%s, content_id=%s", user_id, content_id)
        return False
    except Exception:
        logger.exception("[user_mapping_db_helper] Unexpected error checking mapping user_id=%s, content_id=%s", user_id, content_id)
        return False


async def user_has_feed_mapping(user_id: str, feed_id: str) -> bool:
    """Check whether a user-feed mapping already exists."""
    try:
        async with AsyncDB() as s:
            row = (
                await s.execute(
                    text("""
                        SELECT 1 FROM user_mappings
                        WHERE user_id = :uid AND feed_id = :fid
                    """),
                    {"uid": user_id, "fid": feed_id},
                )
            ).first()
            return row is not None
    except SQLAlchemyError:
        logger.exception("[user_mapping_db_helper] Database error checking mapping user_id=%s, feed_id=%s", user_id, feed_id)
        return False
    except Exception:
        logger.exception("[user_mapping_db_helper] Unexpected error checking mapping user_id=%s, feed_id=%s", user_id, feed_id)
        return False


async def count_user_mappings(user_id: str) -> int:
    """Return the total number of mappings (content + feed) for a user."""
    try:
        async with AsyncDB() as s:
            row = (
                await s.execute(
                    text("SELECT COUNT(*) AS cnt FROM user_mappings WHERE user_id = :uid"),
                    {"uid": user_id},
                )
            ).mappings().first()
            return int(row["cnt"]) if row else 0
    except SQLAlchemyError:
        logger.exception("[user_mapping_db_helper] Database error counting mappings for user_id=%s", user_id)
        return 0
    except Exception:
        logger.exception("[user_mapping_db_helper] Unexpected error counting mappings for user_id=%s", user_id)
        return 0


async def unlink_user_from_content(user_id: str, content_id: str) -> bool:
    """Remove a single user-content mapping."""
    try:
        async with AsyncDB() as s:
            result = await s.execute(
                text("""
                    DELETE FROM user_mappings
                    WHERE user_id = :uid AND content_id = :cid
                """),
                {"uid": user_id, "cid": content_id},
            )
            await s.commit()
            return (result.rowcount or 0) > 0
    except SQLAlchemyError:
        logger.exception("[user_mapping_db_helper] Database error unlinking user_id=%s from content_id=%s", user_id, content_id)
        return False
    except Exception:
        logger.exception("[user_mapping_db_helper] Unexpected error unlinking user_id=%s from content_id=%s", user_id, content_id)
        return False


async def unlink_user_from_feed(user_id: str, feed_id: str) -> bool:
    """Remove a single user-feed mapping."""
    try:
        async with AsyncDB() as s:
            result = await s.execute(
                text("""
                    DELETE FROM user_mappings
                    WHERE user_id = :uid AND feed_id = :fid
                """),
                {"uid": user_id, "fid": feed_id},
            )
            await s.commit()
            return (result.rowcount or 0) > 0
    except SQLAlchemyError:
        logger.exception("[user_mapping_db_helper] Database error unlinking user_id=%s from feed_id=%s", user_id, feed_id)
        return False
    except Exception:
        logger.exception("[user_mapping_db_helper] Unexpected error unlinking user_id=%s from feed_id=%s", user_id, feed_id)
        return False


async def delete_all_user_mappings(user_id: str) -> bool:
    """Remove all mappings (content and feed) for a user. Returns True if at least one row was deleted."""
    try:
        async with AsyncDB() as s:
            result = await s.execute(
                text("DELETE FROM user_mappings WHERE user_id = :uid"),
                {"uid": user_id},
            )
            await s.commit()
            return (result.rowcount or 0) > 0
    except SQLAlchemyError:
        logger.exception("[user_mapping_db_helper] Database error deleting all mappings for user_id=%s", user_id)
        return False
    except Exception:
        logger.exception("[user_mapping_db_helper] Unexpected error deleting all mappings for user_id=%s", user_id)
        return False


async def get_user_sources_with_details(user_id: str) -> List[dict]:
    """Fetch all content and feed sources mapped to a user, with full details from contents/feeds tables."""
    try:
        async with AsyncDB() as s:
            # Fetch content sources (mapped to user or unmapped active)
            content_rows = (
                await s.execute(
                    text("""
                        SELECT DISTINCT c.content_id AS id, c.name, c.file_type AS type,
                               c.chunks, c.file_size, c.inserted_at
                        FROM contents c
                        LEFT JOIN user_mappings um ON c.content_id = um.content_id
                        WHERE (um.user_id = :uid OR um.user_id IS NULL)
                          AND c.deleted_at IS NULL
                        ORDER BY c.inserted_at DESC
                    """),
                    {"uid": user_id},
                )
            ).mappings().all()

            # Fetch feed sources (mapped to user or unmapped active)
            feed_rows = (
                await s.execute(
                    text("""
                        SELECT DISTINCT f.feed_id AS id, f.url AS name, 'website' AS type,
                               f.chunks, NULL AS file_size, f.inserted_at
                        FROM feeds f
                        LEFT JOIN user_mappings um ON f.feed_id = um.feed_id
                        WHERE (um.user_id = :uid OR um.user_id IS NULL)
                          AND f.deleted_at IS NULL
                        ORDER BY f.inserted_at DESC
                    """),
                    {"uid": user_id},
                )
            ).mappings().all()

            sources = []
            for r in content_rows:
                sources.append({
                    "id": r["id"],
                    "name": r["name"],
                    "type": str(r["type"]).capitalize() if r["type"] != "website" else "Url",
                    "chunks": r["chunks"],
                    "file_size": r["file_size"],
                    "status": "Ingested",
                    "inserted_at": r["inserted_at"].isoformat() if r["inserted_at"] else None,
                })
            for r in feed_rows:
                sources.append({
                    "id": r["id"],
                    "name": r["name"],
                    "type": "Url",
                    "chunks": r["chunks"],
                    "file_size": None,
                    "status": "Ingested",
                    "inserted_at": r["inserted_at"].isoformat() if r["inserted_at"] else None,
                })

            return sources
    except SQLAlchemyError:
        logger.exception("[user_mapping_db_helper] Database error fetching sources for user_id=%s", user_id)
        return []
    except Exception:
        logger.exception("[user_mapping_db_helper] Unexpected error fetching sources for user_id=%s", user_id)
        return []


async def get_all_sources_with_details(current_user_id: Optional[str] = None) -> List[dict]:
    """Fetch all active content and feed sources in the database across all users, with owner information."""
    try:
        async with AsyncDB() as s:
            content_rows = (
                await s.execute(
                    text("""
                        SELECT DISTINCT c.content_id AS id, c.name, c.file_type AS type,
                               c.chunks, c.file_size, c.inserted_at,
                               um.user_id AS owner_user_id,
                               u.username AS owner_username
                        FROM contents c
                        LEFT JOIN user_mappings um ON c.content_id = um.content_id
                        LEFT JOIN users u ON um.user_id = u.user_id
                        WHERE c.deleted_at IS NULL
                        ORDER BY c.inserted_at DESC
                    """)
                )
            ).mappings().all()

            feed_rows = (
                await s.execute(
                    text("""
                        SELECT DISTINCT f.feed_id AS id, f.url AS name, 'website' AS type,
                               f.chunks, NULL AS file_size, f.inserted_at,
                               um.user_id AS owner_user_id,
                               u.username AS owner_username
                        FROM feeds f
                        LEFT JOIN user_mappings um ON f.feed_id = um.feed_id
                        LEFT JOIN users u ON um.user_id = u.user_id
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
                is_mine = bool(current_user_id and r["owner_user_id"] == current_user_id)
                sources.append({
                    "id": cid,
                    "name": r["name"],
                    "type": str(r["type"]).capitalize() if r["type"] != "website" else "Url",
                    "chunks": r["chunks"],
                    "file_size": r["file_size"],
                    "status": "Ingested",
                    "inserted_at": r["inserted_at"].isoformat() if r["inserted_at"] else None,
                    "is_mine": is_mine,
                    "owner": ("You" if is_mine else (r["owner_username"] or "Shared")),
                })

            for r in feed_rows:
                fid = r["id"]
                if fid in seen_ids:
                    continue
                seen_ids.add(fid)
                is_mine = bool(current_user_id and r["owner_user_id"] == current_user_id)
                sources.append({
                    "id": fid,
                    "name": r["name"],
                    "type": "Url",
                    "chunks": r["chunks"],
                    "file_size": None,
                    "status": "Ingested",
                    "inserted_at": r["inserted_at"].isoformat() if r["inserted_at"] else None,
                    "is_mine": is_mine,
                    "owner": ("You" if is_mine else (r["owner_username"] or "Shared")),
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