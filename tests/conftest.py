import re
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import document, query  # noqa: F401

TOKEN_PATTERN = re.compile(r"\s+|\S+")


class WordLevelEncoding:
    def __init__(self) -> None:
        self.vocabulary: list[str] = []
        self.index: dict[str, int] = {}

    def encode(self, text: str) -> list[int]:
        ids = []
        for piece in TOKEN_PATTERN.findall(text):
            if piece not in self.index:
                self.index[piece] = len(self.vocabulary)
                self.vocabulary.append(piece)
            ids.append(self.index[piece])
        return ids

    def decode(self, ids: list[int]) -> str:
        return "".join(self.vocabulary[i] for i in ids)


@pytest.fixture(autouse=True)
def offline_tokenizer(monkeypatch: pytest.MonkeyPatch) -> None:
    encoding = WordLevelEncoding()
    monkeypatch.setattr("tiktoken.get_encoding", lambda name: encoding)


@pytest_asyncio.fixture
async def session_factory() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[httpx.AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


@pytest.fixture
def vector_store_stub(monkeypatch: pytest.MonkeyPatch) -> dict[str, AsyncMock]:
    stubs = {
        "ensure_collection": AsyncMock(),
        "upsert_vectors": AsyncMock(),
        "delete_document_vectors": AsyncMock(),
    }
    monkeypatch.setattr("app.services.ingest.ensure_collection", stubs["ensure_collection"])
    monkeypatch.setattr("app.services.ingest.upsert_vectors", stubs["upsert_vectors"])
    monkeypatch.setattr(
        "app.api.documents.delete_document_vectors", stubs["delete_document_vectors"]
    )
    return stubs


@pytest.fixture
def embeddings_stub(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    async def fake_embeddings(texts: list[str]) -> list[list[float]]:
        return [[0.1] * 4 for _ in texts]

    stub = AsyncMock(side_effect=fake_embeddings)
    monkeypatch.setattr("app.services.ingest.generate_embeddings", stub)
    return stub
