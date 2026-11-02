from fastapi import Depends, Query, HTTPException
from Backend.Middleware.auth import auth_middleware
from Dbhelper.user_mapping_db_helper import (
    get_user_sources_with_details,
    get_all_sources_with_details,
)
from Dbhelper.document_chunks_db_helper import get_chunks_from_database
from Backend.Utils.Logger import logger
async def get_my_sources(user_id: str = Depends(auth_middleware)):
    """Return all ingested sources (contents + feeds) mapped to the authenticated user."""
    try:
        sources = await get_user_sources_with_details(user_id)
        return {"sources": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_all_sources(user_id: str = Depends(auth_middleware)):
    """Return all ingested sources (contents + feeds) in the entire system."""
    try:
        sources = await get_all_sources_with_details(current_user_id=user_id)
        return {"sources": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def show_all_chunks(
    content_id: str = Query(...),
    feed_id: str = Query(None)
):
    try:
        chunks = await get_chunks_from_database(
            content_id=content_id,
            feed_id=feed_id
        )

        if not chunks:
            return {"chunks": ""}

        contents = [
            chunk["page_content"]
            for chunk in chunks
            if chunk.get("page_content") and chunk["page_content"].strip()
        ]

        return {
            "chunks": "\n\n".join(contents),
            "total_chunks": len(contents)
        }

    except Exception:
        logger.exception("Error retrieving document chunks")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve document chunks"
        )
