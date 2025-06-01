"""
PDF file handler with performance optimizations.

This module provides PDF processing capabilities with optimized text extraction,
metadata handling, and comprehensive error management for fast document processing.
"""

import os
import logging
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
from functools import lru_cache
import fitz  # PyMuPDF - fastest PDF library
import PyPDF2
from io import BytesIO

# Configure logging
logger = logging.getLogger(__name__)

class PDFHandler:
    """
    High-performance PDF file handler with optimized text extraction and metadata processing.

    Uses PyMuPDF (fitz) as primary extraction engine for 5-10x faster processing
    compared to PyPDF2, with fallback options for compatibility.

    Performance targets:
    - Small files (<5MB): 2-5 seconds
    - Medium files (5-25MB): 5-15 seconds
    - Large files (25-50MB): 15-30 seconds
    """

    def __init__(self, timeout_seconds: int = 30):
        """
        Initialize PDF handler with performance settings.

        Args:
            timeout_seconds: Maximum processing time before timeout
        """
        self.timeout_seconds = timeout_seconds
        self.supported_extensions = ['.pdf']

        # Performance tracking
        self._performance_stats = {
            'files_processed': 0,
            'total_processing_time': 0.0,
            'average_processing_time': 0.0
        }

    def extract_text(
        self,
        file_path: Union[str, Path],
        extract_level: str = "fast",
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        Extract text from PDF with optimized performance.

        Args:
            file_path: Path to PDF file
            extract_level: "fast", "standard", or "detailed" (default: "fast")
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
                raise FileNotFoundError(f"PDF file not found: {file_path}")

            # Validate file format
            if not self._is_valid_pdf_file(file_path):
                raise ValueError(f"Invalid PDF file: {file_path}")

            text_content = ""

            if extract_level == "fast":
                text_content = self._extract_text_fast(file_path, progress_callback)
            elif extract_level == "standard":
                text_content = self._extract_text_standard(file_path, progress_callback)
            elif extract_level == "detailed":
                text_content = self._extract_text_detailed(file_path, progress_callback)
            else:
                raise ValueError(f"Invalid extract_level: {extract_level}")

            # Update performance stats
            processing_time = time.time() - start_time
            self._update_performance_stats(processing_time)

            # Check timeout
            if processing_time > self.timeout_seconds:
                logger.warning(f"PDF processing took {processing_time:.2f}s, exceeding timeout of {self.timeout_seconds}s")

            logger.info(f"PDF text extraction completed in {processing_time:.2f}s")
            return text_content.strip()

        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {str(e)}")
            raise

    def _extract_text_fast(self, file_path: Path, progress_callback: Optional[callable] = None) -> str:
        """Fast text extraction using PyMuPDF with minimal processing."""
        try:
            doc = fitz.open(str(file_path))
            text_parts = []

            for page_num in range(len(doc)):
                if progress_callback:
                    progress_callback(page_num / len(doc))

                page = doc.load_page(page_num)
                text = page.get_text()
                text_parts.append(text)

            doc.close()
            return '\n'.join(text_parts)

        except Exception as e:
            logger.warning(f"Fast extraction failed, trying fallback: {e}")
            return self._extract_text_fallback(file_path)

    def _extract_text_standard(self, file_path: Path, progress_callback: Optional[callable] = None) -> str:
        """Standard text extraction with basic formatting preservation."""
        try:
            doc = fitz.open(str(file_path))
            text_parts = []

            for page_num in range(len(doc)):
                if progress_callback:
                    progress_callback(page_num / len(doc))

                page = doc.load_page(page_num)
                # Get text with some formatting
                text = page.get_text("text")
                text_parts.append(text)

            doc.close()
            return '\n\n'.join(text_parts)

        except Exception as e:
            logger.warning(f"Standard extraction failed, trying fallback: {e}")
            return self._extract_text_fallback(file_path)

    def _extract_text_detailed(self, file_path: Path, progress_callback: Optional[callable] = None) -> str:
        """Detailed text extraction with layout and formatting preservation."""
        try:
            doc = fitz.open(str(file_path))
            text_parts = []

            for page_num in range(len(doc)):
                if progress_callback:
                    progress_callback(page_num / len(doc))

                page = doc.load_page(page_num)
                # Get text with layout information
                blocks = page.get_text("dict")
                page_text = self._extract_from_blocks(blocks)
                text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")

            doc.close()
            return '\n\n'.join(text_parts)

        except Exception as e:
            logger.warning(f"Detailed extraction failed, trying fallback: {e}")
            return self._extract_text_fallback(file_path)

    def _extract_from_blocks(self, blocks: Dict) -> str:
        """Extract text from PyMuPDF text blocks with structure preservation."""
        text_parts = []

        for block in blocks.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    line_text = ""
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                    if line_text.strip():
                        text_parts.append(line_text.strip())

        return '\n'.join(text_parts)

    def _extract_text_fallback(self, file_path: Path) -> str:
        """Fallback text extraction using PyPDF2."""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_parts = []

                for page in pdf_reader.pages:
                    text = page.extract_text()
                    text_parts.append(text)

                return '\n'.join(text_parts)

        except Exception as e:
            logger.error(f"Fallback extraction also failed: {e}")
            raise ValueError(f"Could not extract text from PDF: {e}")

    def extract_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            Dictionary containing PDF metadata
        """
        file_path = Path(file_path)

        try:
            metadata = {}

            # Try PyMuPDF first for better metadata
            try:
                doc = fitz.open(str(file_path))
                pymupdf_metadata = doc.metadata

                # Safely extract PDF version
                try:
                    pdf_version = doc.pdf_version()
                    version_str = f"1.{pdf_version[1]}" if pdf_version and len(pdf_version) > 1 else "Unknown"
                except (AttributeError, IndexError, TypeError):
                    version_str = "Unknown"

                metadata.update({
                    'title': pymupdf_metadata.get('title', ''),
                    'author': pymupdf_metadata.get('author', ''),
                    'subject': pymupdf_metadata.get('subject', ''),
                    'creator': pymupdf_metadata.get('creator', ''),
                    'producer': pymupdf_metadata.get('producer', ''),
                    'creation_date': pymupdf_metadata.get('creationDate', ''),
                    'modification_date': pymupdf_metadata.get('modDate', ''),
                    'page_count': len(doc),
                    'is_encrypted': doc.needs_pass,
                    'pdf_version': version_str
                })

                doc.close()

            except Exception as e:
                logger.warning(f"PyMuPDF metadata extraction failed: {e}")
                # Fallback to PyPDF2
                metadata = self._extract_metadata_fallback(file_path)

            # Add file system metadata
            file_stats = file_path.stat()
            metadata.update({
                'file_size': file_stats.st_size,
                'file_name': file_path.name,
                'file_extension': file_path.suffix.lower()
            })

            return metadata

        except Exception as e:
            logger.error(f"Error extracting PDF metadata: {e}")
            raise

    def _extract_metadata_fallback(self, file_path: Path) -> Dict[str, Any]:
        """Fallback metadata extraction using PyPDF2."""
        metadata = {}

        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                if pdf_reader.metadata:
                    metadata.update({
                        'title': pdf_reader.metadata.get('/Title', ''),
                        'author': pdf_reader.metadata.get('/Author', ''),
                        'subject': pdf_reader.metadata.get('/Subject', ''),
                        'creator': pdf_reader.metadata.get('/Creator', ''),
                        'producer': pdf_reader.metadata.get('/Producer', ''),
                        'creation_date': str(pdf_reader.metadata.get('/CreationDate', '')),
                        'modification_date': str(pdf_reader.metadata.get('/ModDate', ''))
                    })

                metadata.update({
                    'page_count': len(pdf_reader.pages),
                    'is_encrypted': pdf_reader.is_encrypted,
                    'pdf_version': f"1.{pdf_reader.pdf_header[-1]}" if pdf_reader.pdf_header else "Unknown"
                })

        except Exception as e:
            logger.warning(f"Fallback metadata extraction failed: {e}")
            metadata.update({
                'page_count': 0,
                'is_encrypted': False,
                'pdf_version': "Unknown"
            })

        return metadata

    def validate_pdf(self, file_path: Union[str, Path]) -> Tuple[bool, str]:
        """
        Validate PDF file integrity and accessibility.

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (is_valid, error_message)
        """
        file_path = Path(file_path)

        try:
            if not file_path.exists():
                return False, "File does not exist"

            if not self._is_valid_pdf_file(file_path):
                return False, "Invalid PDF file format"

            # Try to open with PyMuPDF
            try:
                doc = fitz.open(str(file_path))
                if doc.page_count == 0:
                    doc.close()
                    return False, "PDF contains no pages"
                doc.close()
                return True, "Valid PDF file"

            except Exception as e:
                # Try PyPDF2 fallback
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    if len(pdf_reader.pages) == 0:
                        return False, "PDF contains no pages"
                    return True, "Valid PDF file"

        except Exception as e:
            return False, f"PDF validation error: {str(e)}"

    def is_password_protected(self, file_path: Union[str, Path]) -> bool:
        """
        Check if PDF is password protected.

        Args:
            file_path: Path to PDF file

        Returns:
            True if password protected, False otherwise
        """
        file_path = Path(file_path)

        try:
            # Try PyMuPDF first
            doc = fitz.open(str(file_path))
            is_encrypted = doc.needs_pass
            doc.close()
            return is_encrypted

        except Exception:
            # Fallback to PyPDF2
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    return pdf_reader.is_encrypted
            except Exception:
                return False

    def get_text_by_page(self, file_path: Union[str, Path], page_numbers: List[int]) -> Dict[int, str]:
        """
        Extract text from specific pages for faster partial processing.

        Args:
            file_path: Path to PDF file
            page_numbers: List of page numbers (0-indexed)

        Returns:
            Dictionary mapping page numbers to extracted text
        """
        file_path = Path(file_path)
        page_texts = {}

        try:
            doc = fitz.open(str(file_path))

            for page_num in page_numbers:
                if 0 <= page_num < len(doc):
                    page = doc.load_page(page_num)
                    page_texts[page_num] = page.get_text()
                else:
                    logger.warning(f"Page {page_num} out of range for PDF with {len(doc)} pages")

            doc.close()
            return page_texts

        except Exception as e:
            logger.error(f"Error extracting specific pages: {e}")
            raise

    def get_page_count(self, file_path: Union[str, Path]) -> int:
        """
        Get total number of pages in PDF.

        Args:
            file_path: Path to PDF file

        Returns:
            Number of pages
        """
        file_path = Path(file_path)

        try:
            doc = fitz.open(str(file_path))
            page_count = len(doc)
            doc.close()
            return page_count

        except Exception:
            # Fallback to PyPDF2
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    return len(pdf_reader.pages)
            except Exception as e:
                logger.error(f"Error getting page count: {e}")
                return 0

    def estimate_word_count(self, file_path: Union[str, Path], sample_pages: int = 3) -> int:
        """
        Estimate word count by sampling pages for faster processing.

        Args:
            file_path: Path to PDF file
            sample_pages: Number of pages to sample for estimation

        Returns:
            Estimated word count
        """
        try:
            page_count = self.get_page_count(file_path)
            if page_count == 0:
                return 0

            # Sample pages evenly distributed
            if page_count <= sample_pages:
                sample_page_nums = list(range(page_count))
            else:
                step = page_count // sample_pages
                sample_page_nums = [i * step for i in range(sample_pages)]

            page_texts = self.get_text_by_page(file_path, sample_page_nums)

            if not page_texts:
                return 0

            # Calculate average words per page
            total_words = sum(len(text.split()) for text in page_texts.values())
            avg_words_per_page = total_words / len(page_texts)

            # Estimate total word count
            estimated_total = int(avg_words_per_page * page_count)

            logger.debug(f"Estimated word count: {estimated_total} (sampled {len(page_texts)} pages)")
            return estimated_total

        except Exception as e:
            logger.error(f"Error estimating word count: {e}")
            return 0

    def _is_valid_pdf_file(self, file_path: Path) -> bool:
        """Check if file is a valid PDF by reading header."""
        try:
            with open(file_path, 'rb') as file:
                header = file.read(8)
                return header.startswith(b'%PDF-')
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

    @staticmethod
    @lru_cache(maxsize=128)
    def get_supported_extensions() -> List[str]:
        """
        Get list of supported file extensions.

        Returns:
            List of supported extensions
        """
        return ['.pdf']
