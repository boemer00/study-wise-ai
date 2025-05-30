"""
Initialize Supabase tables for StudyWise AI application.
This script creates the necessary tables and indices in Supabase.

Note: This requires Supabase admin privileges. Alternatively, these tables
can be created manually in the Supabase dashboard SQL editor.
"""
import os
import sys
from typing import List
import time

from src.supabase_client import get_supabase_client

# SQL statements to create tables
CREATE_FLASHCARDS_TABLE = """
CREATE TABLE IF NOT EXISTS flashcards (
    id UUID PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    tags JSONB,
    level TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id UUID
);

-- Create index on tags for faster filtering
CREATE INDEX IF NOT EXISTS idx_flashcards_tags ON flashcards USING GIN (tags);

-- Create index on level for faster filtering
CREATE INDEX IF NOT EXISTS idx_flashcards_level ON flashcards (level);
"""

CREATE_USER_FLASHCARD_STATS_TABLE = """
CREATE TABLE IF NOT EXISTS user_flashcard_stats (
    id UUID PRIMARY KEY,
    flashcard_id UUID NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    last_studied_at TIMESTAMP WITH TIME ZONE,
    next_review_at TIMESTAMP WITH TIME ZONE,
    correct_count INTEGER DEFAULT 0,
    incorrect_count INTEGER DEFAULT 0,
    easiness_factor REAL DEFAULT 2.5,

    -- Add a unique constraint on flashcard_id and user_id
    UNIQUE(flashcard_id, user_id)
);

-- Create index on next_review_at for efficient retrieval of due cards
CREATE INDEX IF NOT EXISTS idx_next_review ON user_flashcard_stats (next_review_at);

-- Create index on user_id for faster user-specific queries
CREATE INDEX IF NOT EXISTS idx_user_stats ON user_flashcard_stats (user_id);
"""

def initialize_tables() -> List[str]:
    """
    Initialize the Supabase tables for the StudyWise AI application.

    Note: This function doesn't actually create the tables through the Python client
    as the required query functionality might not be available in all Supabase client versions.
    It returns instructions for manual table creation.

    Returns:
        List[str]: List of messages with SQL setup instructions
    """
    messages = []

    messages.append("IMPORTANT: Unable to automatically create tables via the Python client.")
    messages.append("Please create the tables manually using the Supabase dashboard SQL editor with the following SQL:")
    messages.append("\n--- FLASHCARDS TABLE ---\n")
    messages.append(CREATE_FLASHCARDS_TABLE)
    messages.append("\n--- USER FLASHCARD STATS TABLE ---\n")
    messages.append(CREATE_USER_FLASHCARD_STATS_TABLE)

    return messages

if __name__ == "__main__":
    messages = initialize_tables()
    for message in messages:
        print(message)
