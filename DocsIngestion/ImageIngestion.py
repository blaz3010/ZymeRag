import asyncio
import uuid
from io import BytesIO

import numpy as np
from PIL import Image

from Dbhelper.document_chunks_db_helper import (
    save_chunks_to_database,
    delete_chunks_from_database,
)
from Dbhelper.pdf_db_helper import save_content_to_database
from Embeddings.Embeddingmaker import embedder as embedding_maker
from Splitter.PdfSplitter import pdf_splitter

_ocr_engine = None
image_semaphore = asyncio.Semaphore(2)

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            import torch
            from paddleocr import PaddleOCR

            device = "gpu" if torch.cuda.is_available() else "cpu"
            _ocr_engine = PaddleOCR(
                lang="en",
                use_doc_orientation_classify=False,
                use_doc_unwarping=True,
                use_textline_orientation=False,
                device=device,
            )
        except Exception as e:
            print(f"PaddleOCR unavailable, falling back to pytesseract: {e}")
            _ocr_engine = False
    return _ocr_engine


def ocr_doing(image_bytes: bytes) -> str:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    engine = get_ocr_engine()
    if not engine:
        import pytesseract

        return pytesseract.image_to_string(image)

    result = engine.predict(np.array(image))
    texts = []
    for res in result:
        texts.extend(res.json["res"]["rec_texts"])
    return "\n".join(texts)


async def read_text_from_image(file) -> str:
    image_bytes = await file.read()
    return await asyncio.to_thread(ocr_doing, image_bytes)


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


async def ingestimage(file, name: str):
    content_id = str(uuid.uuid4())
    chunks_save_started = False

    try:
        async with image_semaphore:
            text = await read_text_from_image(file)
        if not text or not text.strip():
            print(f"No text detected in image {name}")
            return None

        chunks = await asyncio.to_thread(pdf_splitter.split, text)
        if not chunks:
            print(f"Splitter produced no chunks for image {name}")
            return None

        database_saved = await save_content_to_database(
            name=name,
            content_id=content_id,
            doc_type="image",
            chunks=len(chunks),
        )
        if not database_saved:
            raise RuntimeError(
                f"Failed to save content record for {content_id}; "
                "chunks were not inserted"
            )

        # Set before starting because a later batch may fail after earlier
        # batches have already been inserted.
        chunks_save_started = True
        await build_and_save_index(
            chunks,
            content_id=content_id,
            feed_id=None,
        )

        print(f"Image ingested and saved to database with ID: {content_id}")
        return content_id

    except Exception as e:
        print(f"Error occurred while processing image {name}: {e}")

        if chunks_save_started:
            try:
                await delete_chunks_from_database(content_id=content_id)
            except Exception as cleanup_error:
                print(f"Cleanup failed for {content_id}: {cleanup_error}")

        return None