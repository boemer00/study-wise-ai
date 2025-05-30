import os
from .flashcard_generator import FlashcardGenerator
from .supabase import SupabaseClient


def main():
    chunks = []

    generator = FlashcardGenerator()
    cards = generator.generate(chunks)

    # Optionally, print or save locally
    for card in cards:
        print(f"Q: {card['question']}\nA: {card['answer']}\nTags: {card['tags']}\n")

    # Insert into Supabase
    supa = SupabaseClient()
    supa.insert_flashcards(cards)

if __name__ == "__main__":
    main()
