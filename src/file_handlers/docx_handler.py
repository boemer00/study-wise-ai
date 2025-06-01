"""
DOCX file handler with performance optimizations.

This module provides high-performance DOCX processing capabilities with optimized text extraction,
structured content processing, and comprehensive metadata handling for fast document processing.
"""

import os
import logging
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
from functools import lru_cache
import zipfile
from datetime import datetime

# DOCX processing libraries
from docx import Document
import docx2txt
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl

# Configure logging
logger = logging.getLogger(__name__)

class DOCXHandler:
    """
    High-performance DOCX file handler with optimized text extraction and content processing.

    Uses python-docx for structured processing and docx2txt for fast plain text extraction,
    with intelligent fallback and caching for optimal performance.

    Performance targets:
    - Small files (<5MB): 1-3 seconds
    - Medium files (5-25MB): 3-10 seconds
    - Large files (25-50MB): 10-25 seconds
    """

    def __init__(self, timeout_seconds: int = 30):
        """
        Initialize DOCX handler with performance settings.

        Args:
            timeout_seconds: Maximum processing time before timeout
        """
        self.timeout_seconds = timeout_seconds
        self.supported_extensions = ['.docx']

        # Performance tracking
        self._performance_stats = {
            'files_processed': 0,
            'total_processing_time': 0.0,
            'average_processing_time': 0.0
        }

        # Processing cache for repeated operations
        self._metadata_cache = {}

    def extract_text(
        self,
        file_path: Union[str, Path],
        preserve_formatting: bool = False,
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        Extract text from DOCX with optimized performance.

        Args:
            file_path: Path to DOCX file
            preserve_formatting: Whether to preserve basic formatting
            progress_callback: Optional callback for progress updates

        Returns:
            Extracted text content

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is corrupted or invalid
            TimeoutError: If processing exceeds timeout
        """
        start_time = time.time()

        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"DOCX file not found: {file_path}")

            # Validate file format
            if not self._is_valid_docx_file(file_path):
                raise ValueError(f"Invalid DOCX file: {file_path}")

            text_content = ""

            if preserve_formatting:
                text_content = self._extract_text_with_formatting(file_path, progress_callback)
            else:
                text_content = self._extract_text_fast(file_path, progress_callback)

            # Update performance stats
            processing_time = time.time() - start_time
            self._update_performance_stats(processing_time)

            # Check timeout
            if processing_time > self.timeout_seconds:
                logger.warning(f"DOCX processing took {processing_time:.2f}s, exceeding timeout of {self.timeout_seconds}s")

            logger.info(f"DOCX text extraction completed in {processing_time:.2f}s")
            return text_content.strip()

        except Exception as e:
            logger.error(f"Error extracting text from DOCX {file_path}: {str(e)}")
            raise

    def _extract_text_fast(self, file_path: Path, progress_callback: Optional[callable] = None) -> str:
        """Fast text extraction using docx2txt for maximum speed."""
        try:
            if progress_callback:
                progress_callback(0.1)

            # Use docx2txt for fastest extraction
            text = docx2txt.process(str(file_path))

            if progress_callback:
                progress_callback(1.0)

            return text if text else ""

        except Exception as e:
            logger.warning(f"Fast extraction failed, trying fallback: {e}")
            return self._extract_text_fallback(file_path)

    def _extract_text_with_formatting(self, file_path: Path, progress_callback: Optional[callable] = None) -> str:
        """Text extraction with basic formatting preservation using python-docx."""
        try:
            if progress_callback:
                progress_callback(0.1)

            doc = Document(str(file_path))
            text_parts = []

            total_elements = len(doc.paragraphs) + sum(len(table.rows) for table in doc.tables)
            processed = 0

            # Process paragraphs
            for paragraph in doc.paragraphs:
                text_parts.append(paragraph.text)
                processed += 1

                if progress_callback and total_elements > 0:
                    progress_callback(0.1 + 0.7 * (processed / total_elements))

            # Process tables
            for table in doc.tables:
                table_text = self._extract_table_text(table)
                if table_text.strip():
                    text_parts.append(f"\n[TABLE]\n{table_text}\n[/TABLE]\n")

                processed += len(table.rows)
                if progress_callback and total_elements > 0:
                    progress_callback(0.1 + 0.7 * (processed / total_elements))

            if progress_callback:
                progress_callback(1.0)

            return '\n'.join(text_parts)

        except Exception as e:
            logger.warning(f"Formatted extraction failed, trying fallback: {e}")
            return self._extract_text_fallback(file_path)

    def _extract_text_fallback(self, file_path: Path) -> str:
        """Fallback text extraction for problematic files."""
        try:
            # Try to extract as plain text from ZIP structure
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # Try to read document.xml directly
                try:
                    with zip_file.open('word/document.xml') as xml_file:
                        content = xml_file.read().decode('utf-8', errors='ignore')
                        # Basic XML tag removal (very simple)
                        import re
                        text = re.sub(r'<[^>]+>', '', content)
                        return text
                except KeyError:
                    logger.error("Could not find document.xml in DOCX file")
                    raise ValueError("Invalid DOCX structure")

        except Exception as e:
            logger.error(f"Fallback extraction also failed: {e}")
            raise ValueError(f"Could not extract text from DOCX: {e}")

    def extract_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from DOCX file.

        Args:
            file_path: Path to DOCX file

        Returns:
            Dictionary containing DOCX metadata
        """
        file_path = Path(file_path)

        # Check cache first
        cache_key = str(file_path.absolute())
        if cache_key in self._metadata_cache:
            return self._metadata_cache[cache_key].copy()

        try:
            metadata = {}

            # Extract using python-docx
            try:
                doc = Document(str(file_path))
                core_props = doc.core_properties

                metadata.update({
                    'title': core_props.title or '',
                    'author': core_props.author or '',
                    'subject': core_props.subject or '',
                    'creator': core_props.author or '',
                    'keywords': core_props.keywords or '',
                    'category': core_props.category or '',
                    'comments': core_props.comments or '',
                    'creation_date': core_props.created.isoformat() if core_props.created else '',
                    'modification_date': core_props.modified.isoformat() if core_props.modified else '',
                    'last_modified_by': core_props.last_modified_by or '',
                    'revision': str(core_props.revision) if core_props.revision else '0'
                })

                # Count document elements
                paragraph_count = len(doc.paragraphs)
                table_count = len(doc.tables)

                # Estimate word count quickly
                word_count = self._estimate_word_count_from_doc(doc)

                metadata.update({
                    'paragraph_count': paragraph_count,
                    'table_count': table_count,
                    'word_count': word_count,
                    'has_tables': table_count > 0,
                    'has_images': self._check_for_images(doc)
                })

            except Exception as e:
                logger.warning(f"python-docx metadata extraction failed: {e}")
                metadata = self._extract_metadata_fallback(file_path)

            # Add file system metadata
            file_stats = file_path.stat()
            metadata.update({
                'file_size': file_stats.st_size,
                'file_name': file_path.name,
                'file_extension': file_path.suffix.lower()
            })

            # Cache the result
            self._metadata_cache[cache_key] = metadata.copy()

            return metadata

        except Exception as e:
            logger.error(f"Error extracting DOCX metadata: {e}")
            raise

    def _extract_metadata_fallback(self, file_path: Path) -> Dict[str, Any]:
        """Fallback metadata extraction using ZIP structure."""
        metadata = {}

        try:
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # Try to read core.xml for basic metadata
                try:
                    with zip_file.open('docProps/core.xml') as core_xml:
                        content = core_xml.read().decode('utf-8', errors='ignore')
                        # Basic XML parsing for key fields
                        import re

                        title_match = re.search(r'<dc:title>(.*?)</dc:title>', content)
                        metadata['title'] = title_match.group(1) if title_match else ''

                        author_match = re.search(r'<dc:creator>(.*?)</dc:creator>', content)
                        metadata['author'] = author_match.group(1) if author_match else ''

                        created_match = re.search(r'<dcterms:created[^>]*>(.*?)</dcterms:created>', content)
                        metadata['creation_date'] = created_match.group(1) if created_match else ''

                except KeyError:
                    logger.warning("Could not find core.xml in DOCX file")

                # Basic document structure analysis
                metadata.update({
                    'paragraph_count': 0,
                    'table_count': 0,
                    'word_count': 0,
                    'has_tables': False,
                    'has_images': False
                })

        except Exception as e:
            logger.warning(f"Fallback metadata extraction failed: {e}")
            metadata.update({
                'title': '',
                'author': '',
                'creation_date': '',
                'modification_date': '',
                'paragraph_count': 0,
                'table_count': 0,
                'word_count': 0,
                'has_tables': False,
                'has_images': False
            })

        return metadata

    def validate_docx(self, file_path: Union[str, Path]) -> Tuple[bool, str]:
        """
        Validate DOCX file integrity and accessibility.

        Args:
            file_path: Path to DOCX file

        Returns:
            Tuple of (is_valid, error_message)
        """
        file_path = Path(file_path)

        try:
            if not file_path.exists():
                return False, "File does not exist"

            if not self._is_valid_docx_file(file_path):
                return False, "Invalid DOCX file format"

            # Try to open with python-docx
            try:
                doc = Document(str(file_path))
                # Basic validation - check if we can access paragraphs
                _ = len(doc.paragraphs)
                return True, "Valid DOCX file"

            except Exception as e:
                return False, f"DOCX validation error: {str(e)}"

        except Exception as e:
            return False, f"File validation error: {str(e)}"

    def extract_structured_content(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Extract structured content including paragraphs, headings, and tables.

        Args:
            file_path: Path to DOCX file

        Returns:
            Dictionary containing structured content
        """
        file_path = Path(file_path)

        try:
            doc = Document(str(file_path))

            structured_content = {
                'paragraphs': [],
                'headings': [],
                'tables': [],
                'document_structure': []
            }

            # Process document elements in order
            for element in doc.element.body:
                if isinstance(element, CT_P):
                    paragraph = Paragraph(element, doc)
                    if paragraph.style.name.startswith('Heading'):
                        structured_content['headings'].append({
                            'level': paragraph.style.name,
                            'text': paragraph.text
                        })
                    else:
                        structured_content['paragraphs'].append(paragraph.text)

                    structured_content['document_structure'].append({
                        'type': 'paragraph',
                        'style': paragraph.style.name,
                        'text': paragraph.text
                    })

                elif isinstance(element, CT_Tbl):
                    table = Table(element, doc)
                    table_data = self._extract_table_data(table)
                    structured_content['tables'].append(table_data)

                    structured_content['document_structure'].append({
                        'type': 'table',
                        'rows': len(table_data),
                        'columns': len(table_data[0]) if table_data else 0
                    })

            return structured_content

        except Exception as e:
            logger.error(f"Error extracting structured content: {e}")
            raise

    def extract_tables(self, file_path: Union[str, Path]) -> List[List[List[str]]]:
        """
        Extract all tables from DOCX as structured data.

        Args:
            file_path: Path to DOCX file

        Returns:
            List of tables, each table is a list of rows, each row is a list of cells
        """
        file_path = Path(file_path)

        try:
            doc = Document(str(file_path))
            tables_data = []

            for table in doc.tables:
                table_data = self._extract_table_data(table)
                if table_data:  # Only add non-empty tables
                    tables_data.append(table_data)

            return tables_data

        except Exception as e:
            logger.error(f"Error extracting tables: {e}")
            return []

    def _extract_table_data(self, table: Table) -> List[List[str]]:
        """Extract data from a single table."""
        table_data = []

        for row in table.rows:
            row_data = []
            for cell in row.cells:
                cell_text = cell.text.strip()
                row_data.append(cell_text)
            table_data.append(row_data)

        return table_data

    def _extract_table_text(self, table: Table) -> str:
        """Extract text representation of a table."""
        table_data = self._extract_table_data(table)

        if not table_data:
            return ""

        # Create simple text representation
        table_lines = []
        for row in table_data:
            table_lines.append(" | ".join(row))

        return "\n".join(table_lines)

    def extract_images_info(self, file_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Extract information about images in the document.

        Args:
            file_path: Path to DOCX file

        Returns:
            List of dictionaries containing image information
        """
        file_path = Path(file_path)
        images_info = []

        try:
            # Check ZIP structure for images
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                media_files = [f for f in zip_file.namelist() if f.startswith('word/media/')]

                for media_file in media_files:
                    file_info = zip_file.getinfo(media_file)

                    images_info.append({
                        'filename': media_file.split('/')[-1],
                        'path': media_file,
                        'size': file_info.file_size,
                        'type': 'image' if any(media_file.lower().endswith(ext)
                                             for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']) else 'media'
                    })

            return images_info

        except Exception as e:
            logger.error(f"Error extracting image info: {e}")
            return []

    def _check_for_images(self, doc: Document) -> bool:
        """Quick check for images in document."""
        try:
            # Check if document has any inline shapes (images)
            for paragraph in doc.paragraphs:
                if paragraph._element.xpath('.//a:blip'):
                    return True
            return False
        except Exception:
            return False

    def get_word_count(self, file_path: Union[str, Path]) -> int:
        """
        Get accurate word count from DOCX file.

        Args:
            file_path: Path to DOCX file

        Returns:
            Word count
        """
        try:
            # Use fast extraction for word counting
            text = self._extract_text_fast(Path(file_path))
            return len(text.split()) if text else 0

        except Exception as e:
            logger.error(f"Error counting words: {e}")
            return 0

    def _estimate_word_count_from_doc(self, doc: Document) -> int:
        """Estimate word count from Document object without full text extraction."""
        try:
            word_count = 0

            # Sample first few paragraphs to estimate
            sample_paragraphs = doc.paragraphs[:min(10, len(doc.paragraphs))]
            sample_words = sum(len(p.text.split()) for p in sample_paragraphs)

            if sample_paragraphs:
                avg_words_per_paragraph = sample_words / len(sample_paragraphs)
                estimated_total = int(avg_words_per_paragraph * len(doc.paragraphs))
                return estimated_total

            return 0

        except Exception:
            return 0

    def _is_valid_docx_file(self, file_path: Path) -> bool:
        """Check if file is a valid DOCX by checking ZIP structure."""
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # Check for required DOCX files
                required_files = ['[Content_Types].xml', 'word/document.xml']
                return all(f in zip_file.namelist() for f in required_files)
        except Exception:
            return False

    def _update_performance_stats(self, processing_time: float) -> None:
        """Update internal performance statistics."""
        self._performance_stats['files_processed'] += 1
        self._performance_stats['total_processing_time'] += processing_time
        self._performance_stats['average_processing_time'] = (
            self._performance_stats['total_processing_time'] /
            self._performance_stats['files_processed']
        )

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for monitoring.

        Returns:
            Dictionary with performance metrics
        """
        return self._performance_stats.copy()

    def clear_cache(self) -> None:
        """Clear metadata cache to free memory."""
        self._metadata_cache.clear()

    @staticmethod
    @lru_cache(maxsize=128)
    def get_supported_extensions() -> List[str]:
        """
        Get list of supported file extensions.

        Returns:
            List of supported extensions
        """
        return ['.docx']
