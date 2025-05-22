"""
Main entry point for the application.
"""
import os
from .flashcard_generator import FlashcardGenerator
from .flashcards_db import upsert_flashcards_from_json


def main():
    chunks = []

    generator = FlashcardGenerator()
    cards = generator.generate(chunks)

    # Optionally, print or save locally
    for card in cards:
        print(f"Q: {card['question']}\nA: {card['answer']}\nTags: {card['tags']}\n")

    # Save cards to JSON
    output_file = "flashcards_output.json"
    with open(output_file, "w") as f:
        import json
        json.dump(cards, f, indent=2)

    # Upload to Supabase
    upsert_flashcards_from_json(output_file)
    print(f"Uploaded {len(cards)} flashcards to Supabase")


if __name__ == "__main__":
    main()
