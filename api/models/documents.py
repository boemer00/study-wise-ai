"""
Document management Pydantic models
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Document metadata for API responses."""
    document_id: str
    title: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    source: str
    status: Literal['processing', 'completed', 'failed', 'partial']
    created_at: datetime
    updated_at: datetime
    chunks_count: int = 0
    flashcards_count: int = 0
    tags: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    supabase_id: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    """Response for document upload operations."""
    document_id: str
    title: str
    status: Literal['success', 'partial', 'failed']
    message: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    supabase_id: Optional[str] = None
    weaviate_id: Optional[str] = None
    chunks_created: int = 0
    flashcards_created: int = 0
    processing_time: Optional[float] = None
    errors: List[str] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    """Response for document listing operations."""
    documents: List[DocumentMetadata]
    total: int
    skip: int
    limit: int
    has_next: bool


class DocumentDeleteResponse(BaseModel):
    """Response for document deletion operations."""
    document_id: str
    title: str
    status: Literal['success', 'failed']
    message: str
    errors: List[str] = Field(default_factory=list)


class DocumentUploadRequest(BaseModel):
    """Optional metadata for document upload."""
    title: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    generate_flashcards: bool = True
