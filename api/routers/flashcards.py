"""
Flashcard API routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Form
from datetime import datetime, timedelta

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
    FlashcardLevel,
    FlashcardGenerateFromTextRequest,
    FlashcardGenerationResponse
)
from api.core.dependencies import (
    get_current_user_id,
    verify_flashcard_access,
    get_pagination_params
)

# Import the actual database functions
from src.flashcards_db import get_flashcards, get_flashcard_by_id, update_flashcard_stats, save_generated_flashcards
# Import FSRS system
from src.flashcards.scheduler import get_due_cards, get_scheduling_metrics, review_card, schedule_new_card
from src.flashcards.models import CardRating
# Import flashcard generator
from src.flashcard_generator import FlashcardGenerator


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


@router.get("/due-today", response_model=FlashcardListResponse)
async def get_cards_due_today(
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(50, ge=1, le=100, description="Maximum cards to return")
) -> FlashcardListResponse:
    """
    Get flashcards due for review today using FSRS scheduling.

    This endpoint prioritizes FSRS-scheduled cards and only falls back to new cards
    when there are no due cards available. If FSRS system fails completely,
    an error is returned rather than silently falling back to broken behavior.

    Args:
        user_id: Authenticated user ID
        limit: Maximum cards to return

    Returns:
        List of flashcards due today

    Raises:
        HTTPException: If retrieval fails or system is unavailable
    """
    try:
        # Use FSRS system to get due cards
        due_cards = get_due_cards(user_id, limit=limit)

        if not due_cards:
            # No cards due - this is a valid state, return empty list
            return FlashcardListResponse(
                flashcards=[],
                total=0,
                has_more=False
            )

        flashcards = []
        for card_data in due_cards:
            # Handle both regular flashcards (id) and FSRS cards (flashcard_id)
            card_id = card_data.get('flashcard_id') or card_data.get('id', 'unknown')

            flashcard = FlashcardResponse(
                id=card_id,
                question=card_data.get('question', ''),
                answer=card_data.get('answer', ''),
                tags=card_data.get('tags', []),
                level=FlashcardLevel(card_data.get('level', 'beginner')),
                created_at=datetime.fromisoformat(card_data.get('created_at') or datetime.now().isoformat().replace('+00:00', '')),
                user_id=user_id,
                metadata=card_data.get('metadata', {})
            )
            flashcards.append(flashcard)

        return FlashcardListResponse(
            flashcards=flashcards,
            total=len(flashcards),
            has_more=len(flashcards) >= limit  # More cards available if we hit the limit
        )
    except Exception as e:
        # Log the error for debugging but still return a meaningful error
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"FSRS system failed for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Flashcard scheduling system is currently unavailable. Please try again later."
        )


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
    Record a flashcard review session using FSRS scheduling.

    This endpoint uses a two-tier approach:
    1. Try to process review with existing FSRS state
    2. If card doesn't have FSRS state, initialize it first, then process review

    No silent fallbacks to broken legacy systems - if FSRS fails, return an error.

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
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Map difficulty_rating (1-4) to FSRS CardRating
        if request.difficulty_rating:
            # Frontend sends: 1=Again, 2=Hard, 3=Good, 4=Easy
            rating_map = {1: CardRating.AGAIN, 2: CardRating.HARD, 3: CardRating.GOOD, 4: CardRating.EASY}
            rating = rating_map.get(request.difficulty_rating, CardRating.GOOD)
        else:
            # Fallback for boolean correct field
            rating = CardRating.GOOD if request.correct else CardRating.AGAIN

        # Primary: Try to process review with existing FSRS state
        try:
            review_result = review_card(flashcard_id, user_id, rating)
            logger.info(f"Successfully processed FSRS review for card {flashcard_id}")

            return FlashcardReviewResponse(
                flashcard_id=flashcard_id,
                next_review_at=review_result.next_due_date,
                easiness_factor=2.5,  # Not used in FSRS, but required by API
                correct_count=0,  # Would need additional tracking
                incorrect_count=0,  # Would need additional tracking
                streak=0  # Would need additional tracking
            )

        except Exception as fsrs_error:
            # Secondary: If FSRS state doesn't exist, try to initialize it
            error_msg = str(fsrs_error).lower()
            if "not found" in error_msg or "no fsrs state" in error_msg:
                logger.info(f"No FSRS state found for card {flashcard_id}, initializing...")

                try:
                    # Initialize FSRS state for this card
                    card_state = schedule_new_card(flashcard_id, user_id)
                    logger.info(f"Successfully initialized FSRS state for card {flashcard_id}")

                    # Now process the review with the newly initialized state
                    review_result = review_card(flashcard_id, user_id, rating)
                    logger.info(f"Successfully processed review for newly initialized card {flashcard_id}")

                    return FlashcardReviewResponse(
                        flashcard_id=flashcard_id,
                        next_review_at=review_result.next_due_date,
                        easiness_factor=2.5,
                        correct_count=0,
                        incorrect_count=0,
                        streak=0
                    )

                except Exception as init_error:
                    logger.error(f"Failed to initialize FSRS state for card {flashcard_id}: {str(init_error)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to initialize flashcard for FSRS scheduling: {str(init_error)}"
                    )
            else:
                # This is a different kind of FSRS error, not related to missing state
                logger.error(f"FSRS processing failed for card {flashcard_id}: {str(fsrs_error)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Flashcard review processing failed: {str(fsrs_error)}"
                )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing review for card {flashcard_id}: {str(e)}")
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
                # Get FSRS scheduling metrics
        metrics = get_scheduling_metrics(user_id)

        # Get all user's flashcards to calculate total count
        flashcards_data = get_flashcards(limit=1000, offset=0)

        return UserFlashcardStats(
            total_flashcards=metrics.total_cards,
            cards_due_today=metrics.cards_due_today,
            total_reviews_today=metrics.daily_review_count,
            accuracy_today=metrics.average_retention,
            study_streak_days=metrics.study_streak,
            total_study_time_minutes=0,  # Not tracked yet
            cards_by_level={"beginner": len(flashcards_data), "intermediate": 0, "advanced": 0},
            upcoming_reviews=[]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user stats: {str(e)}")


def get_flashcard_generator() -> FlashcardGenerator:
    """Get FlashcardGenerator instance."""
    return FlashcardGenerator()


@router.post("/generate", response_model=FlashcardGenerationResponse)
async def generate_flashcards_from_text(
    text: str = Form(...),
    difficulty: str = Form("intermediate"),
    limit: int = Form(8),
    user_id: str = Depends(get_current_user_id),
    flashcard_gen: FlashcardGenerator = Depends(get_flashcard_generator)
) -> FlashcardGenerationResponse:
    """
    Generate flashcards from raw text input.
    
    This endpoint allows users to paste or type text content and
    automatically generate flashcards from it. Useful for creating
    flashcards from notes, articles, or any text content without
    needing to upload a file.
    
    Args:
        text: Text content to generate flashcards from
        difficulty: Difficulty level (beginner, intermediate, advanced)
        limit: Maximum number of flashcards to generate (1-20)
        user_id: Authenticated user ID
        flashcard_gen: Flashcard generator instance
        
    Returns:
        FlashcardGenerationResponse with generated flashcards
        
    Raises:
        HTTPException: If text is invalid or generation fails
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Validate text content
        text_content = text.strip()
        if len(text_content) < 50:
            raise HTTPException(
                status_code=400,
                detail="Text content is too short. Please provide at least 50 characters for meaningful flashcard generation."
            )
        
        if len(text_content) > 10000:
            raise HTTPException(
                status_code=400,
                detail="Text content is too long. Please limit to 10,000 characters for optimal processing."
            )
        
        # Validate difficulty level
        valid_difficulties = ['beginner', 'intermediate', 'advanced']
        if difficulty not in valid_difficulties:
            difficulty = 'intermediate'
        
        # Validate limit
        if limit < 1 or limit > 20:
            limit = 8
        
        # Split content into chunks for better processing
        content_chunks = [text_content[i:i+2000] for i in range(0, len(text_content), 2000)]
        
        try:
            # Generate flashcards using the flashcard generator
            generated_flashcards = flashcard_gen.generate(
                content_chunks[:5],  # Limit chunks for performance
                difficulty
            )
            
            # Limit to requested number of flashcards
            limited_flashcards = generated_flashcards[:limit]
            
            if not limited_flashcards:
                raise HTTPException(
                    status_code=400,
                    detail="Could not generate any flashcards from the provided text. Please try with different content."
                )
            
            # Save generated flashcards to database
            saved_flashcard_ids = []
            if limited_flashcards:
                try:
                    saved_flashcard_ids = save_generated_flashcards(
                        limited_flashcards,
                        user_id,
                        None  # No document ID for text-based generation
                    )
                    logger.info(f"Successfully saved {len(saved_flashcard_ids)} flashcards from text for user {user_id}")
                except Exception as save_error:
                    logger.warning(f"Failed to save flashcards from text for user {user_id}: {str(save_error)}")
                    # Continue anyway - flashcards were generated successfully
            
            # Convert to response format
            flashcard_responses = []
            for i, flashcard in enumerate(limited_flashcards):
                flashcard_id = saved_flashcard_ids[i] if i < len(saved_flashcard_ids) else f"temp-text-{i}"
                
                flashcard_response = FlashcardResponse(
                    id=flashcard_id,
                    question=flashcard.get('question', ''),
                    answer=flashcard.get('answer', ''),
                    tags=flashcard.get('tags', []),
                    level=FlashcardLevel(difficulty),
                    created_at=datetime.now(),
                    user_id=user_id,
                    metadata={
                        'source_type': 'text_input',
                        'generation_method': 'text_to_flashcards',
                        'text_length': len(text_content)
                    }
                )
                flashcard_responses.append(flashcard_response)
            
            return FlashcardGenerationResponse(
                flashcards=flashcard_responses,
                total_generated=len(flashcard_responses),
                source_type="text"
            )
            
        except Exception as gen_error:
            logger.error(f"Flashcard generation from text failed for user {user_id}: {str(gen_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate flashcards from text: {str(gen_error)}"
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating flashcards from text for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process text for flashcard generation: {str(e)}"
        )
