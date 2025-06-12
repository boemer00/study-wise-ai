"""
Pydantic models for flashcard API
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class FlashcardLevel(str, Enum):
    """Flashcard difficulty levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class FlashcardCreateRequest(BaseModel):
    """Request model for creating a flashcard."""

    question: str = Field(..., min_length=1, max_length=500, description="Flashcard question")
    answer: str = Field(..., min_length=1, max_length=2000, description="Flashcard answer")
    tags: Optional[List[str]] = Field(None, description="Flashcard tags")
    level: Optional[FlashcardLevel] = Field(FlashcardLevel.INTERMEDIATE, description="Difficulty level")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class FlashcardUpdateRequest(BaseModel):
    """Request model for updating a flashcard."""

    question: Optional[str] = Field(None, min_length=1, max_length=500, description="Flashcard question")
    answer: Optional[str] = Field(None, min_length=1, max_length=2000, description="Flashcard answer")
    tags: Optional[List[str]] = Field(None, description="Flashcard tags")
    level: Optional[FlashcardLevel] = Field(None, description="Difficulty level")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class FlashcardResponse(BaseModel):
    """Response model for flashcard data."""

    id: str = Field(..., description="Flashcard ID")
    question: str = Field(..., description="Flashcard question")
    answer: str = Field(..., description="Flashcard answer")
    tags: List[str] = Field(default_factory=list, description="Flashcard tags")
    level: FlashcardLevel = Field(..., description="Difficulty level")
    created_at: datetime = Field(..., description="Creation timestamp")
    user_id: str = Field(..., description="Owner user ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class FlashcardListResponse(BaseModel):
    """Response model for listing flashcards."""

    flashcards: List[FlashcardResponse] = Field(..., description="List of flashcards")
    total: int = Field(..., ge=0, description="Total flashcard count")
    has_more: bool = Field(..., description="Whether more flashcards exist")


class FlashcardReviewRequest(BaseModel):
    """Request model for recording a flashcard review."""

    correct: Optional[bool] = Field(None, description="Whether answer was correct (legacy)")
    response_time_seconds: Optional[float] = Field(None, ge=0, description="Response time")
    difficulty_rating: Optional[int] = Field(None, ge=1, le=4, description="FSRS difficulty rating 1-4 (1=Again, 2=Hard, 3=Good, 4=Easy)")
    notes: Optional[str] = Field(None, max_length=500, description="Review notes")

    @model_validator(mode='before')
    @classmethod
    def validate_rating_fields(cls, values):
        """Ensure either correct or difficulty_rating is provided."""
        if isinstance(values, dict):
            correct = values.get('correct')
            difficulty_rating = values.get('difficulty_rating')
            if correct is None and difficulty_rating is None:
                raise ValueError('Either correct or difficulty_rating must be provided')
        return values


class FlashcardReviewResponse(BaseModel):
    """Response model for flashcard review recording."""

    flashcard_id: str = Field(..., description="Flashcard ID")
    next_review_at: datetime = Field(..., description="Next scheduled review")
    easiness_factor: float = Field(..., ge=1.0, le=3.0, description="Spaced repetition easiness")
    correct_count: int = Field(..., ge=0, description="Total correct answers")
    incorrect_count: int = Field(..., ge=0, description="Total incorrect answers")
    streak: int = Field(..., ge=0, description="Current correct streak")


class FlashcardStats(BaseModel):
    """Model for flashcard statistics."""

    flashcard_id: str = Field(..., description="Flashcard ID")
    total_reviews: int = Field(..., ge=0, description="Total review count")
    correct_count: int = Field(..., ge=0, description="Correct answer count")
    incorrect_count: int = Field(..., ge=0, description="Incorrect answer count")
    accuracy_rate: float = Field(..., ge=0.0, le=1.0, description="Accuracy percentage")
    average_response_time: Optional[float] = Field(None, ge=0, description="Average response time")
    last_studied_at: Optional[datetime] = Field(None, description="Last study timestamp")
    next_review_at: Optional[datetime] = Field(None, description="Next review timestamp")
    easiness_factor: float = Field(..., ge=1.0, le=3.0, description="Spaced repetition factor")
    current_streak: int = Field(..., ge=0, description="Current correct streak")


class StudySessionRequest(BaseModel):
    """Request model for starting a study session."""

    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    level: Optional[FlashcardLevel] = Field(None, description="Filter by difficulty")
    max_cards: Optional[int] = Field(20, ge=1, le=100, description="Maximum cards in session")
    review_mode: Optional[str] = Field("spaced", description="Review mode (spaced/random/new)")


class StudySessionResponse(BaseModel):
    """Response model for study session."""

    session_id: str = Field(..., description="Study session ID")
    flashcards: List[FlashcardResponse] = Field(..., description="Flashcards for study")
    total_cards: int = Field(..., ge=0, description="Total cards in session")
    estimated_time_minutes: int = Field(..., ge=0, description="Estimated completion time")


class UserFlashcardStats(BaseModel):
    """Model for user's overall flashcard statistics."""

    total_flashcards: int = Field(..., ge=0, description="Total flashcard count")
    cards_due_today: int = Field(..., ge=0, description="Cards due for review today")
    total_reviews_today: int = Field(..., ge=0, description="Reviews completed today")
    accuracy_today: float = Field(..., ge=0.0, le=1.0, description="Today's accuracy rate")
    study_streak_days: int = Field(..., ge=0, description="Current study streak")
    total_study_time_minutes: int = Field(..., ge=0, description="Total study time")
    cards_by_level: Dict[str, int] = Field(default_factory=dict, description="Cards per difficulty level")
    upcoming_reviews: List[Dict[str, Any]] = Field(default_factory=list, description="Upcoming review schedule")
