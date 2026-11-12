import asyncio
import re
import shutil
import sys
import os
from io import BytesIO
from typing import List, Optional

from fastapi import Form, HTTPException

from Dbhelper.document_chunks_db_helper import delete_chunks_from_database, delete_source_row_by_id
from Dbhelper.website_db_helper import delete_website_from_database
from Dbhelper.pdf_db_helper import delete_content_from_database


async def delete_id(id: str = Form(...)):
    try:
        result = await asyncio.gather(
            delete_chunks_from_database(content_id=id),
            delete_chunks_from_database(feed_id=id),
            delete_source_row_by_id(id),
        )
        if any(result):
            return {"status": "success", "message": "Content and database records successfully removed."}
        else:
            raise HTTPException(status_code=404, detail="Content not found in the database.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))