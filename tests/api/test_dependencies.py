# file: tests/api/test_dependencies.py
import pytest
from fastapi import HTTPException
import os
import uuid
import jwt

from api.core import dependencies
from fastapi.security import HTTPAuthorizationCredentials


# Ensure we run in development mode by default during these tests.
@pytest.fixture(autouse=True)
def _set_dev_mode(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")


@pytest.mark.asyncio
async def test_get_current_user_id_valid_token(monkeypatch):
    """A well-formed, signed JWT should yield the correct user UUID."""

    secret = "test-secret"
    monkeypatch.setenv("SECRET_KEY", secret)

    expected_user_id = str(uuid.uuid4())

    # --- stub Settings object so dependency code finds required attributes ---
    class _StubSettings:
        supabase_url: str = "https://stub.supabase.co"
        supabase_key: str = "stub-key"
        supabase_anon_key: str = "anon-key"
        secret_key: str = secret

    # Ensure get_settings() returns the stub
    monkeypatch.setattr(dependencies, "get_settings", lambda: _StubSettings())

    # Force get_jwt_secret() to return the same testing secret
    monkeypatch.setattr(dependencies, "get_jwt_secret", lambda: secret)

    jwt_token: str = jwt.encode({"sub": expected_user_id}, secret, algorithm="HS256")  # type: ignore[arg-type]

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=jwt_token)

    user_id = await dependencies.get_current_user_id(token=credentials)

    assert user_id == expected_user_id


@pytest.mark.asyncio
async def test_get_current_user_id_missing_token():
    """Absence of token should raise HTTP 401."""

    with pytest.raises(HTTPException) as exc:
        await dependencies.get_current_user_id(token=None)  # type: ignore[arg-type]

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_id_demo_token():
    """`demo-token` should be accepted in development mode and return DEMO_USER_UUID."""

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="demo-token")

    user_id = await dependencies.get_current_user_id(token=credentials)

    assert user_id == dependencies.DEMO_USER_UUID
