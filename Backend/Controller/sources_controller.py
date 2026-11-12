from fastapi import Query, HTTPException
from Dbhelper.user_mapping_db_helper import (
    get_all_sources_with_details,
)
from Dbhelper.document_chunks_db_helper import get_chunks_from_database
from Backend.Utils.Logger import logger
async def get_all_sources():
    """Return all ingested sources (contents + feeds) in the entire system."""
    try:
        sources = await get_all_sources_with_details()
        return {"sources": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def show_all_chunks(
    content_id: str = Query(None),
    feed_id: str = Query(None)
):
    try:
        if not content_id and not feed_id:
            raise HTTPException(status_code=400, detail="content_id or feed_id required")
        chunks = await get_chunks_from_database(
            content_id=content_id,
            feed_id=feed_id
        )

        if not chunks:
            return {"chunks": ""}

        contents = [
            chunk.get("page_content") or chunk.get("content") or ""
            for chunk in chunks
        ]
        contents = [str(c).strip() for c in contents if str(c).strip()]

        return {
            "chunks": "\n\n".join(contents),
            "total_chunks": len(contents)
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error retrieving document chunks")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve document chunks"
        )
