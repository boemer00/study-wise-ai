"""
Text file handler for plain text documents.
"""

import logging
from typing import Dict, Any, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class TextHandler:
    """Handler for processing plain text documents."""

    def __init__(self):
        """Initialize text handler."""
        self.supported_extensions = ['.txt']

    def extract_text(self, file_path: Union[str, Path]) -> str:
        """
        Extract text from text file.

        Args:
            file_path: Path to text file

        Returns:
            Text content
        """
        file_path = Path(file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as file:
                return file.read()

    def extract_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Extract basic metadata from text file.

        Args:
            file_path: Path to text file

        Returns:
            Dictionary containing metadata
        """
        file_path = Path(file_path)
        file_stats = file_path.stat()

        # Read content to get basic stats
        try:
            content = self.extract_text(file_path)

            return {
                'file_name': file_path.name,
                'file_size': file_stats.st_size,
                'file_extension': file_path.suffix.lower(),
                'creation_date': file_stats.st_ctime,
                'modification_date': file_stats.st_mtime,
                'word_count': len(content.split()),
                'character_count': len(content),
                'line_count': len(content.splitlines())
            }
        except Exception as e:
            logger.error(f"Error extracting text metadata: {e}")
            return {
                'file_name': file_path.name,
                'file_size': file_stats.st_size,
                'file_extension': file_path.suffix.lower(),
                'creation_date': file_stats.st_ctime,
                'modification_date': file_stats.st_mtime,
                'word_count': 0,
                'character_count': 0,
                'line_count': 0
            }
