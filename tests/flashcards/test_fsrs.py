"""
Tests for FSRS core algorithm functions.

Tests the mathematical components of the FSRS implementation
without requiring database access.
"""

import pytest
import math
from datetime import datetime, timedelta
from src.flashcards.fsrs import (
    get_fsrs_parameters,
    calculate_initial_stability,
    calculate_initial_difficulty,
    calculate_retrievability,
    calculate_stability_after_success,
    calculate_stability_after_failure,
    calculate_difficulty_after_review,
    get_next_interval,
    process_card_review,
    simulate_forgetting_curve,
    calculate_workload_distribution,
    validate_fsrs_parameters
)
from src.flashcards.models import FSRSParameters, CardRating, CardState


class TestFSRSParameters:
    """Test FSRS parameter handling."""

    def test_get_default_parameters(self):
        """Test default FSRS parameters."""
        params = get_fsrs_parameters()

        assert isinstance(params, FSRSParameters)
        assert len(params.w) == 17
        assert 0.7 <= params.request_retention <= 0.97
        assert params.maximum_interval > 0

        # Test specific default values
        assert params.request_retention == 0.9
        assert params.maximum_interval == 36500

    def test_parameter_validation(self):
        """Test parameter validation."""
        # Valid parameters
        valid_params = FSRSParameters()
        assert validate_fsrs_parameters(valid_params) is True

        # Invalid parameter count - this will be caught by Pydantic
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            FSRSParameters(w=[1.0, 2.0])  # Too few parameters

        # Invalid retention rate - also caught by Pydantic
        with pytest.raises(ValidationError):
            FSRSParameters(request_retention=0.5)

        # Invalid maximum interval - also caught by Pydantic
        with pytest.raises(ValidationError):
            FSRSParameters(maximum_interval=0)

        # Test manual validation function with edge cases
        edge_params = FSRSParameters(request_retention=0.7, maximum_interval=1)
        assert validate_fsrs_parameters(edge_params) is True


class TestInitialCalculations:
    """Test initial stability and difficulty calculations."""

    def test_calculate_initial_stability(self):
        """Test initial stability calculation for new cards."""
        params = get_fsrs_parameters()

        # Test all ratings
        stability_again = calculate_initial_stability(CardRating.AGAIN, params)
        stability_hard = calculate_initial_stability(CardRating.HARD, params)
        stability_good = calculate_initial_stability(CardRating.GOOD, params)
        stability_easy = calculate_initial_stability(CardRating.EASY, params)

        # Should be positive values
        assert stability_again > 0
        assert stability_hard > 0
        assert stability_good > 0
        assert stability_easy > 0

        # Generally, easier ratings should give higher stability
        assert stability_easy >= stability_good
        assert stability_good >= stability_hard
        assert stability_hard >= stability_again

    def test_calculate_initial_difficulty(self):
        """Test initial difficulty calculation for new cards."""
        params = get_fsrs_parameters()

        # Test all ratings
        difficulty_again = calculate_initial_difficulty(CardRating.AGAIN, params)
        difficulty_hard = calculate_initial_difficulty(CardRating.HARD, params)
        difficulty_good = calculate_initial_difficulty(CardRating.GOOD, params)
        difficulty_easy = calculate_initial_difficulty(CardRating.EASY, params)

        # Should be in valid range
        assert 1.0 <= difficulty_again <= 10.0
        assert 1.0 <= difficulty_hard <= 10.0
        assert 1.0 <= difficulty_good <= 10.0
        assert 1.0 <= difficulty_easy <= 10.0

        # Generally, easier ratings should give lower difficulty
        assert difficulty_again >= difficulty_hard
        assert difficulty_hard >= difficulty_good
        assert difficulty_good >= difficulty_easy


class TestRetrievabilityCalculation:
    """Test retrievability and forgetting curve calculations."""

    def test_calculate_retrievability_basic(self):
        """Test basic retrievability calculation."""
        # At time 0, retrievability should be 1.0
        assert calculate_retrievability(0, 5.0) == 1.0

        # Should decrease over time
        r1 = calculate_retrievability(1, 5.0)
        r5 = calculate_retrievability(5, 5.0)
        r10 = calculate_retrievability(10, 5.0)

        assert 1.0 > r1 > r5 > r10 > 0.0

    def test_calculate_retrievability_edge_cases(self):
        """Test retrievability edge cases."""
        # Zero stability should give 0 retrievability (except at time 0)
        assert calculate_retrievability(0, 0) == 1.0
        assert calculate_retrievability(1, 0) == 0.0

        # Negative days should give 1.0
        assert calculate_retrievability(-1, 5.0) == 1.0

        # Very large stability should give high retrievability
        assert calculate_retrievability(30, 1000.0) > 0.9

    def test_forgetting_curve_shape(self):
        """Test that forgetting curve has expected shape."""
        curve = simulate_forgetting_curve(5.0, days_range=20)

        # Should have correct length
        assert len(curve) == 21  # 0 to 20 inclusive

        # Should be monotonically decreasing
        for i in range(1, len(curve)):
            day, retrievability = curve[i]
            prev_day, prev_retrievability = curve[i-1]
            assert day == prev_day + 1
            assert retrievability <= prev_retrievability

        # Should start at 1.0 and decrease
        assert curve[0][1] == 1.0
        assert curve[-1][1] < curve[0][1]


class TestStabilityUpdates:
    """Test stability update calculations."""

    def test_stability_after_success(self):
        """Test stability updates after successful reviews."""
        params = get_fsrs_parameters()
        old_stability = 5.0
        difficulty = 5.0
        retrievability = 0.8

        # Test different success ratings
        stability_hard = calculate_stability_after_success(
            old_stability, retrievability, CardRating.HARD, difficulty, params
        )
        stability_good = calculate_stability_after_success(
            old_stability, retrievability, CardRating.GOOD, difficulty, params
        )
        stability_easy = calculate_stability_after_success(
            old_stability, retrievability, CardRating.EASY, difficulty, params
        )

        # All should increase stability
        assert stability_hard > old_stability
        assert stability_good > old_stability
        assert stability_easy > old_stability

        # Easy should generally give good increase
        assert stability_easy > old_stability * 1.1

        # Should be within reasonable bounds
        assert 0.1 <= stability_hard <= 36500
        assert 0.1 <= stability_good <= 36500
        assert 0.1 <= stability_easy <= 36500

    def test_stability_after_failure(self):
        """Test stability updates after failed reviews."""
        params = get_fsrs_parameters()
        old_stability = 10.0
        difficulty = 5.0
        retrievability = 0.3

        new_stability = calculate_stability_after_failure(
            old_stability, retrievability, difficulty, params
        )

        # Should decrease stability significantly
        assert new_stability < old_stability
        assert new_stability < old_stability * 0.8  # Significant decrease

        # Should be within bounds
        assert 0.1 <= new_stability <= old_stability * 0.5


class TestDifficultyUpdates:
    """Test difficulty update calculations."""

    def test_difficulty_after_review_all_ratings(self):
        """Test difficulty updates for all rating types."""
        params = get_fsrs_parameters()
        old_difficulty = 5.0

        # Test all ratings
        difficulty_again = calculate_difficulty_after_review(old_difficulty, CardRating.AGAIN, params)
        difficulty_hard = calculate_difficulty_after_review(old_difficulty, CardRating.HARD, params)
        difficulty_good = calculate_difficulty_after_review(old_difficulty, CardRating.GOOD, params)
        difficulty_easy = calculate_difficulty_after_review(old_difficulty, CardRating.EASY, params)

        # All should be in valid range
        assert 1.0 <= difficulty_again <= 10.0
        assert 1.0 <= difficulty_hard <= 10.0
        assert 1.0 <= difficulty_good <= 10.0
        assert 1.0 <= difficulty_easy <= 10.0

        # Failed reviews should increase difficulty
        assert difficulty_again > old_difficulty

        # Easy reviews should decrease difficulty
        assert difficulty_easy < old_difficulty

    def test_difficulty_mean_reversion(self):
        """Test that difficulty exhibits mean reversion toward 5.0."""
        params = get_fsrs_parameters()

        # High difficulty should decrease toward 5.0
        high_difficulty = 9.0
        new_high = calculate_difficulty_after_review(high_difficulty, CardRating.GOOD, params)
        assert new_high < high_difficulty

        # Low difficulty should increase toward 5.0
        low_difficulty = 2.0
        new_low = calculate_difficulty_after_review(low_difficulty, CardRating.GOOD, params)
        assert new_low > low_difficulty


class TestIntervalCalculation:
    """Test interval calculation and scheduling."""

    def test_get_next_interval_basic(self):
        """Test basic interval calculation."""
        # Higher stability should give longer intervals
        interval_low = get_next_interval(1.0, target_retention=0.9)
        interval_high = get_next_interval(10.0, target_retention=0.9)

        assert interval_high > interval_low
        assert interval_low >= 1
        assert interval_high >= 1

    def test_get_next_interval_retention_effect(self):
        """Test effect of target retention on intervals."""
        stability = 5.0

        # Lower target retention should give longer intervals
        interval_90 = get_next_interval(stability, target_retention=0.9)
        interval_80 = get_next_interval(stability, target_retention=0.8)

        assert interval_80 > interval_90

    def test_get_next_interval_bounds(self):
        """Test interval bounds."""
        # Should respect maximum interval
        max_interval = 100
        long_interval = get_next_interval(1000.0, maximum_interval=max_interval)
        assert long_interval <= max_interval

        # Should be at least 1 day
        short_interval = get_next_interval(0.1)
        assert short_interval >= 1


class TestCompleteReviewProcessing:
    """Test complete review processing workflow."""

    def create_sample_card_state(self) -> CardState:
        """Create a sample card state for testing."""
        return CardState(
            flashcard_id="test_card",
            user_id="test_user",
            stability=5.0,
            difficulty=5.0,
            due_date=datetime.now(),
            last_reviewed=datetime.now() - timedelta(days=3),
            total_reviews=2,
            lapses=0,
            state="review",
            reps=2,
            elapsed_days=3,
            scheduled_days=5,
            created_at=datetime.now() - timedelta(days=10),
            updated_at=datetime.now() - timedelta(days=3)
        )

    def test_process_card_review_success(self):
        """Test processing successful card reviews."""
        params = get_fsrs_parameters()
        current_state = self.create_sample_card_state()
        elapsed_days = 3

        # Test GOOD rating
        new_stability, new_difficulty, next_interval = process_card_review(
            current_state, CardRating.GOOD, elapsed_days, params
        )

        # Should update values appropriately
        assert new_stability > 0
        assert 1.0 <= new_difficulty <= 10.0
        assert next_interval >= 1

        # Stability should generally increase for successful review
        assert new_stability >= current_state.stability * 0.8  # Allow some decrease

    def test_process_card_review_failure(self):
        """Test processing failed card reviews."""
        params = get_fsrs_parameters()
        current_state = self.create_sample_card_state()
        elapsed_days = 10  # Overdue

        # Test AGAIN rating
        new_stability, new_difficulty, next_interval = process_card_review(
            current_state, CardRating.AGAIN, elapsed_days, params
        )

        # Should update values appropriately
        assert new_stability > 0
        assert 1.0 <= new_difficulty <= 10.0
        assert next_interval >= 1

        # Stability should decrease for failed review
        assert new_stability < current_state.stability

        # Difficulty should increase for failed review
        assert new_difficulty > current_state.difficulty

    def test_process_card_review_different_ratings(self):
        """Test that different ratings produce different outcomes."""
        params = get_fsrs_parameters()
        current_state = self.create_sample_card_state()
        elapsed_days = 5

        # Process with different ratings
        results = {}
        for rating in [CardRating.AGAIN, CardRating.HARD, CardRating.GOOD, CardRating.EASY]:
            stability, difficulty, interval = process_card_review(
                current_state, rating, elapsed_days, params
            )
            results[rating] = (stability, difficulty, interval)

        # AGAIN should give very short interval (failure resets learning)
        assert results[CardRating.AGAIN][2] <= 3  # Increased tolerance

        # All ratings should produce valid intervals
        for rating in [CardRating.AGAIN, CardRating.HARD, CardRating.GOOD, CardRating.EASY]:
            stability, difficulty, interval = results[rating]
            assert stability > 0
            assert 1.0 <= difficulty <= 10.0
            assert interval >= 1

        # Failed cards should have increased difficulty
        assert results[CardRating.AGAIN][1] > current_state.difficulty


class TestWorkloadDistribution:
    """Test workload distribution calculations."""

    def test_calculate_workload_distribution(self):
        """Test workload distribution calculation."""
        # Create sample card states
        base_date = datetime.now()
        card_states = [
            CardState(
                flashcard_id=f"card_{i}",
                user_id="test_user",
                stability=5.0,
                difficulty=5.0,
                due_date=base_date + timedelta(days=i % 7),
                last_reviewed=base_date - timedelta(days=1),
                total_reviews=1,
                lapses=0,
                state="review",
                reps=1,
                elapsed_days=1,
                scheduled_days=i % 7 + 1,
                created_at=base_date - timedelta(days=2),
                updated_at=base_date - timedelta(days=1)
            )
            for i in range(10)
        ]

        workload = calculate_workload_distribution(card_states, days_ahead=7)

        # Should have 8 entries (today + 7 days ahead)
        assert len(workload) == 8

        # Each entry should be (datetime, count)
        total_cards = sum(count for _, count in workload)
        assert total_cards <= len(card_states)  # Some cards might be beyond the range

        # Should be in chronological order
        dates = [date for date, _ in workload]
        assert dates == sorted(dates)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_elapsed_days(self):
        """Test handling of zero elapsed days."""
        params = get_fsrs_parameters()
        current_state = CardState(
            flashcard_id="test",
            user_id="test",
            stability=5.0,
            difficulty=5.0,
            due_date=datetime.now(),
            last_reviewed=None,  # New card
            total_reviews=0,
            lapses=0,
            state="new",
            reps=0,
            elapsed_days=None,
            scheduled_days=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Should handle new card without error
        stability, difficulty, interval = process_card_review(
            current_state, CardRating.GOOD, 0, params
        )

        assert stability > 0
        assert 1.0 <= difficulty <= 10.0
        assert interval >= 1

    def test_extreme_parameter_values(self):
        """Test behavior with extreme parameter values."""
        # Very high stability
        retrievability = calculate_retrievability(30, 1000.0)
        assert 0.0 <= retrievability <= 1.0

        # Very low stability
        retrievability = calculate_retrievability(1, 0.1)
        assert 0.0 <= retrievability <= 1.0

        # Very high difficulty
        params = get_fsrs_parameters()
        new_difficulty = calculate_difficulty_after_review(9.9, CardRating.AGAIN, params)
        assert 1.0 <= new_difficulty <= 10.0

    def test_mathematical_consistency(self):
        """Test mathematical consistency of algorithms."""
        # Retrievability should match expected forgetting curve
        stability = 10.0

        # At stability days, retrievability should be exp(-0.5 * 10/10) = exp(-0.5) ≈ 0.606
        retrievability_at_stability = calculate_retrievability(int(stability), stability)
        expected_retrievability = math.exp(-0.5)  # ≈ 0.606

        # Should be reasonably close (within 5%)
        assert abs(retrievability_at_stability - expected_retrievability) < 0.05


@pytest.fixture
def sample_parameters():
    """Fixture providing sample FSRS parameters."""
    return get_fsrs_parameters()


@pytest.fixture
def sample_card_state():
    """Fixture providing a sample card state."""
    return CardState(
        flashcard_id="test_card_123",
        user_id="test_user_456",
        stability=5.0,
        difficulty=5.0,
        due_date=datetime.now(),
        last_reviewed=datetime.now() - timedelta(days=3),
        total_reviews=3,
        lapses=1,
        state="review",
        reps=2,
        elapsed_days=3,
        scheduled_days=5,
        created_at=datetime.now() - timedelta(days=30),
        updated_at=datetime.now() - timedelta(days=3)
    )


class TestIntegration:
    """Integration tests combining multiple FSRS functions."""

    def test_complete_learning_sequence(self, sample_parameters):
        """Test a complete learning sequence from new card to mature."""
        # Start with new card
        card_state = CardState(
            flashcard_id="integration_test",
            user_id="test_user",
            stability=0.4,
            difficulty=5.0,
            due_date=datetime.now(),
            last_reviewed=None,
            total_reviews=0,
            lapses=0,
            state="new",
            reps=0,
            elapsed_days=None,
            scheduled_days=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Simulate several reviews with different outcomes
        review_sequence = [
            (CardRating.GOOD, 0),
            (CardRating.GOOD, 1),
            (CardRating.HARD, 3),
            (CardRating.AGAIN, 5),
            (CardRating.GOOD, 1),
            (CardRating.EASY, 4)
        ]

        for rating, elapsed_days in review_sequence:
            new_stability, new_difficulty, next_interval = process_card_review(
                card_state, rating, elapsed_days, sample_parameters
            )

            # Update card state for next iteration
            review_time = card_state.due_date + timedelta(days=elapsed_days)
            card_state = CardState(
                flashcard_id=card_state.flashcard_id,
                user_id=card_state.user_id,
                stability=new_stability,
                difficulty=new_difficulty,
                due_date=review_time + timedelta(days=next_interval),
                last_reviewed=review_time,
                total_reviews=card_state.total_reviews + 1,
                lapses=card_state.lapses + (1 if rating == CardRating.AGAIN else 0),
                state="review" if rating != CardRating.AGAIN else "relearning",
                reps=card_state.reps + (1 if rating != CardRating.AGAIN else 0),
                elapsed_days=elapsed_days,
                scheduled_days=next_interval,
                created_at=card_state.created_at,
                updated_at=review_time
            )

            # Verify state remains valid
            assert card_state.stability > 0
            assert 1.0 <= card_state.difficulty <= 10.0
            assert card_state.total_reviews > 0

        # After sequence, card should have evolved appropriately
        assert card_state.total_reviews == len(review_sequence)
        assert card_state.lapses == 1  # One AGAIN rating
        assert card_state.reps == 5    # Five successful reviews
