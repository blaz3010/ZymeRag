import asyncio
import re
import shutil
import sys
import os
from io import BytesIO
from typing import List, Optional

from fastapi import Form, HTTPException

from Dbhelper.document_chunks_db_helper import delete_chunks_from_database
from Dbhelper.website_db_helper import delete_website_from_database
from Dbhelper.pdf_db_helper import delete_content_from_database


async def delete_id(id: str = Form(...)):
    try:
        result=await delete_chunks_from_database(id)
        if result:
            return {"status": "success", "message": "Content and database records successfully removed."}
        else:
            raise HTTPException(status_code=404, detail="Content not found in the database.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))