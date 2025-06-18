"""
User profile and statistics API routes
"""

from typing import List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException

from api.core.dependencies import get_current_user_id


router = APIRouter()


@router.get("/profile")
async def get_user_profile(
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """
    Get user profile information.

    Args:
        user_id: Authenticated user ID

    Returns:
        User profile data
    """
    try:
        # Return basic user profile structure
        # In production, this would come from a user database
        profile = {
            "user_id": user_id,
            "email": "user@example.com",  # Would come from JWT/Supabase user data
            "display_name": "StudyWise User",
            "created_at": datetime.utcnow().isoformat(),
            "last_login": datetime.utcnow().isoformat(),
            "preferences": {
                "study_reminders": True,
                "email_notifications": True,
                "difficulty_preference": "intermediate",
                "daily_goal": 20  # flashcards per day
            },
            "subscription": {
                "plan": "free",
                "features": ["basic_flashcards", "ai_chat", "document_upload"]
            }
        }
        
        return profile
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user profile: {str(e)}"
        )


@router.get("/stats")
async def get_user_stats(
    user_id: str = Depends(get_current_user_id)
) -> dict:
    """
    Get user's learning statistics.

    Args:
        user_id: Authenticated user ID

    Returns:
        Comprehensive learning statistics
    """
    # TODO: Calculate real user learning statistics
    # For now, return demo data that matches frontend expectations
    return {
        "user_id": user_id,
        "total_study_time": 150,  # minutes
        "conversations_count": 5,
        "flashcards_studied": 23,
        "accuracy_rate": 0.78,
        "current_streak": 3,
        "weekly_goal_progress": 0.6,
        "favorite_topics": ["Machine Learning", "Python", "Data Science"],
        "recent_activity": [
            {
                "type": "conversation",
                "topic": "Neural Networks",
                "timestamp": "2025-05-30T10:30:00Z"
            },
            {
                "type": "flashcard_study",
                "cards_reviewed": 5,
                "timestamp": "2025-05-30T09:15:00Z"
            }
        ]
    }


@router.get("/conversations")
async def get_user_conversations(
    user_id: str = Depends(get_current_user_id)
) -> List[Dict[str, Any]]:
    """
    Get user's conversation list.

    Args:
        user_id: Authenticated user ID

    Returns:
        List of user's conversations
    """
    try:
        # Return basic conversation list structure
        # In production, this would query the conversations database
        conversations = [
            {
                "conversation_id": "conv-001",
                "title": "Machine Learning Discussion",
                "topic_focus": "Neural Networks",
                "created_at": datetime.utcnow().isoformat(),
                "last_message_at": datetime.utcnow().isoformat(),
                "message_count": 8,
                "status": "active"
            },
            {
                "conversation_id": "conv-002", 
                "title": "Python Programming Help",
                "topic_focus": "Data Structures",
                "created_at": datetime.utcnow().isoformat(),
                "last_message_at": datetime.utcnow().isoformat(),
                "message_count": 5,
                "status": "active"
            }
        ]
        
        return conversations
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user conversations: {str(e)}"
        )
