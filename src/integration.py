"""
Integration module connecting document processing with flashcard generation.
This module provides the main workflow for the application:
1. Upload and process documents
2. Generate flashcards from the processed text
3. Store the flashcards for later use
"""
from typing import List, Dict, Any, Optional
import os
from pathlib import Path

from .document import DocumentUploader, UploadedDocument
from .flashcard_generator import FlashcardGenerator
from .supabase import SupabaseClient


class StudyWiseAI:
    """
    Main integration class that coordinates document processing and flashcard generation.
    """
    def __init__(self):
        self.document_uploader = DocumentUploader()
        self.flashcard_generator = FlashcardGenerator()
        self.db_client = SupabaseClient()

    def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Process a file and generate flashcards from it.

        Args:
            file_path: Path to the file to process

        Returns:
            List of generated flashcards
        """
        # 1. Upload and process the document
        document = self.document_uploader.upload_from_file(file_path)

        # 2. Generate flashcards from the document chunks
        return self.generate_flashcards_from_document(document)

    def process_url(self, url: str) -> List[Dict[str, Any]]:
        """
        Download and process a file from a URL and generate flashcards.

        Args:
            url: URL to the document to process

        Returns:
            List of generated flashcards
        """
        # 1. Download, upload and process the document
        document = self.document_uploader.upload_from_url(url)

        # 2. Generate flashcards from the document chunks
        return self.generate_flashcards_from_document(document)

    def process_text(self, text: str, name: str = "pasted_text.txt") -> List[Dict[str, Any]]:
        """
        Process provided text and generate flashcards.

        Args:
            text: Text content to process
            name: Name to assign to the document (optional)

        Returns:
            List of generated flashcards
        """
        # 1. Create a document from the text
        document = self.document_uploader.upload_from_text(text, name)

        # 2. Generate flashcards from the document chunks
        return self.generate_flashcards_from_document(document)

    def generate_flashcards_from_document(self, document: UploadedDocument) -> List[Dict[str, Any]]:
        """
        Generate flashcards from a processed document.

        Args:
            document: Processed document with content and chunks

        Returns:
            List of generated flashcards
        """
        # Generate flashcards from the document chunks
        flashcards = self.flashcard_generator.generate(document.chunks)

        # Add document metadata to the flashcards
        for card in flashcards:
            card["source_document"] = document.file_name
            card["document_type"] = document.file_type

        return flashcards

    def save_flashcards(self, flashcards: List[Dict[str, Any]]) -> bool:
        """
        Save generated flashcards to the database.

        Args:
            flashcards: List of flashcards to save

        Returns:
            True if saved successfully, False otherwise
        """
        return self.db_client.insert_flashcards(flashcards)
