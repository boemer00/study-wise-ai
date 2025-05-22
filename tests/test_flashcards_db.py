"""
Unit tests for the flashcards database module.
These tests mock the Supabase client to avoid actual API calls.
"""
import json
import os
import tempfile
import uuid
from unittest.mock import patch, MagicMock

import pytest

from src.flashcards_db import (
    upsert_flashcards_from_json,
    get_flashcards,
    get_flashcard_by_id,
    update_flashcard_stats
)


@pytest.fixture
def sample_flashcards():
    """Fixture to provide sample flashcard data."""
    return [
        {
            "question": "What is the Transformer model?",
            "answer": "A neural network architecture based solely on attention mechanisms.",
            "tags": ["transformers", "attention", "deep learning"],
            "level": "intermediate"
        },
        {
            "question": "What is self-attention?",
            "answer": "A mechanism relating different positions of a single sequence.",
            "tags": ["attention", "deep learning"],
            "level": "intermediate"
        }
    ]


@pytest.fixture
def temp_flashcards_file(sample_flashcards):
    """Fixture to create a temporary file with sample flashcards."""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as f:
        json.dump(sample_flashcards, f)
        filepath = f.name

    yield filepath

    # Cleanup
    if os.path.exists(filepath):
        os.unlink(filepath)


def test_upsert_flashcards_from_json(temp_flashcards_file, sample_flashcards):
    """Test uploading flashcards from a JSON file."""
    with patch('src.flashcards_db.get_supabase_client') as mock_get_client:
        # Set up the mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_upsert = MagicMock()
        mock_table.upsert.return_value = mock_upsert

        mock_execute = MagicMock()
        mock_upsert.execute.return_value = mock_execute

        # Call the function
        result = upsert_flashcards_from_json(temp_flashcards_file)

        # Verify behavior
        mock_client.table.assert_called_once_with('flashcards')
        mock_table.upsert.assert_called_once()
        mock_upsert.execute.assert_called_once()

        # Verify the result
        assert len(result) == 2
        assert all(isinstance(id, str) for id in result)


def test_upsert_flashcards_nonexistent_file():
    """Test uploading flashcards from a nonexistent file."""
    with pytest.raises(FileNotFoundError):
        upsert_flashcards_from_json('nonexistent_file.json')


def test_get_flashcards():
    """Test retrieving flashcards with various filters."""
    with patch('src.flashcards_db.get_supabase_client') as mock_get_client:
        # Set up the mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select

        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq

        mock_range = MagicMock()
        mock_eq.range.return_value = mock_range
        mock_select.range.return_value = mock_range

        mock_execute = MagicMock()
        mock_range.execute.return_value = mock_execute

        # Set up mock data
        mock_execute.data = [
            {
                "id": str(uuid.uuid4()),
                "question": "Test question",
                "answer": "Test answer",
                "tags": ["test", "mock"],
                "level": "intermediate"
            }
        ]

        # Call the function
        result = get_flashcards(limit=10, offset=0, level="intermediate", tags=["test"])

        # Verify behavior
        mock_client.table.assert_called_once_with('flashcards')
        mock_table.select.assert_called_once_with('*')
        mock_select.eq.assert_called_once_with('level', 'intermediate')

        # Verify the result
        assert len(result) == 1
        assert "test" in result[0]["tags"]


def test_get_flashcard_by_id():
    """Test retrieving a single flashcard by ID."""
    test_id = str(uuid.uuid4())

    with patch('src.flashcards_db.get_supabase_client') as mock_get_client:
        # Set up the mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select

        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq

        mock_execute = MagicMock()
        mock_eq.execute.return_value = mock_execute

        # Set up mock data
        mock_execute.data = [
            {
                "id": test_id,
                "question": "Test question",
                "answer": "Test answer",
                "tags": ["test", "mock"],
                "level": "intermediate"
            }
        ]

        # Call the function
        result = get_flashcard_by_id(test_id)

        # Verify behavior
        mock_client.table.assert_called_once_with('flashcards')
        mock_table.select.assert_called_once_with('*')
        mock_select.eq.assert_called_once_with('id', test_id)

        # Verify the result
        assert result["id"] == test_id
        assert result["question"] == "Test question"


def test_get_flashcard_by_id_not_found():
    """Test retrieving a nonexistent flashcard."""
    test_id = str(uuid.uuid4())

    with patch('src.flashcards_db.get_supabase_client') as mock_get_client:
        # Set up the mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select

        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq

        mock_execute = MagicMock()
        mock_eq.execute.return_value = mock_execute

        # Set up mock data for not found
        mock_execute.data = []

        # Call the function
        result = get_flashcard_by_id(test_id)

        # Verify the result
        assert result is None


def test_update_flashcard_stats_new_record():
    """Test updating stats for a new flashcard-user combination."""
    flashcard_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    with patch('src.flashcards_db.get_supabase_client') as mock_get_client, \
         patch('src.flashcards_db.uuid.uuid4') as mock_uuid:
        # Set up the UUID mock
        mock_uuid_value = uuid.uuid4()
        mock_uuid.return_value = mock_uuid_value

        # Set up the client mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock for checking existing record
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select

        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1

        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2

        mock_execute1 = MagicMock()
        mock_eq2.execute.return_value = mock_execute1

        # Set up mock data for not found
        mock_execute1.data = []

        # Mock for inserting new record
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert

        mock_execute2 = MagicMock()
        mock_insert.execute.return_value = mock_execute2

        # Set up mock data for insert result
        mock_execute2.data = [
            {
                "id": str(mock_uuid_value),
                "flashcard_id": flashcard_id,
                "user_id": user_id,
                "correct_count": 1,
                "incorrect_count": 0,
            }
        ]

        # Call the function
        result = update_flashcard_stats(flashcard_id, user_id, True)

        # Verify behavior for checking existing record
        mock_client.table.assert_called_with('user_flashcard_stats')
        mock_table.select.assert_called_once_with('*')

        # Verify behavior for inserting new record
        mock_table.insert.assert_called_once()

        # Verify the result
        assert result["flashcard_id"] == flashcard_id
        assert result["user_id"] == user_id
        assert result["correct_count"] == 1
        assert result["incorrect_count"] == 0


def test_update_flashcard_stats_existing_record():
    """Test updating stats for an existing flashcard-user combination."""
    flashcard_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    record_id = str(uuid.uuid4())

    with patch('src.flashcards_db.get_supabase_client') as mock_get_client:
        # Set up the client mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock for checking existing record
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select

        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1

        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2

        mock_execute1 = MagicMock()
        mock_eq2.execute.return_value = mock_execute1

        # Set up mock data for existing record
        mock_execute1.data = [
            {
                "id": record_id,
                "flashcard_id": flashcard_id,
                "user_id": user_id,
                "correct_count": 2,
                "incorrect_count": 1,
            }
        ]

        # Mock for updating existing record
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update

        mock_eq3 = MagicMock()
        mock_update.eq.return_value = mock_eq3

        mock_execute2 = MagicMock()
        mock_eq3.execute.return_value = mock_execute2

        # Set up mock data for update result
        mock_execute2.data = [
            {
                "id": record_id,
                "flashcard_id": flashcard_id,
                "user_id": user_id,
                "correct_count": 2,
                "incorrect_count": 2,
            }
        ]

        # Call the function
        result = update_flashcard_stats(flashcard_id, user_id, False)

        # Verify behavior for checking existing record
        mock_client.table.assert_called_with('user_flashcard_stats')
        mock_table.select.assert_called_once_with('*')

        # Verify behavior for updating existing record
        mock_table.update.assert_called_once()

        # Verify the result
        assert result["id"] == record_id
        assert result["flashcard_id"] == flashcard_id
        assert result["user_id"] == user_id
        assert result["correct_count"] == 2
        assert result["incorrect_count"] == 2
