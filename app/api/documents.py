import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.document import Document
from app.schemas.document import DocumentList, DocumentResponse
from app.services.ingest import ingest_document
from app.services.vector_store import delete_document_vectors

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {"application/pdf", "text/plain"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@router.post("/", response_model=DocumentResponse, status_code=201)
async def upload_document(file: UploadFile, db: AsyncSession = Depends(get_db)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}. Use PDF or TXT.")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large. Max 20MB.")

    doc = Document(
        id=uuid.uuid4(),
        filename=file.filename or "untitled",
        content_type=file.content_type or "application/octet-stream",
    )
    db.add(doc)
    await db.flush()

    await ingest_document(db, doc, file_bytes)

    return doc


@router.get("/", response_model=DocumentList)
async def list_documents(db: AsyncSession = Depends(get_db)):
    count_result = await db.execute(select(func.count(Document.id)))
    total = count_result.scalar_one()

    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    items = list(result.scalars().all())

    return DocumentList(items=items, total=total)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    await delete_document_vectors(str(document_id))
    await db.delete(doc)
