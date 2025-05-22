"""
Command-line interface for StudyWise AI Supabase integration.
This module provides CLI commands to manage flashcards in Supabase.
"""
import argparse
import os
import sys
from typing import List, Optional

from src.flashcards_db import upsert_flashcards_from_json, get_flashcards
from src.init_supabase import initialize_tables


def upload_flashcards(filepath: str) -> None:
    """
    Upload flashcards from a JSON file to Supabase.

    Args:
        filepath: Path to the JSON file containing flashcards
    """
    try:
        card_ids = upsert_flashcards_from_json(filepath)
        print(f"Successfully uploaded {len(card_ids)} flashcards to Supabase")
    except Exception as e:
        print(f"Error uploading flashcards: {str(e)}")
        sys.exit(1)


def list_flashcards(limit: int, offset: int, level: Optional[str], tags: Optional[List[str]]) -> None:
    """
    List flashcards from Supabase with optional filtering.

    Args:
        limit: Maximum number of flashcards to retrieve
        offset: Number of flashcards to skip
        level: Difficulty level to filter by
        tags: List of tags to filter by
    """
    try:
        cards = get_flashcards(limit=limit, offset=offset, level=level, tags=tags)
        print(f"Found {len(cards)} flashcards:")
        for i, card in enumerate(cards, 1):
            print(f"\n{i}. {card['question']}")
            print(f"   Answer: {card['answer']}")
            print(f"   Level: {card['level']}")
            print(f"   Tags: {', '.join(card['tags'])}")
    except Exception as e:
        print(f"Error retrieving flashcards: {str(e)}")
        sys.exit(1)


def setup_db() -> None:
    """Initialize the Supabase database tables."""
    try:
        messages = initialize_tables()
        for message in messages:
            print(message)
    except Exception as e:
        print(f"Error setting up database: {str(e)}")
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="StudyWise AI Supabase Integration")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up Supabase tables")

    # Upload command
    upload_parser = subparsers.add_parser("upload", help="Upload flashcards from JSON")
    upload_parser.add_argument("filepath", help="Path to the JSON file containing flashcards")

    # List command
    list_parser = subparsers.add_parser("list", help="List flashcards")
    list_parser.add_argument("--limit", type=int, default=10, help="Maximum number of flashcards to retrieve")
    list_parser.add_argument("--offset", type=int, default=0, help="Number of flashcards to skip")
    list_parser.add_argument("--level", help="Filter by difficulty level")
    list_parser.add_argument("--tags", nargs="+", help="Filter by tags")

    args = parser.parse_args()

    if args.command == "setup":
        setup_db()
    elif args.command == "upload":
        upload_flashcards(args.filepath)
    elif args.command == "list":
        list_flashcards(args.limit, args.offset, args.level, args.tags)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
