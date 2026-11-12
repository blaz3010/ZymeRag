import asyncio
import re
import shutil
import sys
import os
from io import BytesIO
from typing import List, Optional

from DocsIngestion.AudioVideoIngestion import ingestaudio, ingestvideo
from DocsIngestion.PptxIngestion import ingest_pptx
from WebsiteIngestion.websiteingestion import ingest_website
from DocsIngestion.TextIngestion import ingest_raw_text, count_words, RAW_TEXT_MAX_WORDS
lock = asyncio.Lock()
URL_PATTERN = r"(https?://[^\s]+)"
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".pdf", ".docx",
    ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp",
    ".mp4", ".mp3", ".wav", ".m4a",
    ".xlsx", ".xls",
}
from fastapi import File, Form, HTTPException, Query, UploadFile, Depends
from DocsIngestion.PdfIngestion import ingest_pdf
from DocsIngestion.ImageIngestion import ingestimage
from DocsIngestion.CsvIngestion import ingestCsv
idempotent_keys={}
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

async def upload_pdf(file: UploadFile = File(...), name: str = Form(...), idempotent_key: Optional[str] = Form(None)):
    try:
        print("Received request to upload PDF") 
        async with lock:
            if idempotent_key:
                if idempotent_key in idempotent_keys:
                    return {"message": "Duplicate request", "status": "success", "id": idempotent_keys[idempotent_key]}
        if file.content_type not in ["application/pdf"]:
            raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are allowed.")
        idempotent_keys[idempotent_key]=1
        print("Ingesting PDF file...")
        upload_id_pdf=await ingest_pdf(file, name)
        if upload_id_pdf is None:
            idempotent_keys.pop(idempotent_key, None)
            raise HTTPException(status_code=400, detail="Failed to upload PDF")
        return {"message": "PDF uploaded successfully", "status": "success", "id": upload_id_pdf}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def upload_docx(file: UploadFile = File(...), name: str = Form(...), idempotent_key: Optional[str] = Form(None)):
    try:
        async with lock:
            if idempotent_key:
                if idempotent_key in idempotent_keys:
                    return {"message": "Duplicate request", "status": "success", "id": idempotent_keys[idempotent_key]}
        if file.content_type not in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            raise HTTPException(status_code=400, detail="Invalid file type. Only DOCX files are allowed.")
        idempotent_keys[idempotent_key]=1
        file_size_bytes=file.size
        file_size_mb = file_size_bytes / (1024 * 1024)
        if file_size_mb > 10:
            idempotent_keys.pop(idempotent_key, None)
            raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 10MB")
        upload_id_docx=await ingest_pdf(file, name)
        if upload_id_docx is None:
            idempotent_keys.pop(idempotent_key, None)
            raise HTTPException(status_code=400, detail="Failed to upload docx")
        return {"message": "docx uploaded successfully", "status": "success", "id": upload_id_docx}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def upload_image(file: UploadFile = File(...), name: str = Form(...), idempotent_key: Optional[str] = Form(None)):
    try:
        async with lock:
            if idempotent_key:
                if idempotent_key in idempotent_keys:
                    return {"message": "Duplicate request", "status": "success", "id": idempotent_keys[idempotent_key]}
        if file.content_type not in ["image/jpeg","image/png"]:
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG and PNG images are allowed.")
        idempotent_keys[idempotent_key]=1
        file_size_bytes=file.size
        file_size_mb = file_size_bytes / (1024 * 1024)
        if file_size_mb > 10:
            idempotent_keys.pop(idempotent_key, None)
            raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 10MB")
        upload_id_image=await ingestimage(file,name)
        if upload_id_image is None:
            idempotent_keys.pop(idempotent_key, None)
            raise HTTPException(status_code=400, detail="Failed to upload image")
        return {"message": "image uploaded successfully", "status": "success", "id": upload_id_image}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def upload_csv(file: UploadFile = File(...), name: str = Form(...), idempotent_key: Optional[str] = Form(None)):
    try:
        async with lock:
            if idempotent_key:
                if idempotent_key in idempotent_keys:
                    return {"message": "Duplicate request", "status": "success", "id": idempotent_keys[idempotent_key]}
        if file.content_type not in ["text/csv"]:
            raise HTTPException(status_code=400, detail="Invalid file type. Only CSV files are allowed.")
        idempotent_keys[idempotent_key]=1
        file_size_bytes=file.size
        file_size_mb = file_size_bytes / (1024 * 1024)
        if file_size_mb > 10:
            idempotent_keys.pop(idempotent_key, None)
            raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 10MB")
        upload_id_csv=await ingestCsv(file,name)
        if upload_id_csv is None:
            idempotent_keys.pop(idempotent_key, None)
            raise HTTPException(status_code=400, detail="Failed to upload csv")
        return {"message": "csv uploaded successfully", "status": "success", "id": upload_id_csv}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

async def upload_audio(file: UploadFile = File(...), name: str = Form(...), idempotent_key: Optional[str] = Form(None)):
    try:
        async with lock:
            if idempotent_key:
                if idempotent_key in idempotent_keys:
                    return {"message": "Duplicate request", "status": "success", "id": idempotent_keys[idempotent_key]}
        if file.content_type not in ["audio/mpeg","audio/wav","audio/x-wav","audio/x-m4a"]:
            raise HTTPException(status_code=400, detail="Invalid file type. Only MP3, WAV, and M4A audio files are allowed.")
        idempotent_keys[idempotent_key]=1
        file_size_bytes=file.size
        file_size_mb = file_size_bytes / (1024 * 1024)
        if file_size_mb > 10:
            idempotent_keys.pop(idempotent_key, None)
            raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 10MB")
        upload_id_audio=await ingestaudio(file,name)
        if upload_id_audio is None:
            idempotent_keys.pop(idempotent_key, None)
            raise HTTPException(status_code=400, detail="Failed to upload audio")
        return {"message": "audio uploaded successfully", "status": "success", "id": upload_id_audio}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def upload_video(file: UploadFile = File(...), name: str = Form(...), idempotent_key: Optional[str] = Form(None)):
    try:
        async with lock:
            if idempotent_key:
                if idempotent_key in idempotent_keys:
                    return {"message": "Duplicate request", "status": "success", "id": idempotent_keys[idempotent_key]}
        if file.content_type not in ["video/mp4","video/x-m4v","video/quicktime"]:
            raise HTTPException(status_code=400, detail="Invalid file type. Only MP4, M4V, and MOV video files are allowed.")
        idempotent_keys[idempotent_key]=1
        file_size_bytes=file.size
        file_size_mb = file_size_bytes / (1024 * 1024)
        if file_size_mb > 10:
            idempotent_keys.pop(idempotent_key, None)
            raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 10MB")
        upload_id_video=await ingestvideo(file,name)
        if upload_id_video is None:
            idempotent_keys.pop(idempotent_key, None)
            raise HTTPException(status_code=400, detail="Failed to upload video")
        return {"message": "video uploaded successfully", "status": "success", "id": upload_id_video}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def upload_website(url: str = Form(...), idempotent_key: Optional[str] = Form(None)):
    try:
        async with lock:
            if idempotent_key:
                if idempotent_key in idempotent_keys:
                    return {"message": "Duplicate request", "status": "success", "id": idempotent_keys[idempotent_key]}
        if not re.match(URL_PATTERN, url or ""):
            raise HTTPException(status_code=400, detail="Invalid URL. A valid http/https URL is required.")
        idempotent_keys[idempotent_key]=1
        print("Ingesting website...")
        upload_id_website=await ingest_website(url)
        if upload_id_website is None:
            idempotent_keys.pop(idempotent_key, None)
            raise HTTPException(status_code=400, detail="Failed to upload website")
        return {"message": "website uploaded successfully","status": "success" ,"id": upload_id_website}
    except HTTPException:
        raise
    except Exception as e:
        idempotent_keys.pop(idempotent_key, None)
        raise HTTPException(status_code=500, detail=str(e))

async def upload_raw_text(text: str = Form(...), name: str = Form(...), idempotent_key: Optional[str] = Form(None)):
    try:
        print("Received request to upload raw text")
        async with lock:
            if idempotent_key:
                if idempotent_key in idempotent_keys:
                    return {"message": "Duplicate request", "id": idempotent_keys[idempotent_key]}
        text = (text or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Raw text cannot be empty")
        word_count = count_words(text)
        if word_count > RAW_TEXT_MAX_WORDS:
            raise HTTPException(status_code=400, detail=f"Raw text must be {RAW_TEXT_MAX_WORDS} words or fewer (received {word_count})")
        idempotent_keys[idempotent_key]=1
        print("Ingesting raw text...")
        upload_id_raw=await ingest_raw_text(text, name)
        if upload_id_raw is None:
            idempotent_keys.pop(idempotent_key, None)
            raise HTTPException(status_code=400, detail="Failed to upload raw text")
        return {"message": "raw text uploaded successfully", "status": "success", "id": upload_id_raw}
    except HTTPException:
        raise
    except Exception as e:
        idempotent_keys.pop(idempotent_key, None)
        raise HTTPException(status_code=500, detail=str(e))

async def upload_presentation(file: UploadFile = File(...),name: str = Form(...),idempotent_key: Optional[str] = Form(None)):
    try:
        async with lock:
            if idempotent_key and idempotent_key in idempotent_keys:
                return {
                    "message": "Duplicate request",
                    "id": idempotent_keys[idempotent_key]
                }
        if not file.filename.lower().endswith(".pptx"):
            raise HTTPException(
                status_code=400,
                detail="Only PPTX files are supported"
            )
        print("Ingesting presentation...")
        upload_id = await ingest_pptx(file, name)
        if upload_id is None:
            raise HTTPException(status_code=400,detail="Failed to upload presentation")
        if idempotent_key:
            async with lock:
                idempotent_keys[idempotent_key] = upload_id
        return {
            "message": "Presentation uploaded successfully",
            "status": "success",
            "id": upload_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))


async def replace_content(
    content_id: str = Form(...),
    file: UploadFile = File(...),
    name: str = Form(...),
):
    """Replace an existing document/feed with a new file, keeping the same logical source id."""
    from Dbhelper.pdf_db_helper import delete_content_from_database
    from Dbhelper.website_db_helper import delete_website_from_database
    from Dbhelper.document_chunks_db_helper import delete_chunks_from_database

    content_dir = os.path.join("Data", "Content", content_id)
    feed_dir = os.path.join("Data", "Feed", content_id)
    is_feed = os.path.isdir(feed_dir) and not os.path.isdir(content_dir)

    # --- Delete old content (reuse delete logic) ---
    if os.path.isdir(content_dir):
        def _rm(p):
            try:
                shutil.rmtree(p)
            except Exception as e:
                print(f"[replace] rmtree error {p}: {e}")
        await asyncio.to_thread(_rm, content_dir)
        await delete_content_from_database(content_id=content_id)
        await delete_chunks_from_database(content_id=content_id)
    elif os.path.isdir(feed_dir):
        def _rm(p):
            try:
                shutil.rmtree(p)
            except Exception as e:
                print(f"[replace] rmtree error {p}: {e}")
        await asyncio.to_thread(_rm, feed_dir)
        await delete_website_from_database(feed_id=content_id)
        await delete_chunks_from_database(feed_id=content_id)
    else:
        await delete_content_from_database(content_id=content_id)
        await delete_website_from_database(feed_id=content_id)
        await delete_chunks_from_database(content_id=content_id)
        await delete_chunks_from_database(feed_id=content_id)

    # --- Ingest new file (reuse upload ingest logic) ---
    ext = os.path.splitext(file.filename or "")[1].lower()
    ctype = (file.content_type or "").lower()

    try:
        if ext in (".pdf", ".docx") or ctype in ("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
            new_id = await ingest_pdf(file, name)
        elif ext == ".csv" or ctype in ("text/csv", "application/vnd.ms-excel", "text/plain"):
            new_id = await ingestCsv(file, name)
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp") or ctype.startswith("image/"):
            new_id = await ingestimage(file, name)
        elif ext in (".mp3", ".wav", ".m4a", ".mp4") or ctype.startswith("audio/"):
            new_id = await ingestaudio(file, name)
        elif ext in (".mp4", ".m4v", ".mov") or ctype.startswith("video/"):
            new_id = await ingestvideo(file, name)
        elif ext in (".xlsx", ".xls"):
            new_id = await ingestCsv(file, name)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext or ctype}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}")

    if not new_id:
        raise HTTPException(status_code=500, detail="Failed to ingest replacement file")

    return {
        "status": "success",
        "message": "Content replaced successfully",
        "old_id": content_id,
        "new_id": new_id,
        "name": name,
    }