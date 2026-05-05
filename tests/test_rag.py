from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import rag


@pytest.mark.asyncio
async def test_query_documents_builds_context_and_returns_sources():
    fake_results = [
        {
            "chunk_id": "c1",
            "score": 0.91,
            "content": "Pgvector is a PostgreSQL extension.",
            "document_id": "d1",
            "document_name": "vector-stores.pdf",
            "page_number": 3,
        },
        {
            "chunk_id": "c2",
            "score": 0.84,
            "content": "Qdrant is a dedicated vector database.",
            "document_id": "d1",
            "document_name": "vector-stores.pdf",
            "page_number": 4,
        },
    ]

    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(content="Both work; Qdrant scales independently."))]
    fake_completion.usage = MagicMock(prompt_tokens=120, completion_tokens=18)

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_completion)

    with (
        patch.object(rag, "generate_embedding", AsyncMock(return_value=[0.0] * 1536)),
        patch.object(rag, "search_similar", AsyncMock(return_value=fake_results)),
        patch.object(rag, "get_openai_client", return_value=fake_client),
    ):
        result = await rag.query_documents("What is the difference between Qdrant and pgvector?")

    assert result["answer"] == "Both work; Qdrant scales independently."
    assert len(result["sources"]) == 2
    assert result["sources"][0]["document_name"] == "vector-stores.pdf"
    assert result["sources"][0]["page_number"] == 3
    assert result["prompt_tokens"] == 120
    assert result["completion_tokens"] == 18
    assert result["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_query_documents_handles_empty_retrieval():
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(content="The context does not contain that information."))]
    fake_completion.usage = MagicMock(prompt_tokens=40, completion_tokens=10)

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_completion)

    with (
        patch.object(rag, "generate_embedding", AsyncMock(return_value=[0.0] * 1536)),
        patch.object(rag, "search_similar", AsyncMock(return_value=[])),
        patch.object(rag, "get_openai_client", return_value=fake_client),
    ):
        result = await rag.query_documents("Anything?")

    assert result["sources"] == []
    assert "context" in result["answer"].lower() or "information" in result["answer"].lower()
