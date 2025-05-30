"""
Conversational RAG module for StudyWise AI.

This module provides intelligent, context-aware conversation capabilities
for the StudyWise AI study assistant.
"""

# Core conversation models
from .models import (
    MessageRole,
    QuestionType,
    DocumentSource,
    Message,
    ConversationContext,
    ChatResponse,
    RetrievalResult,
    ConversationSummary,
    ResponseStrategy
)

# Memory management
from .memory import (
    ConversationMemory,
    ConversationNotFoundError,
    AuthorizationError
)

# Context retrieval
from .retriever import (
    ContextRetriever,
    RetrievalError,
    SearchError,
    EmbeddingError
)

# Response generation
from .generator import (
    ResponseGenerator,
    ResponseGenerationError,
    OpenAIAPIError
)

# Conversation management
from .manager import (
    ConversationManager,
    ConversationError
)

# Main interface
from .rag import (
    StudyAssistant,
    StudyAssistantError,
    ConfigurationError,
    InitializationError
)

__all__ = [
    # Models
    "MessageRole",
    "QuestionType",
    "DocumentSource",
    "Message",
    "ConversationContext",
    "ChatResponse",
    "RetrievalResult",
    "ConversationSummary",
    "ResponseStrategy",

    # Memory
    "ConversationMemory",
    "ConversationNotFoundError",
    "AuthorizationError",

    # Retrieval
    "ContextRetriever",
    "RetrievalError",
    "SearchError",
    "EmbeddingError",

    # Generation
    "ResponseGenerator",
    "ResponseGenerationError",
    "OpenAIAPIError",

    # Management
    "ConversationManager",
    "ConversationError",

    # Main Interface
    "StudyAssistant",
    "StudyAssistantError",
    "ConfigurationError",
    "InitializationError",
]
