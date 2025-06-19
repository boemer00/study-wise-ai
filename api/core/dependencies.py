"""
Dependency injection for FastAPI routes
"""

from typing import Optional, Generator, Dict, Any
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()
import uuid
import jwt
import requests

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

from src.conversation.rag import StudyAssistant
from studywise.settings import get_settings, Settings


security = HTTPBearer(auto_error=False)

# Global assistant instance
_assistant_instance = None

# Demo user UUIDs - only for development mode
DEMO_USER_UUID = "550e8400-e29b-41d4-a716-446655440000"
DEMO_USER_2_UUID = "550e8400-e29b-41d4-a716-446655440001"

# Check if we're in development mode
def is_development_mode() -> bool:
    """Check if the application is running in development mode."""
    return os.getenv('ENVIRONMENT', 'development').lower() in ['development', 'dev', 'local']


def get_jwt_secret() -> str:
    """
    Get the JWT secret for token verification.

    For Supabase, this is typically the JWT secret from your project settings.
    If not available, fall back to SECRET_KEY for development.
    """
    # Try Supabase JWT secret first (if available)
    jwt_secret = os.getenv('SUPABASE_JWT_SECRET')
    if jwt_secret:
        return jwt_secret

    # Fall back to SECRET_KEY for development
    secret_key = os.getenv('SECRET_KEY')
    if secret_key:
        return secret_key

    # Last resort: use settings
    settings = get_settings()
    if settings.secret_key:
        return settings.secret_key

    raise HTTPException(
        status_code=500,
        detail="No JWT secret configured. Set SUPABASE_JWT_SECRET or SECRET_KEY environment variable."
    )


async def get_study_assistant() -> StudyAssistant:
    """
    Get StudyAssistant instance.

    Returns:
        Initialized StudyAssistant instance
    """
    global _assistant_instance
    if _assistant_instance is None:
        settings = get_settings()

        # Get credentials from environment or settings
        openai_key = settings.openai_api_key or os.getenv('OPENAI_API_KEY')
        supabase_url = settings.supabase_url or os.getenv('SUPABASE_URL')
        # Use anon key for user operations with JWT auth
        supabase_key = settings.supabase_anon_key or os.getenv('SUPABASE_ANON_KEY') or settings.supabase_key or os.getenv('SUPABASE_KEY')
        weaviate_url = settings.weaviate_url or os.getenv('WEAVIATE_URL')
        weaviate_key = settings.weaviate_api_key or os.getenv('WEAVIATE_API_KEY')

        _assistant_instance = StudyAssistant(
            openai_api_key=openai_key,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            weaviate_url=weaviate_url,
            weaviate_api_key=weaviate_key,
            model_name="gpt-4o-mini",  # Use more cost-effective model
            enable_advanced_features=True
        )

        try:
            await _assistant_instance.initialize()
            print("✅ StudyAssistant initialized successfully for API")
        except Exception as e:
            # Log error but don't raise - let endpoints handle fallback gracefully
            print(f"⚠️ StudyAssistant initialization failed: {str(e)}")
            print("   API will use fallback mode for chat responses")
            # Keep the non-initialized instance for graceful degradation
            # The chat endpoints will catch initialization errors and use demo mode

    return _assistant_instance


async def get_current_user_id(token: Optional[str] = Depends(security)) -> str:
    """
    Extract user ID - MVP mode: always return demo user.
    """
    # MVP: No authentication complexity, just return fixed demo user
    return DEMO_USER_UUID

    try:
        # Get Supabase configuration
        settings = get_settings()
        supabase_url = settings.supabase_url or os.getenv('SUPABASE_URL')

        if not supabase_url:
            if dev_mode:
                print("Supabase not configured, using demo user in development mode")
                return DEMO_USER_UUID
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Authentication service not configured"
                )

        # Handle demo tokens (for development demo mode)
        if token.credentials == "demo-token" and dev_mode:
            return DEMO_USER_UUID
        if token.credentials == "demo_token_user2" and dev_mode:
            return DEMO_USER_2_UUID

        # Supabase JWT verification
        # Get JWT secret from Supabase
        supabase_key = settings.supabase_key or os.getenv('SUPABASE_KEY')

        # Get JWT secret for signature verification
        try:
            jwt_secret = get_jwt_secret()
        except HTTPException as e:
            # In development mode, allow fallback to demo token if JWT secret is not configured
            if dev_mode and token.credentials.startswith("demo_token_"):
                print("⚠️ JWT secret not configured, allowing demo token in development mode")
                return DEMO_USER_UUID
            raise e

        # Decode and verify JWT signature
        try:
            payload = jwt.decode(
                token.credentials,
                jwt_secret,
                algorithms=["HS256", "RS256"],  # Support both symmetric and asymmetric
                options={"verify_signature": True, "verify_exp": True, "verify_aud": False}  # Skip audience verification for now
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            # In development mode, allow fallback to demo token
            if dev_mode and token.credentials.startswith("demo_token_"):
                print("⚠️ Invalid JWT token, allowing demo token in development mode")
                return DEMO_USER_UUID
            raise HTTPException(
                status_code=401,
                detail=f"Invalid token: {str(e)}"
            )

        # Extract user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token: no user ID found"
            )

        # Validate that it's a proper UUID
        try:
            uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=401,
                detail="Invalid token: malformed user ID"
            )

        # Additional validation: check token expiration
        exp = payload.get("exp")
        if exp:
            import time
            if time.time() > exp:
                raise HTTPException(
                    status_code=401,
                    detail="Token has expired"
                )

        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log error for debugging
        print(f"JWT validation error: {e}")

        if dev_mode:
            print("Authentication error in development mode, using demo user")
            return DEMO_USER_UUID
        else:
            raise HTTPException(
                status_code=401,
                detail="Authentication failed"
            )


def generate_user_uuid() -> str:
    """
    Generate a new UUID for user registration.

    In production, this would be handled by Supabase Auth automatically.
    This function is provided for reference/testing purposes.

    Returns:
        New UUID string
    """
    return str(uuid.uuid4())


async def verify_conversation_access(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id)
) -> str:
    """
    Verify user has access to conversation.
    """
    try:
        from src.supabase_client import get_supabase_client

        supabase = get_supabase_client()
        result = supabase.table('conversations').select('user_id').eq('id', conversation_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if result.data[0]['user_id'] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

    except HTTPException:
        raise
    except Exception as e:
        # In development mode, allow access if database check fails
        if is_development_mode():
            print(f"⚠️ Conversation access check failed in dev mode: {e}")
            return conversation_id
        else:
            raise HTTPException(status_code=500, detail="Access verification failed")

    return conversation_id


async def verify_flashcard_access(
    flashcard_id: str,
    user_id: str = Depends(get_current_user_id)
) -> str:
    """
    Verify user has access to flashcard.
    """
    try:
        from src.supabase_client import get_supabase_client

        supabase = get_supabase_client()
        result = supabase.table('flashcards').select('user_id').eq('id', flashcard_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Flashcard not found")

        if result.data[0]['user_id'] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

    except HTTPException:
        raise
    except Exception as e:
        # In development mode, allow access if database check fails
        if is_development_mode():
            print(f"⚠️ Flashcard access check failed in dev mode: {e}")
            return flashcard_id
        else:
            raise HTTPException(status_code=500, detail="Access verification failed")

    return flashcard_id


async def verify_document_access(
    document_id: str,
    user_id: str = Depends(get_current_user_id)
) -> str:
    """
    Verify user has access to document.
    """
    try:
        from src.supabase_client import get_supabase_client

        supabase = get_supabase_client()
        result = supabase.table('documents').select('user_id').eq('document_id', document_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        if result.data[0]['user_id'] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

    except HTTPException:
        raise
    except Exception as e:
        # In development mode, allow access if database check fails
        if is_development_mode():
            print(f"⚠️ Document access check failed in dev mode: {e}")
            return document_id
        else:
            raise HTTPException(status_code=500, detail="Access verification failed")

    return document_id


def get_pagination_params(
    skip: int = 0,
    limit: int = 20
) -> dict:
    """
    Get pagination parameters with validation.
    """
    if skip < 0:
        raise HTTPException(status_code=400, detail="Skip must be >= 0")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")

    return {"skip": skip, "limit": limit}
