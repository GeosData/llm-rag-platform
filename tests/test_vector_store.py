import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import settings
from app.services import embeddings, vector_store


@pytest.fixture
def qdrant_stub(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    stub = MagicMock()
    stub.get_collections = AsyncMock()
    stub.create_collection = AsyncMock()
    stub.upsert = AsyncMock()
    stub.query_points = AsyncMock()
    stub.delete = AsyncMock()
    monkeypatch.setattr(vector_store, "get_qdrant_client", lambda: stub)
    return stub


async def test_ensure_collection_creates_missing_collection(qdrant_stub):
    qdrant_stub.get_collections.return_value = SimpleNamespace(collections=[])

    await vector_store.ensure_collection()

    qdrant_stub.create_collection.assert_awaited_once()
    arguments = qdrant_stub.create_collection.await_args.kwargs
    assert arguments["collection_name"] == settings.qdrant_collection
    assert arguments["vectors_config"].size == 1536
    assert arguments["vectors_config"].distance.name == "COSINE"


async def test_ensure_collection_skips_existing_collection(qdrant_stub):
    existing = SimpleNamespace(name=settings.qdrant_collection)
    qdrant_stub.get_collections.return_value = SimpleNamespace(collections=[existing])

    await vector_store.ensure_collection()

    qdrant_stub.create_collection.assert_not_awaited()


async def test_upsert_vectors_builds_points(qdrant_stub):
    chunk_id = uuid.uuid4()

    await vector_store.upsert_vectors([chunk_id], [[0.1, 0.2]], [{"content": "text"}])

    points = qdrant_stub.upsert.await_args.kwargs["points"]
    assert len(points) == 1
    assert points[0].id == str(chunk_id)
    assert points[0].vector == [0.1, 0.2]
    assert points[0].payload == {"content": "text"}


async def test_upsert_vectors_rejects_mismatched_lengths(qdrant_stub):
    with pytest.raises(ValueError):
        await vector_store.upsert_vectors([uuid.uuid4()], [[0.1], [0.2]], [{}])

    qdrant_stub.upsert.assert_not_awaited()


async def test_search_similar_flattens_payload_and_score(qdrant_stub):
    point = SimpleNamespace(id="chunk-1", score=0.8, payload={"content": "hello", "page_number": 2})
    qdrant_stub.query_points.return_value = SimpleNamespace(points=[point])

    results = await vector_store.search_similar([0.1, 0.2], top_k=3)

    assert results == [{"chunk_id": "chunk-1", "score": 0.8, "content": "hello", "page_number": 2}]
    assert qdrant_stub.query_points.await_args.kwargs["limit"] == 3


async def test_search_similar_returns_empty_list_without_matches(qdrant_stub):
    qdrant_stub.query_points.return_value = SimpleNamespace(points=[])

    assert await vector_store.search_similar([0.1]) == []


async def test_delete_document_vectors_filters_by_document_id(qdrant_stub):
    await vector_store.delete_document_vectors("doc-123")

    selector = qdrant_stub.delete.await_args.kwargs["points_selector"]
    condition = selector.must[0]
    assert condition.key == "document_id"
    assert condition.match.value == "doc-123"


def test_get_qdrant_client_is_cached(monkeypatch):
    monkeypatch.setattr(vector_store, "_client", None)
    monkeypatch.setattr(vector_store, "AsyncQdrantClient", lambda url: object())

    first = vector_store.get_qdrant_client()
    second = vector_store.get_qdrant_client()

    assert first is second


def test_get_openai_client_is_cached(monkeypatch):
    monkeypatch.setattr(embeddings, "_client", None)

    first = embeddings.get_openai_client()
    second = embeddings.get_openai_client()

    assert first is second


async def test_generate_embeddings_returns_vectors_in_order(monkeypatch):
    response = SimpleNamespace(
        data=[SimpleNamespace(embedding=[1.0]), SimpleNamespace(embedding=[2.0])]
    )
    client = MagicMock()
    client.embeddings.create = AsyncMock(return_value=response)
    monkeypatch.setattr(embeddings, "get_openai_client", lambda: client)

    result = await embeddings.generate_embeddings(["a", "b"])

    assert result == [[1.0], [2.0]]
    assert client.embeddings.create.await_args.kwargs["input"] == ["a", "b"]
    assert client.embeddings.create.await_args.kwargs["model"] == settings.embedding_model


async def test_generate_embedding_returns_single_vector(monkeypatch):
    monkeypatch.setattr(embeddings, "generate_embeddings", AsyncMock(return_value=[[0.5, 0.5]]))

    assert await embeddings.generate_embedding("text") == [0.5, 0.5]
