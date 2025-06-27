# file: api/services/user_cleanup.py
"""User data cleanup service (scaffold).

Provides helper functions that will orchestrate removal of a user's
application data across Supabase, Weaviate, and the authentication
store. Implementation logic will be added in the next phase.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Final

from scripts.cleanup_user_data import cleanup_user_data

# Optional: Supabase admin deletion
from src.supabase_client import get_supabase_client

# Optional: local simple-auth store
from api.core.simple_auth import SimpleAuth

logger = logging.getLogger(__name__)

__all__: Final = [
    "purge_user_data",
]


async def purge_user_data(user_id: str) -> None:  # noqa: D401
    """Hard-delete *user_id* from all data stores.

    Runs blocking cleanup logic in a thread-pool so that FastAPI background
    tasks remain non-blocking.
    """

    loop = asyncio.get_running_loop()

    # 1. Application data (Supabase tables + Weaviate chunks)
    def _run_cleanup() -> None:  # Blocking function
        cleanup_user_data(user_id, confirm=True)

    await loop.run_in_executor(None, _run_cleanup)

    # 2. Delete Supabase Auth user (if service role key is configured)
    try:
        if os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
            client = get_supabase_client()
            client.auth.admin.delete_user(user_id)  # type: ignore[attr-defined]
            logger.info("Deleted Supabase auth user %s", user_id)
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not delete Supabase user %s: %s", user_id, exc)

    # 3. Delete from local simple-auth store (if present)
    try:
        SimpleAuth().delete_user(user_id=user_id)
    except Exception as exc:  # pragma: no cover
        logger.debug("Local SimpleAuth delete failed (may be unused): %s", exc)
