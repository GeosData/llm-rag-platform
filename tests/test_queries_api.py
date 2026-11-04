from unittest.mock import AsyncMock

import pytest

from app.models.document import Document

RAG_RESULT = {
    "answer": "Qdrant is a vector database.",
    "sources": [
        {
            "content": "Qdrant is a dedicated vector database.",
            "document_id": "6f1c1a44-8d58-4f6e-9a54-3b7a7a1c2e11",
            "document_name": "stores.pdf",
            "page_number": 4,
            "score": 0.9,
        }
    ],
    "model": "gpt-4o-mini",
    "prompt_tokens": 100,
    "completion_tokens": 12,
    "latency_ms": 42.5,
}


@pytest.fixture
def rag_stub(monkeypatch):
    stub = AsyncMock(return_value=RAG_RESULT)
    monkeypatch.setattr("app.api.queries.query_documents", stub)
    return stub


async def add_document(db_session, status: str) -> None:
    db_session.add(Document(filename="f.txt", content_type="text/plain", status=status))
    await db_session.commit()


async def test_query_without_ready_documents_returns_400(client, db_session, rag_stub):
    response = await client.post("/api/v1/query/", json={"question": "What is Qdrant?"})

    assert response.status_code == 400
    assert "No documents indexed" in response.json()["detail"]
    rag_stub.assert_not_awaited()


async def test_query_ignores_documents_that_are_not_ready(client, db_session, rag_stub):
    await add_document(db_session, "error")

    response = await client.post("/api/v1/query/", json={"question": "What is Qdrant?"})

    assert response.status_code == 400
    rag_stub.assert_not_awaited()


async def test_query_returns_answer_sources_and_usage(client, db_session, rag_stub):
    await add_document(db_session, "ready")

    response = await client.post("/api/v1/query/", json={"question": "What is Qdrant?"})

    assert response.status_code == 200
    body = response.json()
    assert body["question"] == "What is Qdrant?"
    assert body["answer"] == RAG_RESULT["answer"]
    assert body["sources"][0]["document_name"] == "stores.pdf"
    assert body["sources"][0]["page_number"] == 4
    assert body["prompt_tokens"] == 100
    assert body["completion_tokens"] == 12
    assert body["latency_ms"] == 42.5
    assert body["id"]
    assert body["created_at"]
    rag_stub.assert_awaited_once_with("What is Qdrant?")


async def test_query_persists_log_entry(client, db_session, rag_stub):
    from sqlalchemy import select

    from app.models.query import QueryLog

    await add_document(db_session, "ready")

    await client.post("/api/v1/query/", json={"question": "What is Qdrant?"})

    logs = (await db_session.execute(select(QueryLog))).scalars().all()
    assert len(logs) == 1
    assert logs[0].question == "What is Qdrant?"
    assert logs[0].chunks_used == 1
    assert logs[0].model == "gpt-4o-mini"


async def test_query_requires_question_field(client, db_session, rag_stub):
    response = await client.post("/api/v1/query/", json={})

    assert response.status_code == 422
    rag_stub.assert_not_awaited()


async def test_query_returns_server_error_when_pipeline_fails(client, db_session, rag_stub):
    await add_document(db_session, "ready")
    rag_stub.side_effect = RuntimeError("llm unavailable")

    response = await client.post("/api/v1/query/", json={"question": "Anything?"})

    assert response.status_code == 500
