"""
Markdown file handler for markdown documents.
"""

import logging
from typing import Dict, Any, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class MarkdownHandler:
    """Handler for processing markdown documents."""

    def __init__(self):
        """Initialize markdown handler."""
        self.supported_extensions = ['.md', '.markdown']

    def extract_text(self, file_path: Union[str, Path]) -> str:
        """
        Extract text from markdown file.

        Args:
            file_path: Path to markdown file

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
        Extract basic metadata from markdown file.

        Args:
            file_path: Path to markdown file

        Returns:
            Dictionary containing metadata
        """
        file_path = Path(file_path)
        file_stats = file_path.stat()

        # Read content to get basic stats
        try:
            content = self.extract_text(file_path)

            # Count headings
            lines = content.splitlines()
            heading_count = sum(1 for line in lines if line.strip().startswith('#'))

            return {
                'file_name': file_path.name,
                'file_size': file_stats.st_size,
                'file_extension': file_path.suffix.lower(),
                'creation_date': file_stats.st_ctime,
                'modification_date': file_stats.st_mtime,
                'word_count': len(content.split()),
                'character_count': len(content),
                'line_count': len(content.splitlines()),
                'heading_count': heading_count
            }
        except Exception as e:
            logger.error(f"Error extracting markdown metadata: {e}")
            return {
                'file_name': file_path.name,
                'file_size': file_stats.st_size,
                'file_extension': file_path.suffix.lower(),
                'creation_date': file_stats.st_ctime,
                'modification_date': file_stats.st_mtime,
                'word_count': 0,
                'character_count': 0,
                'line_count': 0,
                'heading_count': 0
            }
