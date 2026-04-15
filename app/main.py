import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import documents, health, queries
from app.config import settings

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer(),
    ],
)

app = FastAPI(
    title=settings.app_name,
    description="RAG platform: upload documents, ask questions, get answers with source references",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(documents.router, prefix="/api/v1")
app.include_router(queries.router, prefix="/api/v1")
