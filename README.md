# DocuQuery

RAG platform that indexes document corpora and answers natural language queries with LLM. Contextualized answers with source references in seconds.

## Features

- **Document ingestion** — Upload PDF or TXT, automatic text extraction and chunking
- **Vector search** — Semantic similarity search with Qdrant and OpenAI embeddings
- **RAG pipeline** — Retrieve relevant chunks, build context, generate answer with GPT-4o-mini
- **Source citations** — Every answer includes document name, page number, and relevance score
- **Query logging** — Track all queries with token usage, latency, and cost metrics
- **REST API** — Full CRUD for documents + query endpoint with Swagger docs

## Tech Stack

| Layer | Technology |
|---|---|
| **API** | FastAPI, Pydantic v2 |
| **Database** | PostgreSQL 16, SQLAlchemy 2 (async), Alembic |
| **Vector DB** | Qdrant |
| **LLM** | OpenAI GPT-4o-mini |
| **Embeddings** | OpenAI text-embedding-3-small (1536 dims) |
| **PDF parsing** | pypdf |
| **Tokenization** | tiktoken |
| **Logging** | structlog (JSON) |
| **Infra** | Docker, Docker Compose |

## Quick Start

```bash
git clone https://github.com/GeosData/llm-rag-platform.git
cd llm-rag-platform
cp .env.example .env  # add your OPENAI_API_KEY
make dev
# API docs at http://localhost:8000/docs
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/documents/` | Upload document (PDF/TXT) |
| `GET` | `/api/v1/documents/` | List all documents |
| `GET` | `/api/v1/documents/{id}` | Get document details |
| `DELETE` | `/api/v1/documents/{id}` | Delete document + vectors |
| `POST` | `/api/v1/query/` | Ask a question |

## How it works

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Upload  │────▶│  Extract │────▶│  Chunk   │────▶│  Embed   │
│   PDF    │     │   Text   │     │  (512t)  │     │ (OpenAI) │
└──────────┘     └──────────┘     └──────────┘     └────┬─────┘
                                                        │
                                                   ┌────▼─────┐
                                                   │  Qdrant  │
                                                   │  Store   │
                                                   └────┬─────┘
                                                        │
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌────▼─────┐
│  Answer  │◀────│   LLM    │◀────│ Context  │◀────│  Search  │
│ + Sources│     │ (GPT-4o) │     │  Build   │     │  Top-K   │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
```

## Project Structure

```
llm-rag-platform/
├── app/
│   ├── main.py            # FastAPI application
│   ├── config.py           # Settings (Pydantic)
│   ├── database.py         # SQLAlchemy async engine
│   ├── models/             # SQLAlchemy models (Document, Chunk, QueryLog)
│   ├── schemas/            # Pydantic schemas
│   ├── api/                # Route handlers
│   └── services/
│       ├── chunker.py      # Token-based text chunking
│       ├── embeddings.py   # OpenAI embeddings client
│       ├── vector_store.py # Qdrant operations
│       ├── ingest.py       # Document processing pipeline
│       └── rag.py          # RAG query pipeline
├── alembic/                # Database migrations
├── docker-compose.yml      # PostgreSQL + Redis + Qdrant + API
├── Dockerfile
└── pyproject.toml
```

## Development

```bash
make lint          # Check code style
make format        # Auto-format
make type-check    # mypy strict mode
make test          # Run tests with coverage
make migration msg="add users table"
make migrate       # Apply migrations
```

### Pre-commit hooks

Install once after cloning to block style/format issues before they hit CI:

```bash
pip install pre-commit
pre-commit install
```

Hooks run on `git commit`. Manual run: `pre-commit run --all-files`.

## Architecture decisions

The non-obvious calls are documented as ADRs under [`docs/adr/`](docs/adr/):

- [ADR-001: Qdrant over pgvector](docs/adr/0001-vector-store-qdrant-vs-pgvector.md) — why we accept the operational cost of a separate vector engine instead of staying inside Postgres.

---

*Built by [jotive](https://github.com/jotive) | [dev.jotive.com.co](https://dev.jotive.com.co) | [GeosData](https://geosdata.com)*
