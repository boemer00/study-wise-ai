"""
Admin endpoints for user management and platform oversight.
MVP implementation with basic user statistics and management.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.core.dependencies import get_current_user_id, is_development_mode


# Admin user ID - in production, this should be configured via environment
ADMIN_USER_ID = "550e8400-e29b-41d4-a716-446655440000"  # Demo admin user


class UserStats(BaseModel):
    """User statistics model."""
    user_id: str
    flashcards_count: int
    documents_count: int
    reviews_count: int
    last_activity: Optional[datetime]
    created_at: Optional[datetime]


class PlatformStats(BaseModel):
    """Platform-wide statistics model."""
    total_users: int
    total_flashcards: int
    total_documents: int
    total_reviews: int
    active_users_7d: int
    active_users_30d: int


router = APIRouter()


def verify_admin_access(user_id: str = Depends(get_current_user_id)) -> str:
    """
    Verify user has admin access.
    For MVP: Simple user ID check. In production: proper role-based access.
    """
    # In development mode, allow admin access for demo user
    if is_development_mode() and user_id == ADMIN_USER_ID:
        return user_id
    
    # In production, check admin role in database
    # TODO: Implement proper role-based access control
    if user_id != ADMIN_USER_ID:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user_id


@router.get("/stats/platform", response_model=PlatformStats)
async def get_platform_stats(
    admin_id: str = Depends(verify_admin_access)
) -> PlatformStats:
    """
    Get platform-wide statistics for admin dashboard.
    """
    try:
        from src.supabase_client import get_supabase_client
        
        supabase = get_supabase_client()
        
        # Get user count
        users_result = supabase.table('users').select('id', count='exact').execute()
        total_users = users_result.count or 0
        
        # Get flashcard count
        flashcards_result = supabase.table('flashcards').select('id', count='exact').execute()
        total_flashcards = flashcards_result.count or 0
        
        # Get document count
        documents_result = supabase.table('documents').select('document_id', count='exact').execute()
        total_documents = documents_result.count or 0
        
        # Get review count
        reviews_result = supabase.table('flashcard_reviews').select('id', count='exact').execute()
        total_reviews = reviews_result.count or 0
        
        # Calculate active users (7 days)
        seven_days_ago = datetime.now() - timedelta(days=7)
        active_7d_result = supabase.table('flashcard_reviews')\
            .select('user_id', count='exact')\
            .gte('review_date', seven_days_ago.isoformat())\
            .execute()
        active_users_7d = len(set(review['user_id'] for review in active_7d_result.data)) if active_7d_result.data else 0
        
        # Calculate active users (30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        active_30d_result = supabase.table('flashcard_reviews')\
            .select('user_id')\
            .gte('review_date', thirty_days_ago.isoformat())\
            .execute()
        active_users_30d = len(set(review['user_id'] for review in active_30d_result.data)) if active_30d_result.data else 0
        
        return PlatformStats(
            total_users=total_users,
            total_flashcards=total_flashcards,
            total_documents=total_documents,
            total_reviews=total_reviews,
            active_users_7d=active_users_7d,
            active_users_30d=active_users_30d
        )
        
    except Exception as e:
        if is_development_mode():
            # Return demo stats in development mode
            return PlatformStats(
                total_users=5,
                total_flashcards=150,
                total_documents=25,
                total_reviews=500,
                active_users_7d=3,
                active_users_30d=4
            )
        else:
            raise HTTPException(status_code=500, detail=f"Failed to fetch platform stats: {str(e)}")


@router.get("/users", response_model=List[UserStats])
async def get_user_list(
    admin_id: str = Depends(verify_admin_access),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> List[UserStats]:
    """
    Get list of users with basic statistics.
    """
    try:
        from src.supabase_client import get_supabase_client
        
        supabase = get_supabase_client()
        
        # Get users with pagination
        users_result = supabase.table('users')\
            .select('id, created_at')\
            .range(offset, offset + limit - 1)\
            .execute()
        
        if not users_result.data:
            return []
        
        user_stats = []
        for user in users_result.data:
            user_id = user['id']
            
            # Get user's flashcard count
            flashcards_result = supabase.table('flashcards')\
                .select('id', count='exact')\
                .eq('user_id', user_id)\
                .execute()
            flashcards_count = flashcards_result.count or 0
            
            # Get user's document count
            documents_result = supabase.table('documents')\
                .select('document_id', count='exact')\
                .eq('user_id', user_id)\
                .execute()
            documents_count = documents_result.count or 0
            
            # Get user's review count and last activity
            reviews_result = supabase.table('flashcard_reviews')\
                .select('id, review_date', count='exact')\
                .eq('user_id', user_id)\
                .order('review_date', desc=True)\
                .limit(1)\
                .execute()
            
            reviews_count = reviews_result.count or 0
            last_activity = None
            if reviews_result.data:
                last_activity = datetime.fromisoformat(reviews_result.data[0]['review_date'].replace('Z', '+00:00'))
            
            user_stats.append(UserStats(
                user_id=user_id,
                flashcards_count=flashcards_count,
                documents_count=documents_count,
                reviews_count=reviews_count,
                last_activity=last_activity,
                created_at=datetime.fromisoformat(user['created_at'].replace('Z', '+00:00')) if user.get('created_at') else None
            ))
        
        return user_stats
        
    except Exception as e:
        if is_development_mode():
            # Return demo user stats in development mode
            return [
                UserStats(
                    user_id="550e8400-e29b-41d4-a716-446655440000",
                    flashcards_count=45,
                    documents_count=8,
                    reviews_count=120,
                    last_activity=datetime.now() - timedelta(hours=2),
                    created_at=datetime.now() - timedelta(days=30)
                ),
                UserStats(
                    user_id="550e8400-e29b-41d4-a716-446655440001",
                    flashcards_count=32,
                    documents_count=5,
                    reviews_count=89,
                    last_activity=datetime.now() - timedelta(days=1),
                    created_at=datetime.now() - timedelta(days=15)
                )
            ]
        else:
            raise HTTPException(status_code=500, detail=f"Failed to fetch user list: {str(e)}")


@router.get("/users/{user_id}/stats", response_model=UserStats)
async def get_user_stats(
    user_id: str,
    admin_id: str = Depends(verify_admin_access)
) -> UserStats:
    """
    Get detailed statistics for a specific user.
    """
    try:
        from src.supabase_client import get_supabase_client
        
        supabase = get_supabase_client()
        
        # Verify user exists
        user_result = supabase.table('users')\
            .select('id, created_at')\
            .eq('id', user_id)\
            .execute()
        
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user_result.data[0]
        
        # Get detailed user statistics
        flashcards_result = supabase.table('flashcards')\
            .select('id', count='exact')\
            .eq('user_id', user_id)\
            .execute()
        flashcards_count = flashcards_result.count or 0
        
        documents_result = supabase.table('documents')\
            .select('document_id', count='exact')\
            .eq('user_id', user_id)\
            .execute()
        documents_count = documents_result.count or 0
        
        reviews_result = supabase.table('flashcard_reviews')\
            .select('id, review_date', count='exact')\
            .eq('user_id', user_id)\
            .order('review_date', desc=True)\
            .limit(1)\
            .execute()
        
        reviews_count = reviews_result.count or 0
        last_activity = None
        if reviews_result.data:
            last_activity = datetime.fromisoformat(reviews_result.data[0]['review_date'].replace('Z', '+00:00'))
        
        return UserStats(
            user_id=user_id,
            flashcards_count=flashcards_count,
            documents_count=documents_count,
            reviews_count=reviews_count,
            last_activity=last_activity,
            created_at=datetime.fromisoformat(user['created_at'].replace('Z', '+00:00')) if user.get('created_at') else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        if is_development_mode():
            # Return demo stats in development mode
            return UserStats(
                user_id=user_id,
                flashcards_count=25,
                documents_count=3,
                reviews_count=75,
                last_activity=datetime.now() - timedelta(hours=5),
                created_at=datetime.now() - timedelta(days=20)
            )
        else:
            raise HTTPException(status_code=500, detail=f"Failed to fetch user stats: {str(e)}")


@router.get("/health")
async def admin_health_check(
    admin_id: str = Depends(verify_admin_access)
) -> Dict[str, Any]:
    """
    Admin health check with system overview.
    """
    try:
        from src.supabase_client import get_supabase_client
        from src.weaviate_client import create_weaviate_client
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "admin_id": admin_id,
            "services": {
                "supabase": "unknown",
                "weaviate": "unknown"
            },
            "environment": "development" if is_development_mode() else "production"
        }
        
        # Check Supabase connection
        try:
            supabase = get_supabase_client()
            supabase.table('flashcards').select('id').limit(1).execute()
            status["services"]["supabase"] = "healthy"
        except Exception as e:
            status["services"]["supabase"] = f"error: {str(e)[:50]}"
        
        # Check Weaviate connection
        try:
            weaviate_client = create_weaviate_client()
            if weaviate_client.health_check():
                status["services"]["weaviate"] = "healthy"
            else:
                status["services"]["weaviate"] = "unhealthy"
            weaviate_client.close()
        except Exception as e:
            status["services"]["weaviate"] = f"error: {str(e)[:50]}"
        
        return status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Admin health check failed: {str(e)}")