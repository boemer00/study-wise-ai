"""
Chat/conversation API routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timedelta

from api.models.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationCreateRequest,
    ConversationCreateResponse,
    ConversationHistoryResponse,
    ConversationSummary,
    ConversationUpdateRequest,
    ConversationEndRequest,
    ConversationEndResponse
)
from api.core.dependencies import (
    get_study_assistant,
    get_current_user_id,
    verify_conversation_access,
    get_pagination_params
)
from src.conversation.rag import StudyAssistant


router = APIRouter()


@router.post("/conversations/create-friendly")
async def create_conversation_friendly(
    request: Optional[ConversationCreateRequest] = None,
    user_id: str = Depends(get_current_user_id),
    assistant: StudyAssistant = Depends(get_study_assistant)
) -> dict:
    """
    Create a new conversation with frontend-friendly response format.
    Includes both snake_case and camelCase field names for compatibility.
    """
    try:
        # Use empty request if none provided
        if request is None:
            request = ConversationCreateRequest()

        # Try to use the real StudyAssistant to create conversation
        try:
            conversation_id = await assistant.start_conversation(
                user_id=user_id,
                topic_focus=request.topic_focus,
                document_ids=request.active_documents,
                send_welcome=False
            )

            # Return both formats for frontend compatibility
            return {
                "conversation_id": conversation_id,     # snake_case (backend standard)
                "conversationId": conversation_id,      # camelCase (frontend might expect)
                "user_id": user_id,
                "userId": user_id,
                "topic_focus": request.topic_focus,
                "topicFocus": request.topic_focus,
                "created_at": datetime.now().isoformat(),
                "createdAt": datetime.now().isoformat(),
                "success": True
            }

        except Exception as assistant_error:
            # Log the error and fall back to generating a UUID
            import logging
            import uuid
            logger = logging.getLogger(__name__)
            logger.error(f"StudyAssistant conversation creation error: {str(assistant_error)}")

            # Generate a proper UUID as fallback
            conversation_id = str(uuid.uuid4())

            return {
                "conversation_id": conversation_id,
                "conversationId": conversation_id,
                "user_id": user_id,
                "userId": user_id,
                "topic_focus": request.topic_focus,
                "topicFocus": request.topic_focus,
                "created_at": datetime.now().isoformat(),
                "createdAt": datetime.now().isoformat(),
                "success": True,
                "fallback": True
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "conversation_id": None,
            "conversationId": None
        }


@router.post("/conversations", response_model=ConversationCreateResponse)
async def create_conversation(
    request: Optional[ConversationCreateRequest] = None,
    user_id: str = Depends(get_current_user_id),
    assistant: StudyAssistant = Depends(get_study_assistant)
) -> ConversationCreateResponse:
    """
    Create a new conversation.
    """
    try:
        # Use empty request if none provided
        if request is None:
            request = ConversationCreateRequest()

        # Try to use the real StudyAssistant to create conversation
        try:
            conversation_id = await assistant.start_conversation(
                user_id=user_id,
                topic_focus=request.topic_focus,
                document_ids=request.active_documents,
                send_welcome=False  # Don't send welcome message automatically
            )

            return ConversationCreateResponse(
                conversation_id=conversation_id,
                user_id=user_id,
                topic_focus=request.topic_focus,
                created_at=datetime.now()
            )

        except Exception as assistant_error:
            # Log the error and fall back to generating a UUID
            import logging
            import uuid
            logger = logging.getLogger(__name__)
            logger.error(f"StudyAssistant conversation creation error: {str(assistant_error)}")

            # Generate a proper UUID as fallback
            conversation_id = str(uuid.uuid4())

            return ConversationCreateResponse(
                conversation_id=conversation_id,
                user_id=user_id,
                topic_focus=request.topic_focus,
                created_at=datetime.now()
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")


@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    conversation_id: str,
    request: ChatMessageRequest,
    user_id: str = Depends(get_current_user_id),
    assistant: StudyAssistant = Depends(get_study_assistant),
    verified_conversation_id: str = Depends(verify_conversation_access)
) -> ChatMessageResponse:
    """
    Send a message to the AI assistant.
    """
    try:
        # Try to use the real StudyAssistant for actual AI responses
        try:
            response = await assistant.ask_question(
                conversation_id=conversation_id,
                question=request.message,
                document_filter=request.user_documents
            )

            # Convert to API response format
            return ChatMessageResponse(
                answer=response.answer,
                sources=[source.to_dict() for source in response.sources],
                conversation_id=response.conversation_id,
                response_id=response.response_id,
                follow_up_suggestions=response.follow_up_suggestions,
                confidence_score=response.confidence_score,
                processing_time_ms=response.processing_time_ms,
                metadata=response.metadata
            )

        except Exception as assistant_error:
            # Log the actual error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"StudyAssistant error: {str(assistant_error)}")

            # For now, fall back to demo mode if StudyAssistant fails
            # Generate a simple response based on the message
            user_message = request.message.lower()

            if "machine learning" in user_message or "ml" in user_message:
                answer = "Machine Learning is fascinating! Are you interested in supervised learning, unsupervised learning, or deep learning concepts?"
            elif "python" in user_message:
                answer = "Python is a versatile programming language! What specific Python topic would you like to explore?"
            elif "math" in user_message or "mathematics" in user_message:
                answer = "Mathematics is the foundation of many subjects! What area of math are you working on?"
            elif "hello" in user_message or "hi" in user_message:
                answer = "Hello! I'm your AI study tutor. How can I help you learn today?"
            else:
                answer = f"That's an interesting question about '{request.message}'. I can help you explore this topic further. What specific aspect would you like to understand better?"

            import uuid
            response_id = str(uuid.uuid4())

            return ChatMessageResponse(
                answer=f"[DEMO MODE] {answer}",
                sources=[],  # No sources in demo mode
                conversation_id=conversation_id,
                response_id=response_id,
                follow_up_suggestions=[
                    "Can you explain this in more detail?",
                    "What are some practical applications?",
                    "Are there any related concepts I should know?"
                ],
                confidence_score=0.8,
                processing_time_ms=150,
                metadata={"mode": "demo_fallback", "user_message": request.message, "error": str(assistant_error)}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")


@router.get("/conversations/{conversation_id}/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    conversation_id: str,
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum messages to return"),
    user_id: str = Depends(get_current_user_id),
    assistant: StudyAssistant = Depends(get_study_assistant),
    verified_conversation_id: str = Depends(verify_conversation_access)
) -> ConversationHistoryResponse:
    """
    Get conversation message history.
    """
    try:
        # For demo, return mock conversation history
        # TODO: Use StudyAssistant once initialization issues are resolved

        from api.models.chat import ConversationMessage
        import uuid

        # Generate demo conversation history
        demo_messages = [
            ConversationMessage(
                message_id=str(uuid.uuid4()),
                role="user",
                content="Hello, can you help me learn Python?",
                timestamp=datetime.now() - timedelta(minutes=5),
                sources=[],
                metadata={}
            ),
            ConversationMessage(
                message_id=str(uuid.uuid4()),
                role="assistant",
                content="Hello! I'm your AI study tutor. How can I help you learn today?",
                timestamp=datetime.now() - timedelta(minutes=4),
                sources=[],
                metadata={"mode": "demo"}
            ),
            ConversationMessage(
                message_id=str(uuid.uuid4()),
                role="user",
                content="What are Python data types?",
                timestamp=datetime.now() - timedelta(minutes=3),
                sources=[],
                metadata={}
            ),
            ConversationMessage(
                message_id=str(uuid.uuid4()),
                role="assistant",
                content="Python is a versatile programming language! What specific Python topic would you like to explore?",
                timestamp=datetime.now() - timedelta(minutes=2),
                sources=[],
                metadata={"mode": "demo"}
            )
        ]

        # Apply pagination
        total_messages = len(demo_messages)
        paginated_messages = demo_messages[skip:skip + limit] if skip < total_messages else []

        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            messages=paginated_messages,
            total_messages=total_messages,
            has_more=skip + limit < total_messages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation history: {str(e)}")


@router.put("/conversations/{conversation_id}", response_model=ConversationSummary)
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    assistant: StudyAssistant = Depends(get_study_assistant),
    verified_conversation_id: str = Depends(verify_conversation_access)
) -> ConversationSummary:
    """
    Update conversation settings.

    Args:
        conversation_id: ID of the conversation
        request: Update parameters
        user_id: Authenticated user ID
        assistant: StudyAssistant instance
        verified_conversation_id: Verified conversation ID

    Returns:
        Updated conversation summary

    Raises:
        HTTPException: If conversation not found or update fails
    """
    # TODO: Update conversation settings
    pass


@router.delete("/conversations/{conversation_id}", response_model=ConversationEndResponse)
async def end_conversation(
    conversation_id: str,
    request: ConversationEndRequest,
    user_id: str = Depends(get_current_user_id),
    assistant: StudyAssistant = Depends(get_study_assistant),
    verified_conversation_id: str = Depends(verify_conversation_access)
) -> ConversationEndResponse:
    """
    End a conversation and generate summary.

    Args:
        conversation_id: ID of the conversation
        request: End conversation parameters
        user_id: Authenticated user ID
        assistant: StudyAssistant instance
        verified_conversation_id: Verified conversation ID

    Returns:
        Conversation end summary

    Raises:
        HTTPException: If conversation not found
    """
    # TODO: End conversation and generate summary
    pass


@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(
    user_id: str = Depends(get_current_user_id),
    skip: int = Query(0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum conversations to return"),
    status: Optional[str] = Query(None, description="Filter by conversation status"),
    assistant: StudyAssistant = Depends(get_study_assistant)
) -> List[ConversationSummary]:
    """
    List user's conversations.

    Args:
        user_id: Authenticated user ID
        skip: Number of conversations to skip
        limit: Maximum conversations to return
        status: Filter by conversation status
        assistant: StudyAssistant instance

    Returns:
        List of conversation summaries

    Raises:
        HTTPException: If listing fails
    """
    # TODO: List user conversations
    pass


@router.get("/debug/test-conversation")
async def debug_test_conversation() -> dict:
    """
    Debug endpoint to test frontend conversation handling.
    """
    import uuid
    return {
        "conversation_id": str(uuid.uuid4()),
        "user_id": "debug-user",
        "topic_focus": "Debug Test",
        "created_at": datetime.now().isoformat(),
        "debug": True
    }
