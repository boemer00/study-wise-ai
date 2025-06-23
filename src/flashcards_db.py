"""
Flashcards database operations for StudyWise AI.
This module provides functions to create, retrieve, and manage flashcards in Supabase.
"""
import json
from typing import Dict, Any, List, Optional, Union
import uuid
from datetime import datetime

from src.supabase_client import get_supabase_client


def save_generated_flashcards(
    flashcards: List[Dict[str, Any]],
    user_id: str,
    document_id: Optional[str] = None
) -> List[str]:
    """
    Save generated flashcards directly to the database.

    Args:
        flashcards: List of flashcard dictionaries
        user_id: UUID of the user who generated the flashcards
        document_id: Optional document ID the flashcards were generated from

    Returns:
        List[str]: List of IDs of the saved flashcards
    """
    if not flashcards:
        return []

    # Prepare flashcards for database storage
    processed_cards = []
    for card in flashcards:
        # Ensure required fields exist
        if not card.get('question') or not card.get('answer'):
            continue  # Skip invalid cards

        processed_card = {
            'id': str(uuid.uuid4()),
            'question': card['question'],
            'answer': card['answer'],
            'tags': card.get('tags', []),
            'level': card.get('level', 'intermediate'),
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat()
        }

        # Add document reference if provided
        if document_id:
            if not processed_card['tags']:
                processed_card['tags'] = []
            processed_card['tags'].append(f"document:{document_id}")

        processed_cards.append(processed_card)

    if not processed_cards:
        return []

    # Save to Supabase
    supabase = get_supabase_client()
    try:
        result = supabase.table('flashcards').insert(processed_cards).execute()
        return [card['id'] for card in processed_cards]
    except Exception as e:
        print(f"Error saving flashcards to database: {e}")
        return []


def upsert_flashcards_from_json(filepath: str) -> List[str]:
    """
    Read flashcards from a JSON file and upsert them into Supabase.

    Args:
        filepath: Path to the JSON file containing flashcards

    Returns:
        List[str]: List of IDs of the upserted flashcards

    Raises:
        FileNotFoundError: If the specified JSON file does not exist
        ValueError: If the JSON file is invalid or does not contain flashcards
    """
    try:
        with open(filepath, 'r') as f:
            flashcards = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Flashcard file not found: {filepath}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in file: {filepath}")

    if not isinstance(flashcards, list):
        raise ValueError("Flashcards data must be a list")

    # Add UUIDs and timestamps to flashcards
    for card in flashcards:
        if 'id' not in card:
            card['id'] = str(uuid.uuid4())
        card['created_at'] = datetime.utcnow().isoformat()

    # Get Supabase client
    supabase = get_supabase_client()

    # Upsert flashcards to Supabase
    result = supabase.table('flashcards').upsert(flashcards).execute()

    # Extract and return IDs of upserted flashcards
    return [card['id'] for card in flashcards]


def get_flashcards(
    limit: int = 100,
    offset: int = 0,
    tags: Optional[List[str]] = None,
    level: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve flashcards from the database with optional filtering.

    Args:
        limit: Maximum number of flashcards to retrieve
        offset: Number of flashcards to skip
        tags: List of tags to filter by
        level: Difficulty level to filter by
        user_id: UUID of the user to filter by

    Returns:
        List[Dict[str, Any]]: List of flashcard objects
    """
    supabase = get_supabase_client()

    # Base query
    query = supabase.table('flashcards').select('*')

    # Scope to current user if provided
    if user_id:
        query = query.eq('user_id', user_id)

    # Apply filters if provided
    if level:
        query = query.eq('level', level)

    # Apply pagination
    query = query.range(offset, offset + limit - 1)

    # Execute query
    result = query.execute()

    # Post-process for tag filtering if needed
    # (This is done in Python because JSONB array filtering is complex)
    data = result.data
    if tags:
        data = [
            card for card in data
            if any(tag in card.get('tags', []) for tag in tags)
        ]

    return data


def get_flashcard_by_id(flashcard_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a single flashcard by its ID.

    Args:
        flashcard_id: UUID of the flashcard

    Returns:
        Optional[Dict[str, Any]]: Flashcard object if found, None otherwise
    """
    supabase = get_supabase_client()
    result = supabase.table('flashcards').select('*').eq('id', flashcard_id).execute()

    if not result.data:
        return None

    return result.data[0]


def update_flashcard_stats(
    flashcard_id: str,
    user_id: str,
    is_correct: bool
) -> Dict[str, Any]:
    """
    Update user-specific statistics for a flashcard.

    Args:
        flashcard_id: UUID of the flashcard
        user_id: UUID of the user
        is_correct: Whether the user answered correctly

    Returns:
        Dict[str, Any]: Updated stats record
    """
    supabase = get_supabase_client()

    # Check if stats record exists
    result = supabase.table('user_flashcard_stats').select('*').eq(
        'flashcard_id', flashcard_id
    ).eq('user_id', user_id).execute()

    now = datetime.utcnow().isoformat()

    if not result.data:
        # Create new stats record
        stats = {
            'id': str(uuid.uuid4()),
            'flashcard_id': flashcard_id,
            'user_id': user_id,
            'last_studied_at': now,
            'next_review_at': now,  # Simple implementation - would calculate based on SRS in production
            'correct_count': 1 if is_correct else 0,
            'incorrect_count': 0 if is_correct else 1,
            'easiness_factor': 2.5  # Default easiness factor for SM-2 algorithm
        }
        result = supabase.table('user_flashcard_stats').insert(stats).execute()
    else:
        # Update existing stats record
        existing = result.data[0]
        stats = {
            'last_studied_at': now,
            'next_review_at': now,  # Simple implementation - would calculate based on SRS in production
            'correct_count': existing['correct_count'] + (1 if is_correct else 0),
            'incorrect_count': existing['incorrect_count'] + (0 if is_correct else 1),
        }
        result = supabase.table('user_flashcard_stats').update(stats).eq(
            'id', existing['id']
        ).execute()

    return result.data[0]
