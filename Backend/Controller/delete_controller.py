import asyncio
import re
import shutil
import sys
import os
from io import BytesIO
from typing import List, Optional

from fastapi import Form, HTTPException

from Dbhelper.website_db_helper import delete_website_from_database
from Dbhelper.pdf_db_helper import delete_content_from_database

def background_delete_content(path:str):
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
    except Exception as e:
        print(f"Error occurred while deleting content: {e}")
async def delete_id(id: str = Form(...)):
    try:
        content_dir = os.path.join("Data", "Content", id)
        feed_dir = os.path.join("Data", "Feed", id)

        if os.path.exists(content_dir):
            await asyncio.to_thread(background_delete_content, content_dir)
            await delete_content_from_database(content_id=id)
        elif os.path.exists(feed_dir):
            await asyncio.to_thread(background_delete_content, feed_dir)
            await delete_website_from_database(feed_id=id)
        else:
            # If filesystem directory does not exist, clean up from database tables
            await delete_content_from_database(content_id=id)
            await delete_website_from_database(feed_id=id)

        return {"status": "success", "message": "Content and database records successfully removed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))