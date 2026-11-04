import uuid
from unittest.mock import AsyncMock

import pytest
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.api import documents
from tests.pdf_factory import build_pdf


@pytest.fixture
def ingestion_stubs(vector_store_stub, embeddings_stub):
    return vector_store_stub


async def upload_text(client, content: bytes = b"Hello retrieval world.", name: str = "a.txt"):
    return await client.post("/api/v1/documents/", files={"file": (name, content, "text/plain")})


async def test_health_endpoint(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "docuquery"}


async def test_upload_text_document_returns_ready_document(client, ingestion_stubs):
    response = await upload_text(client)

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "a.txt"
    assert body["content_type"] == "text/plain"
    assert body["status"] == "ready"
    assert body["chunk_count"] == 1
    assert body["page_count"] == 1
    assert body["error_message"] is None


async def test_upload_pdf_document(client, ingestion_stubs):
    response = await client.post(
        "/api/v1/documents/",
        files={"file": ("r.pdf", build_pdf(["Page one", "Page two"]), "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["page_count"] == 2


async def test_upload_rejects_unsupported_content_type(client, ingestion_stubs):
    response = await client.post(
        "/api/v1/documents/", files={"file": ("a.png", b"\x89PNG", "image/png")}
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
    ingestion_stubs["upsert_vectors"].assert_not_awaited()


async def test_upload_rejects_oversized_file(client, ingestion_stubs, monkeypatch):
    monkeypatch.setattr(documents, "MAX_FILE_SIZE", 10)

    response = await upload_text(client, b"x" * 11)

    assert response.status_code == 400
    assert response.json()["detail"] == "File too large. Max 20MB."


async def test_upload_accepts_file_at_size_limit(client, ingestion_stubs, monkeypatch):
    monkeypatch.setattr(documents, "MAX_FILE_SIZE", 10)

    response = await upload_text(client, b"x" * 10)

    assert response.status_code == 201


async def test_upload_without_file_returns_validation_error(client, ingestion_stubs):
    response = await client.post("/api/v1/documents/")

    assert response.status_code == 422


async def test_upload_empty_text_is_stored_with_error_status(client, ingestion_stubs):
    response = await upload_text(client, b"   ")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "error"
    assert body["error_message"] == "No text content found in document"


async def test_upload_returns_server_error_when_embedding_fails(
    client, vector_store_stub, monkeypatch
):
    monkeypatch.setattr(
        "app.services.ingest.generate_embeddings", AsyncMock(side_effect=RuntimeError("boom"))
    )

    response = await upload_text(client)

    assert response.status_code == 500


async def test_list_documents_returns_total_and_newest_first(client, ingestion_stubs):
    await upload_text(client, name="first.txt")
    await upload_text(client, name="second.txt")

    response = await client.get("/api/v1/documents/")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["filename"] for item in body["items"]} == {"first.txt", "second.txt"}


async def test_list_documents_empty(client, ingestion_stubs):
    response = await client.get("/api/v1/documents/")

    assert response.json() == {"items": [], "total": 0}


async def test_get_document_returns_document(client, ingestion_stubs):
    created = (await upload_text(client)).json()

    response = await client.get(f"/api/v1/documents/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_document_unknown_id_returns_404(client, ingestion_stubs):
    response = await client.get(f"/api/v1/documents/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


async def test_get_document_invalid_id_returns_422(client, ingestion_stubs):
    response = await client.get("/api/v1/documents/not-a-uuid")

    assert response.status_code == 422


async def test_delete_document_removes_vectors_and_record(client, ingestion_stubs):
    created = (await upload_text(client)).json()

    response = await client.delete(f"/api/v1/documents/{created['id']}")

    assert response.status_code == 204
    ingestion_stubs["delete_document_vectors"].assert_awaited_once_with(created["id"])
    assert (await client.get(f"/api/v1/documents/{created['id']}")).status_code == 404


async def test_delete_document_unknown_id_returns_404_without_vector_call(client, ingestion_stubs):
    response = await client.delete(f"/api/v1/documents/{uuid.uuid4()}")

    assert response.status_code == 404
    ingestion_stubs["delete_document_vectors"].assert_not_awaited()


async def test_upload_truncates_overlong_filename(client, ingestion_stubs):
    response = await upload_text(client, name="n" * 600 + ".txt")

    assert response.status_code == 201
    assert len(response.json()["filename"]) == documents.MAX_FILENAME_LENGTH


async def test_upload_reads_at_most_one_byte_over_limit(client, ingestion_stubs, monkeypatch):
    monkeypatch.setattr(documents, "MAX_FILE_SIZE", 10)
    read_sizes = []
    original_read = StarletteUploadFile.read

    async def recording_read(self, size=-1):
        read_sizes.append(size)
        return await original_read(self, size)

    monkeypatch.setattr(StarletteUploadFile, "read", recording_read)

    await upload_text(client, b"x" * 50)

    assert read_sizes == [11]
