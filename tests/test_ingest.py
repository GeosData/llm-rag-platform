import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Chunk, Document
from app.services import ingest
from tests.pdf_factory import build_pdf


async def create_document(
    db: AsyncSession, content_type: str = "text/plain", filename: str = "notes.txt"
) -> Document:
    document = Document(id=uuid.uuid4(), filename=filename, content_type=content_type)
    db.add(document)
    await db.flush()
    return document


async def stored_chunks(db: AsyncSession, document: Document) -> list[Chunk]:
    from sqlalchemy import select

    result = await db.execute(
        select(Chunk).where(Chunk.document_id == document.id).order_by(Chunk.chunk_index)
    )
    return list(result.scalars().all())


def test_extract_text_from_pdf_returns_numbered_pages():
    pages = ingest.extract_text_from_pdf(build_pdf(["First page text", "Second page text"]))

    assert [number for number, _ in pages] == [1, 2]
    assert "First page text" in pages[0][1]
    assert "Second page text" in pages[1][1]


def test_extract_text_from_pdf_skips_blank_pages():
    pages = ingest.extract_text_from_pdf(build_pdf(["Only content", " "]))

    assert [number for number, _ in pages] == [1]


def test_extract_text_from_pdf_rejects_invalid_bytes():
    with pytest.raises(Exception):  # noqa: B017
        ingest.extract_text_from_pdf(b"this is not a pdf")


async def test_ingest_plain_text_stores_chunks_and_vectors(
    db_session, vector_store_stub, embeddings_stub
):
    document = await create_document(db_session)

    await ingest.ingest_document(db_session, document, b"Alpha beta gamma delta.")

    assert document.status == "ready"
    assert document.page_count == 1
    assert document.chunk_count == 1
    chunks = await stored_chunks(db_session, document)
    assert len(chunks) == 1
    assert chunks[0].content == "Alpha beta gamma delta."
    assert chunks[0].page_number == 1
    assert chunks[0].token_count > 0
    vector_store_stub["ensure_collection"].assert_awaited_once()
    vector_store_stub["upsert_vectors"].assert_awaited_once()
    chunk_ids, embeddings, payloads = vector_store_stub["upsert_vectors"].await_args.args
    assert chunk_ids == [chunks[0].id]
    assert len(embeddings) == 1
    assert payloads[0]["document_id"] == str(document.id)
    assert payloads[0]["document_name"] == "notes.txt"
    assert payloads[0]["page_number"] == 1
    assert payloads[0]["content"] == "Alpha beta gamma delta."


async def test_ingest_pdf_keeps_page_numbers(db_session, vector_store_stub, embeddings_stub):
    document = await create_document(db_session, "application/pdf", "report.pdf")

    await ingest.ingest_document(db_session, document, build_pdf(["Revenue grew", "Costs shrank"]))

    assert document.status == "ready"
    assert document.page_count == 2
    chunks = await stored_chunks(db_session, document)
    assert [chunk.page_number for chunk in chunks] == [1, 2]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1]


async def test_ingest_batches_embedding_requests(
    db_session, vector_store_stub, embeddings_stub, monkeypatch
):
    monkeypatch.setattr(ingest, "chunk_text", lambda text: [f"chunk {i}" for i in range(250)])
    document = await create_document(db_session)

    await ingest.ingest_document(db_session, document, b"anything")

    assert document.chunk_count == 250
    assert embeddings_stub.await_count == 3
    batch_sizes = [len(call.args[0]) for call in embeddings_stub.await_args_list]
    assert batch_sizes == [100, 100, 50]
    assert vector_store_stub["upsert_vectors"].await_count == 3


async def test_ingest_empty_text_marks_error_without_touching_vector_store(
    db_session, vector_store_stub, embeddings_stub
):
    document = await create_document(db_session)

    await ingest.ingest_document(db_session, document, b"   \n  ")

    assert document.status == "error"
    assert document.error_message == "No text content found in document"
    assert await stored_chunks(db_session, document) == []
    embeddings_stub.assert_not_awaited()
    vector_store_stub["upsert_vectors"].assert_not_awaited()


async def test_ingest_decodes_invalid_utf8_with_replacement(
    db_session, vector_store_stub, embeddings_stub
):
    document = await create_document(db_session)

    await ingest.ingest_document(db_session, document, b"valid \xff\xfe text")

    assert document.status == "ready"
    chunks = await stored_chunks(db_session, document)
    assert "valid" in chunks[0].content
    assert "�" in chunks[0].content


async def test_ingest_embedding_failure_sets_error_and_reraises(
    db_session, vector_store_stub, monkeypatch
):
    monkeypatch.setattr(
        ingest, "generate_embeddings", AsyncMock(side_effect=RuntimeError("embedding backend down"))
    )
    document = await create_document(db_session)

    with pytest.raises(RuntimeError, match="embedding backend down"):
        await ingest.ingest_document(db_session, document, b"some text")

    assert document.status == "error"
    assert document.error_message == "embedding backend down"
    vector_store_stub["upsert_vectors"].assert_not_awaited()


async def test_ingest_vector_store_failure_sets_error_and_reraises(
    db_session, vector_store_stub, embeddings_stub
):
    vector_store_stub["upsert_vectors"].side_effect = ConnectionError("qdrant unreachable")
    document = await create_document(db_session)

    with pytest.raises(ConnectionError):
        await ingest.ingest_document(db_session, document, b"some text")

    assert document.status == "error"
    assert document.error_message == "qdrant unreachable"


async def test_ingest_corrupt_pdf_sets_error_and_reraises(
    db_session, vector_store_stub, embeddings_stub
):
    document = await create_document(db_session, "application/pdf", "broken.pdf")

    with pytest.raises(Exception):  # noqa: B017
        await ingest.ingest_document(db_session, document, b"not a pdf")

    assert document.status == "error"
    assert document.error_message
