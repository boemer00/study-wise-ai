"""
Document management API routes
"""

import os
import tempfile
from pathlib import Path
from typing import List, Optional
import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Form
from datetime import datetime

from api.core.dependencies import get_current_user_id
from api.models.documents import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentDeleteResponse,
    DocumentMetadata,
    DocumentUploadRequest
)
from src.document_processor import DocumentProcessor
from src.flashcard_generator import FlashcardGenerator
from src.flashcards_db import save_generated_flashcards

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Global document processor instance
_processor_instance = None

def get_document_processor() -> DocumentProcessor:
    """Get or create DocumentProcessor instance."""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = DocumentProcessor()
    return _processor_instance

def get_flashcard_generator() -> FlashcardGenerator:
    """
    Get FlashcardGenerator instance.

    Returns:
        FlashcardGenerator: Initialized generator
    """
    return FlashcardGenerator()

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    tags: str = Form(""),  # Comma-separated tags
    generate_flashcards: bool = Form(True),
    flashcard_difficulty: str = Form("intermediate"),  # NEW: Flashcard difficulty level
    flashcard_limit: int = Form(8),  # NEW: Max number of flashcards to generate
    extract_tables: bool = Form(True),  # NEW: For PDF/DOCX
    extract_images_info: bool = Form(False),  # NEW: For PDF/DOCX
    preserve_formatting: bool = Form(False),  # NEW: For PDF/DOCX
    password: Optional[str] = Form(None),  # NEW: For encrypted PDFs
    user_id: str = Depends(get_current_user_id),
    processor: DocumentProcessor = Depends(get_document_processor),
    flashcard_gen: FlashcardGenerator = Depends(get_flashcard_generator)
) -> DocumentUploadResponse:
    """
    Upload and process a document with enhanced PDF/DOCX support.

    This endpoint now supports:
    - Text files (.txt, .md, .markdown): Basic text extraction
    - PDF files (.pdf): Advanced extraction with PyMuPDF/PyPDF2 fallback
    - DOCX files (.docx): Table extraction, image info, formatting preservation

    The uploaded document will be:
    1. Processed and validated
    2. Text extracted with appropriate handler
    3. Stored in Weaviate (vector database) for semantic search
    4. Metadata stored in Supabase for structured queries
    5. Made available for AI-powered study assistance

    Args:
        file: Uploaded file (supported: .txt, .md, .pdf, .docx)
        title: Optional custom title (defaults to filename)
        tags: Comma-separated tags for organization
        generate_flashcards: Whether to generate flashcards (future feature)
        flashcard_difficulty: Difficulty level for generated flashcards
        flashcard_limit: Maximum number of flashcards to generate
        extract_tables: Extract table content from PDF/DOCX
        extract_images_info: Extract image information from PDF/DOCX
        preserve_formatting: Preserve document formatting
        password: Password for encrypted PDFs
        user_id: Authenticated user ID
        processor: Document processor instance
        flashcard_gen: Flashcard generator instance

    Returns:
        DocumentUploadResponse with processing results and storage status

    Raises:
        HTTPException: 400 for invalid files, 413 for size limits, 500 for processing errors
    """
    temp_file_path = None

    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="File must have a name")

        # Get file extension and validate type
        file_extension = Path(file.filename).suffix.lower()
        if not processor.validate_file_type(file_extension):
            supported_types = processor.get_supported_file_types()
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{file_extension}'. Supported types: {', '.join(supported_types)}"
            )

        # Read file content
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="File appears to be empty")

        # File size validation with different limits for different types
        file_size = len(content)
        max_size_pdf_docx = 50 * 1024 * 1024  # 50MB for PDF/DOCX
        max_size_text = 10 * 1024 * 1024      # 10MB for text files

        is_pdf_docx = file_extension in {'.pdf', '.docx'}
        max_size = max_size_pdf_docx if is_pdf_docx else max_size_text
        max_size_text_display = "50MB" if is_pdf_docx else "10MB"

        if file_size > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size for {file_extension} files is {max_size_text_display}"
            )

        # Create temporary file for processing
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=file_extension,
            prefix=f"upload_{user_id}_"
        ) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Prepare processing options
        processing_options = {
            'extract_tables': extract_tables,
            'extract_images_info': extract_images_info,
            'preserve_formatting': preserve_formatting,
            'password': password,
            'extract_level': 'standard'  # Default extraction level
        }

        # Process the document
        result = processor.process_document(
            temp_file_path,
            extract_metadata=True,
            processing_options=processing_options
        )

        # Determine document title
        document_title = title or file.filename

        # Parse tags
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []

        # Prepare metadata for storage
        storage_metadata = result.get('metadata', {})
        storage_metadata.update({
            'tags': tag_list,
            'file_type': file_extension,
            'extract_tables': extract_tables,
            'extract_images_info': extract_images_info,
            'preserve_formatting': preserve_formatting,
            'processing_options': processing_options,
            'original_filename': file.filename
        })

        # Store document in databases (Weaviate + Supabase)
        extracted_content = result.get('content', '')
        if extracted_content.strip():
            storage_result = await processor.store_document(
                content=extracted_content,
                title=document_title,
                file_type=file_extension,
                file_size=file_size,
                user_id=user_id,
                metadata=storage_metadata
            )
        else:
            # Handle case where no content was extracted
            storage_result = None
            logger.warning(f"No content extracted from {file.filename}")

        # FLASHCARD GENERATION - Implement the missing feature!
        flashcards_created = 0
        flashcard_generation_error = None

        if generate_flashcards and storage_result and extracted_content.strip():
            try:
                logger.info(f"Generating flashcards for document {storage_result.document_id}")

                # Create text chunks for flashcard generation
                # Simple chunking by paragraphs, then by sentences if needed
                chunks = []
                if extracted_content:
                    # Split into paragraphs first
                    paragraphs = extracted_content.split('\n\n')
                    # Take meaningful chunks (not too short)
                    chunks = [p.strip() for p in paragraphs if len(p.strip()) > 100]

                    # If no good paragraphs, chunk by sentences
                    if not chunks:
                        sentences = extracted_content.split('. ')
                        current_chunk = ""
                        for sentence in sentences:
                            if len(current_chunk + sentence) < 500:
                                current_chunk += sentence + ". "
                            else:
                                if current_chunk.strip():
                                    chunks.append(current_chunk.strip())
                                current_chunk = sentence + ". "
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())

                # Generate flashcards if we have content
                if chunks:
                    # Set difficulty level
                    flashcard_gen.set_difficulty_level(flashcard_difficulty)

                    # Generate flashcards from document chunks
                    generated_flashcards = flashcard_gen.generate(chunks[:10], flashcard_difficulty)  # Limit chunks for performance

                    # Limit the number of flashcards
                    limited_flashcards = generated_flashcards[:flashcard_limit]
                    flashcards_created = len(limited_flashcards)

                    # Add document reference to each flashcard
                    for card in limited_flashcards:
                        card['document_id'] = storage_result.document_id
                        card['user_id'] = user_id
                        card['created_at'] = datetime.now().isoformat()

                    logger.info(f"Generated {flashcards_created} flashcards for document {storage_result.document_id}")

                    # Store flashcards in database
                    try:
                        saved_flashcard_ids = save_generated_flashcards(
                            flashcards=limited_flashcards,
                            user_id=user_id,
                            document_id=storage_result.document_id
                        )
                        logger.info(f"Successfully saved {len(saved_flashcard_ids)} flashcards to database")
                        flashcards_created = len(saved_flashcard_ids)
                    except Exception as db_error:
                        logger.error(f"Failed to save flashcards to database: {str(db_error)}")
                        flashcard_generation_error = f"Generated flashcards but failed to save: {str(db_error)}"
                        # Keep flashcards_created as the number generated even if saving failed

                else:
                    logger.warning(f"No suitable content chunks found for flashcard generation in {file.filename}")

            except Exception as e:
                logger.error(f"Error generating flashcards for {file.filename}: {str(e)}")
                flashcard_generation_error = str(e)
                # Don't fail the entire upload if flashcard generation fails

        # Prepare response
        response_data = {
            'document_id': storage_result.document_id if storage_result else f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(file.filename) % 10000:04d}",
            'title': document_title,
            'status': 'success' if storage_result and storage_result.status == 'success' else 'partial' if storage_result else 'failed',
            'message': f"Document '{document_title}' processed and stored successfully" if storage_result and storage_result.status == 'success' else f"Document processed but storage failed",
            'file_type': file_extension,
            'file_size': file_size,
            'supabase_id': storage_result.supabase_id if storage_result else None,
            'weaviate_id': storage_result.weaviate_id if storage_result else None,
            'chunks_created': storage_result.chunks_created if storage_result else 0,
            'flashcards_created': flashcards_created,  # ✅ IMPLEMENTED: Real flashcard count
            'processing_time': result.get('processing_metrics', {}).get('processing_time_seconds'),
            'errors': storage_result.errors if storage_result else ['No content extracted']
        }

        # Add flashcard generation info
        if generate_flashcards:
            response_data['flashcard_info'] = {
                'requested': True,
                'difficulty': flashcard_difficulty,
                'limit': flashcard_limit,
                'generated': flashcards_created,
                'generator_available': flashcard_gen.is_available(),
                'error': flashcard_generation_error
        }

        # Add enhanced metadata for PDF/DOCX
        if file_extension in {'.pdf', '.docx'}:
            metadata = result.get('metadata', {})
            response_data.update({
                'extracted_metadata': metadata,
                'page_count': metadata.get('page_count'),
                'word_count': metadata.get('word_count'),
                'has_tables': metadata.get('has_tables'),
                'has_images': metadata.get('has_images'),
                'extraction_warnings': result.get('extraction_warnings', [])
            })

        return DocumentUploadResponse(**response_data)

    except ValueError as e:
        # Handle validation errors (invalid files, unsupported formats, etc.)
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    user_id: str = Depends(get_current_user_id),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    processor: DocumentProcessor = Depends(get_document_processor)
) -> DocumentListResponse:
    """
    List documents for the authenticated user.

    Retrieves documents from Supabase database with metadata including:
    - Document title and file information
    - Processing status and timestamps
    - Vector storage information (chunk count)
    - Processing metadata (word count, page count, etc.)

    Args:
        user_id: Authenticated user ID
        skip: Number of documents to skip (for pagination)
        limit: Maximum number of documents to return (max 100)
        processor: Document processor instance

    Returns:
        DocumentListResponse with list of user's documents

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        # Retrieve documents from storage
        stored_documents = await processor.get_stored_documents(user_id, skip, limit)

        # Transform stored documents to API response format
        documents = []
        for doc in stored_documents:
            document_metadata = DocumentMetadata(
                document_id=doc.get('document_id', ''),
                title=doc.get('title', ''),
                file_name=doc.get('file_name'),
                file_size=doc.get('file_size'),
                file_type=doc.get('file_type'),
                source=doc.get('title', ''),
                status=doc.get('status', 'completed'),
                created_at=datetime.fromisoformat(doc['created_at']) if doc.get('created_at') else datetime.now(),
                updated_at=datetime.fromisoformat(doc['updated_at']) if doc.get('updated_at') else datetime.now(),
                chunks_count=doc.get('chunks_count', 0),
                flashcards_count=doc.get('flashcards_count', 0),
                tags=[],  # TODO: Implement tag parsing from metadata
                supabase_id=doc.get('document_id'),

                # Enhanced metadata fields
                author=doc.get('author'),
                creation_date=datetime.fromisoformat(doc['creation_date']) if doc.get('creation_date') else None,
                modification_date=datetime.fromisoformat(doc['modification_date']) if doc.get('modification_date') else None,
                word_count=doc.get('word_count'),
                page_count=doc.get('page_count'),
                language=doc.get('language'),
                is_encrypted=doc.get('is_encrypted', False),
                application=doc.get('application'),
                pdf_version=doc.get('pdf_version'),
                has_tables=doc.get('has_tables', False),
                has_images=doc.get('has_images', False),
                extraction_method=doc.get('extraction_method')
            )
            documents.append(document_metadata)

        # Calculate pagination info
        total_count = len(stored_documents)  # This is approximate - should be improved with actual count query
        has_next = len(stored_documents) == limit  # Simple check - there might be more

        return DocumentListResponse(
            documents=documents,
            total=total_count + skip if has_next else skip + len(stored_documents),  # Rough estimate
            skip=skip,
            limit=limit,
            has_next=has_next
        )

    except Exception as e:
        logger.error(f"Failed to list documents for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@router.get("/{document_id}/metadata")
async def get_document_metadata(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    processor: DocumentProcessor = Depends(get_document_processor)
):
    """
    Get document metadata without full content.

    Args:
        document_id: Document identifier
        user_id: Authenticated user ID
        processor: Document processor instance

    Returns:
        Document metadata

    Raises:
        HTTPException: If document not found or access denied
    """
    try:
        # TODO: Implement database lookup for document metadata
        # For now, return processor performance stats
        return {
            'document_id': document_id,
            'message': 'Metadata extraction endpoint - not yet implemented',
            'processor_stats': processor.get_performance_stats()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document metadata: {str(e)}")

@router.get("/supported-formats")
async def get_supported_formats(
    processor: DocumentProcessor = Depends(get_document_processor)
):
    """
    Get list of supported document formats.

    Args:
        processor: Document processor instance

    Returns:
        List of supported file extensions and their capabilities
    """
    try:
        supported_types = processor.get_supported_file_types()

        # Categorize file types with their capabilities
        format_info = {
            'text_formats': {
                'extensions': ['.txt', '.md', '.markdown'],
                'capabilities': ['text_extraction', 'basic_metadata']
            },
            'pdf_formats': {
                'extensions': ['.pdf'],
                'capabilities': [
                    'text_extraction', 'metadata_extraction', 'page_counting',
                    'password_protection_detection', 'fast_processing',
                    'word_count_estimation', 'performance_monitoring'
                ]
            },
            'office_formats': {
                'extensions': ['.docx'],
                'capabilities': [
                    'text_extraction', 'metadata_extraction', 'structured_content',
                    'table_extraction', 'image_info_extraction', 'formatting_preservation',
                    'fast_processing', 'word_counting', 'performance_monitoring'
                ]
            }
        }

        return {
            'supported_formats': format_info,
            'total_extensions': len(supported_types),
            'performance_optimized': True,
            'max_file_sizes': {
                'pdf_docx': '50MB',
                'text_markdown': '10MB'
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get supported formats: {str(e)}")

@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    processor: DocumentProcessor = Depends(get_document_processor)
) -> DocumentDeleteResponse:
    """
    Delete a document and its associated data from all storage systems.

    This will remove:
    - Document metadata from Supabase database
    - Document chunks and embeddings from Weaviate vector database
    - Clear any cached processing data

    Args:
        document_id: Document identifier
        user_id: Authenticated user ID
        processor: Document processor instance

    Returns:
        DocumentDeleteResponse with deletion status

    Raises:
        HTTPException: If document not found or deletion fails
    """
    try:
        # Attempt to delete from both storage systems
        deletion_success = await processor.delete_stored_document(document_id, user_id)

        if deletion_success:
            # Clear processor caches for good measure
            processor.clear_caches()

            return DocumentDeleteResponse(
                document_id=document_id,
                title=f"Document {document_id}",
                status='success',
                message=f"Document {document_id} successfully deleted from all storage systems",
                errors=[]
            )
        else:
            return DocumentDeleteResponse(
                document_id=document_id,
                title=f"Document {document_id}",
                status='partial',
                message=f"Document {document_id} deletion completed with some errors",
                errors=["Some storage systems may have failed - check logs"]
            )

    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

# Performance monitoring endpoint
@router.get("/performance/stats")
async def get_performance_stats(
    user_id: str = Depends(get_current_user_id),
    processor: DocumentProcessor = Depends(get_document_processor)
):
    """
    Get document processing performance statistics.

    Args:
        user_id: Authenticated user ID
        processor: Document processor instance

    Returns:
        Performance metrics for monitoring
    """
    try:
        stats = processor.get_performance_stats()

        return {
            'performance_stats': stats,
            'supported_formats': len(processor.get_supported_file_types()),
            'optimization_features': [
                'fast_pdf_processing_with_pymupdf',
                'efficient_docx_processing',
                'intelligent_fallback_mechanisms',
                'performance_monitoring',
                'memory_optimization',
                'timeout_protection'
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance stats: {str(e)}")
