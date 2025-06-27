# file: tests/conversation/test_reranker.py
"""Skeleton tests for the NeuralReranker component.

These will be expanded once the implementation is complete.
"""

import asyncio

from src.conversation.reranker import NeuralReranker
from src.conversation.models import DocumentSource


class _DummyModel:  # noqa: D401
    """A lightweight fake CrossEncoder with deterministic scoring."""

    def predict(self, pairs):  # type: ignore[no-self-use]
        # score = length of passage (shorter => lower score)
        return [len(p[1]) for p in pairs]


def _make_chunks(n: int) -> list[DocumentSource]:
    return [
        DocumentSource(
            document_id=f"doc-{i}",
            chunk_id=f"chunk-{i}",
            title="Test",
            content_snippet=f"content {i}",
            relevance_score=0.5,
        )
        for i in range(n)
    ]


def test_reranker_fallback() -> None:
    """If model can't load, reranker should fall back to original ordering."""
    reranker = NeuralReranker()

    # Force disable model
    reranker._model = None  # type: ignore[attr-defined]

    chunks = _make_chunks(3)
    ordered = asyncio.run(reranker.rerank("query", chunks))
    # Should be sorted by existing relevance_score (all equal) -> keep order
    assert ordered == chunks


def test_reranker_with_dummy_model() -> None:
    """Reranker should reorder chunks using provided dummy model."""
    reranker = NeuralReranker()
    reranker._model = _DummyModel()  # type: ignore[attr-defined]

    chunks = _make_chunks(3)
    reordered = asyncio.run(reranker.rerank("query", chunks))

    # Our dummy model scores longer content higher (later index), so expect reverse order
    assert reordered[0].chunk_id == "chunk-2"
