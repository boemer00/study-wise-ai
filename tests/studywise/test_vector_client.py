"""Skeleton tests for the VectorClient wrapper."""

from studywise.vector.weaviate_client import get_vector_client, VectorClient


def test_singleton() -> None:
    v1 = get_vector_client()
    v2 = get_vector_client()
    assert v1 is v2
    assert isinstance(v1, VectorClient)
