import asyncio
import uuid
from io import BytesIO

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


torch._dynamo.config.suppress_errors = True

print("PyTorch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("CUDA:", torch.version.cuda)

try:
    from docling.document_converter import DocumentConverter, DocumentStream

    converter = DocumentConverter()
except Exception as e:
    print(f"Docling unavailable, using PyMuPDF only: {e}")
    converter = None


def _convert_pdf_sync_fitz(file_bytes: bytes) -> str:
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def _convert_pdf_sync(pdf_bytes: bytes, filename: str) -> str:
    if converter is not None:
        try:
            source = DocumentStream(name=filename, stream=BytesIO(pdf_bytes))
            result = converter.convert(source)
            markdown = result.document.export_to_markdown()
            if markdown and markdown.strip():
                return markdown
            print(f"Docling returned no text for {filename}, falling back to PyMuPDF")
        except Exception as e:
            print(f"Docling failed for {filename} ({e}), falling back to PyMuPDF")

    return _convert_pdf_sync_fitz(pdf_bytes)


async def read_text_from_pdf(file) -> str:
    print(f"Reading PDF file: {file.filename}")
    pdf_bytes = await file.read()
    result = await asyncio.to_thread(_convert_pdf_sync_fitz, pdf_bytes)
    if result and result.strip():
        return result
    return await asyncio.to_thread(_convert_pdf_sync, pdf_bytes, file.filename)


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


async def ingest_pdf(file, name: str):
    content_id = str(uuid.uuid4())
    chunks_save_started = False

    try:
        markdown = await read_text_from_pdf(file)
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

        # Mark before starting: the database helper may insert some batches
        # before a later batch fails.
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


async def delete_content(id: str) -> bool:
    try:
        deleted = await delete_chunks_from_database(content_id=id)
        if deleted:
            print(f"PDF with ID: {id} deleted successfully.")
            return True

        print(f"PDF with ID: {id} does not exist.")
        return False

    except Exception as e:
        print(f"Error occurred while deleting PDF: {e}")
        return False