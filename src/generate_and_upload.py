"""
Script to generate flashcards from a PDF and upload them to Supabase.
"""
import os
import json
import argparse
from pathlib import Path

from src.document import DocumentUploader
from src.flashcard_generator import FlashcardGenerator
from src.cli import upload_flashcards


def main():
    """
    Main function to process a PDF, generate flashcards, and upload them to Supabase.
    """
    parser = argparse.ArgumentParser(description="Generate flashcards from PDF and upload to Supabase")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--output", "-o", default="flashcards_output.json",
                        help="Output JSON file path (default: flashcards_output.json)")
    parser.add_argument("--level", "-l", default="intermediate",
                        choices=["beginner", "intermediate", "advanced"],
                        help="Difficulty level for flashcards")
    args = parser.parse_args()

    # Check if the PDF file exists
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        return 1

    # Process the PDF
    print(f"Processing PDF: {pdf_path}")
    try:
        uploader = DocumentUploader()
        document = uploader.upload_from_file(str(pdf_path))
        print(f"Successfully processed PDF with {len(document.chunks)} chunks")
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return 1

    # Generate flashcards
    print("Generating flashcards...")
    generator = FlashcardGenerator()
    generator.level = args.level
    flashcards = generator.generate(document.chunks)
    print(f"Generated {len(flashcards)} flashcards")

    # Save flashcards to JSON
    output_path = args.output
    try:
        with open(output_path, 'w') as f:
            json.dump(flashcards, f, indent=2)
        print(f"Saved flashcards to {output_path}")
    except Exception as e:
        print(f"Error saving flashcards: {str(e)}")
        return 1

    # Upload flashcards to Supabase
    print("Uploading flashcards to Supabase...")
    try:
        upload_flashcards(output_path)
    except Exception as e:
        print(f"Error uploading flashcards to Supabase: {str(e)}")
        return 1

    print("✅ Process completed successfully!")
    return 0


if __name__ == "__main__":
    exit(main())
