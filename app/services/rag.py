import time

from app.config import settings
from app.services.embeddings import generate_embedding, get_openai_client
from app.services.vector_store import search_similar

SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on \
the provided document context.
Rules:
- Only answer based on the provided context. If the context doesn't contain the answer, say so.
- Cite your sources by referencing the document name and page number when available.
- Be concise and direct.
- Answer in the same language as the question."""


async def query_documents(question: str) -> dict:
    """Full RAG pipeline: embed question → search → generate answer."""
    start = time.perf_counter()

    # 1. Embed the question
    query_embedding = await generate_embedding(question)

    # 2. Search similar chunks
    results = await search_similar(query_embedding, top_k=settings.top_k)

    # 3. Build context from retrieved chunks
    context_parts = []
    sources = []
    for r in results:
        source_label = f"[{r['document_name']}"
        if r.get("page_number"):
            source_label += f", p.{r['page_number']}"
        source_label += "]"

        context_parts.append(f"{source_label}\n{r['content']}")
        sources.append(
            {
                "content": r["content"],
                "document_id": r["document_id"],
                "document_name": r["document_name"],
                "page_number": r.get("page_number"),
                "score": r["score"],
            }
        )

    context = "\n\n---\n\n".join(context_parts)

    # 4. Generate answer with LLM
    client = get_openai_client()
    response = await client.chat.completions.create(
        model=settings.chat_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
        temperature=0.1,
        max_tokens=1000,
    )

    answer = response.choices[0].message.content or ""
    latency_ms = (time.perf_counter() - start) * 1000

    return {
        "answer": answer,
        "sources": sources,
        "model": settings.chat_model,
        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        "latency_ms": round(latency_ms, 1),
    }
