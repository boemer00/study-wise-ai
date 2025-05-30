"""
Document management API routes
"""

import os
import tempfile
from pathlib import Path
from typing import List, Optional
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
from src.document_processor import DocumentProcessor, ProcessingError


router = APIRouter()

# Global document processor instance
_processor_instance = None


async def get_document_processor() -> DocumentProcessor:
    """Get or create DocumentProcessor instance."""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = DocumentProcessor()
    return _processor_instance


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    tags: str = Form(""),  # Comma-separated tags
    generate_flashcards: bool = Form(True),
    user_id: str = Depends(get_current_user_id),
    processor: DocumentProcessor = Depends(get_document_processor)
) -> DocumentUploadResponse:
    """
    Upload and process a document for RAG.

    Args:
        file: Uploaded document file
        title: Optional document title (defaults to filename)
        tags: Comma-separated tags
        generate_flashcards: Whether to generate flashcards
        user_id: Authenticated user ID
        processor: Document processor instance

    Returns:
        Upload status and document metadata

    Raises:
        HTTPException: If upload or processing fails
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Check file size (10MB limit)
    max_size = 10 * 1024 * 1024  # 10MB
    if hasattr(file, 'size') and file.size and file.size > max_size:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    # Supported file types (only implemented ones)
    supported_extensions = {'.txt', '.md'}  # Remove PDF, DOCX until implemented
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_extension}. Currently supported: {', '.join(supported_extensions)}. PDF and DOCX support coming soon!"
        )

    temp_file_path = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file_path = temp_file.name

            # Read and write file content
            content = await file.read()
            if len(content) > max_size:
                raise HTTPException(status_code=413, detail="File content too large (max 10MB)")

            temp_file.write(content)

        # Extract text content (only .txt and .md supported for now)
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            text_content = f.read()

        # Prepare metadata
        document_title = title or Path(file.filename).stem
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []

        metadata = {
            'title': document_title,
            'file_name': file.filename,
            'file_size': len(content),
            'file_type': file_extension,
            'source': 'upload',
            'user_id': user_id,
            'tags': tag_list
        }

        # Process document
        result = await processor.process_document(
            content=text_content,
            metadata=metadata,
            generate_flashcards=generate_flashcards
        )

        # Return response
        return DocumentUploadResponse(
            document_id=result.document_id,
            title=document_title,
            status=result.status,
            message=f"Document '{document_title}' processed successfully" if result.status == 'success'
                   else f"Document '{document_title}' processed with issues",
            file_type=file_extension,
            file_size=len(content),
            supabase_id=result.supabase_id,
            weaviate_id=result.weaviate_id,
            chunks_created=result.chunks_created,
            flashcards_created=result.flashcards_created,
            processing_time=result.processing_time,
            errors=result.errors
        )

    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
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
    List user's uploaded documents.

    Args:
        user_id: Authenticated user ID
        skip: Number of documents to skip
        limit: Maximum documents to return
        processor: Document processor instance

    Returns:
        List of user's documents
    """
    try:
        # Try to query documents from Supabase
        response = processor.supabase_client.table('documents') \
            .select('*') \
            .eq('metadata->>user_id', user_id) \
            .order('created_at', desc=True) \
            .range(skip, skip + limit - 1) \
            .execute()

        documents = []
        for doc in response.data:
            metadata = DocumentMetadata(
                document_id=doc['document_id'],
                title=doc['title'],
                file_name=doc.get('file_name'),
                file_size=doc.get('file_size'),
                file_type=doc.get('file_type'),
                source=doc['source'],
                status=doc['status'],
                created_at=datetime.fromisoformat(doc['created_at']),
                updated_at=datetime.fromisoformat(doc['updated_at']),
                chunks_count=doc.get('chunks_count', 0),
                flashcards_count=0,  # TODO: Count flashcards
                tags=doc.get('tags', []),
                error_message=doc.get('error_message'),
                supabase_id=doc.get('supabase_id', doc['document_id'])
            )
            documents.append(metadata)

        # Get total count
        count_response = processor.supabase_client.table('documents') \
            .select('id', count='exact') \
            .eq('metadata->>user_id', user_id) \
            .execute()

        total = count_response.count or 0
        has_next = skip + limit < total

        return DocumentListResponse(
            documents=documents,
            total=total,
            skip=skip,
            limit=limit,
            has_next=has_next
        )

    except Exception as e:
        # If database table doesn't exist, return demo data
        if 'does not exist' in str(e):
            # Return demo documents for development
            demo_documents = [
                DocumentMetadata(
                    document_id="demo-doc-1",
                    title="Machine Learning Basics",
                    file_name="ml_basics.txt",
                    file_size=15420,
                    file_type=".txt",
                    source="upload",
                    status="completed",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    chunks_count=5,
                    flashcards_count=12,
                    tags=["machine learning", "AI", "basics"]
                ),
                DocumentMetadata(
                    document_id="demo-doc-2",
                    title="Python Programming Guide",
                    file_name="python_guide.md",
                    file_size=28900,
                    file_type=".md",
                    source="upload",
                    status="completed",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    chunks_count=8,
                    flashcards_count=20,
                    tags=["python", "programming", "tutorial"]
                )
            ]

            # Apply pagination to demo data
            paginated_docs = demo_documents[skip:skip + limit]

            return DocumentListResponse(
                documents=paginated_docs,
                total=len(demo_documents),
                skip=skip,
                limit=limit,
                has_next=skip + limit < len(demo_documents)
            )
        else:
            raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    processor: DocumentProcessor = Depends(get_document_processor)
) -> DocumentDeleteResponse:
    """
    Delete a document and its vectors.

    Args:
        document_id: ID of document to delete
        user_id: Authenticated user ID
        processor: Document processor instance

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If document not found or deletion fails
    """
    try:
        # Check if document exists and belongs to user
        doc_response = processor.supabase_client.table('documents') \
            .select('title, metadata') \
            .eq('document_id', document_id) \
            .execute()

        if not doc_response.data:
            raise HTTPException(status_code=404, detail="Document not found")

        doc = doc_response.data[0]
        doc_user_id = doc.get('metadata', {}).get('user_id')

        if doc_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        title = doc['title']

        # Delete from Supabase
        processor.supabase_client.table('documents') \
            .delete() \
            .eq('document_id', document_id) \
            .execute()

        # TODO: Delete from Weaviate vector database
        # TODO: Delete associated flashcards

        return DocumentDeleteResponse(
            document_id=document_id,
            title=title,
            status='success',
            message=f"Document '{title}' deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        return DocumentDeleteResponse(
            document_id=document_id,
            title="Unknown",
            status='failed',
            message=f"Failed to delete document: {str(e)}",
            errors=[str(e)]
        )
