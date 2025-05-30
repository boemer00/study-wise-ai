# StudyWise AI - Supabase Integration

This module provides integration between StudyWise AI and Supabase for persistent storage of flashcards.

## Features

- Store flashcards in a Supabase PostgreSQL database
- Track user performance statistics for spaced repetition learning
- Filter and retrieve flashcards by tags, difficulty level, etc.
- CLI tools for database setup and management

## Database Schema

The Supabase database includes two main tables:

1. **flashcards**: Stores the actual flashcard content
   - `id`: UUID primary key
   - `question`: Text field for the question
   - `answer`: Text field for the answer
   - `tags`: JSONB array for storing tags
   - `level`: Difficulty level
   - `created_at`: Creation timestamp
   - `user_id`: Optional user identifier

2. **user_flashcard_stats**: Tracks user interactions with flashcards
   - `id`: UUID primary key
   - `flashcard_id`: Foreign key to flashcards
   - `user_id`: User identifier
   - `last_studied_at`: Timestamp of last study session
   - `next_review_at`: Scheduled next review date
   - `correct_count`: Number of correct answers
   - `incorrect_count`: Number of incorrect answers
   - `easiness_factor`: SM-2 algorithm parameter

## Setup

1. Create a Supabase account and project at [https://supabase.com](https://supabase.com)
2. Copy the `env.example` file to `.env` and fill in your Supabase URL and API key:

```
cp env.example .env
```

3. Edit the `.env` file with your Supabase credentials
4. Install required dependencies:

```
pip install -r requirements.txt
```

5. Initialize the database tables:

```
python -m src.cli setup
```

## Usage

### Upload Flashcards

Upload flashcards from a JSON file to Supabase:

```
python -m src.cli upload flashcards_output.json
```

### List Flashcards

List flashcards with optional filtering:

```
python -m src.cli list --limit 10 --offset 0 --level "intermediate" --tags "transformers" "attention"
```

## Development

The code is organized as follows:

- `src/supabase_client.py`: Supabase client configuration
- `src/flashcards_db.py`: Flashcard database operations
- `src/init_supabase.py`: Database initialization functions
- `src/cli.py`: Command-line interface

## Benefits

### For Students
- Access flashcards across multiple devices
- Track study progress and performance
- Benefit from spaced repetition algorithms
- Filter and organize flashcards by topic

### For Administrators
- Track usage and effectiveness of flashcards
- Gather analytics on student performance
- Manage and update flashcard content centrally
