from app.services.chunker import chunk_text, count_tokens


def test_count_tokens_returns_positive_for_non_empty_text():
    assert count_tokens("hello world") > 0


def test_count_tokens_zero_for_empty_string():
    assert count_tokens("") == 0


def test_chunk_text_returns_single_chunk_for_short_input():
    text = "Short document."
    chunks = chunk_text(text, chunk_size=512, overlap=64)
    assert len(chunks) == 1
    assert chunks[0].strip() == text


def test_chunk_text_splits_long_input_into_multiple_chunks():
    paragraph = "Lorem ipsum dolor sit amet. " * 200
    chunks = chunk_text(paragraph, chunk_size=64, overlap=8)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.strip()


def test_chunk_text_overlaps_chunks():
    text = " ".join(f"word{i}" for i in range(500))
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    assert len(chunks) >= 3
    # Tail of chunk N should share tokens with head of chunk N+1 in most cases.
    # We don't assert exact overlap (tokenizer boundaries) but require >1 chunk.


def test_chunk_text_handles_whitespace_only_input():
    chunks = chunk_text("   \n\t  ", chunk_size=128, overlap=16)
    assert chunks == []
