"""
Chat/conversation API routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

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
    get_current_user_id,
    verify_conversation_access,
    get_pagination_params
)
import openai
import uuid
import os
from src.weaviate_client import create_weaviate_client
from api.models.chat import ConversationMessage


router = APIRouter()


@router.post("/conversations/create-friendly")
async def create_conversation_friendly(
    request: Optional[ConversationCreateRequest] = None,
    user_id: str = Depends(get_current_user_id)
) -> dict:
    """
    Create a new conversation with frontend-friendly response format.
    Includes both snake_case and camelCase field names for compatibility.
    """
    try:
        # For MVP: Simple conversation creation without StudyAssistant dependency
        conversation_id = str(uuid.uuid4())
        
        topic_focus = None
        if request is not None:
            topic_focus = getattr(request, 'topic_focus', None)

        return {
            "conversation_id": conversation_id,
            "conversationId": conversation_id,
            "user_id": user_id,
            "userId": user_id,
            "topic_focus": topic_focus,
            "topicFocus": topic_focus,
            "created_at": datetime.now().isoformat(),
            "createdAt": datetime.now().isoformat(),
            "success": True,
            "mvp_mode": True
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
    user_id: str = Depends(get_current_user_id)
) -> ConversationCreateResponse:
    """
    Create a new conversation.
    """
    try:
        # Use empty request if none provided
        if request is None:
            request = ConversationCreateRequest()

        # Simple conversation creation without complex dependencies
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
    user_id: str = Depends(get_current_user_id)
) -> ChatMessageResponse:
    """
    Send a message to the AI assistant - MVP: Simple document search with AI responses
    """
    try:
        start_time = datetime.now()
        
        # Initialize OpenAI client
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if openai_api_key:
            openai_client = openai.OpenAI(api_key=openai_api_key)
        
        # Search through user's uploaded documents
        context_snippets = []
        sources = []
        
        # Try document search with available credentials
        search_enabled = bool(os.getenv('WEAVIATE_URL') and os.getenv('WEAVIATE_API_KEY'))
        
        if search_enabled:
            try:
                # Create Weaviate client and search
                weaviate_client = create_weaviate_client(
                    url=os.getenv('WEAVIATE_URL'),
                    api_key=os.getenv('WEAVIATE_API_KEY'),
                    openai_api_key=openai_api_key
                )
                
                search_results = weaviate_client.semantic_search(
                    query=request.message,
                    user_id=user_id,
                    limit=3
                )
                
                if search_results and len(search_results) > 0:
                    for result in search_results:
                        # SearchResult object from WeaviateClient
                        content = result.content
                        context_snippets.append(content[:400])  # More context for better AI responses
                        sources.append({
                            'document_id': result.metadata.get('document_id', result.id),
                            'title': result.title,
                            'snippet': content[:150] + "..." if len(content) > 150 else content,
                            'relevance_score': result.score
                        })
                            
            except Exception as search_error:
                print(f"Document search failed: {str(search_error)}")
        
        # Generate AI response
        if openai_api_key:
            try:
                if context_snippets:
                    # AI response based on document context
                    context_text = "\n\n".join(context_snippets)
                    system_prompt = "You are a helpful study assistant. Answer the user's question based on the provided document context. Be concise, accurate, and helpful."
                    user_prompt = f"Context from uploaded documents:\n{context_text}\n\nQuestion: {request.message}"
                    confidence_score = 0.9
                else:
                    # AI response for general questions (MVP mode)
                    system_prompt = "You are a knowledgeable study assistant. Provide helpful, accurate answers to academic questions. Be concise but informative. Cover key concepts clearly."
                    user_prompt = request.message
                    confidence_score = 0.8
                
                completion = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=300,
                    temperature=0.7
                )
                
                answer = completion.choices[0].message.content
                
            except Exception as ai_error:
                print(f"OpenAI completion failed: {str(ai_error)}")
                if context_snippets:
                    answer = f"Based on your documents, I found {len(sources)} relevant sections about '{request.message}'. " + (context_snippets[0][:200] + "..." if context_snippets else "")
                    confidence_score = 0.7
                else:
                    # Fall back to enhanced static responses
                    answer = None  # Will trigger fallback below
                    confidence_score = 0.6
                
        
        # Enhanced fallback responses (used when OpenAI fails or answer is None)
        if not locals().get('answer') or answer is None:
            user_message_lower = request.message.lower()
            if any(greeting in user_message_lower for greeting in ["hello", "hi", "hey"]):
                answer = "Hello! I'm your study assistant. I can help you understand topics and concepts. Upload documents for personalized insights!"
            elif any(term in user_message_lower for term in ["machine learning", "ml", "artificial intelligence", "ai"]):
                answer = "Machine learning is a subset of AI that enables computers to learn from data. Common types include supervised learning (with labeled data) and unsupervised learning (finding patterns). Would you like to know about specific algorithms or concepts?"
            elif any(term in user_message_lower for term in ["python", "programming", "code"]):
                answer = "Python is a versatile programming language popular for data science, web development, and automation. Key concepts include variables, functions, loops, and object-oriented programming. What specific Python topic interests you?"
            elif any(term in user_message_lower for term in ["neural network", "deep learning"]):
                answer = "Neural networks are computing systems inspired by biological brains, consisting of interconnected nodes (neurons) that process information. Deep learning uses multi-layered neural networks for complex pattern recognition. What aspect would you like to explore?"
            elif "help" in user_message_lower:
                answer = "I can help explain concepts, answer questions about various topics, and provide insights from uploaded documents. Try asking about machine learning, programming, or any academic subject!"
            else:
                answer = f"I'd be happy to help with '{request.message}'. I can provide general explanations on many topics. For personalized insights, upload relevant documents!"
            confidence_score = 0.7
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        response_id = str(uuid.uuid4())
        
        return ChatMessageResponse(
            answer=answer,
            sources=sources,
            conversation_id=conversation_id,
            response_id=response_id,
            follow_up_suggestions=[
                "Can you explain this in more detail?",
                "What are the key points?",
                "How does this relate to other concepts?"
            ] if sources else [
                "Upload a document to get started",
                "Ask me about a specific topic",
                "What can you help me learn?"
            ],
            confidence_score=confidence_score,
            processing_time_ms=int(processing_time),
            metadata={
                "mode": "ai_enhanced" if context_snippets and openai_api_key else "simple_fallback", 
                "documents_found": len(sources),
                "has_context": bool(context_snippets)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")


@router.get("/conversations/{conversation_id}/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    conversation_id: str,
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum messages to return"),
    user_id: str = Depends(get_current_user_id),
    verified_conversation_id: str = Depends(verify_conversation_access)
) -> ConversationHistoryResponse:
    """
    Get conversation message history - MVP: Return demo history
    """
    try:
        # MVP: Return demo conversation history
        demo_messages = [
            ConversationMessage(
                message_id=str(uuid.uuid4()),
                role="user",
                content="Hello, can you help me understand my documents?",
                timestamp=datetime.now() - timedelta(minutes=5),
                sources=[],
                metadata={}
            ),
            ConversationMessage(
                message_id=str(uuid.uuid4()),
                role="assistant",
                content="Hello! I'm your study assistant. I can help you understand your uploaded documents. What would you like to learn about?",
                timestamp=datetime.now() - timedelta(minutes=4),
                sources=[],
                metadata={"mode": "mvp"}
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
    verified_conversation_id: str = Depends(verify_conversation_access)
) -> ConversationSummary:
    """
    Update conversation settings - MVP: Basic implementation
    """
    # MVP: Return basic conversation summary
    return ConversationSummary(
        conversation_id=conversation_id,
        user_id=user_id,
        topic_focus=getattr(request, 'topic_focus', None),
        created_at=datetime.now(),
        last_activity=datetime.now(),
        message_count=0,
        status="active"
    )


@router.delete("/conversations/{conversation_id}", response_model=ConversationEndResponse)
async def end_conversation(
    conversation_id: str,
    request: ConversationEndRequest,
    user_id: str = Depends(get_current_user_id),
    verified_conversation_id: str = Depends(verify_conversation_access)
) -> ConversationEndResponse:
    """
    End a conversation - MVP: Basic implementation
    """
    return ConversationEndResponse(
        conversation_id=conversation_id,
        ended_at=datetime.now(),
        summary="Conversation ended successfully",
        message_count=0,
        total_duration_minutes=0
    )


@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(
    user_id: str = Depends(get_current_user_id),
    skip: int = Query(0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum conversations to return"),
    status: Optional[str] = Query(None, description="Filter by conversation status")
) -> List[ConversationSummary]:
    """
    List user's conversations - MVP: Return empty list
    """
    # MVP: Return empty list for now
    return []


@router.get("/debug/test-conversation")
async def debug_test_conversation() -> dict:
    """
    Debug endpoint to test frontend conversation handling.
    """
    return {
        "conversation_id": str(uuid.uuid4()),
        "user_id": "debug-user",
        "topic_focus": "Debug Test",
        "created_at": datetime.now().isoformat(),
        "debug": True
    }
