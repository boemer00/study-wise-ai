#!/usr/bin/env python
"""
Test script for processing PDF documents and generating flashcards.
"""
import os
import sys
import json
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

# Make sure we have the necessary environment variables
if not os.getenv("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY environment variable not set")
    print("Please create a .env file with your OpenAI API key")
    sys.exit(1)

if not os.getenv("OPENAI_MODEL"):
    print("Setting default model to gpt-4")
    os.environ["OPENAI_MODEL"] = "gpt-4"

from src.document import DocumentProcessor
from src.flashcard_generator import FlashcardGenerator


def process_pdf(file_path, level="intermediate"):
    """
    Process a PDF document and generate flashcards.

    Args:
        file_path: Path to the PDF file
        level: Difficulty level for flashcards (beginner, intermediate, advanced, expert)

    Returns:
        List of generated flashcards
    """
    print(f"Processing {file_path}...")

    # Initialize the document processor
    processor = DocumentProcessor()

    # Extract text from the PDF
    document_text = processor.process_document(file_path)
    print(f"Extracted {len(document_text)} characters from the PDF")

    # Chunk the text
    chunks = processor.chunk_text(document_text)
    print(f"Created {len(chunks)} chunks")

    # Generate flashcards
    generator = FlashcardGenerator()
    generator.level = level

    flashcards = generator.generate(chunks)

    # Print a sample of the flashcards
    print("\nSample Flashcards:")
    sample_size = min(3, len(flashcards))
    for i, card in enumerate(flashcards[:sample_size], 1):
        print(f"\nFlashcard #{i}:")
        print(f"Q: {card['question']}")
        print(f"A: {card['answer']}")
        if "tags" in card:
            print(f"Tags: {', '.join(card['tags'])}")

    # Save flashcards to a file
    output_file = f"flashcards_{os.path.basename(file_path).split('.')[0]}.json"
    with open(output_file, "w") as f:
        json.dump(flashcards, f, indent=2)

    print(f"\nSaved {len(flashcards)} flashcards to {output_file}")

    return flashcards


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_pdf.py <pdf_file_path> [difficulty_level]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    level = sys.argv[2] if len(sys.argv) > 2 else "intermediate"

    process_pdf(pdf_path, level)
