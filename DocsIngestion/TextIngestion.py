import asyncio
import uuid

from langchain_core.documents import Document

from Dbhelper.document_chunks_db_helper import (
    save_chunks_to_database,
    delete_chunks_from_database,
)
from Dbhelper.pdf_db_helper import save_content_to_database
from Embeddings.Embeddingmaker import embedder as embedding_maker
from Splitter.PdfSplitter import pdf_splitter

SPLIT_THRESHOLD_CHARS = 300
RAW_TEXT_MAX_WORDS = 200
text_semaphore = asyncio.Semaphore(5)

def count_words(text: str) -> int:
    return len(text.split())


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


async def _ingest_chunks(chunks, name: str, label: str):
    content_id = str(uuid.uuid4())
    chunks_save_started = False

    try:
        database_saved = await save_content_to_database(
            name=name,
            content_id=content_id,
            doc_type="txt",
            chunks=len(chunks),
        )
        if not database_saved:
            raise RuntimeError(
                f"Failed to save content record for {content_id}; "
                "chunks were not inserted"
            )

        # Set before starting because some batches may be inserted before a
        # later batch fails.
        chunks_save_started = True
        await build_and_save_index(
            chunks,
            content_id=content_id,
            feed_id=None,
        )

        print(f"{label} ingested and saved to database with ID: {content_id}")
        return content_id

    except Exception as e:
        print(f"Error occurred while ingesting {label} '{name}': {e}")

        if chunks_save_started:
            try:
                await delete_chunks_from_database(content_id=content_id)
            except Exception as cleanup_error:
                print(f"Cleanup failed for {content_id}: {cleanup_error}")

        return None


async def ingestText(text: str, name: str):
    try:
        async with text_semaphore:
            text = (text or "").strip()
            if not text:
                print("Empty text provided, nothing to ingest")
                return None

        if len(text) > SPLIT_THRESHOLD_CHARS:
            chunks = await asyncio.to_thread(pdf_splitter.split, text)
        else:
            chunks = [Document(page_content=text)]

        if not chunks:
            print(f"Splitter produced no chunks for text '{name}'")
            return None

        return await _ingest_chunks(chunks, name, "Text")

    except Exception as e:
        print(f"Error occurred while preparing text '{name}': {e}")
        return None


async def ingest_raw_text(text: str, name: str):
    try:
        text = (text or "").strip()
        if not text:
            print("Empty raw text provided, nothing to ingest")
            return None

        if count_words(text) > RAW_TEXT_MAX_WORDS:
            print(f"Raw text exceeds {RAW_TEXT_MAX_WORDS} words, rejected")
            return None

        chunks = [Document(page_content=text)]
        return await _ingest_chunks(chunks, name, "Raw text")

    except Exception as e:
        print(f"Error occurred while preparing raw text '{name}': {e}")
        return None