"""
Chat/conversation API routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

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
from conversation.rag import StudyAssistant


router = APIRouter()


@router.post("/conversations", response_model=ConversationCreateResponse)
async def create_conversation(
    request: ConversationCreateRequest,
    user_id: str = Depends(get_current_user_id),
    assistant: StudyAssistant = Depends(get_study_assistant)
) -> ConversationCreateResponse:
    """
    Create a new conversation.
    """
    try:
        conversation_id = await assistant.start_conversation(
            user_id=user_id,
            initial_context=request.initial_context
        )

        from datetime import datetime
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
        response = await assistant.ask_question(
            conversation_id=conversation_id,
            question=request.message,
            user_documents=request.user_documents
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
        messages = await assistant.get_conversation_history(
            conversation_id=conversation_id,
            limit=limit
        )

        # Convert to API format
        from api.models.chat import ConversationMessage
        api_messages = []
        for msg in messages:
            api_messages.append(ConversationMessage(
                message_id=msg.message_id,
                role=msg.role.value,
                content=msg.content,
                timestamp=msg.timestamp,
                sources=[source.to_dict() for source in msg.sources] if msg.sources else [],
                metadata=msg.metadata
            ))

        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            messages=api_messages,
            total_messages=len(api_messages),
            has_more=False
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
