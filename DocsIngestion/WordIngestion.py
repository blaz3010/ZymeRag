import asyncio
import io
from docx import Document
docx_semaphore = asyncio.Semaphore(5)
def extract_docx_sync(file_bytes):
    doc = Document(io.BytesIO(file_bytes))
    content = []

    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            content.append(paragraph.text)

    for table in doc.tables:
        for row in table.rows:
            content.append(" | ".join(
                cell.text.strip() for cell in row.cells
            ))

    return "\n".join(content)

async def extract_docx(file):
    file_bytes = await file.read()
    async with docx_semaphore:
        return await asyncio.to_thread(extract_docx_sync, file_bytes)