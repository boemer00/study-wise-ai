# file: tests/studywise/test_vector_hybrid_search.py
"""Skeleton tests for VectorClient.hybrid_search_chunks()."""

import pytest

import asyncio

from studywise.vector.weaviate_client import VectorClient


@pytest.mark.skip("Requires live Weaviate instance; integration tested elsewhere")
def test_hybrid_search_chunks_not_implemented(mocker) -> None:
    """The scaffold should raise NotImplementedError for now."""
    client = VectorClient()

    with pytest.raises(NotImplementedError):
        asyncio.run(client.hybrid_search_chunks("test query"))
