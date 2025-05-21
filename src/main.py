"""
Main entry point for the StudyWiseAI application.
"""
import os
import argparse
from pathlib import Path

from .integration import StudyWiseAI


def main():
    """
    Parse command line arguments and run the application.
    """
    parser = argparse.ArgumentParser(description="Generate flashcards from documents")

    # Create a group for mutually exclusive input methods
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--file", "-f", help="Path to a file to process")
    input_group.add_argument("--url", "-u", help="URL to a document to process")
    input_group.add_argument("--text", "-t", help="Text content to process")

    # Additional options
    parser.add_argument("--save", "-s", action="store_true", help="Save flashcards to database")
    parser.add_argument("--output", "-o", help="Path to save flashcards JSON output")

    args = parser.parse_args()

    # Initialize the application
    app = StudyWiseAI()

    # Process the input based on the provided arguments
    if args.file:
        flashcards = app.process_file(args.file)
    elif args.url:
        flashcards = app.process_url(args.url)
    elif args.text:
        flashcards = app.process_text(args.text)

    # Print the generated flashcards
    for i, card in enumerate(flashcards, 1):
        print(f"\nFlashcard #{i}:")
        print(f"Q: {card['question']}")
        print(f"A: {card['answer']}")
        if "tags" in card and card["tags"]:
            print(f"Tags: {', '.join(card['tags'])}")

    # Save to database if requested
    if args.save:
        success = app.save_flashcards(flashcards)
        if success:
            print(f"\nSuccessfully saved {len(flashcards)} flashcards to the database.")
        else:
            print("\nFailed to save flashcards to the database.")

    # Save to file if requested
    if args.output:
        import json
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(flashcards, f, indent=2)
        print(f"\nSaved flashcards to {output_path}")

    print(f"\nGenerated {len(flashcards)} flashcards.")


if __name__ == "__main__":
    main()
