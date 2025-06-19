"""Unified Weaviate client wrapper.

Provides a simplified interface (`VectorClient`) that will back the
retrieval, ingestion, and admin tasks while hiding SDK specifics.
Implementation logic will be added later.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from studywise.settings import get_settings

# Re-use the existing rich client to avoid rewriting logic.
from src.weaviate_client import create_weaviate_client, WeaviateClient as _LegacyWeaviateClient

logger = logging.getLogger(__name__)

__all__ = [
    "VectorClient",
    "SearchResult",
    "get_vector_client",
]


@dataclass
class SearchResult:
    """Result row from vector search."""

    id: str
    content: str
    title: str
    score: float
    metadata: Dict[str, Any]


class VectorClient:
    """Thin wrapper around the Weaviate SDK with helper methods."""

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        openai_key: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        settings = get_settings()
        self._url = url or settings.weaviate_url
        self._api_key = api_key or settings.weaviate_api_key
        self._openai_key = openai_key or settings.openai_api_key
        self._timeout = timeout
        self._client: Optional[_LegacyWeaviateClient] = None  # underlying legacy wrapper

    # ------------------------------------------------------------------
    # CRUD / search API (placeholders)
    # ------------------------------------------------------------------
    def semantic_search(self, query: str, *, limit: int = 10, user_id: Optional[str] = None) -> List[SearchResult]:
        """Perform vector similarity search using underlying client."""
        client = self._ensure_client()
        results = client.semantic_search(query=query, user_id=user_id, limit=limit)
        return [self._to_result(r) for r in results]

    def hybrid_search(self, query: str, *, limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Perform hybrid keyword+vector search."""
        client = self._ensure_client()
        results = client.hybrid_search(query=query, limit=limit, filters=filters)
        return [self._to_result(r) for r in results]

    def upsert_documents(self, docs: List[Dict[str, Any]]) -> int:
        """Insert or update documents.

        Uses the legacy client's add_documents method if available.
        """
        client = self._ensure_client()
        if hasattr(client, "add_documents"):
            return client.add_documents(docs)
        raise NotImplementedError("Underlying client does not support add_documents")

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and its chunks."""
        client = self._ensure_client()
        if hasattr(client, "delete_document"):
            return client.delete_document(document_id)
        logger.warning("delete_document not supported by underlying client")
        return False

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    def close(self) -> None:
        """Close the underlying Weaviate connection."""
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logger.debug("Error closing Weaviate client: %s", e)
            self._client = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_client(self) -> _LegacyWeaviateClient:
        if self._client is None:
            self._client = create_weaviate_client(
                url=self._url,
                api_key=self._api_key,
                openai_api_key=self._openai_key,
                local=False if self._api_key else True,
            )
        return self._client

    @staticmethod
    def _to_result(src_result: Any) -> SearchResult:  # type: ignore[valid-type]
        """Convert legacy SearchResult to the new dataclass."""
        return SearchResult(
            id=src_result.id,
            content=src_result.content,
            title=getattr(src_result, "title", ""),
            score=src_result.score,
            metadata=src_result.metadata,
        )

    # ------------------------------------------------------------------
    # Attribute proxy
    # ------------------------------------------------------------------

    def __getattr__(self, item: str):
        client = self._ensure_client()
        return getattr(client, item)


# Singleton accessor -------------------------------------------------------

_vector_singleton: Optional[VectorClient] = None

def get_vector_client() -> VectorClient:
    """Return a shared VectorClient instance."""
    global _vector_singleton
    if _vector_singleton is None:
        _vector_singleton = VectorClient()
    return _vector_singleton
