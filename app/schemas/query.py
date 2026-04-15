from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str


class SourceChunk(BaseModel):
    content: str
    document_id: UUID
    document_name: str
    page_number: int | None
    score: float


class QueryResponse(BaseModel):
    id: UUID
    question: str
    answer: str
    sources: list[SourceChunk]
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    created_at: datetime
