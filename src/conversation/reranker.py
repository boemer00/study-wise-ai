# file: src/conversation/reranker.py
"""Neural reranking component.

Provides a language-model–based reranker that scores and reorders document
chunks returned by the retriever using a Hugging Face cross-encoder wrapped
by LangChain's `CrossEncoderReranker`.

This is a scaffold; implementation will be added in the next step.
"""

from __future__ import annotations

import logging
from typing import List, Optional

# Local imports – avoid heavy deps at import time
from src.conversation.models import DocumentSource

__all__: list[str] = [
    "NeuralReranker",
]

DEFAULT_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
LOGGER = logging.getLogger(__name__)


class NeuralReranker:
    """Rank document chunks with a cross-encoder.

    Parameters
    ----------
    model_name
        Hugging Face model id to load.
    device
        Torch device string (e.g. "cpu", "cuda:0"). Optional.
    top_k
        Maximum number of chunks to return after reranking. If *None*, all
        chunks are returned in ranked order.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        *,
        device: Optional[str] = None,
    ) -> None:
        self._model_name: str = model_name
        self._device: Optional[str] = device
        self._model = None  # Lazy-loaded sentence-transformers CrossEncoder

    async def rerank(
        self,
        query: str,
        chunks: List[DocumentSource],
        *,
        top_k: Optional[int] = None,
    ) -> List[DocumentSource]:
        """Return *chunks* ordered by relevance to *query*.

        Notes
        -----
        This scaffold does **not** implement the actual ranking logic yet.
        """
        # Lazily load model (may fail in constrained environments)
        self._ensure_model_loaded()

        # If model failed to load, gracefully fall back to original ordering
        if self._model is None:
            return sorted(chunks, key=lambda c: c.relevance_score, reverse=True)

        # ------------------------------------------------------------------
        # Run cross-encoder scoring in a thread pool to avoid blocking event loop
        # ------------------------------------------------------------------
        import asyncio
        from dataclasses import replace

        loop = asyncio.get_running_loop()

        # Prepare sentence pairs (query, chunk text)
        pairs = [(query, chunk.content_snippet) for chunk in chunks]

        def _predict() -> List[float]:  # type: ignore[override]
            return self._model.predict(pairs)  # type: ignore[attr-defined]

        scores: List[float] = await loop.run_in_executor(None, _predict)

        # Zip scores with chunks and sort descending
        scored = [replace(chunk, relevance_score=float(score)) for chunk, score in zip(chunks, scores)]
        scored.sort(key=lambda c: c.relevance_score, reverse=True)

        if top_k is not None:
            return scored[:top_k]
        return scored

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_model_loaded(self) -> None:
        """Load the sentence-transformers CrossEncoder lazily."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name, device=self._device or "cpu")  # type: ignore[assignment]
            LOGGER.info("CrossEncoder model '%s' loaded for neural reranking", self._model_name)
        except (ImportError, OSError, RuntimeError) as exc:
            # Cannot load model – log and disable neural reranking
            LOGGER.warning("Neural reranker disabled: %s", exc)
            self._model = None
