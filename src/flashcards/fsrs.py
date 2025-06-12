"""
FSRS (Free Spaced Repetition Scheduler) core algorithm implementation.

This module contains the pure mathematical functions that implement the FSRS algorithm.
Based on the research paper and implementation at: https://github.com/open-spaced-repetition/fsrs4anki

The FSRS algorithm models human memory using a three-component model:
- Stability (S): How long a memory can be retained before forgetting
- Difficulty (D): How hard a card is to remember (1-10 scale)
- Retrievability (R): Current probability of successful recall (0-1)
"""

import math
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from .models import FSRSParameters, CardRating, CardState


def get_fsrs_parameters() -> FSRSParameters:
    """
    Get default FSRS parameters.

    These are the default parameters optimized from a large dataset.
    Can be personalized for individual users with sufficient data.

    Returns:
        FSRSParameters: Default FSRS algorithm parameters
    """
    return FSRSParameters()


def calculate_initial_stability(rating: CardRating, parameters: FSRSParameters) -> float:
    """
    Calculate initial stability for a new card based on first rating.

    Args:
        rating: User's rating for the first review
        parameters: FSRS algorithm parameters

    Returns:
        float: Initial stability in days
    """
    w = parameters.w

    # Map ratings to initial stability using parameters w[0-3]
    if rating == CardRating.AGAIN:
        return w[0]
    elif rating == CardRating.HARD:
        return w[1]
    elif rating == CardRating.GOOD:
        return w[2]
    elif rating == CardRating.EASY:
        return w[3]
    else:
        return w[2]  # Default to GOOD


def calculate_initial_difficulty(rating: CardRating, parameters: FSRSParameters) -> float:
    """
    Calculate initial difficulty for a new card.

    Args:
        rating: User's rating for the first review
        parameters: FSRS algorithm parameters

    Returns:
        float: Initial difficulty (1-10 scale)
    """
    w = parameters.w

    # Initial difficulty based on rating
    # Higher rating = lower difficulty
    if rating == CardRating.EASY:
        difficulty = w[4] - 2.0
    elif rating == CardRating.GOOD:
        difficulty = w[4]
    elif rating == CardRating.HARD:
        difficulty = w[4] + 1.0
    else:  # AGAIN
        difficulty = w[4] + 2.0

    # Clamp to valid range
    return max(1.0, min(10.0, difficulty))


def calculate_retrievability(
    elapsed_days: int,
    stability: float,
    decay_factor: float = -0.5
) -> float:
    """
    Calculate current retrievability based on forgetting curve.

    Uses exponential decay: R = exp(decay_factor * elapsed_days / stability)

    Args:
        elapsed_days: Days since last review
        stability: Current memory stability
        decay_factor: Decay rate parameter (default -0.5)

    Returns:
        float: Retrievability probability (0-1)
    """
    if elapsed_days <= 0:
        return 1.0

    if stability <= 0:
        return 0.0

    # Forgetting curve formula: R = exp(decay_factor * t / S)
    exponent = decay_factor * elapsed_days / stability
    retrievability = math.exp(exponent)

    # Clamp to valid range
    return max(0.0, min(1.0, retrievability))


def calculate_stability_after_success(
    old_stability: float,
    retrievability: float,
    rating: CardRating,
    difficulty: float,
    parameters: FSRSParameters
) -> float:
    """
    Calculate new stability after successful recall.

    Args:
        old_stability: Previous stability value
        retrievability: Retrievability at time of review
        rating: User's rating (HARD, GOOD, or EASY)
        difficulty: Current card difficulty
        parameters: FSRS algorithm parameters

    Returns:
        float: New stability value
    """
    w = parameters.w

    # Base stability increase factor
    if rating == CardRating.HARD:
        # Hard recall gets smaller increase
        stability_increase = w[5]
    elif rating == CardRating.GOOD:
        # Good recall gets standard increase
        stability_increase = w[6]
    elif rating == CardRating.EASY:
        # Easy recall gets larger increase
        stability_increase = w[7]
    else:
        # Should not happen for success, but handle gracefully
        stability_increase = w[6]

    # Calculate new stability based on FSRS formula
    # S' = S * (exp(w[8]) * (11 - D) * S^(-w[9]) * (exp(w[10] * (1 - R)) - 1) * SInc + 1)
    difficulty_factor = (11 - difficulty) * (old_stability ** (-w[9]))
    retrievability_factor = math.exp(w[10] * (1 - retrievability)) - 1

    stability_multiplier = (
        math.exp(w[8]) *
        difficulty_factor *
        retrievability_factor *
        stability_increase + 1
    )

    new_stability = old_stability * stability_multiplier

    # Apply reasonable bounds
    return max(0.1, min(36500.0, new_stability))


def calculate_stability_after_failure(
    old_stability: float,
    retrievability: float,
    difficulty: float,
    parameters: FSRSParameters
) -> float:
    """
    Calculate new stability after failed recall (AGAIN rating).

    Args:
        old_stability: Previous stability value
        retrievability: Retrievability at time of review
        difficulty: Current card difficulty
        parameters: FSRS algorithm parameters

    Returns:
        float: New stability value (typically much lower)
    """
    w = parameters.w

    # Failure causes significant stability decrease
    # S' = w[11] * D^(-w[12]) * ((S + 1)^(w[13]) - 1) * exp(w[14] * (1 - R))
    difficulty_factor = difficulty ** (-w[12])
    stability_factor = (old_stability + 1) ** w[13] - 1
    retrievability_factor = math.exp(w[14] * (1 - retrievability))

    new_stability = w[11] * difficulty_factor * stability_factor * retrievability_factor

    # Apply reasonable bounds (failure should reduce stability significantly)
    return max(0.1, min(old_stability * 0.5, new_stability))


def calculate_difficulty_after_review(
    old_difficulty: float,
    rating: CardRating,
    parameters: FSRSParameters
) -> float:
    """
    Calculate new difficulty after any review.

    Args:
        old_difficulty: Previous difficulty value
        rating: User's rating
        parameters: FSRS algorithm parameters

    Returns:
        float: New difficulty value (1-10 scale)
    """
    w = parameters.w

    # Difficulty adjustment based on rating
    if rating == CardRating.AGAIN:
        # Failed recall increases difficulty
        difficulty_change = w[6] * 0.5
    elif rating == CardRating.HARD:
        # Hard recall slightly increases difficulty
        difficulty_change = w[6] * 0.2
    elif rating == CardRating.GOOD:
        # Good recall slightly decreases difficulty
        difficulty_change = -w[6] * 0.1
    elif rating == CardRating.EASY:
        # Easy recall decreases difficulty more
        difficulty_change = -w[6] * 0.3
    else:
        difficulty_change = 0

    new_difficulty = old_difficulty + difficulty_change

    # Apply mean reversion toward 5.0
    mean_reversion = 0.1
    new_difficulty = new_difficulty + mean_reversion * (5.0 - new_difficulty)

    # Clamp to valid range
    return max(1.0, min(10.0, new_difficulty))


def get_next_interval(
    stability: float,
    target_retention: float = 0.9,
    maximum_interval: int = 36500
) -> int:
    """
    Calculate next review interval based on stability and target retention.

    Args:
        stability: Current memory stability
        target_retention: Desired retention probability (0-1)
        maximum_interval: Maximum allowed interval in days

    Returns:
        int: Next review interval in days
    """
    if stability <= 0:
        return 1

    # Calculate interval where retrievability would equal target retention
    # R = exp(-0.5 * t/S)
    # target_retention = exp(-0.5 * t/S)
    # ln(target_retention) = -0.5 * t/S
    # t = -S * ln(target_retention) / 0.5
    # t = S * ln(target_retention) / (-0.5)

    if target_retention <= 0 or target_retention >= 1:
        target_retention = 0.9

    ln_retention = math.log(target_retention)
    interval = stability * ln_retention / (-0.5)

    # Apply bounds
    interval = max(1, int(round(interval)))
    interval = min(maximum_interval, interval)

    return interval


def process_card_review(
    current_state: CardState,
    rating: CardRating,
    elapsed_days: int,
    parameters: FSRSParameters
) -> Tuple[float, float, int]:
    """
    Process a single card review and calculate new parameters.

    This is the main FSRS function that updates stability, difficulty,
    and calculates the next review interval.

    Args:
        current_state: Current card state
        rating: User's rating for this review
        elapsed_days: Days since last review
        parameters: FSRS algorithm parameters

    Returns:
        Tuple[float, float, int]: (new_stability, new_difficulty, next_interval)
    """
    # Calculate current retrievability
    retrievability = calculate_retrievability(elapsed_days, current_state.stability)

    # Update stability based on rating
    if rating == CardRating.AGAIN:
        new_stability = calculate_stability_after_failure(
            current_state.stability, retrievability, current_state.difficulty, parameters
        )
    else:
        new_stability = calculate_stability_after_success(
            current_state.stability, retrievability, rating, current_state.difficulty, parameters
        )

    # Update difficulty
    new_difficulty = calculate_difficulty_after_review(
        current_state.difficulty, rating, parameters
    )

    # Calculate next interval
    next_interval = get_next_interval(
        new_stability, parameters.request_retention, parameters.maximum_interval
    )

    return new_stability, new_difficulty, next_interval


def optimize_parameters_for_user(
    review_history: List[dict],
    current_parameters: Optional[FSRSParameters] = None
) -> FSRSParameters:
    """
    Optimize FSRS parameters based on user's review history.

    This function uses machine learning to find optimal parameters
    for a specific user's learning patterns.

    Args:
        review_history: List of historical review data
        current_parameters: Starting parameters (uses defaults if None)

    Returns:
        FSRSParameters: Optimized parameters for this user
    """
    # For now, return default parameters
    # Full optimization requires complex ML algorithms
    if current_parameters is None:
        return get_fsrs_parameters()

    # Placeholder: In a full implementation, this would:
    # 1. Analyze review history patterns
    # 2. Use optimization algorithms (gradient descent, etc.)
    # 3. Find parameters that minimize prediction error
    # 4. Validate on held-out data

    return current_parameters


def simulate_forgetting_curve(
    stability: float,
    days_range: int = 30,
    decay_factor: float = -0.5
) -> List[Tuple[int, float]]:
    """
    Simulate forgetting curve for visualization.

    Args:
        stability: Memory stability value
        days_range: Number of days to simulate
        decay_factor: Decay rate parameter

    Returns:
        List[Tuple[int, float]]: List of (day, retrievability) pairs
    """
    curve_points = []

    for day in range(days_range + 1):
        retrievability = calculate_retrievability(day, stability, decay_factor)
        curve_points.append((day, retrievability))

    return curve_points


def calculate_workload_distribution(
    card_states: List[CardState],
    days_ahead: int = 30
) -> List[Tuple[datetime, int]]:
    """
    Calculate future review workload distribution.

    Args:
        card_states: List of all card states for a user
        days_ahead: Number of days to project

    Returns:
        List[Tuple[datetime, int]]: List of (date, cards_due) pairs
    """
    # Count cards due each day
    workload = {}
    base_date = datetime.now().date()

    for state in card_states:
        due_date = state.due_date.date()
        if due_date <= base_date + timedelta(days=days_ahead):
            if due_date not in workload:
                workload[due_date] = 0
            workload[due_date] += 1

    # Convert to sorted list
    result = []
    for i in range(days_ahead + 1):
        date = base_date + timedelta(days=i)
        count = workload.get(date, 0)
        result.append((datetime.combine(date, datetime.min.time()), count))

    return result


def validate_fsrs_parameters(parameters: FSRSParameters) -> bool:
    """
    Validate FSRS parameters for correctness.

    Args:
        parameters: FSRS parameters to validate

    Returns:
        bool: True if parameters are valid

    Raises:
        ValueError: If parameters are invalid
    """
    # Check parameter count
    if len(parameters.w) != 17:
        raise ValueError(f"FSRS requires exactly 17 parameters, got {len(parameters.w)}")

    # Check parameter ranges (basic validation)
    for i, param in enumerate(parameters.w):
        if not isinstance(param, (int, float)):
            raise ValueError(f"Parameter w[{i}] must be a number, got {type(param)}")
        if not (-10 <= param <= 100):  # Reasonable bounds
            raise ValueError(f"Parameter w[{i}] = {param} is outside reasonable range")

    # Check retention rate
    if not (0.7 <= parameters.request_retention <= 0.97):
        raise ValueError(f"Retention rate {parameters.request_retention} must be between 0.7 and 0.97")

    # Check maximum interval
    if not (1 <= parameters.maximum_interval <= 36500):
        raise ValueError(f"Maximum interval {parameters.maximum_interval} must be between 1 and 36500 days")

    return True
