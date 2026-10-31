import asyncio
import json
import uuid
from io import BytesIO

import pandas as pd
from langchain_core.documents import Document

from Dbhelper.document_chunks_db_helper import save_chunks_to_database, delete_chunks_from_database
from Dbhelper.pdf_db_helper import save_content_to_database
from Embeddings.Embeddingmaker import embedder as embedding_maker


def _read_csv(csv_bytes: bytes) -> pd.DataFrame:
    try:
        return pd.read_csv(BytesIO(csv_bytes), encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(BytesIO(csv_bytes), encoding="latin-1")


def _csv_to_documents_sync(csv_bytes: bytes) -> list[Document]:
    df = _read_csv(csv_bytes)
    df = df.dropna(how="all")
    if df.empty:
        return []
    records = json.loads(df.to_json(orient="records", date_format="iso"))
    documents = []
    for record in records:
        lines = [f"{col}: {value}" for col, value in record.items() if value is not None]
        if not lines:
            continue
        documents.append(Document(page_content="\n".join(lines), metadata=record))
    return documents


async def build_and_save_index(chunks, content_id=None, feed_id=None) -> bool:
    documents = [chunk.page_content for chunk in chunks]
    embeddings = await asyncio.to_thread(embedding_maker.embed_documents, documents)
    success = await save_chunks_to_database(
        chunks=chunks,
        embeddings=embeddings,
        content_id=content_id,
        feed_id=feed_id,
    )
    if not success:
        raise RuntimeError("Failed to save document embeddings")
    return True


async def ingestCsv(file, name: str):
    content_id = str(uuid.uuid4())
    chunks_saved = False
    try:
        csv_bytes = await file.read()
        chunks = await asyncio.to_thread(_csv_to_documents_sync, csv_bytes)
        if not chunks:
            print(f"CSV '{name}' has no usable rows")
            return None

        await build_and_save_index(chunks, content_id=content_id, feed_id=None)
        chunks_saved = True
        database_saved = await save_content_to_database(
            name=name, content_id=content_id, doc_type="csv", chunks=len(chunks)
        )
        if database_saved:
            print(f"CSV ingested and saved to database with ID: {content_id}")
            return content_id
        await delete_chunks_from_database(content_id=content_id)
        return None

    except Exception as e:
        print(f"Error occurred while ingesting CSV '{name}': {e}")
        if chunks_saved:
            try:
                await delete_chunks_from_database(content_id=content_id)
            except Exception as cleanup_error:
                print(f"Cleanup failed for {content_id}: {cleanup_error}")
        return None