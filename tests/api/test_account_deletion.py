"""Skeleton tests for the account deletion endpoint."""

import pytest
import httpx

import api.main  # FastAPI app
from api.core.dependencies import get_current_user_id


@pytest.mark.asyncio
async def test_delete_me_endpoint_returns_204(monkeypatch):
    """DELETE /users/me should return 204 even with stub implementation."""

    # Patch auth dependency to inject fake user id
    async def _fake_get_user_id():  # noqa: D401
        return "user-123"

    api.main.app.dependency_overrides[get_current_user_id] = _fake_get_user_id

    transport = httpx.ASGITransport(app=api.main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete("/api/v1/users/me")
    assert resp.status_code == 204
