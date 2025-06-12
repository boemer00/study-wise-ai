"""
Flashcards module with FSRS (Free Spaced Repetition Scheduler) implementation.

This module provides advanced spaced repetition scheduling for flashcards,
replacing the legacy SM-2 implementation with modern FSRS algorithms.
"""

from .fsrs import (
    calculate_initial_stability,
    calculate_initial_difficulty,
    calculate_retrievability,
    get_next_interval,
    get_fsrs_parameters,
    process_card_review,
    simulate_forgetting_curve
)

from .scheduler import (
    review_card,
    get_due_cards,
    get_card_state,
    schedule_new_card,
    update_card_parameters,
    get_scheduling_metrics,
    get_learning_forecast
)

from .models import (
    FSRSParameters,
    CardState,
    ReviewResult,
    CardRating
)

__all__ = [
    # FSRS Core Functions
    'calculate_initial_stability',
    'calculate_initial_difficulty',
    'calculate_retrievability',
    'get_next_interval',
    'get_fsrs_parameters',
    'process_card_review',
    'simulate_forgetting_curve',

    # Scheduler Functions
    'review_card',
    'get_due_cards',
    'get_card_state',
    'schedule_new_card',
    'update_card_parameters',
    'get_scheduling_metrics',
    'get_learning_forecast',

    # Models
    'FSRSParameters',
    'CardState',
    'ReviewResult',
    'CardRating'
]
