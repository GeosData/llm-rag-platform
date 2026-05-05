# TRACE — DocuQuery

Append-only log of decisions, events, milestones, kills, pivots, locks, blockers. Newest at top.

Types: `DECISION` | `EVENT` | `MILESTONE` | `KILL` | `PIVOT` | `LOCK` | `BLOCKER`

---

## 2026-05-05 — MILESTONE — Open-sourced + ADR-001 + tests

Repo flipped from private to public on GeosData org.

Pre-flip additions:
- `docs/adr/0001-vector-store-qdrant-vs-pgvector.md` — first ADR documenting the Qdrant choice with explicit trade-offs and revisit conditions.
- `tests/test_chunker.py` — 6 tests, 100% coverage of `services/chunker.py`.
- `tests/test_rag.py` — 2 tests with mocked OpenAI client, 100% coverage of `services/rag.py`.
- `README.md` — added "Architecture decisions" section linking ADR-001.
- `ROADMAP.md` — Now / Next / Later / Won't do with revisit conditions.

Coverage at flip time: 25% global (was 0%). `services/chunker.py` and `services/rag.py` at 100%; ingest, embeddings, vector_store, API handlers still uncovered.

Commit: `2568429 docs: ADR-001 vector store choice + chunker/rag tests + README decisions`.

Amplification: post on dev.jotive.com.co — `2026-05-05-docuquery-rag-fastapi-qdrant-publico`. LinkedIn post pending (manual).

Reasons for ship-now over polish-later:
- Trajectory visible (next commits will show progression) is more valuable than perfect first impression.
- Public scrutiny accelerates feedback loop.
- Was sitting in private with the "5 aspirational repos" anti-pattern. Counter-acted by shipping the one that had real code.

## 2026-04-15 — EVENT — Initial scaffold pushed

First public-org commit (private at the time). FastAPI + SQLAlchemy 2 async + Qdrant + OpenAI stack laid out. PostgreSQL models, basic API routes, Dockerfile, docker-compose, Alembic baseline.

## 2026-04-15 — DECISION — Qdrant over pgvector

Chosen for failure isolation and latency headroom. Accepted operational cost of separate engine. Documented later as ADR-001 (2026-05-05). See `docs/adr/0001-vector-store-qdrant-vs-pgvector.md`.
