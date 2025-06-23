"""
Document processing module for Study-Wise AI.

This module provides the DocumentProcessor class that serves as the bridge between
Supabase (structured data) and Weaviate (vector embeddings), handling document
ingestion, processing, and synchronization across both systems.
"""

import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Literal, AsyncGenerator
from pathlib import Path
import uuid
import time
import hashlib
import weaviate.classes as wvc

from .supabase_client import get_supabase_client
from .weaviate_client import create_weaviate_client

# Configure logging
logger = logging.getLogger(__name__)

# Import existing handlers
from .file_handlers.text_handler import TextHandler
from .file_handlers.markdown_handler import MarkdownHandler

# Import new handlers
from .file_handlers.pdf_handler import PDFHandler
from .file_handlers.docx_handler import DOCXHandler

# Data Models
@dataclass
class DocumentInput:
    """Input data structure for document processing."""
    content: str
    metadata: Dict[str, Any]
    generate_flashcards: bool = True
    chunk_size: Optional[int] = None
    overlap_size: Optional[int] = None


@dataclass
class ProcessingResult:
    """Result of document processing operations."""
    document_id: str
    supabase_id: Optional[str] = None
    weaviate_id: Optional[str] = None
    flashcards_created: int = 0
    chunks_created: int = 0
    status: Literal['success', 'partial', 'failed'] = 'success'
    errors: List[str] = field(default_factory=list)
    processing_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchProcessingResult:
    """Result of batch document processing operations."""
    total_documents: int
    successful: int
    partial: int
    failed: int
    results: List[ProcessingResult]
    total_processing_time: float
    errors: List[str] = field(default_factory=list)


@dataclass
class DocumentStatus:
    """Status information for a processed document."""
    document_id: str
    title: str
    status: Literal['processing', 'completed', 'failed', 'partial']
    created_at: datetime
    updated_at: datetime
    supabase_synced: bool
    weaviate_synced: bool
    flashcards_count: int
    chunks_count: int
    error_message: Optional[str] = None


@dataclass
class DocumentChunk:
    """Represents a chunk of a larger document."""
    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    start_position: int
    end_position: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProcessingError(Exception):
    """Custom exception for document processing errors."""

    def __init__(self, message: str, document_id: Optional[str] = None, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.document_id = document_id
        self.errors = errors or []


class DocumentProcessor:
    """
    Enhanced document processor with PDF/DOCX support and performance optimizations.

    Handles multiple file formats with intelligent routing, caching, and comprehensive
    metadata extraction for fast document processing.
    """

    def __init__(self):
        """Initialize document processor with all file handlers."""
        self.text_handler = TextHandler()
        self.markdown_handler = MarkdownHandler()

        # Initialize new handlers with performance settings
        self.pdf_handler = PDFHandler(timeout_seconds=30)
        self.docx_handler = DOCXHandler(timeout_seconds=30)

        # Supported file types mapping
        self._file_handlers = {
            '.txt': self.text_handler,
            '.md': self.markdown_handler,
            '.markdown': self.markdown_handler,
            '.pdf': self.pdf_handler,
            '.docx': self.docx_handler
        }

        # Processing cache for performance
        self._processing_cache = {}

        # Initialize database clients
        self._initialize_database_clients()

        logger.info("DocumentProcessor initialized with PDF/DOCX support")

    def _initialize_database_clients(self):
        """Initialize Weaviate and Supabase clients with graceful fallback."""
        self.weaviate_client = None
        self.supabase_client = None

        try:
            # Try to initialize Weaviate client
            from .weaviate_client import create_weaviate_client
            self.weaviate_client = create_weaviate_client()
            logger.info("Weaviate client initialized successfully")
        except Exception as e:
            logger.warning(f"Weaviate client initialization failed: {e}")
            logger.info("Document processing will work without vector storage")

        try:
            # Try to initialize Supabase client
            from .supabase_client import get_supabase_client
            self.supabase_client = get_supabase_client()
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.warning(f"Supabase client initialization failed: {e}")
            logger.info("Document processing will work without metadata storage")

    async def store_document(
        self,
        content: str,
        title: str,
        file_type: str,
        file_size: int,
        user_id: str,
        user_jwt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> ProcessingResult:
        """
        Store document in both Weaviate (vector) and Supabase (metadata) databases.

        Args:
            content: Document text content
            title: Document title/filename
            file_type: File extension (e.g., '.pdf', '.docx')
            file_size: File size in bytes
            user_id: User who uploaded the document
            metadata: Additional document metadata
            chunk_size: Size of text chunks for vector storage
            overlap: Overlap between chunks

        Returns:
            ProcessingResult with storage status
        """
        start_time = time.time()
        document_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(title) % 10000:04d}"

        result = ProcessingResult(
            document_id=document_id,
            status='success',
            metadata=metadata or {}
        )

        try:
            # Step 1: Store metadata in Supabase
            supabase_id = None
            if self.supabase_client:
                try:
                    supabase_id = await self._store_document_metadata(
                        document_id, title, file_type, file_size, user_id, user_jwt, metadata, content
                    )
                    result.supabase_id = supabase_id
                    logger.info(f"Document metadata stored in Supabase: {supabase_id}")
                except Exception as e:
                    logger.error(f"Failed to store in Supabase: {e}")
                    logger.error(f"Supabase error details: {type(e).__name__}: {str(e)}")
                    result.errors.append(f"Supabase storage failed: {str(e)}")

            # Step 2: Chunk text and store in Weaviate
            weaviate_ids = []
            if self.weaviate_client and content.strip():
                try:
                    chunks = self._chunk_text(content, chunk_size, overlap)
                    weaviate_ids = await self._store_document_chunks(
                        document_id, title, chunks, user_id, supabase_id, metadata
                    )
                    result.weaviate_id = weaviate_ids[0] if weaviate_ids else None
                    result.chunks_created = len(weaviate_ids)
                    logger.info(f"Document chunks stored in Weaviate: {len(weaviate_ids)} chunks")
                except Exception as e:
                    logger.error(f"Failed to store in Weaviate: {e}")
                    result.errors.append(f"Weaviate storage failed: {str(e)}")

            # Update processing metrics
            result.processing_time = time.time() - start_time

            # Determine final status
            if result.errors:
                result.status = 'partial' if (supabase_id or weaviate_ids) else 'failed'

            return result

        except Exception as e:
            logger.error(f"Document storage failed: {e}")
            result.status = 'failed'
            result.errors.append(str(e))
            return result

    async def _store_document_metadata(
        self,
        document_id: str,
        title: str,
        file_type: str,
        file_size: int,
        user_id: str,
        user_jwt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        content: str = ""
    ) -> str:
        """Store document metadata in Supabase."""
        document_data = {
            'document_id': document_id,
            'title': title,
            'file_name': title,
            'file_type': file_type,
            'file_size': file_size,
            'user_id': user_id,
            'status': 'completed',
            'content': content,
            'source': 'upload',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'chunks_count': 0,  # Will be updated after chunking
            'flashcards_count': 0
        }

        # Add extracted metadata
        if metadata:
            document_data.update({
                'author': metadata.get('author'),
                'creation_date': self._format_timestamp(metadata.get('creation_date')),
                'modification_date': self._format_timestamp(metadata.get('modification_date')),
                'word_count': metadata.get('word_count'),
                'page_count': metadata.get('page_count'),
                'language': metadata.get('language'),
                'is_encrypted': metadata.get('is_encrypted', False),
                'application': metadata.get('application'),
                'pdf_version': metadata.get('pdf_version'),
                'has_tables': metadata.get('has_tables', False),
                'has_images': metadata.get('has_images', False),
                'extraction_method': metadata.get('extraction_method')
            })

        # Insert into Supabase (always via service-role client).
        # Using a user-authenticated client would require both access and refresh tokens,
        # but the backend only receives the JWT access token in the Authorization header.
        # To avoid validation errors (`refresh_token` None), we consistently use the
        # service-role client which has full insert privileges and scopes by user_id.

        result = self.supabase_client.table('documents').insert(document_data).execute()

        if result.data:
            return result.data[0]['document_id']
        else:
            raise Exception("Failed to insert document metadata")

    async def _store_document_chunks(
        self,
        document_id: str,
        title: str,
        chunks: List[str],
        user_id: str,
        supabase_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Store document chunks in Weaviate with embeddings."""
        if not self.weaviate_client:
            return []

        chunk_ids = []

        try:
            # Create schema if it doesn't exist
            self.weaviate_client.create_schema()

            # Prepare chunk data for batch insertion
            chunk_data = []
            for i, chunk_content in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{i:04d}"

                chunk_obj = {
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    "title": title,
                    "content": chunk_content,
                    "page_number": metadata.get('page_number', 1) if metadata else 1,
                    "chunk_index": i,
                    "user_id": user_id,
                    "source": title,
                    "tags": metadata.get('tags', []) if metadata else [],
                    "supabase_id": supabase_id,
                    "created_at": datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                    "file_type": metadata.get('file_type', '') if metadata else '',
                    "word_count": len(chunk_content.split()),
                    "character_count": len(chunk_content)
                }

                chunk_data.append(chunk_obj)
                chunk_ids.append(chunk_id)

            # Batch insert chunks into Weaviate
            collection = self.weaviate_client.client.collections.get("Document")

            with collection.batch.dynamic() as batch:
                for chunk in chunk_data:
                    batch.add_object(
                        properties=chunk
                    )

            # Update chunk count in Supabase if available
            if self.supabase_client and supabase_id:
                self.supabase_client.table('documents').update({
                    'chunks_count': len(chunks),
                    'updated_at': datetime.now().isoformat()
                }).eq('document_id', document_id).execute()

            return chunk_ids

        except Exception as e:
            logger.error(f"Failed to store chunks in Weaviate: {e}")
            raise

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for vector storage."""
        if not text.strip():
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < text_length:
                # Look for sentence endings
                for punct in ['. ', '! ', '? ']:
                    last_punct = text.rfind(punct, start, end)
                    if last_punct > start + chunk_size // 2:
                        end = last_punct + len(punct)
                        break

                # If no good sentence break, try paragraph break
                if end == start + chunk_size:
                    last_para = text.rfind('\n\n', start, end)
                    if last_para > start + chunk_size // 2:
                        end = last_para + 2

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position with overlap
            start = max(start + chunk_size - overlap, end - overlap)

            # Prevent infinite loops
            if start >= text_length:
                break

        return chunks

    async def get_stored_documents(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Retrieve stored documents for a user from Supabase."""
        if not self.supabase_client:
            return []

        try:
            result = self.supabase_client.table('documents')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .range(skip, skip + limit - 1)\
                .execute()

            return result.data if result.data else []

        except Exception as e:
            logger.error(f"Failed to retrieve documents: {e}")
            return []

    async def delete_stored_document(self, document_id: str, user_id: str) -> bool:
        """Delete document from both Weaviate and Supabase."""
        success = True

        try:
            # Delete from Weaviate
            if self.weaviate_client:
                try:
                    collection = self.weaviate_client.client.collections.get("Document")
                    # Delete all chunks for this document
                    collection.data.delete_many(
                        where=wvc.query.Filter.by_property("document_id").equal(document_id)
                    )
                    logger.info(f"Deleted document chunks from Weaviate: {document_id}")
                except Exception as e:
                    logger.error(f"Failed to delete from Weaviate: {e}")
                    success = False

            # Delete from Supabase
            if self.supabase_client:
                try:
                    self.supabase_client.table('documents')\
                        .delete()\
                        .eq('document_id', document_id)\
                        .eq('user_id', user_id)\
                        .execute()
                    logger.info(f"Deleted document metadata from Supabase: {document_id}")
                except Exception as e:
                    logger.error(f"Failed to delete from Supabase: {e}")
                    success = False

            return success

        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False

    def process_document(
        self,
        file_path: Union[str, Path],
        extract_metadata: bool = True,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process document with enhanced options for PDF/DOCX files.

        Args:
            file_path: Path to document file
            extract_metadata: Whether to extract comprehensive metadata
            processing_options: Additional processing options for specific file types

        Returns:
            Dictionary containing processed document data
        """
        start_time = time.time()
        file_path = Path(file_path)

        try:
            # Validate file exists and get basic info
            if not file_path.exists():
                raise FileNotFoundError(f"Document not found: {file_path}")

            file_extension = file_path.suffix.lower()

            # Validate file type
            if not self.validate_file_type(file_extension):
                raise ValueError(f"Unsupported file type: {file_extension}")

            # Prepare processing options
            options = processing_options or {}

            # Route to appropriate processor
            if file_extension == '.pdf':
                result = self.process_pdf_document(file_path, extract_metadata, options)
            elif file_extension == '.docx':
                result = self.process_docx_document(file_path, extract_metadata, options)
            elif file_extension in ['.txt', '.md', '.markdown']:
                result = self._process_text_document(file_path, extract_metadata)
            else:
                raise ValueError(f"No handler available for {file_extension}")

            # Add processing metrics
            processing_time = time.time() - start_time
            result['processing_metrics'] = {
                'processing_time_seconds': round(processing_time, 3),
                'file_size_bytes': file_path.stat().st_size,
                'processing_speed_mb_per_second': round(
                    (file_path.stat().st_size / (1024 * 1024)) / max(processing_time, 0.001), 2
                )
            }

            logger.info(f"Document processed in {processing_time:.2f}s: {file_path.name}")
            return result

        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            raise

    def process_pdf_document(
        self,
        file_path: Path,
        extract_metadata: bool = True,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process PDF document with performance optimizations.

        Args:
            file_path: Path to PDF file
            extract_metadata: Whether to extract metadata
            options: PDF-specific processing options

        Returns:
            Dictionary containing processed PDF data
        """
        options = options or {}

        try:
            # Validate PDF
            is_valid, error_msg = self.pdf_handler.validate_pdf(file_path)
            if not is_valid:
                raise ValueError(f"Invalid PDF: {error_msg}")

            result = {
                'file_path': str(file_path),
                'file_type': 'pdf',
                'is_valid': True,
                'extraction_warnings': []
            }

            # Check for password protection
            if self.pdf_handler.is_password_protected(file_path):
                password = options.get('password')
                if not password:
                    result['extraction_warnings'].append("PDF is password protected but no password provided")
                    raise ValueError("PDF is password protected")

            # Extract text with specified level
            extract_level = options.get('extract_level', 'fast')
            progress_callback = options.get('progress_callback')

            text_content = self.pdf_handler.extract_text(
                file_path,
                extract_level=extract_level,
                progress_callback=progress_callback
            )

            result['content'] = text_content
            result['text_length'] = len(text_content)

            # Extract metadata if requested
            if extract_metadata:
                pdf_metadata = self.pdf_handler.extract_metadata(file_path)
                result['metadata'] = self._merge_extracted_metadata(pdf_metadata, file_path)

                # Add performance estimates
                result['metadata']['estimated_word_count'] = self.pdf_handler.estimate_word_count(file_path)

            # Add PDF-specific information
            result.update({
                'page_count': self.pdf_handler.get_page_count(file_path),
                'is_encrypted': self.pdf_handler.is_password_protected(file_path)
            })

            return result

        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            raise

    def process_docx_document(
        self,
        file_path: Path,
        extract_metadata: bool = True,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process DOCX document with performance optimizations.

        Args:
            file_path: Path to DOCX file
            extract_metadata: Whether to extract metadata
            options: DOCX-specific processing options

        Returns:
            Dictionary containing processed DOCX data
        """
        options = options or {}

        try:
            # Validate DOCX
            is_valid, error_msg = self.docx_handler.validate_docx(file_path)
            if not is_valid:
                raise ValueError(f"Invalid DOCX: {error_msg}")

            result = {
                'file_path': str(file_path),
                'file_type': 'docx',
                'is_valid': True,
                'extraction_warnings': []
            }

            # Extract text content
            preserve_formatting = options.get('preserve_formatting', False)
            progress_callback = options.get('progress_callback')

            text_content = self.docx_handler.extract_text(
                file_path,
                preserve_formatting=preserve_formatting,
                progress_callback=progress_callback
            )

            result['content'] = text_content
            result['text_length'] = len(text_content)

            # Extract metadata if requested
            if extract_metadata:
                docx_metadata = self.docx_handler.extract_metadata(file_path)
                result['metadata'] = self._merge_extracted_metadata(docx_metadata, file_path)

            # Extract structured content if requested
            if options.get('extract_structured_content', False):
                try:
                    structured_content = self.docx_handler.extract_structured_content(file_path)
                    result['structured_content'] = structured_content
                except Exception as e:
                    result['extraction_warnings'].append(f"Could not extract structured content: {e}")

            # Extract tables if requested
            if options.get('extract_tables', False):
                try:
                    tables = self.docx_handler.extract_tables(file_path)
                    result['tables'] = tables
                    result['table_count'] = len(tables)
                except Exception as e:
                    result['extraction_warnings'].append(f"Could not extract tables: {e}")

            # Extract image information if requested
            if options.get('extract_images_info', False):
                try:
                    images_info = self.docx_handler.extract_images_info(file_path)
                    result['images_info'] = images_info
                    result['image_count'] = len(images_info)
                except Exception as e:
                    result['extraction_warnings'].append(f"Could not extract image info: {e}")

            return result

        except Exception as e:
            logger.error(f"Error processing DOCX {file_path}: {str(e)}")
            raise

    def _process_text_document(self, file_path: Path, extract_metadata: bool = True) -> Dict[str, Any]:
        """Process text/markdown documents (existing functionality)."""
        file_extension = file_path.suffix.lower()

        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            result = {
                'file_path': str(file_path),
                'file_type': file_extension.lstrip('.'),
                'content': content,
                'text_length': len(content),
                'is_valid': True
            }

            if extract_metadata:
                # Basic metadata for text files
                file_stats = file_path.stat()
                result['metadata'] = {
                    'file_name': file_path.name,
                    'file_size': file_stats.st_size,
                    'file_extension': file_extension,
                    'creation_date': file_stats.st_ctime,
                    'modification_date': file_stats.st_mtime,
                    'word_count': len(content.split()),
                    'character_count': len(content),
                    'line_count': len(content.splitlines())
                }

            return result

        except Exception as e:
            logger.error(f"Error processing text document {file_path}: {str(e)}")
            raise

    def get_supported_file_types(self) -> List[str]:
        """
        Get list of all supported file extensions.

        Returns:
            List of supported file extensions
        """
        return list(self._file_handlers.keys())

    def validate_file_type(self, file_extension: str) -> bool:
        """
        Validate if file type is supported.

        Args:
            file_extension: File extension to validate (with or without dot)

        Returns:
            True if supported, False otherwise
        """
        if not file_extension.startswith('.'):
            file_extension = f'.{file_extension}'

        return file_extension.lower() in self._file_handlers

    def extract_file_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Extract metadata from file without full content processing.

        Args:
            file_path: Path to file

        Returns:
            Dictionary containing file metadata
        """
        file_path = Path(file_path)
        file_extension = file_path.suffix.lower()

        try:
            if file_extension == '.pdf':
                return self.pdf_handler.extract_metadata(file_path)
            elif file_extension == '.docx':
                return self.docx_handler.extract_metadata(file_path)
            else:
                # Basic metadata for other file types
                file_stats = file_path.stat()
                return {
                    'file_name': file_path.name,
                    'file_size': file_stats.st_size,
                    'file_extension': file_extension,
                    'creation_date': file_stats.st_ctime,
                    'modification_date': file_stats.st_mtime
                }

        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {str(e)}")
            raise

    def _get_file_handler(self, file_extension: str):
        """
        Get appropriate file handler for extension.

        Args:
            file_extension: File extension

        Returns:
            File handler instance
        """
        return self._file_handlers.get(file_extension.lower())

    def _merge_extracted_metadata(self, extracted_metadata: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """
        Merge extracted metadata with additional computed metadata.

        Args:
            extracted_metadata: Metadata from file handler
            file_path: Path to file

        Returns:
            Enhanced metadata dictionary
        """
        # Start with extracted metadata
        merged_metadata = extracted_metadata.copy()

        # Add computed fields
        if 'word_count' in merged_metadata and merged_metadata['word_count'] > 0:
            # Estimate reading time (average 200 words per minute)
            estimated_reading_time_minutes = max(1, merged_metadata['word_count'] // 200)
            merged_metadata['estimated_reading_time_minutes'] = estimated_reading_time_minutes

        # Add file hash for deduplication
        try:
            file_hash = self._calculate_file_hash(file_path)
            merged_metadata['file_hash'] = file_hash
        except Exception as e:
            logger.warning(f"Could not calculate file hash: {e}")
            merged_metadata['file_hash'] = None

        # Add processing timestamp
        merged_metadata['processed_at'] = time.time()

        return merged_metadata

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file for deduplication."""
        hash_sha256 = hashlib.sha256()

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)

        return hash_sha256.hexdigest()

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics from all handlers.

        Returns:
            Dictionary with performance metrics
        """
        return {
            'pdf_handler_stats': self.pdf_handler.get_performance_stats(),
            'docx_handler_stats': self.docx_handler.get_performance_stats()
        }

    def _format_timestamp(self, timestamp: Optional[float]) -> Optional[str]:
        """Format timestamp for PostgreSQL."""
        if timestamp is None:
            return None
        try:
            return datetime.fromtimestamp(timestamp).isoformat()
        except (ValueError, TypeError, OSError):
            return None

    def clear_caches(self) -> None:
        """Clear all caches to free memory."""
        self._processing_cache.clear()
        self.docx_handler.clear_cache()
        logger.info("All caches cleared")

    async def delete_all_user_data(self, user_id: str) -> bool:
        """
        Delete all data for a user from both Supabase and Weaviate.
        
        Args:
            user_id: The user ID to clean up
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Starting cleanup for user: {user_id}")
        success = True
        
        try:
            # 1. Delete from Weaviate first (vector chunks)
            if self.weaviate_client:
                try:
                    collection = self.weaviate_client.client.collections.get("Document")
                    collection.data.delete_many(
                        where=wvc.query.Filter.by_property("user_id").equal(user_id)
                    )
                    logger.info(f"Deleted all Weaviate chunks for user: {user_id}")
                except Exception as e:
                    logger.error(f"Failed to delete Weaviate data for user {user_id}: {e}")
                    success = False
            
            # 2. Delete from Supabase (metadata)
            if self.supabase_client:
                try:
                    # Delete documents
                    docs_result = self.supabase_client.table('documents')\
                        .delete()\
                        .eq('user_id', user_id)\
                        .execute()
                    
                    # Try to delete flashcards if table exists
                    try:
                        cards_result = self.supabase_client.table('flashcards')\
                            .delete()\
                            .eq('user_id', user_id)\
                            .execute()
                        logger.info(f"Deleted flashcards for user: {user_id}")
                    except Exception:
                        # Flashcards table may not exist yet
                        pass
                    
                    logger.info(f"Deleted all Supabase data for user: {user_id}")
                except Exception as e:
                    logger.error(f"Failed to delete Supabase data for user {user_id}: {e}")
                    success = False
            
            if success:
                logger.info(f"Successfully cleaned up all data for user: {user_id}")
            else:
                logger.warning(f"Partial cleanup completed for user: {user_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"User cleanup failed for {user_id}: {e}")
            return False
