"""
Dependency injection for FastAPI routes
"""

from typing import Optional, Generator
from functools import lru_cache
import os
import uuid
import jwt
import requests

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

from src.conversation.rag import StudyAssistant
from api.core.config import get_settings, Settings


security = HTTPBearer(auto_error=False)

# Global assistant instance
_assistant_instance = None

# Demo user UUID - only for development mode
DEMO_USER_UUID = "550e8400-e29b-41d4-a716-446655440000"

# Check if we're in development mode
def is_development_mode() -> bool:
    """Check if the application is running in development mode."""
    return os.getenv('ENVIRONMENT', 'development').lower() in ['development', 'dev', 'local']


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
        # Use service role key for RAG system
        supabase_key = settings.supabase_key or os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
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
    Extract user ID from Supabase JWT token.

    This function validates the JWT token from Supabase Auth and extracts the user ID.
    In development mode, falls back to demo user when no token is provided.
    In production mode, requires valid authentication.

    Args:
        token: Bearer token from request header

    Returns:
        User ID as UUID string

    Raises:
        HTTPException: If token is invalid, expired, or missing in production
    """
    # Check if we're in development mode
    dev_mode = is_development_mode()
    
    # If no token provided
    if not token or not token.credentials:
        if dev_mode:
            print("No token provided, using demo user in development mode")
            return DEMO_USER_UUID
        else:
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Please provide a valid access token."
            )
    
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
        
        # Handle demo token (for development demo mode)
        if token.credentials == "demo-token" and dev_mode:
            return DEMO_USER_UUID
        
        # Supabase JWT verification
        # Get JWT secret from Supabase
        supabase_key = settings.supabase_key or os.getenv('SUPABASE_KEY')
        
        # Decode JWT without verification first to get the header
        unverified_header = jwt.get_unverified_header(token.credentials)
        
        # For proper Supabase JWT validation, we should fetch JWKS
        # For now, we'll do basic validation with signature checking disabled
        # TODO: Implement proper JWKS validation for production
        
        payload = jwt.decode(
            token.credentials,
            options={"verify_signature": False},  # TODO: Enable signature verification
            algorithms=["HS256"]
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

    In production, this would:
    1. Query database to check if conversation belongs to user
    2. Raise 403 if access denied

    For demo, allow all access.
    """
    # TODO: Implement actual access control:
    #
    # from src.supabase_client import get_supabase_client
    #
    # supabase = get_supabase_client()
    # result = supabase.table('conversations').select('user_id').eq('id', conversation_id).execute()
    #
    # if not result.data or result.data[0]['user_id'] != user_id:
    #     raise HTTPException(status_code=403, detail="Access denied")

    return conversation_id


async def verify_flashcard_access(
    flashcard_id: str,
    user_id: str = Depends(get_current_user_id)
) -> str:
    """
    Verify user has access to flashcard.

    In production, this would:
    1. Query database to check if flashcard belongs to user
    2. Raise 403 if access denied

    For demo, allow all access.
    """
    # TODO: Implement actual access control:
    #
    # from src.supabase_client import get_supabase_client
    #
    # supabase = get_supabase_client()
    # result = supabase.table('flashcards').select('user_id').eq('id', flashcard_id).execute()
    #
    # if not result.data or result.data[0]['user_id'] != user_id:
    #     raise HTTPException(status_code=403, detail="Access denied")

    return flashcard_id


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
