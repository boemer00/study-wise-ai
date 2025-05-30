"""
Data models for the Conversational RAG system.

This module defines the core data structures used throughout the conversational
interface for StudyWise AI.
"""

import uuid
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from enum import Enum


class MessageRole(Enum):
    """Enumeration for conversation message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

    def __str__(self) -> str:
        return self.value


class QuestionType(Enum):
    """Enumeration for different types of student questions."""
    FACTUAL = "factual"           # What is X?
    CONCEPTUAL = "conceptual"     # How does X work?
    APPLICATION = "application"   # How do I use X?
    COMPARISON = "comparison"     # What's the difference between X and Y?
    EXPLANATION = "explanation"   # Why does X happen?
    SYNTHESIS = "synthesis"       # How do X and Y relate?

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> 'QuestionType':
        """Create QuestionType from string value."""
        for question_type in cls:
            if question_type.value == value:
                return question_type
        raise ValueError(f"Invalid question type: {value}")


class ResponseStrategy(Enum):
    """Different strategies for generating responses."""
    DIRECT_ANSWER = "direct_answer"
    GUIDED_DISCOVERY = "guided_discovery"
    EXAMPLE_BASED = "example_based"
    COMPARATIVE = "comparative"
    STEP_BY_STEP = "step_by_step"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> 'ResponseStrategy':
        """Create ResponseStrategy from string value."""
        for strategy in cls:
            if strategy.value == value:
                return strategy
        raise ValueError(f"Invalid response strategy: {value}")


@dataclass
class DocumentSource:
    """Information about a document source used in a response."""

    document_id: str
    chunk_id: str
    title: str
    content_snippet: str
    relevance_score: float
    page_number: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate fields after initialization."""
        if not self.document_id:
            raise ValueError("document_id cannot be empty")
        if not self.chunk_id:
            raise ValueError("chunk_id cannot be empty")
        if not self.title:
            raise ValueError("title cannot be empty")
        if not (0.0 <= self.relevance_score <= 1.0):
            raise ValueError("relevance_score must be between 0.0 and 1.0")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentSource':
        """Create from dictionary."""
        return cls(**data)

    def get_citation(self) -> str:
        """Get formatted citation string."""
        if self.page_number:
            return f"{self.title}, p. {self.page_number}"
        return self.title


@dataclass
class Message:
    """A single message in a conversation."""

    role: MessageRole
    content: str
    timestamp: datetime
    conversation_id: str
    message_id: Optional[str] = None
    sources: Optional[List[DocumentSource]] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate and set defaults after initialization."""
        if not self.content.strip():
            raise ValueError("Message content cannot be empty")
        if not self.conversation_id:
            raise ValueError("conversation_id cannot be empty")
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
        if self.sources is None:
            self.sources = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['role'] = self.role.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create from dictionary."""
        data = data.copy()
        data['role'] = MessageRole(data['role'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if 'sources' in data and data['sources']:
            data['sources'] = [DocumentSource.from_dict(s) for s in data['sources']]
        return cls(**data)

    def get_content_preview(self, max_length: int = 100) -> str:
        """Get truncated content preview."""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."

    def has_sources(self) -> bool:
        """Check if message has document sources."""
        return bool(self.sources and len(self.sources) > 0)


@dataclass
class ConversationContext:
    """Context for maintaining conversation state."""

    conversation_id: str
    user_id: str
    messages: List[Message]
    last_updated: datetime
    topic_focus: Optional[str] = None
    active_documents: Optional[List[str]] = None

    def __post_init__(self):
        """Validate fields after initialization."""
        if not self.conversation_id:
            raise ValueError("conversation_id cannot be empty")
        if not self.user_id:
            raise ValueError("user_id cannot be empty")
        if self.active_documents is None:
            self.active_documents = []

    def add_message(self, message: Message) -> None:
        """Add a message to the context."""
        if message.conversation_id != self.conversation_id:
            raise ValueError("Message conversation_id doesn't match context")
        self.messages.append(message)
        self.last_updated = datetime.now(timezone.utc)

    def get_recent_messages(self, limit: int = 10) -> List[Message]:
        """Get the most recent messages."""
        return self.messages[-limit:] if limit > 0 else self.messages

    def get_message_count(self) -> int:
        """Get total message count."""
        return len(self.messages)

    def get_user_messages(self) -> List[Message]:
        """Get only user messages."""
        return [msg for msg in self.messages if msg.role == MessageRole.USER]

    def get_assistant_messages(self) -> List[Message]:
        """Get only assistant messages."""
        return [msg for msg in self.messages if msg.role == MessageRole.ASSISTANT]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['last_updated'] = self.last_updated.isoformat()
        data['messages'] = [msg.to_dict() for msg in self.messages]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        """Create from dictionary."""
        data = data.copy()
        data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        data['messages'] = [Message.from_dict(msg) for msg in data['messages']]
        return cls(**data)


@dataclass
class ChatResponse:
    """Response from the study assistant to a user question."""

    answer: str
    sources: List[DocumentSource]
    conversation_id: str
    response_id: str
    follow_up_suggestions: List[str] = field(default_factory=list)
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate fields after initialization."""
        if not self.answer.strip():
            raise ValueError("Answer cannot be empty")
        # Note: conversation_id can be empty during initial creation - will be set by manager
        if not self.response_id:
            self.response_id = str(uuid.uuid4())
        if self.confidence_score is not None:
            if not (0.0 <= self.confidence_score <= 1.0):
                raise ValueError("confidence_score must be between 0.0 and 1.0")
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['sources'] = [source.to_dict() for source in self.sources]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatResponse':
        """Create from dictionary."""
        data = data.copy()
        data['sources'] = [DocumentSource.from_dict(s) for s in data['sources']]
        return cls(**data)

    def get_source_titles(self) -> List[str]:
        """Get list of source document titles."""
        return [source.title for source in self.sources]

    def get_high_confidence_sources(self, threshold: float = 0.8) -> List[DocumentSource]:
        """Get sources above confidence threshold."""
        return [source for source in self.sources if source.relevance_score >= threshold]

    def has_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if response has high confidence."""
        return self.confidence_score is not None and self.confidence_score >= threshold


@dataclass
class RetrievalResult:
    """Result from document retrieval for a query."""

    query: str
    chunks: List[DocumentSource]
    total_results: int
    search_time_ms: int
    query_enhancement: Optional[str] = None

    def __post_init__(self):
        """Validate fields after initialization."""
        if not self.query.strip():
            raise ValueError("Query cannot be empty")
        if self.total_results < 0:
            raise ValueError("total_results cannot be negative")
        if self.search_time_ms < 0:
            raise ValueError("search_time_ms cannot be negative")

    def get_top_chunks(self, limit: int = 5) -> List[DocumentSource]:
        """Get top N chunks by relevance score."""
        sorted_chunks = sorted(self.chunks, key=lambda x: x.relevance_score, reverse=True)
        return sorted_chunks[:limit]

    def get_average_relevance(self) -> float:
        """Get average relevance score of chunks."""
        if not self.chunks:
            return 0.0
        return sum(chunk.relevance_score for chunk in self.chunks) / len(self.chunks)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['chunks'] = [chunk.to_dict() for chunk in self.chunks]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RetrievalResult':
        """Create from dictionary."""
        data = data.copy()
        data['chunks'] = [DocumentSource.from_dict(chunk) for chunk in data['chunks']]
        return cls(**data)


@dataclass
class ConversationSummary:
    """Summary of a conversation for analytics and context."""

    conversation_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime]
    message_count: int
    topics_covered: List[str]
    documents_referenced: List[str]
    avg_response_time_ms: float

    def __post_init__(self):
        """Validate fields after initialization."""
        if not self.conversation_id:
            raise ValueError("conversation_id cannot be empty")
        if not self.user_id:
            raise ValueError("user_id cannot be empty")
        if self.message_count < 0:
            raise ValueError("message_count cannot be negative")
        if self.avg_response_time_ms < 0:
            raise ValueError("avg_response_time_ms cannot be negative")

    def get_duration_minutes(self) -> Optional[float]:
        """Get conversation duration in minutes."""
        if not self.end_time:
            return None
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 60.0

    def is_active(self) -> bool:
        """Check if conversation is still active."""
        return self.end_time is None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationSummary':
        """Create from dictionary."""
        data = data.copy()
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        if data.get('end_time'):
            data['end_time'] = datetime.fromisoformat(data['end_time'])
        return cls(**data)


# Helper functions for model operations
def create_user_message(
    content: str,
    conversation_id: str,
    sources: Optional[List[DocumentSource]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Message:
    """Create a user message with current timestamp."""
    return Message(
        role=MessageRole.USER,
        content=content,
        timestamp=datetime.now(timezone.utc),
        conversation_id=conversation_id,
        sources=sources,
        metadata=metadata
    )


def create_assistant_message(
    content: str,
    conversation_id: str,
    sources: Optional[List[DocumentSource]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Message:
    """Create an assistant message with current timestamp."""
    return Message(
        role=MessageRole.ASSISTANT,
        content=content,
        timestamp=datetime.now(timezone.utc),
        conversation_id=conversation_id,
        sources=sources,
        metadata=metadata
    )


def create_system_message(
    content: str,
    conversation_id: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Message:
    """Create a system message with current timestamp."""
    return Message(
        role=MessageRole.SYSTEM,
        content=content,
        timestamp=datetime.now(timezone.utc),
        conversation_id=conversation_id,
        metadata=metadata
    )
