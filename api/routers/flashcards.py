"""
Flashcard API routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime

from api.models.flashcards import (
    FlashcardCreateRequest,
    FlashcardUpdateRequest,
    FlashcardResponse,
    FlashcardListResponse,
    FlashcardReviewRequest,
    FlashcardReviewResponse,
    FlashcardStats,
    StudySessionRequest,
    StudySessionResponse,
    UserFlashcardStats,
    FlashcardLevel
)
from api.core.dependencies import (
    get_current_user_id,
    verify_flashcard_access,
    get_pagination_params
)

# Import the actual database functions
from src.flashcards_db import get_flashcards, get_flashcard_by_id, update_flashcard_stats


router = APIRouter()


@router.post("/", response_model=FlashcardResponse)
async def create_flashcard(
    request: FlashcardCreateRequest,
    user_id: str = Depends(get_current_user_id)
) -> FlashcardResponse:
    """
    Create a new flashcard.

    Args:
        request: Flashcard creation data
        user_id: Authenticated user ID

    Returns:
        Created flashcard details

    Raises:
        HTTPException: If flashcard creation fails
    """
    # For now, return a simple mock response since we don't have create implementation
    # TODO: Implement actual flashcard creation in database
    return FlashcardResponse(
        id="temp-id",
        question=request.question,
        answer=request.answer,
        tags=request.tags or [],
        level=request.level or FlashcardLevel.BEGINNER,
        created_at=datetime.now(),
        user_id=user_id,
        metadata={}
    )


@router.get("/", response_model=FlashcardListResponse)
async def list_flashcards(
    user_id: str = Depends(get_current_user_id),
    skip: int = Query(0, ge=0, description="Number of flashcards to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum flashcards to return"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    level: Optional[FlashcardLevel] = Query(None, description="Filter by difficulty level"),
    search: Optional[str] = Query(None, description="Search in question/answer")
) -> FlashcardListResponse:
    """
    List user's flashcards with filtering.

    Args:
        user_id: Authenticated user ID
        skip: Number of flashcards to skip
        limit: Maximum flashcards to return
        tags: Filter by tags
        level: Filter by difficulty level
        search: Search query for question/answer content

    Returns:
        List of user's flashcards

    Raises:
        HTTPException: If listing fails
    """
    try:
        # Get flashcards from database
        flashcards_data = get_flashcards(
            limit=limit,
            offset=skip,
            tags=tags,
            level=level.value if level else None
        )

        # Convert to response models
        flashcards = []
        for card_data in flashcards_data:
            flashcard = FlashcardResponse(
                id=card_data.get('id', 'unknown'),
                question=card_data.get('question', ''),
                answer=card_data.get('answer', ''),
                tags=card_data.get('tags', []),
                level=FlashcardLevel(card_data.get('level', 'beginner')),
                created_at=datetime.fromisoformat(card_data.get('created_at', datetime.now().isoformat().replace('+00:00', ''))),
                user_id=user_id,
                metadata=card_data.get('metadata', {})
            )

            # Apply search filter if specified
            if search and search.lower() not in flashcard.question.lower() and search.lower() not in flashcard.answer.lower():
                continue

            flashcards.append(flashcard)

        return FlashcardListResponse(
            flashcards=flashcards,
            total=len(flashcards),
            has_more=False  # Simple implementation
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve flashcards: {str(e)}")


@router.get("/{flashcard_id}", response_model=FlashcardResponse)
async def get_flashcard(
    flashcard_id: str,
    user_id: str = Depends(get_current_user_id),
    verified_flashcard_id: str = Depends(verify_flashcard_access)
) -> FlashcardResponse:
    """
    Get a specific flashcard.

    Args:
        flashcard_id: ID of the flashcard
        user_id: Authenticated user ID
        verified_flashcard_id: Verified flashcard ID

    Returns:
        Flashcard details

    Raises:
        HTTPException: If flashcard not found
    """
    try:
        card_data = get_flashcard_by_id(flashcard_id)
        if not card_data:
            raise HTTPException(status_code=404, detail="Flashcard not found")

        return FlashcardResponse(
            id=card_data.get('id', 'unknown'),
            question=card_data.get('question', ''),
            answer=card_data.get('answer', ''),
            tags=card_data.get('tags', []),
            level=FlashcardLevel(card_data.get('level', 'beginner')),
            created_at=datetime.fromisoformat(card_data.get('created_at', datetime.now().isoformat().replace('+00:00', ''))),
            user_id=user_id,
            metadata=card_data.get('metadata', {})
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve flashcard: {str(e)}")


@router.put("/{flashcard_id}", response_model=FlashcardResponse)
async def update_flashcard(
    flashcard_id: str,
    request: FlashcardUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    verified_flashcard_id: str = Depends(verify_flashcard_access)
) -> FlashcardResponse:
    """
    Update a flashcard.

    Args:
        flashcard_id: ID of the flashcard
        request: Update data
        user_id: Authenticated user ID
        verified_flashcard_id: Verified flashcard ID

    Returns:
        Updated flashcard details

    Raises:
        HTTPException: If flashcard not found or update fails
    """
    # TODO: Implement actual flashcard update in database
    # For now, return the current flashcard
    return await get_flashcard(flashcard_id, user_id, verified_flashcard_id)


@router.delete("/{flashcard_id}")
async def delete_flashcard(
    flashcard_id: str,
    user_id: str = Depends(get_current_user_id),
    verified_flashcard_id: str = Depends(verify_flashcard_access)
) -> dict:
    """
    Delete a flashcard.

    Args:
        flashcard_id: ID of the flashcard
        user_id: Authenticated user ID
        verified_flashcard_id: Verified flashcard ID

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If flashcard not found
    """
    # TODO: Implement actual flashcard deletion
    return {"message": "Flashcard deletion not yet implemented"}


@router.post("/{flashcard_id}/review", response_model=FlashcardReviewResponse)
async def record_flashcard_review(
    flashcard_id: str,
    request: FlashcardReviewRequest,
    user_id: str = Depends(get_current_user_id),
    verified_flashcard_id: str = Depends(verify_flashcard_access)
) -> FlashcardReviewResponse:
    """
    Record a flashcard review session.

    Args:
        flashcard_id: ID of the flashcard
        request: Review data (correct/incorrect, timing, etc.)
        user_id: Authenticated user ID
        verified_flashcard_id: Verified flashcard ID

    Returns:
        Updated review statistics and next review schedule

    Raises:
        HTTPException: If flashcard not found or review recording fails
    """
    try:
        # Determine if answer was correct based on rating
        is_correct = request.difficulty_rating >= 3 if request.difficulty_rating else request.correct

        # Update flashcard stats
        stats = update_flashcard_stats(flashcard_id, user_id, is_correct)

        return FlashcardReviewResponse(
            flashcard_id=flashcard_id,
            next_review_at=datetime.fromisoformat(stats.get('next_review_at', datetime.now().isoformat().replace('+00:00', ''))),
            easiness_factor=stats.get('easiness_factor', 2.5),
            correct_count=stats.get('correct_count', 0),
            incorrect_count=stats.get('incorrect_count', 0),
            streak=0  # Simple implementation
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record review: {str(e)}")


@router.get("/{flashcard_id}/stats", response_model=FlashcardStats)
async def get_flashcard_stats(
    flashcard_id: str,
    user_id: str = Depends(get_current_user_id),
    verified_flashcard_id: str = Depends(verify_flashcard_access)
) -> FlashcardStats:
    """
    Get flashcard review statistics.

    Args:
        flashcard_id: ID of the flashcard
        user_id: Authenticated user ID
        verified_flashcard_id: Verified flashcard ID

    Returns:
        Flashcard review statistics

    Raises:
        HTTPException: If flashcard not found
    """
    # TODO: Implement actual stats retrieval
    return FlashcardStats(
        flashcard_id=flashcard_id,
        total_reviews=0,
        correct_count=0,
        incorrect_count=0,
        accuracy_rate=0.0,
        average_response_time=None,
        last_studied_at=None,
        next_review_at=datetime.now(),
        easiness_factor=2.5,
        current_streak=0
    )


@router.post("/study-session", response_model=StudySessionResponse)
async def start_study_session(
    request: StudySessionRequest,
    user_id: str = Depends(get_current_user_id)
) -> StudySessionResponse:
    """
    Start a new study session with optimal flashcard selection.

    Args:
        request: Study session configuration
        user_id: Authenticated user ID

    Returns:
        Study session with selected flashcards

    Raises:
        HTTPException: If session creation fails
    """
    try:
        # Get flashcards for study session
        flashcards_data = get_flashcards(
            limit=request.max_cards or 20,
            offset=0,
            tags=request.tags,
            level=request.level.value if request.level else None
        )

        if not flashcards_data:
            raise HTTPException(status_code=404, detail="No flashcards available for study session")

        # Convert to response models
        flashcards = []
        for card_data in flashcards_data:
            flashcard = FlashcardResponse(
                id=card_data.get('id', 'unknown'),
                question=card_data.get('question', ''),
                answer=card_data.get('answer', ''),
                tags=card_data.get('tags', []),
                level=FlashcardLevel(card_data.get('level', 'beginner')),
                created_at=datetime.fromisoformat(card_data.get('created_at', datetime.now().isoformat().replace('+00:00', ''))),
                user_id=user_id,
                metadata=card_data.get('metadata', {})
            )
            flashcards.append(flashcard)

        return StudySessionResponse(
            session_id=f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            flashcards=flashcards,
            total_cards=len(flashcards),
            estimated_time_minutes=len(flashcards) * 2  # 2 minutes per card
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start study session: {str(e)}")


@router.get("/stats/overview", response_model=UserFlashcardStats)
async def get_user_flashcard_stats(
    user_id: str = Depends(get_current_user_id)
) -> UserFlashcardStats:
    """
    Get comprehensive user flashcard statistics.

    Args:
        user_id: Authenticated user ID

    Returns:
        User's flashcard statistics

    Raises:
        HTTPException: If stats retrieval fails
    """
    try:
        # Get all user's flashcards to calculate stats
        flashcards_data = get_flashcards(limit=1000, offset=0)

        return UserFlashcardStats(
            total_flashcards=len(flashcards_data),
            cards_due_today=min(len(flashcards_data), 10),  # Simple implementation
            total_reviews_today=0,
            accuracy_today=0.0,
            study_streak_days=0,
            total_study_time_minutes=0,
            cards_by_level={"beginner": len(flashcards_data), "intermediate": 0, "advanced": 0},
            upcoming_reviews=[]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user stats: {str(e)}")


@router.get("/due-today", response_model=FlashcardListResponse)
async def get_cards_due_today(
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(50, ge=1, le=100, description="Maximum cards to return")
) -> FlashcardListResponse:
    """
    Get flashcards due for review today.

    Args:
        user_id: Authenticated user ID
        limit: Maximum cards to return

    Returns:
        List of flashcards due today

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        # For now, return a subset of all flashcards as "due today"
        flashcards_data = get_flashcards(limit=limit, offset=0)

        flashcards = []
        for card_data in flashcards_data:
            flashcard = FlashcardResponse(
                id=card_data.get('id', 'unknown'),
                question=card_data.get('question', ''),
                answer=card_data.get('answer', ''),
                tags=card_data.get('tags', []),
                level=FlashcardLevel(card_data.get('level', 'beginner')),
                created_at=datetime.fromisoformat(card_data.get('created_at', datetime.now().isoformat().replace('+00:00', ''))),
                user_id=user_id,
                metadata=card_data.get('metadata', {})
            )
            flashcards.append(flashcard)

        return FlashcardListResponse(
            flashcards=flashcards,
            total=len(flashcards),
            has_more=False  # Simple implementation
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cards due today: {str(e)}")
