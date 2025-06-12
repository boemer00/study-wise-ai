"""
Tests for FSRS scheduler implementation.

Tests the database integration and scheduling functions.
These tests require a test database to be set up.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from src.flashcards.scheduler import (
    get_card_state,
    schedule_new_card,
    review_card,
    get_due_cards,
    get_overdue_cards,
    batch_review_cards,
    update_card_parameters,
    calculate_user_retention_rate,
    get_scheduling_metrics,
    reset_card_progress,
    get_learning_forecast,
    migrate_from_legacy_srs,
    validate_card_state,
    backup_scheduling_data,
    restore_scheduling_data
)
from src.flashcards.models import (
    CardState,
    CardRating,
    ReviewResult,
    BatchReviewRequest,
    DueCardsFilter,
    SchedulingMetrics
)


class TestCardStateManagement:
    """Test card state management functions."""

    @pytest.fixture
    def sample_user_id(self):
        """Fixture providing a test user ID."""
        return f"test_user_{uuid.uuid4()}"

    @pytest.fixture
    def sample_flashcard_id(self):
        """Fixture providing a test flashcard ID."""
        return f"test_card_{uuid.uuid4()}"

    @patch('src.flashcards.scheduler.get_supabase_client')
    def test_get_card_state_exists(self, mock_supabase, sample_user_id, sample_flashcard_id):
        """Test retrieving existing card state."""
        # Mock database response
        mock_client = Mock()
        mock_supabase.return_value = mock_client

        mock_data = {
            'flashcard_id': sample_flashcard_id,
            'user_id': sample_user_id,
            'stability': 5.0,
            'difficulty': 6.0,
            'due_date': '2024-01-15T10:00:00Z',
            'last_reviewed': '2024-01-10T10:00:00Z',
            'total_reviews': 3,
            'lapses': 1,
            'state': 'review',
            'reps': 2,
            'elapsed_days': 5,
            'scheduled_days': 5,
            'created_at': '2024-01-01T10:00:00Z',
            'updated_at': '2024-01-10T10:00:00Z'
        }

        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [mock_data]

        # Test retrieval
        card_state = get_card_state(sample_flashcard_id, sample_user_id)

        assert card_state is not None
        assert card_state.flashcard_id == sample_flashcard_id
        assert card_state.user_id == sample_user_id
        assert card_state.stability == 5.0
        assert card_state.difficulty == 6.0
        assert card_state.total_reviews == 3

    @patch('src.flashcards.scheduler.get_supabase_client')
    def test_get_card_state_not_exists(self, mock_supabase, sample_user_id, sample_flashcard_id):
        """Test retrieving non-existent card state."""
        # Mock empty database response
        mock_client = Mock()
        mock_supabase.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        # Test retrieval
        card_state = get_card_state(sample_flashcard_id, sample_user_id)

        assert card_state is None

    @patch('src.flashcards.scheduler.get_supabase_client')
    @patch('src.flashcards.scheduler.get_card_state')
    def test_schedule_new_card_success(self, mock_get_state, mock_supabase, sample_user_id, sample_flashcard_id):
        """Test scheduling a new card successfully."""
        # Mock that card doesn't exist yet
        mock_get_state.return_value = None

        # Mock database insertion
        mock_client = Mock()
        mock_supabase.return_value = mock_client
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [{'id': 'test_id'}]

        # Test scheduling
        card_state = schedule_new_card(sample_flashcard_id, sample_user_id)

        assert card_state.flashcard_id == sample_flashcard_id
        assert card_state.user_id == sample_user_id
        assert card_state.stability == 0.4
        assert card_state.difficulty == 5.0
        assert card_state.total_reviews == 0
        assert card_state.state == "new"

    @patch('src.flashcards.scheduler.get_card_state')
    def test_schedule_new_card_already_exists(self, mock_get_state, sample_user_id, sample_flashcard_id):
        """Test scheduling card that already exists."""
        # Mock existing card
        mock_get_state.return_value = Mock()

        # Should raise ValueError
        with pytest.raises(ValueError, match="already has FSRS state"):
            schedule_new_card(sample_flashcard_id, sample_user_id)


class TestCardReview:
    """Test card review processing."""

    @pytest.fixture
    def sample_card_state(self):
        """Fixture providing a sample card state."""
        return CardState(
            flashcard_id="test_card",
            user_id="test_user",
            stability=5.0,
            difficulty=5.0,
            due_date=datetime.now() - timedelta(days=1),  # Overdue
            last_reviewed=datetime.now() - timedelta(days=5),
            total_reviews=2,
            lapses=0,
            state="review",
            reps=2,
            elapsed_days=4,
            scheduled_days=4,
            created_at=datetime.now() - timedelta(days=30),
            updated_at=datetime.now() - timedelta(days=5)
        )

    @patch('src.flashcards.scheduler.get_supabase_client')
    @patch('src.flashcards.scheduler.get_card_state')
    def test_review_card_success(self, mock_get_state, mock_supabase, sample_card_state):
        """Test successful card review."""
        mock_get_state.return_value = sample_card_state

        # Mock database operations
        mock_client = Mock()
        mock_supabase.return_value = mock_client
        mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = Mock()
        mock_client.table.return_value.insert.return_value.execute.return_value = Mock()

        # Test review
        result = review_card(
            sample_card_state.flashcard_id,
            sample_card_state.user_id,
            CardRating.GOOD
        )

        assert isinstance(result, ReviewResult)
        assert result.flashcard_id == sample_card_state.flashcard_id
        assert result.user_id == sample_card_state.user_id
        assert result.rating == CardRating.GOOD
        assert result.new_state.total_reviews == sample_card_state.total_reviews + 1
        assert result.new_state.stability > 0
        assert 1.0 <= result.new_state.difficulty <= 10.0
        assert result.interval_days >= 1

    @patch('src.flashcards.scheduler.get_supabase_client')
    @patch('src.flashcards.scheduler.get_card_state')
    def test_review_card_failure(self, mock_get_state, mock_supabase, sample_card_state):
        """Test failed card review (AGAIN rating)."""
        mock_get_state.return_value = sample_card_state

        # Mock database operations
        mock_client = Mock()
        mock_supabase.return_value = mock_client
        mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = Mock()
        mock_client.table.return_value.insert.return_value.execute.return_value = Mock()

        # Test review with failure
        result = review_card(
            sample_card_state.flashcard_id,
            sample_card_state.user_id,
            CardRating.AGAIN
        )

        assert result.rating == CardRating.AGAIN
        assert result.new_state.lapses == sample_card_state.lapses + 1
        assert result.new_state.state == "relearning"
        assert result.new_state.stability < sample_card_state.stability  # Should decrease

    @patch('src.flashcards.scheduler.schedule_new_card')
    @patch('src.flashcards.scheduler.get_card_state')
    def test_review_new_card(self, mock_get_state, mock_schedule_new):
        """Test reviewing a card that doesn't exist yet."""
        # Mock that card doesn't exist
        mock_get_state.return_value = None

        # Mock new card creation
        new_card_state = CardState(
            flashcard_id="new_card",
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
        mock_schedule_new.return_value = new_card_state

        with patch('src.flashcards.scheduler.get_supabase_client') as mock_supabase:
            mock_client = Mock()
            mock_supabase.return_value = mock_client
            mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = Mock()
            mock_client.table.return_value.insert.return_value.execute.return_value = Mock()

            result = review_card("new_card", "test_user", CardRating.GOOD)

            assert result.new_state.total_reviews == 1
            mock_schedule_new.assert_called_once()


class TestDueCards:
    """Test due cards retrieval and filtering."""

    @patch('src.flashcards.scheduler.get_supabase_client')
    def test_get_due_cards_basic(self, mock_supabase):
        """Test getting due cards without filters."""
        # Mock database response
        mock_client = Mock()
        mock_supabase.return_value = mock_client

        mock_due_cards = [
            {
                'flashcard_id': 'card1',
                'user_id': 'user1',
                'stability': 5.0,
                'difficulty': 4.0,
                'due_date': '2024-01-15T10:00:00Z',
                'state': 'review'
            },
            {
                'flashcard_id': 'card2',
                'user_id': 'user1',
                'stability': 3.0,
                'difficulty': 6.0,
                'due_date': '2024-01-14T10:00:00Z',
                'state': 'review'
            }
        ]

        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value.data = mock_due_cards

        # Test retrieval
        due_cards = get_due_cards("user1", limit=10)

        assert len(due_cards) == 2
        assert due_cards[0]['flashcard_id'] == 'card1'
        assert due_cards[1]['flashcard_id'] == 'card2'

    @patch('src.flashcards.scheduler.get_supabase_client')
    def test_get_due_cards_with_filters(self, mock_supabase):
        """Test getting due cards with filters."""
        mock_client = Mock()
        mock_supabase.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        # Test with difficulty filter - provide required user_id
        filters = DueCardsFilter(user_id="user1", difficulty_range=(3.0, 7.0))
        due_cards = get_due_cards("user1", limit=10, filters=filters)

        # Should call with difficulty filters
        assert due_cards == []  # Simplified assertion

    @patch('src.flashcards.scheduler.get_supabase_client')
    def test_get_overdue_cards(self, mock_supabase):
        """Test getting overdue cards."""
        mock_client = Mock()
        mock_supabase.return_value = mock_client

        mock_overdue_cards = [
            {
                'flashcard_id': 'overdue1',
                'user_id': 'user1',
                'due_date': '2024-01-10T10:00:00Z',
                'stability': 5.0
            }
        ]

        mock_client.table.return_value.select.return_value.eq.return_value.lt.return_value.order.return_value.execute.return_value.data = mock_overdue_cards

        overdue_cards = get_overdue_cards("user1", days_overdue=2)

        assert len(overdue_cards) == 1
        assert overdue_cards[0]['flashcard_id'] == 'overdue1'


class TestBatchOperations:
    """Test batch review operations."""

    @patch('src.flashcards.scheduler.review_card')
    def test_batch_review_cards_success(self, mock_review_card):
        """Test successful batch review processing."""
        # Create a proper CardState for the ReviewResult
        new_state = CardState(
            flashcard_id="card1",
            user_id="user1",
            stability=5.0,
            difficulty=5.0,
            due_date=datetime.now() + timedelta(days=5),
            last_reviewed=datetime.now(),
            total_reviews=1,
            lapses=0,
            state="review",
            reps=1,
            elapsed_days=1,
            scheduled_days=5,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Mock individual review results
        mock_result = ReviewResult(
            flashcard_id="card1",
            user_id="user1",
            rating=CardRating.GOOD,
            review_time=datetime.now(),
            new_state=new_state,
            next_due_date=datetime.now() + timedelta(days=5),
            interval_days=5,
            retrievability=0.8,
            previous_stability=5.0,
            fsrs_version="4.5"
        )
        mock_review_card.return_value = mock_result

        # Create batch request
        batch_request = BatchReviewRequest(
            user_id="user1",
            reviews=[
                {
                    'flashcard_id': 'card1',
                    'rating': 3,  # GOOD
                    'review_time': datetime.now().isoformat()
                },
                {
                    'flashcard_id': 'card2',
                    'rating': 2,  # HARD
                }
            ]
        )

        results = batch_review_cards(batch_request)

        assert len(results) == 2
        assert all(isinstance(r, ReviewResult) for r in results)
        assert mock_review_card.call_count == 2

    @patch('src.flashcards.scheduler.review_card')
    def test_batch_review_cards_partial_failure(self, mock_review_card):
        """Test batch review with some failures."""
        # Mock one success, one failure
        def side_effect(flashcard_id, user_id, rating, review_time=None):
            if flashcard_id == 'card1':
                return Mock()
            else:
                raise ValueError("Card not found")

        mock_review_card.side_effect = side_effect

        batch_request = BatchReviewRequest(
            user_id="user1",
            reviews=[
                {'flashcard_id': 'card1', 'rating': 3},
                {'flashcard_id': 'card2', 'rating': 3}
            ]
        )

        results = batch_review_cards(batch_request)

        # Should return only successful reviews
        assert len(results) == 1


class TestParameterUpdates:
    """Test parameter update operations."""

    @patch('src.flashcards.scheduler.get_supabase_client')
    def test_update_card_parameters_success(self, mock_supabase):
        """Test successful parameter update."""
        mock_client = Mock()
        mock_supabase.return_value = mock_client
        mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{'id': 'updated'}]

        success = update_card_parameters(
            "card1", "user1",
            stability=10.0,
            difficulty=4.0,
            due_date=datetime.now()
        )

        assert success is True

    def test_update_card_parameters_invalid_stability(self):
        """Test parameter update with invalid stability."""
        with pytest.raises(ValueError, match="Stability .* must be between"):
            update_card_parameters(
                "card1", "user1",
                stability=0.0,  # Invalid
                difficulty=5.0,
                due_date=datetime.now()
            )

    def test_update_card_parameters_invalid_difficulty(self):
        """Test parameter update with invalid difficulty."""
        with pytest.raises(ValueError, match="Difficulty .* must be between"):
            update_card_parameters(
                "card1", "user1",
                stability=5.0,
                difficulty=15.0,  # Invalid
                due_date=datetime.now()
            )


class TestMetricsAndAnalytics:
    """Test metrics and analytics functions."""

    @patch('src.flashcards.scheduler.get_supabase_client')
    def test_calculate_user_retention_rate(self, mock_supabase):
        """Test retention rate calculation."""
        mock_client = Mock()
        mock_supabase.return_value = mock_client

        # Mock review history data
        mock_reviews = [
            {'rating': 3},  # GOOD
            {'rating': 2},  # HARD
            {'rating': 1},  # AGAIN
            {'rating': 4},  # EASY
            {'rating': 3}   # GOOD
        ]
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = mock_reviews

        retention_rate = calculate_user_retention_rate("user1", days_back=30)

        # 4 successful (rating >= 2) out of 5 total = 0.8
        assert retention_rate == 0.8

    @patch('src.flashcards.scheduler.get_supabase_client')
    @patch('src.flashcards.scheduler.calculate_user_retention_rate')
    def test_get_scheduling_metrics(self, mock_retention, mock_supabase):
        """Test scheduling metrics retrieval."""
        mock_client = Mock()
        mock_supabase.return_value = mock_client

        # Mock metrics data
        mock_metrics_data = {
            'total_cards': 100,
            'cards_due_today': 15,
            'avg_difficulty': 5.2,
            'avg_stability': 8.5
        }
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [mock_metrics_data]
        mock_retention.return_value = 0.85

        metrics = get_scheduling_metrics("user1")

        assert isinstance(metrics, SchedulingMetrics)
        assert metrics.total_cards == 100
        assert metrics.cards_due_today == 15
        assert metrics.average_retention == 0.85
        assert metrics.average_difficulty == 5.2
        assert metrics.average_stability == 8.5

    @patch('src.flashcards.scheduler.get_supabase_client')
    def test_get_learning_forecast(self, mock_supabase):
        """Test learning forecast calculation."""
        mock_client = Mock()
        mock_supabase.return_value = mock_client

        # Mock card states with various due dates
        base_date = datetime.now()
        mock_card_states = [
            {'due_date': base_date.isoformat()},  # Today
            {'due_date': (base_date + timedelta(days=1)).isoformat()},  # Tomorrow
            {'due_date': (base_date + timedelta(days=1)).isoformat()},  # Tomorrow (2nd card)
            {'due_date': (base_date + timedelta(days=3)).isoformat()},  # Day 3
        ]
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_card_states

        forecast = get_learning_forecast("user1", days_ahead=7)

        # Should return 8 entries (today + 7 days)
        assert len(forecast) == 8

        # Check that forecast is in chronological order
        dates = [date for date, count in forecast]
        assert dates == sorted(dates)

        # Check counts for specific days
        day_counts = {date.date(): count for date, count in forecast}
        assert day_counts[base_date.date()] == 1  # Today: 1 card
        assert day_counts[(base_date + timedelta(days=1)).date()] == 2  # Tomorrow: 2 cards


class TestUtilityFunctions:
    """Test utility and helper functions."""

    @patch('src.flashcards.scheduler.get_supabase_client')
    def test_reset_card_progress(self, mock_supabase):
        """Test resetting card progress."""
        mock_client = Mock()
        mock_supabase.return_value = mock_client
        mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{'id': 'reset'}]

        success = reset_card_progress("card1", "user1")

        assert success is True

        # Verify reset data was used
        call_args = mock_client.table.return_value.update.call_args[0][0]
        assert call_args['stability'] == 0.4
        assert call_args['difficulty'] == 5.0
        assert call_args['total_reviews'] == 0
        assert call_args['state'] == 'new'

    def test_validate_card_state_valid(self):
        """Test validation of valid card state."""
        valid_state = CardState(
            flashcard_id="test",
            user_id="test",
            stability=5.0,
            difficulty=5.0,
            due_date=datetime.now(),
            last_reviewed=datetime.now(),
            total_reviews=1,
            lapses=0,
            state="review",
            reps=1,
            elapsed_days=1,
            scheduled_days=5,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        assert validate_card_state(valid_state) is True

    def test_validate_card_state_invalid_stability(self):
        """Test validation with invalid stability."""
        invalid_state = CardState(
            flashcard_id="test",
            user_id="test",
            stability=50000.0,  # Too high
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

        with pytest.raises(ValueError, match="Stability .* must be between"):
            validate_card_state(invalid_state)

    def test_validate_card_state_invalid_difficulty(self):
        """Test validation with invalid difficulty."""
        # Create a valid state first, then manually modify it for testing
        valid_state = CardState(
            flashcard_id="test",
            user_id="test",
            stability=5.0,
            difficulty=5.0,  # Valid value initially
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

        # Manually set invalid difficulty to test our validation function
        valid_state.difficulty = 15.0  # Too high

        with pytest.raises(ValueError, match="Difficulty .* must be between"):
            validate_card_state(valid_state)

    def test_validate_card_state_negative_reviews(self):
        """Test validation with negative review counts."""
        # Create a valid state first, then manually modify it for testing
        valid_state = CardState(
            flashcard_id="test",
            user_id="test",
            stability=5.0,
            difficulty=5.0,
            due_date=datetime.now(),
            last_reviewed=None,
            total_reviews=0,  # Valid value initially
            lapses=0,
            state="new",
            reps=0,
            elapsed_days=None,
            scheduled_days=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Manually set invalid value to test our validation function
        valid_state.total_reviews = -1  # Invalid

        with pytest.raises(ValueError, match="Total reviews cannot be negative"):
            validate_card_state(valid_state)


class TestDataManagement:
    """Test data backup and migration functions."""

    @patch('src.flashcards.scheduler.get_supabase_client')
    def test_backup_scheduling_data(self, mock_supabase):
        """Test scheduling data backup."""
        mock_client = Mock()
        mock_supabase.return_value = mock_client

        # Mock database responses
        mock_states = [{'flashcard_id': 'card1', 'stability': 5.0}]
        mock_history = [{'rating': 3, 'review_time': '2024-01-15T10:00:00Z'}]
        mock_params = {'user_id': 'user1', 'w': [1.0, 2.0]}

        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_states

        # Different responses for different table calls
        def mock_table(table_name):
            mock_table_obj = Mock()
            if table_name == 'fsrs_card_states':
                mock_table_obj.select.return_value.eq.return_value.execute.return_value.data = mock_states
            elif table_name == 'fsrs_review_history':
                mock_table_obj.select.return_value.eq.return_value.execute.return_value.data = mock_history
            elif table_name == 'fsrs_parameters':
                mock_table_obj.select.return_value.eq.return_value.execute.return_value.data = [mock_params]
            return mock_table_obj

        mock_client.table.side_effect = mock_table

        backup_data = backup_scheduling_data("user1")

        assert backup_data['user_id'] == "user1"
        assert 'backup_date' in backup_data
        assert backup_data['card_states'] == mock_states
        assert backup_data['review_history'] == mock_history
        assert backup_data['parameters'] == mock_params

    @patch('src.flashcards.scheduler.get_supabase_client')
    def test_restore_scheduling_data_success(self, mock_supabase):
        """Test successful data restoration."""
        mock_client = Mock()
        mock_supabase.return_value = mock_client

        # Mock successful database operations
        mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = Mock()
        mock_client.table.return_value.insert.return_value.execute.return_value = Mock()
        mock_client.table.return_value.upsert.return_value.execute.return_value = Mock()

        backup_data = {
            'user_id': 'user1',
            'backup_date': '2024-01-15T10:00:00Z',
            'card_states': [{'flashcard_id': 'card1'}],
            'review_history': [{'rating': 3}],
            'parameters': {'user_id': 'user1'}
        }

        success = restore_scheduling_data("user1", backup_data)

        assert success is True

    def test_restore_scheduling_data_user_mismatch(self):
        """Test data restoration with user ID mismatch."""
        backup_data = {
            'user_id': 'user2',  # Different user
            'card_states': []
        }

        success = restore_scheduling_data("user1", backup_data)

        assert success is False

    @patch('src.flashcards.scheduler.get_supabase_client')
    def test_migrate_from_legacy_srs(self, mock_supabase):
        """Test migration from legacy SRS system."""
        mock_client = Mock()
        mock_supabase.return_value = mock_client

        # Mock legacy data
        legacy_data = [
            {
                'flashcard_id': 'legacy_card1',
                'easiness_factor': 2.5,
                'correct_count': 5,
                'incorrect_count': 1,
                'next_review_at': '2024-01-20T10:00:00Z',
                'last_studied_at': '2024-01-15T10:00:00Z'
            }
        ]

        # Mock responses for different tables
        def mock_table(table_name):
            mock_table_obj = Mock()
            if table_name == 'user_flashcard_stats':
                mock_table_obj.select.return_value.eq.return_value.execute.return_value.data = legacy_data
            elif table_name == 'fsrs_card_states':
                mock_table_obj.upsert.return_value.execute.return_value = Mock()
            return mock_table_obj

        mock_client.table.side_effect = mock_table

        migrated_count = migrate_from_legacy_srs("user1")

        assert migrated_count == 1


class TestErrorHandling:
    """Test error handling and edge cases."""

    @patch('src.flashcards.scheduler.get_supabase_client')
    def test_database_connection_error(self, mock_supabase):
        """Test handling of database connection errors."""
        # Mock database error
        mock_supabase.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception):
            get_card_state("card1", "user1")

    def test_invalid_card_rating_enum(self):
        """Test handling of invalid card rating values."""
        # This should be handled by the CardRating enum validation
        with pytest.raises(ValueError):
            CardRating(999)  # Invalid rating value


@pytest.fixture
def mock_supabase_client():
    """Fixture providing a mock Supabase client."""
    with patch('src.flashcards.scheduler.get_supabase_client') as mock:
        client = Mock()
        mock.return_value = client
        yield client


@pytest.fixture
def sample_review_data():
    """Fixture providing sample review data."""
    return {
        'flashcard_id': 'test_card_123',
        'user_id': 'test_user_456',
        'rating': 3,  # GOOD
        'review_time': datetime.now().isoformat(),
        'elapsed_days': 3
    }


class TestIntegrationScenarios:
    """Integration tests for complete workflows."""

    def test_complete_card_lifecycle(self, mock_supabase_client):
        """Test complete card lifecycle from creation to maturity."""
        # Mock database responses for different operations
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []  # Card doesn't exist
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value.data = [{'id': 'new_id'}]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = Mock()

        # 1. Schedule new card
        with patch('src.flashcards.scheduler.get_card_state', return_value=None):
            card_state = schedule_new_card("lifecycle_card", "test_user")
            assert card_state.state == "new"
            assert card_state.total_reviews == 0

        # 2. First review (simulate getting the card state we just created)
        with patch('src.flashcards.scheduler.get_card_state', return_value=card_state):
            result = review_card("lifecycle_card", "test_user", CardRating.GOOD)
            assert result.new_state.total_reviews == 1
            assert result.new_state.state == "review"

    def test_overdue_card_handling(self, mock_supabase_client):
        """Test handling of overdue cards."""
        # Mock overdue card data
        overdue_card_data = {
            'flashcard_id': 'overdue_card',
            'user_id': 'test_user',
            'due_date': (datetime.now() - timedelta(days=5)).isoformat() + 'Z',
            'stability': 5.0,
            'difficulty': 6.0
        }

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.lt.return_value.order.return_value.execute.return_value.data = [overdue_card_data]

        overdue_cards = get_overdue_cards("test_user", days_overdue=1)

        assert len(overdue_cards) == 1
        assert overdue_cards[0]['flashcard_id'] == 'overdue_card'

    def test_user_metrics_calculation(self, mock_supabase_client):
        """Test comprehensive user metrics calculation."""
        # Mock various database responses for metrics
        mock_metrics = {
            'total_cards': 50,
            'cards_due_today': 10,
            'avg_difficulty': 5.5,
            'avg_stability': 12.3
        }

        mock_reviews = [
            {'rating': 3}, {'rating': 4}, {'rating': 2}, {'rating': 3}, {'rating': 1}
        ]

        def mock_table(table_name):
            mock_table_obj = Mock()
            if table_name == 'fsrs_user_metrics':
                mock_table_obj.select.return_value.eq.return_value.execute.return_value.data = [mock_metrics]
            elif table_name == 'fsrs_review_history':
                mock_table_obj.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = mock_reviews
            return mock_table_obj

        mock_supabase_client.table.side_effect = mock_table

        metrics = get_scheduling_metrics("test_user")

        assert metrics.total_cards == 50
        assert metrics.cards_due_today == 10
        assert metrics.average_difficulty == 5.5
        assert metrics.average_stability == 12.3
        # Retention: 4 successful (rating >= 2) out of 5 = 0.8
        assert metrics.average_retention == 0.8
