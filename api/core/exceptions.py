"""
Custom exceptions and error handlers for StudyWise AI API
"""

from typing import Any, Dict, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse


class StudyWiseAPIException(Exception):
    """
    Base exception for StudyWise AI API errors.
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ConversationNotFoundError(StudyWiseAPIException):
    """Raised when conversation is not found."""

    def __init__(self, conversation_id: str):
        super().__init__(
            message=f"Conversation {conversation_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"conversation_id": conversation_id}
        )


class FlashcardNotFoundError(StudyWiseAPIException):
    """Raised when flashcard is not found."""

    def __init__(self, flashcard_id: str):
        super().__init__(
            message=f"Flashcard {flashcard_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"flashcard_id": flashcard_id}
        )


class DocumentNotFoundError(StudyWiseAPIException):
    """Raised when document is not found."""

    def __init__(self, document_id: str):
        super().__init__(
            message=f"Document {document_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"document_id": document_id}
        )


class AuthenticationError(StudyWiseAPIException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(StudyWiseAPIException):
    """Raised when user lacks permission."""

    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )


class ValidationError(StudyWiseAPIException):
    """Raised when request validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class RateLimitError(StudyWiseAPIException):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )


class AIServiceError(StudyWiseAPIException):
    """Raised when AI service fails."""

    def __init__(self, message: str = "AI service unavailable"):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


async def api_exception_handler(request: Request, exc: StudyWiseAPIException) -> JSONResponse:
    """
    Global exception handler for StudyWise API exceptions.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details,
            "type": exc.__class__.__name__
        }
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle Pydantic validation errors.
    """
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "details": str(exc)
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle standard HTTP exceptions.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )
