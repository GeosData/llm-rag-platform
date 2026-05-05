# ADR-001: Qdrant over pgvector for the vector store

- **Status:** Accepted
- **Date:** 2026-04-15
- **Deciders:** jotive

## Context

DocuQuery needs a vector store to index document chunks (≤1M vectors at first, multi-tenant in the future) and serve top-k similarity queries with sub-200ms p95 latency. We already run PostgreSQL 16 for relational data (documents, queries, audit logs).

Two realistic options:

1. **pgvector** — extension on the existing PostgreSQL instance.
2. **Qdrant** — dedicated vector database, separate process/container.

## Options compared

| Dimension | pgvector | Qdrant |
|---|---|---|
| Operational footprint | Zero new service. Same backups, same monitoring. | Separate container. Separate backup story. Adds 1 dependency. |
| Latency at 1M vectors | HNSW index works, but query planner overhead is real. p95 ~80–150ms typical. | Dedicated engine. p95 ~20–60ms typical at the same scale. |
| Filtering by payload | SQL `WHERE` over indexed columns. Excellent ergonomics. | Payload filters with native types. Good ergonomics but custom DSL. |
| Multi-tenant isolation | Row-level security or schema-per-tenant. Mature. | Collection-per-tenant or payload filter. Less mature pattern. |
| Cost at small scale (<100k vectors) | Effectively free (already paying for Postgres). | Adds memory/CPU for a service that is mostly idle. |
| Cost at large scale (>10M vectors) | Postgres becomes the bottleneck for the whole app. | Scales independently. |
| Hybrid search (vector + lexical) | Postgres FTS in the same query is trivial. | Possible with sparse vectors but more code. |
| Recovery and backup | `pg_dump` covers it. | Snapshot API + separate volume strategy. |
| Local dev experience | Already running. | One more `docker compose` service. |

## Decision

**Qdrant**, despite the operational cost.

The driver is **isolation of failure modes**. RAG queries are a hot path that runs at higher rate than CRUD. Putting them on the same Postgres node means a vector-index recompaction or a slow RAG burst can degrade the rest of the API. A separate engine keeps that blast radius contained.

The secondary driver is **latency headroom for the future**. p95 ~30ms today gives us room to add reranking, multi-vector search, and hybrid retrieval without hitting a wall. pgvector at 1M+ rows on a single node is workable, but every optimization spends Postgres budget that other tables also need.

Filtering ergonomics is real cost, but the schema we need (document_id, page_number, score) is small. Payload filtering covers it.

## Consequences

**Positive:**

- Independent scaling for vector load.
- Snapshot/restore separate from app DB; we can rebuild the vector store from source documents without touching Postgres.
- Faster latency baseline.

**Negative:**

- Another service to deploy, monitor, and back up. We accept this; documented in the runbook.
- Payload filters are looser than SQL. Acceptable for the current schema, would revisit if filters grow complex.
- Two sources of truth for vector ↔ chunk mapping. We keep `chunks.id` as the single ID across both systems and validate consistency in the ingest pipeline.

## Revisit when

- The vector store grows past ~50M vectors. At that point, sharding strategy (Qdrant cluster vs. external managed) becomes the next decision.
- Hybrid search requirements push us toward a single-engine solution (e.g., Vespa).
- Operational cost of Qdrant becomes the bottleneck rather than Postgres.

## References

- [Qdrant benchmarks](https://qdrant.tech/benchmarks/)
- [pgvector indexing strategies](https://github.com/pgvector/pgvector#indexing)
- [Pinecone vs Qdrant vs pgvector trade-off discussions](https://qdrant.tech/articles/pinecone-vs-qdrant/)
