"""Smoke test for ContextRetriever initialisation using new wrapper defaults."""

from studywise.llm.openai_client import get_openai_client
from studywise.vector.weaviate_client import VectorClient

from src.conversation.retriever import ContextRetriever


class DummyWeaviate(VectorClient):
    """Use VectorClient but avoid network connection during tests."""

    def __init__(self) -> None:  # noqa: D401
        # Bypass base init to skip connection
        pass


def test_retriever_init_with_wrappers() -> None:
    openai_client = get_openai_client()
    vector_client = DummyWeaviate()

    # Using dummy weaviate_client to avoid network
    retriever = ContextRetriever(
        weaviate_client=vector_client,  # type: ignore[arg-type]
        openai_api_key="dummy",
        openai_client=openai_client,
        vector_client=vector_client,
    )

    assert retriever.openai_client is openai_client
