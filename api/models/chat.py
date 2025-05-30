"""
Pydantic models for chat/conversation API
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """Request model for sending a message to AI."""

    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    user_documents: Optional[List[str]] = Field(None, description="Document IDs to search")
    processing_options: Optional[Dict[str, Any]] = Field(None, description="Processing options")


class ChatMessageResponse(BaseModel):
    """Response model for AI chat message."""

    answer: str = Field(..., description="AI response")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Source documents")
    conversation_id: str = Field(..., description="Conversation ID")
    response_id: str = Field(..., description="Response ID")
    follow_up_suggestions: List[str] = Field(default_factory=list, description="Suggested follow-up questions")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Response confidence")
    processing_time_ms: Optional[int] = Field(None, ge=0, description="Processing time in milliseconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")


class ConversationCreateRequest(BaseModel):
    """Request model for creating a new conversation."""

    topic_focus: Optional[str] = Field(None, max_length=200, description="Initial topic focus")
    active_documents: Optional[List[str]] = Field(None, description="Active document IDs")
    initial_context: Optional[Dict[str, Any]] = Field(None, description="Initial conversation context")


class ConversationCreateResponse(BaseModel):
    """Response model for conversation creation."""

    conversation_id: str = Field(..., description="Created conversation ID")
    user_id: str = Field(..., description="User ID")
    topic_focus: Optional[str] = Field(None, description="Topic focus")
    created_at: datetime = Field(..., description="Creation timestamp")


class ConversationMessage(BaseModel):
    """Model for conversation message in history."""

    message_id: str = Field(..., description="Message ID")
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="Message sources")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history."""

    conversation_id: str = Field(..., description="Conversation ID")
    messages: List[ConversationMessage] = Field(..., description="Conversation messages")
    total_messages: int = Field(..., ge=0, description="Total message count")
    has_more: bool = Field(..., description="Whether more messages exist")


class ConversationSummary(BaseModel):
    """Model for conversation summary."""

    conversation_id: str = Field(..., description="Conversation ID")
    topic_focus: Optional[str] = Field(None, description="Topic focus")
    status: str = Field(..., description="Conversation status")
    message_count: int = Field(..., ge=0, description="Total messages")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    ended_at: Optional[datetime] = Field(None, description="End timestamp")


class ConversationUpdateRequest(BaseModel):
    """Request model for updating conversation."""

    topic_focus: Optional[str] = Field(None, max_length=200, description="New topic focus")
    active_documents: Optional[List[str]] = Field(None, description="Active document IDs")
    status: Optional[str] = Field(None, description="Conversation status")


class ConversationEndRequest(BaseModel):
    """Request model for ending conversation."""

    summary_notes: Optional[str] = Field(None, max_length=1000, description="Summary notes")


class ConversationEndResponse(BaseModel):
    """Response model for conversation ending."""

    conversation_id: str = Field(..., description="Ended conversation ID")
    duration_minutes: float = Field(..., ge=0, description="Conversation duration")
    message_count: int = Field(..., ge=0, description="Total messages")
    topics_covered: List[str] = Field(default_factory=list, description="Topics discussed")
    summary: Optional[str] = Field(None, description="Conversation summary")
