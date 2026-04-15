from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.document import Document
from app.models.query import QueryLog
from app.schemas.query import QueryRequest, QueryResponse
from app.services.rag import query_documents

router = APIRouter(prefix="/query", tags=["query"])


@router.post("/", response_model=QueryResponse)
async def ask_question(req: QueryRequest, db: AsyncSession = Depends(get_db)):
    # Check there are documents to query
    result = await db.execute(select(Document).where(Document.status == "ready").limit(1))
    if not result.scalar_one_or_none():
        raise HTTPException(400, "No documents indexed yet. Upload a document first.")

    rag_result = await query_documents(req.question)

    # Log the query
    log = QueryLog(
        question=req.question,
        answer=rag_result["answer"],
        model=rag_result["model"],
        chunks_used=len(rag_result["sources"]),
        prompt_tokens=rag_result["prompt_tokens"],
        completion_tokens=rag_result["completion_tokens"],
        latency_ms=rag_result["latency_ms"],
    )
    db.add(log)
    await db.flush()

    return QueryResponse(
        id=log.id,
        question=req.question,
        answer=rag_result["answer"],
        sources=rag_result["sources"],
        model=rag_result["model"],
        prompt_tokens=rag_result["prompt_tokens"],
        completion_tokens=rag_result["completion_tokens"],
        latency_ms=rag_result["latency_ms"],
        created_at=log.created_at,
    )
