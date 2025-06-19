"""Skeleton tests for the OpenAIClient wrapper."""

import pytest

from studywise.llm.openai_client import get_openai_client, OpenAIClient


def test_singleton() -> None:
    """`get_openai_client` should return the same instance."""
    c1 = get_openai_client()
    c2 = get_openai_client()
    assert c1 is c2
    assert isinstance(c1, OpenAIClient)


def test_model_name_default() -> None:
    client = get_openai_client()
    assert client.model_name
