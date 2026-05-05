# Roadmap — DocuQuery

Plan público. Items concretos, no ideas. Si no está acá, no está commited.

## Now (alpha — 2026-05)

- [x] Core RAG pipeline: ingest → chunk → embed → store → search → generate
- [x] PostgreSQL schema + migrations (Alembic)
- [x] Qdrant integration with COSINE similarity, 1536-dim vectors
- [x] FastAPI endpoints: documents CRUD + query
- [x] Docker Compose dev stack (Postgres + Redis + Qdrant + API)
- [x] structlog JSON logs, ruff lint, mypy strict
- [x] ADR-001: vector store choice
- [x] Tests for `chunker` and `rag` services (8 tests passing)

## Next (next 30 days)

- [ ] **ADR-002**: why GPT-4o-mini over Claude/Gemini
- [ ] **ADR-003**: chunking strategy (512 tokens / 64 overlap, why not semantic chunking)
- [ ] **Tests**: `services/ingest.py` (PDF parse + chunk + embed + upsert end-to-end with fixtures)
- [ ] **Tests**: API handlers (`api/documents.py`, `api/queries.py`) using `httpx.AsyncClient`
- [ ] **Coverage target**: 70% global
- [ ] **Hybrid search behind feature flag**: combine vector similarity with PostgreSQL FTS for keyword-heavy queries
- [ ] **Reranking**: optional cross-encoder reranker for top-20 → top-5

## Later (60–90 days)

- [ ] **Multi-tenant support**: collection-per-tenant in Qdrant + tenant scoping in API
- [ ] **Streaming responses**: SSE for chat-style query endpoint
- [ ] **Cost dashboard**: Postgres view aggregating token usage and latency by document/tenant
- [ ] **Eval harness**: regression suite with question/expected-source pairs to detect retrieval drift
- [ ] **OpenTelemetry**: traces across embed → search → LLM with cost attribution
- [ ] **Public demo**: read-only deployment with sample corpus

## Won't do (yet)

- Self-hosted LLM. Adds infra cost without product gain at this scale.
- Knowledge graph layer (Neo4j-style). Premature for current document types.
- Native PDF visual layout extraction. `pypdf` text-only is enough until proven otherwise.
- Multi-modal (images in PDFs). Out of scope for the alpha.

## Revisit conditions

- If retrieval quality drops below acceptable threshold → reranking moves from Later to Next.
- If cost per query exceeds 1.5x budget for a tenant → cost dashboard moves from Later to Next.
- If a real user reports the chunking strategy hurts answer quality → ADR-003 may pivot to semantic chunking.
