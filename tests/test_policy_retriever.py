from src.policy_retriever import (
    _cosine_similarity,
    _lexical_evidence,
    chunk_text,
)


def test_chunk_text_preserves_all_content():
    text = "Refund policy\nRule one\nRule two\nRule three"
    chunks = chunk_text(text, max_chars=25)

    assert len(chunks) > 1
    combined = "\n".join(chunks)

    for line in text.splitlines():
        assert line in combined


def test_chunk_text_rejects_invalid_input():
    import pytest

    with pytest.raises(TypeError):
        chunk_text(123)

    with pytest.raises(ValueError):
        chunk_text("Some text", max_chars=0)


def test_chunk_text_splits_long_lines():
    text = "A" * 120
    chunks = chunk_text(text, max_chars=50)

    assert len(chunks) > 1
    assert all(len(chunk) <= 50 for chunk in chunks)


def test_cosine_similarity_identical_vectors():
    assert _cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_cosine_similarity_orthogonal_vectors():
    assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_similarity_zero_vector():
    assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_cosine_similarity_rejects_dimension_mismatch():
    import pytest

    with pytest.raises(ValueError):
        _cosine_similarity([1.0], [1.0, 0.0])


def test_lexical_evidence_matches_policy_synonyms():
    matches = _lexical_evidence(
        "My order was damaged",
        "Escalate defective items for support-team review.",
    )

    assert "broken" in matches


def test_lexical_evidence_rejects_unrelated_policy():
    matches = _lexical_evidence(
        "International customs duties",
        "Refund approval requires review by the support team.",
    )

    assert matches == []



def test_embedding_cache_reuses_document_vectors(tmp_path, monkeypatch):
    from src import policy_retriever as retriever

    policy_dir = tmp_path / "policies"
    policy_dir.mkdir()
    (policy_dir / "refund_policy.txt").write_text(
        "Refund policy\\nRefunds require support-team approval.",
        encoding="utf-8",
    )

    cache_file = policy_dir / "embedding_cache.json"

    monkeypatch.setattr(retriever, "POLICY_DIR", policy_dir)
    monkeypatch.setattr(retriever, "CACHE_FILE", cache_file)

    embedding_calls = []

    def fake_embeddings(texts):
        embedding_calls.append(list(texts))
        return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(retriever, "_request_embeddings", fake_embeddings)

    first = retriever.search_policy_docs("refund approval")
    assert first["found"] is True
    assert first["cache"]["embedded_chunks"] == 1
    assert first["cache"]["cache_hits"] == 0
    assert cache_file.exists()

    second = retriever.search_policy_docs("refund approval")
    assert second["found"] is True
    assert second["cache"]["embedded_chunks"] == 0
    assert second["cache"]["cache_hits"] == 1

    # First call embeds the document and query.
    # Second call embeds only the query.
    assert len(embedding_calls) == 3
    assert len(embedding_calls[0]) == 1
    assert len(embedding_calls[1]) == 1
    assert len(embedding_calls[2]) == 1


def test_policy_documents_are_read_without_utf8_bom(tmp_path, monkeypatch):
    from src import policy_retriever as retriever

    policy_dir = tmp_path / "policies"
    policy_dir.mkdir()

    (policy_dir / "refund_policy.txt").write_text(
        "\ufeffRefund policy\nRefunds require approval.",
        encoding="utf-8",
    )

    monkeypatch.setattr(retriever, "POLICY_DIR", policy_dir)
    monkeypatch.setattr(
        retriever,
        "CACHE_FILE",
        policy_dir / "embedding_cache.json",
    )
    monkeypatch.setattr(
        retriever,
        "_request_embeddings",
        lambda texts: [[1.0, 0.0] for _ in texts],
    )

    result = retriever.search_policy_docs("refund approval")

    assert result["found"] is True
    assert not result["results"][0]["content"].startswith("\ufeff")
