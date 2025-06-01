"""
File handlers package for processing different document types.

This package contains specialized handlers for:
- PDF files (pdf_handler.py)
- DOCX files (docx_handler.py)
"""

from .pdf_handler import PDFHandler
from .docx_handler import DOCXHandler

__all__ = ["PDFHandler", "DOCXHandler"]
