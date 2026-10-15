from fastapi import Depends, HTTPException
from Backend.Middleware.auth import auth_middleware
from Dbhelper.user_mapping_db_helper import (
    get_user_sources_with_details,
    get_all_sources_with_details,
)


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

