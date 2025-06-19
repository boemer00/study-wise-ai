"""Async OpenAI client wrapper.

This module centralises all OpenAI interactions (embeddings, chat, etc.)
so that credentials, retries, and streaming behaviour are controlled in
one place.

Implementation is deferred to the *Implement* phase.
"""
from __future__ import annotations

import logging
from typing import AsyncIterator, List, Dict, Optional, Union, Any

from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from studywise.settings import get_settings

# Import the official OpenAI async client lazily to avoid the cost at
# module import time when it might not be needed.
from importlib import import_module

logger = logging.getLogger(__name__)

__all__ = [
    "OpenAIClient",
    "get_openai_client",
]


class OpenAIClient:
    """Thin async wrapper around the official OpenAI SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._api_key = api_key or get_settings().openai_api_key
        self._model = model or get_settings().openai_model or "gpt-4o-mini"
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: Optional[Any] = None  # openai.AsyncClient instance

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    async def aclose(self) -> None:
        """Close the underlying OpenAI client session if open."""
        if self._client and hasattr(self._client, "close"):
            await self._client.close()
            self._client = None

    async def embed(self, texts: List[str], model: Optional[str] = None) -> List[List[float]]:
        """Generate embeddings for a batch of texts.

        This is a convenience wrapper around `client.embeddings.create`.
        Uses tenacity to retry transient failures.
        """
        client = self._create_client()

        async for attempt in self._retryer():
            with attempt:
                response = await client.embeddings.create(
                    model=model or "text-embedding-3-small",
                    input=texts,
                )
                # The SDK returns a list of dicts with "embedding" keys.
                vectors = [item.embedding for item in response.data]  # type: ignore[attr-defined]
                return vectors

        # If we somehow exit loop without returning.
        raise RuntimeError("Failed to generate embeddings after retries")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> Union[str, AsyncIterator[str]]:
        """Send a chat completion request.

        If *stream* is True, returns an async iterator yielding chunks of
        text; otherwise returns the full combined response.
        """
        client = self._create_client()

        async def _request():
            return await client.chat.completions.create(
                model=model or self._model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream,
            )

        async for attempt in self._retryer():
            with attempt:
                response = await _request()
                if stream:
                    # The streamed response is an async iterator of
                    # events; wrap to yield content only.
                    async def _generator():  # type: ignore[return-value]
                        async for chunk in response:  # type: ignore[union-attr]
                            choice = chunk.choices[0]
                            if choice.delta.content:
                                yield choice.delta.content

                    return _generator()

                # Non-stream: take first choice text
                if not response.choices:
                    raise ValueError("OpenAI returned no choices")
                return response.choices[0].message.content  # type: ignore[return-value]

        raise RuntimeError("Failed to get chat completion after retries")

    # ------------------------------------------------------------------
    # Internal helpers (placeholders)
    # ------------------------------------------------------------------

    def _create_client(self):
        """Lazy-instantiate and memoise the OpenAI Async client."""
        if self._client is None:
            openai_module = import_module("openai")
            AsyncOpenAI = getattr(openai_module, "AsyncOpenAI")

            self._client = AsyncOpenAI(
                api_key=self._api_key,
                timeout=self._timeout,
            )
        return self._client

    def _retryer(self):
        """Return a configured tenacity.AsyncRetrying instance."""
        return AsyncRetrying(
            retry=retry_if_exception_type(Exception),  # refined later
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential_jitter(initial=1, max=8),
            reraise=True,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def model_name(self) -> str:  # noqa: D401
        """Return default model name."""
        return self._model

    # ------------------------------------------------------------------
    # Attribute delegation to underlying SDK for backward compatibility
    # ------------------------------------------------------------------

    def __getattr__(self, item: str):
        """Delegate attribute access to the underlying AsyncOpenAI client.

        This allows existing code that calls, e.g.,
        ``openai_client.chat.completions.create`` to continue working
        transparently.
        """
        client = self._create_client()
        return getattr(client, item)


# Singleton accessor -------------------------------------------------------

_openai_singleton: Optional[OpenAIClient] = None

def get_openai_client() -> OpenAIClient:
    """Return a lazily-initialised shared OpenAIClient instance."""
    global _openai_singleton
    if _openai_singleton is None:
        _openai_singleton = OpenAIClient()
    return _openai_singleton
