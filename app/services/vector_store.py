import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import settings

_client: AsyncQdrantClient | None = None


def get_qdrant_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(url=settings.qdrant_url)
    return _client


async def ensure_collection() -> None:
    """Create collection if it doesn't exist."""
    client = get_qdrant_client()
    collections = await client.get_collections()
    names = [c.name for c in collections.collections]
    if settings.qdrant_collection not in names:
        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )


async def upsert_vectors(
    chunk_ids: list[uuid.UUID],
    embeddings: list[list[float]],
    payloads: list[dict],
) -> None:
    """Store vectors with metadata in Qdrant."""
    client = get_qdrant_client()
    points = [
        PointStruct(
            id=str(chunk_id),
            vector=embedding,
            payload=payload,
        )
        for chunk_id, embedding, payload in zip(chunk_ids, embeddings, payloads, strict=True)
    ]
    await client.upsert(collection_name=settings.qdrant_collection, points=points)


async def search_similar(
    query_embedding: list[float],
    top_k: int = settings.top_k,
) -> list[dict]:
    """Search for similar chunks."""
    client = get_qdrant_client()
    results = await client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_embedding,
        limit=top_k,
        with_payload=True,
    )
    return [
        {
            "chunk_id": point.id,
            "score": point.score,
            **point.payload,
        }
        for point in results.points
    ]


async def delete_document_vectors(document_id: str) -> None:
    """Delete all vectors for a document."""
    client = get_qdrant_client()
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    await client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        ),
    )
