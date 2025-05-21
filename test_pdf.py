#!/usr/bin/env python
"""
Test script to process the 'attention_is_all_you_need.pdf' file.
"""
import os
import sys
import json
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, os.path.abspath('.'))

from src.document import DocumentUploader, DocumentProcessor
from src.flashcard_generator import FlashcardGenerator

def main():
    # Process the PDF file directly without the integration layer
    pdf_path = 'raw_data/attention_is_all_you_need.pdf'
    print(f"Processing {pdf_path}...")

    try:
        # Step 1: Upload and process the document
        uploader = DocumentUploader()
        document = uploader.upload_from_file(pdf_path)
        print(f"Successfully processed document: {document.file_name}")
        print(f"Content length: {len(document.content)} characters")
        print(f"Divided into {len(document.chunks)} chunks")

        # Step 2: Generate flashcards
        generator = FlashcardGenerator(level="intermediate")
        flashcards = generator.generate(document.chunks)

        # Display the results
        print(f"\nGenerated {len(flashcards)} flashcards:")

        # Print all flashcards
        for i, card in enumerate(flashcards, 1):
            print(f"\nFlashcard #{i}:")
            print(f"Q: {card['question']}")
            print(f"A: {card['answer']}")
            if "tags" in card and card["tags"]:
                print(f"Tags: {', '.join(card['tags'])}")

        # Save the flashcards to a JSON file
        output_file = 'flashcards_output.json'
        with open(output_file, 'w') as f:
            json.dump(flashcards, f, indent=2)
        print(f"\nSaved all flashcards to {output_file}")

    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
