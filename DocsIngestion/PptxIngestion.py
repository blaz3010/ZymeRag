import asyncio
import uuid
from io import BytesIO
from pptx import Presentation
import pymupdf
import torch
import torch._dynamo

from Dbhelper.document_chunks_db_helper import (
    save_chunks_to_database,
    delete_chunks_from_database,
)
from Dbhelper.pdf_db_helper import save_content_to_database
from Splitter.PdfSplitter import pdf_splitter
from Embeddings.Embeddingmaker import embedder as embedding_maker

pptx_semaphore=asyncio.Semaphore(2)
def extract_text_from_pptx(file_bytes):
    presentation = Presentation(BytesIO(file_bytes))
    text_content = []
    for slide in presentation.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text_content.append(shape.text)
    return "\n".join(text_content)

async def build_and_save_index(chunks, content_id=None, feed_id=None) -> bool:
    documents = [chunk.page_content for chunk in chunks]
    embeddings = await asyncio.to_thread(
        embedding_maker.embed_documents, documents
    )

    success = await save_chunks_to_database(
        chunks=chunks,
        embeddings=embeddings,
        content_id=content_id,
        feed_id=feed_id,
    )
    if not success:
        raise RuntimeError("Failed to save document embeddings")

    return True

async def ingest_pptx(file, name: str):
    content_id = str(uuid.uuid4())
    chunks_save_started = False

    try:
        async with pptx_semaphore:
            file_bytes = await file.read()
            markdown = await asyncio.to_thread(extract_text_from_pptx, file_bytes)
        if not markdown or not markdown.strip():
            print(f"No extractable text in {file.filename} (scanned PDF? try OCR)")
            return None

        chunks = await asyncio.to_thread(pdf_splitter.split, markdown)
        if not chunks:
            print(f"Splitter produced no chunks for {file.filename}")
            return None

        database_saved = await save_content_to_database(
            name=name,
            content_id=content_id,
            doc_type="pdf",
            chunks=len(chunks),
        )
        if not database_saved:
            raise RuntimeError(
                f"Failed to save content record for {content_id}; "
                "chunks were not inserted"
            )
        chunks_save_started = True
        await build_and_save_index(
            chunks,
            content_id=content_id,
            feed_id=None,
        )

        print(f"PDF index built for: {file.filename}")
        print(f"Database save status for PDF: {file.filename} - {database_saved}")
        print(f"PDF ingested and saved to database with ID: {content_id}")
        return content_id

    except Exception as e:
        print(f"Error occurred while ingesting PDF: {e}")

        if chunks_save_started:
            try:
                await delete_chunks_from_database(content_id=content_id)
            except Exception as cleanup_error:
                print(f"Cleanup failed for {content_id}: {cleanup_error}")

        return None