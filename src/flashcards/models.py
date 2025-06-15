"""
FSRS data models for flashcard spaced repetition scheduling.

This module defines the core data structures used in the FSRS algorithm
and flashcard scheduling system.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import IntEnum
from pydantic import BaseModel, Field


class CardRating(IntEnum):
    """
    Card rating scale used in FSRS algorithm.

    These ratings determine how the algorithm adjusts scheduling intervals.
    """
    AGAIN = 1    # Failed recall, needs immediate review
    HARD = 2     # Difficult recall, shorter interval
    GOOD = 3     # Normal recall, standard interval
    EASY = 4     # Easy recall, longer interval


class FSRSParameters(BaseModel):
    """
    FSRS algorithm parameters.

    These parameters control the behavior of the FSRS scheduling algorithm.
    They can be optimized based on user performance data.
    """
    # Memory model parameters
    w: List[float] = Field(
        default_factory=lambda: [
            0.4072, 1.1829, 3.1262, 15.4722, 7.2102, 0.5316, 1.0651, 0.0234,
            1.616, 0.1544, 0.9849, 2.18, 0.11, 5.0, 2.4, 1.0, 2.0
        ],
        description="FSRS weight parameters",
        min_length=17,
        max_length=17
    )

    # Scheduling constraints
    maximum_interval: int = Field(36500, ge=1, description="Maximum interval in days")
    request_retention: float = Field(0.9, ge=0.7, le=0.97, description="Target retention rate")

    # Optimization metadata
    version: str = Field("4.5", description="FSRS algorithm version")
    created_at: datetime = Field(default_factory=datetime.now, description="Parameters creation time")
    optimized_for_user: Optional[str] = Field(None, description="User ID if personalized")


class CardState(BaseModel):
    """
    Current state of a flashcard in the FSRS system.

    This represents all the data needed to schedule the next review
    of a specific flashcard for a specific user.
    """
    flashcard_id: str = Field(..., description="Flashcard identifier")
    user_id: str = Field(..., description="User identifier")

    # FSRS core state
    stability: float = Field(..., ge=0.1, description="Memory stability in days")
    difficulty: float = Field(..., ge=1.0, le=10.0, description="Card difficulty (1-10)")
    due_date: datetime = Field(..., description="Next review due date")

    # Review tracking
    last_reviewed: Optional[datetime] = Field(None, description="Last review timestamp")
    total_reviews: int = Field(0, ge=0, description="Total number of reviews")
    lapses: int = Field(0, ge=0, description="Number of times card was forgotten")

    # State metadata
    state: str = Field("new", description="Card state: new, learning, review, relearning")
    reps: int = Field(0, ge=0, description="Number of successful reviews")

    # Performance tracking
    elapsed_days: Optional[int] = Field(None, ge=0, description="Days since last review")
    scheduled_days: Optional[int] = Field(None, ge=0, description="Originally scheduled interval")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now, description="State creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")


class ReviewResult(BaseModel):
    """
    Result of processing a flashcard review.

    Contains the updated card state and scheduling information
    after a user reviews a flashcard.
    """
    # Input data
    flashcard_id: str = Field(..., description="Flashcard identifier")
    user_id: str = Field(..., description="User identifier")
    rating: CardRating = Field(..., description="User's rating for this review")
    review_time: datetime = Field(default_factory=datetime.now, description="When review occurred")

    # Updated state
    new_state: CardState = Field(..., description="Updated card state after review")

    # Scheduling info
    next_due_date: datetime = Field(..., description="Next review due date")
    interval_days: int = Field(..., ge=0, description="Interval until next review in days")

    # Performance metrics
    retrievability: float = Field(..., ge=0.0, le=1.0, description="Calculated retrievability at review time")
    previous_stability: Optional[float] = Field(None, description="Stability before this review")

    # Algorithm metadata
    fsrs_version: str = Field("4.5", description="FSRS version used")
    parameters_version: Optional[str] = Field(None, description="Parameters set version")


class BatchReviewRequest(BaseModel):
    """
    Request model for batch processing multiple flashcard reviews.

    Useful for processing study sessions with multiple cards.
    """
    user_id: str = Field(..., description="User identifier")
    reviews: List[Dict[str, Any]] = Field(
        ...,
        description="List of review data: {flashcard_id, rating, review_time}",
        min_items=1
    )
    session_id: Optional[str] = Field(None, description="Study session identifier")


class DueCardsFilter(BaseModel):
    """
    Filter criteria for retrieving due flashcards.

    Allows filtering cards by various criteria for study sessions.
    """
    user_id: str = Field(..., description="User identifier")
    limit: int = Field(20, ge=1, le=100, description="Maximum cards to return")

    # Filtering options
    tags: Optional[List[str]] = Field(None, description="Filter by card tags")
    difficulty_range: Optional[tuple[float, float]] = Field(None, description="Filter by difficulty range")
    overdue_only: bool = Field(False, description="Only return overdue cards")

    # Date constraints
    due_before: Optional[datetime] = Field(None, description="Cards due before this date")
    exclude_new: bool = Field(False, description="Exclude new (never reviewed) cards")


class SchedulingMetrics(BaseModel):
    """
    Metrics and analytics for flashcard scheduling performance.

    Provides insights into user learning patterns and algorithm effectiveness.
    """
    user_id: str = Field(..., description="User identifier")

    # Overall statistics
    total_cards: int = Field(..., ge=0, description="Total cards in system")
    cards_due_today: int = Field(..., ge=0, description="Cards due today")
    average_retention: float = Field(..., ge=0.0, le=1.0, description="Average retention rate")

    # Performance metrics
    average_difficulty: float = Field(..., ge=1.0, le=10.0, description="Average card difficulty")
    average_stability: float = Field(..., ge=0.0, description="Average memory stability")

    # Study patterns
    daily_review_count: int = Field(..., ge=0, description="Average daily reviews")
    study_streak: int = Field(..., ge=0, description="Current study streak in days")

    # Time-based metrics
    calculated_at: datetime = Field(default_factory=datetime.now, description="Metrics calculation time")
    period_start: datetime = Field(..., description="Start date for metrics period")
    period_end: datetime = Field(..., description="End date for metrics period")
