import uuid

import structlog
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Chunk, Document
from app.services.chunker import chunk_text, count_tokens
from app.services.embeddings import generate_embeddings
from app.services.vector_store import ensure_collection, upsert_vectors

logger = structlog.get_logger()


def extract_text_from_pdf(file_bytes: bytes) -> list[tuple[int, str]]:
    """Extract text per page from PDF. Returns list of (page_number, text)."""
    from io import BytesIO

    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((i, text))
    return pages


async def ingest_document(
    db: AsyncSession,
    document: Document,
    file_bytes: bytes,
) -> None:
    """Process a document: extract text, chunk, embed, store vectors."""
    try:
        document.status = "processing"
        await db.flush()

        # 1. Extract text
        if document.content_type == "application/pdf":
            pages = extract_text_from_pdf(file_bytes)
        else:
            # Plain text
            text = file_bytes.decode("utf-8", errors="replace")
            pages = [(1, text)]

        document.page_count = len(pages)

        # 2. Chunk each page
        all_chunks: list[tuple[int | None, str]] = []
        for page_num, page_text in pages:
            for chunk in chunk_text(page_text):
                all_chunks.append((page_num, chunk))

        if not all_chunks:
            document.status = "error"
            document.error_message = "No text content found in document"
            return

        # 3. Create chunk records
        chunk_records = []
        for idx, (page_num, content) in enumerate(all_chunks):
            chunk = Chunk(
                id=uuid.uuid4(),
                document_id=document.id,
                content=content,
                page_number=page_num,
                chunk_index=idx,
                token_count=count_tokens(content),
            )
            db.add(chunk)
            chunk_records.append(chunk)

        document.chunk_count = len(chunk_records)
        await db.flush()

        # 4. Generate embeddings in batches
        await ensure_collection()

        batch_size = 100
        for i in range(0, len(chunk_records), batch_size):
            batch = chunk_records[i : i + batch_size]
            texts = [c.content for c in batch]
            embeddings = await generate_embeddings(texts)

            chunk_ids = [c.id for c in batch]
            payloads = [
                {
                    "document_id": str(document.id),
                    "document_name": document.filename,
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                    "content": c.content,
                }
                for c in batch
            ]

            await upsert_vectors(chunk_ids, embeddings, payloads)

        document.status = "ready"
        logger.info(
            "document_ingested",
            document_id=str(document.id),
            chunks=len(chunk_records),
            pages=document.page_count,
        )

    except Exception as e:
        document.status = "error"
        document.error_message = str(e)
        logger.error("ingest_failed", document_id=str(document.id), error=str(e))
        raise
