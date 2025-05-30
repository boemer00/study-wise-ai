"""
Conversation management for the Conversational RAG system.

This module orchestrates the complete conversational workflow, coordinating
memory, retrieval, and generation components.
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import logging

from .models import (
    Message,
    ConversationContext,
    ChatResponse,
    MessageRole,
    QuestionType,
    create_user_message,
    create_assistant_message
)
from .memory import ConversationMemory, ConversationNotFoundError, AuthorizationError
from .retriever import ContextRetriever, RetrievalError
from .generator import ResponseGenerator, ResponseGenerationError

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Orchestrates complete conversational interactions.

    Coordinates memory management, context retrieval, and response generation
    to provide seamless conversational experiences for the study assistant.
    """

    def __init__(
        self,
        memory: ConversationMemory,
        retriever: ContextRetriever,
        generator: ResponseGenerator,
        max_context_turns: int = 10,
        enable_context_memory: bool = True,
        enable_intent_detection: bool = True
    ) -> None:
        """
        Initialize conversation manager.

        Args:
            memory: Conversation memory component
            retriever: Context retrieval component
            generator: Response generation component
            max_context_turns: Maximum conversation turns to maintain in context
            enable_context_memory: Whether to use conversation context in responses
            enable_intent_detection: Whether to detect user intents
        """
        self.memory = memory
        self.retriever = retriever
        self.generator = generator
        self.max_context_turns = max_context_turns
        self.enable_context_memory = enable_context_memory
        self.enable_intent_detection = enable_intent_detection

        # Intent patterns for detection
        self.intent_patterns = {
            'clarification': ['what do you mean', 'can you clarify', 'i don\'t understand', 'unclear'],
            'examples': ['give me an example', 'show me an example', 'can you provide examples', 'for example'],
            'deeper_explanation': ['tell me more', 'explain further', 'go deeper', 'more details'],
            'related_topics': ['what else', 'related to', 'similar topics', 'connected to'],
            'practical_application': ['how to use', 'in practice', 'real world', 'apply this'],
            'summary': ['summarize', 'sum up', 'in summary', 'main points']
        }

    async def start_conversation(
        self,
        user_id: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new conversation.

        Args:
            user_id: ID of the user starting the conversation
            initial_context: Optional initial context (topics, documents, etc.)

        Returns:
            Conversation ID

        Raises:
            ConversationError: If conversation creation fails
        """
        try:
            conversation_id = await self.memory.create_conversation(
                user_id=user_id,
                initial_context=initial_context
            )

            # Add optional system message with welcome
            if initial_context and initial_context.get('send_welcome', True):
                welcome_message = self._generate_welcome_message(initial_context)
                if welcome_message:
                    await self.memory.add_message(
                        conversation_id=conversation_id,
                        role=MessageRole.SYSTEM,
                        content=welcome_message,
                        metadata={'message_type': 'welcome'}
                    )

            logger.info(f"Started conversation {conversation_id} for user {user_id}")
            return conversation_id

        except Exception as e:
            logger.error(f"Failed to start conversation: {str(e)}")
            raise ConversationError(f"Failed to start conversation: {str(e)}")

    async def process_user_message(
        self,
        conversation_id: str,
        user_message: str,
        user_documents: Optional[List[str]] = None,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> ChatResponse:
        """
        Process a user message and generate a response.

        Args:
            conversation_id: ID of the conversation
            user_message: User's message content
            user_documents: Optional list of specific documents to search
            processing_options: Optional processing configuration

        Returns:
            ChatResponse with generated answer and metadata

        Raises:
            ConversationError: If message processing fails
        """
        try:
            start_time = time.time()

            # Get conversation context
            conversation_context = await self.memory.get_conversation_context(conversation_id)

            # Detect user intent if enabled
            user_intent = None
            if self.enable_intent_detection:
                user_intent = self._detect_user_intent(user_message, conversation_context.messages)

            # Classify question type
            question_type = await self.retriever.classify_question_type(
                user_message,
                self._build_conversation_context_string(conversation_context.messages) if self.enable_context_memory else None
            )

            # Store user message
            user_msg_id = await self.memory.add_message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=user_message,
                metadata={
                    'question_type': question_type.value,
                    'user_intent': user_intent,
                    'processing_timestamp': datetime.now(timezone.utc).isoformat()
                }
            )

            # Handle special intents first
            if user_intent == 'summary':
                response = await self._generate_conversation_summary(conversation_context)
            elif user_intent == 'clarification' and conversation_context.messages:
                response = await self._handle_clarification_request(user_message, conversation_context, user_documents)
            else:
                # Regular context retrieval and response generation
                response = await self._generate_regular_response(
                    user_message,
                    conversation_context,
                    question_type,
                    user_documents,
                    processing_options
                )

            # Set conversation and response metadata
            response.conversation_id = conversation_id
            response.response_id = str(uuid.uuid4())
            response.processing_time_ms = int((time.time() - start_time) * 1000)

            # Store assistant message
            await self.memory.add_message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=response.answer,
                sources=[source.to_dict() for source in response.sources],
                metadata={
                    'response_id': response.response_id,
                    'confidence_score': response.confidence_score,
                    'follow_up_suggestions': response.follow_up_suggestions,
                    'question_type': question_type.value,
                    'user_intent': user_intent,
                    'processing_time_ms': response.processing_time_ms,
                    **response.metadata
                }
            )

            # Update conversation metadata if needed
            await self._update_conversation_focus(conversation_context, user_message, response)

            logger.info(f"Processed message in conversation {conversation_id}: {response.processing_time_ms}ms")
            return response

        except (ConversationNotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error processing user message: {str(e)}")
            raise ConversationError(f"Failed to process message: {str(e)}")

    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        include_system_messages: bool = False
    ) -> List[Message]:
        """
        Get conversation message history.

        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages to return
            include_system_messages: Whether to include system messages

        Returns:
            List of conversation messages

        Raises:
            ConversationNotFoundError: If conversation doesn't exist
        """
        try:
            messages = await self.memory.get_conversation_history(
                conversation_id=conversation_id,
                limit=limit
            )

            # Filter out system messages if requested
            if not include_system_messages:
                messages = [msg for msg in messages if msg.role != MessageRole.SYSTEM]

            return messages

        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            raise ConversationError(f"Failed to get conversation history: {str(e)}")

    async def update_conversation_focus(
        self,
        conversation_id: str,
        new_focus: str,
        active_documents: Optional[List[str]] = None
    ) -> None:
        """
        Update the conversation's topic focus and active documents.

        Args:
            conversation_id: ID of the conversation
            new_focus: New topic focus
            active_documents: List of active document IDs

        Raises:
            ConversationNotFoundError: If conversation doesn't exist
        """
        try:
            metadata_update = {
                'topic_focus': new_focus,
                'focus_updated_at': datetime.now(timezone.utc).isoformat()
            }

            if active_documents is not None:
                metadata_update['active_documents'] = active_documents

            await self.memory.update_conversation_metadata(
                conversation_id=conversation_id,
                metadata=metadata_update
            )

            logger.debug(f"Updated conversation {conversation_id} focus to: {new_focus}")

        except Exception as e:
            logger.error(f"Error updating conversation focus: {str(e)}")
            raise ConversationError(f"Failed to update conversation focus: {str(e)}")

    async def end_conversation(
        self,
        conversation_id: str,
        user_id: str,
        summary_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        End a conversation and generate final summary.

        Args:
            conversation_id: ID of the conversation to end
            user_id: ID of the user (for authorization)
            summary_notes: Optional user notes about the conversation

        Returns:
            Conversation summary statistics

        Raises:
            ConversationNotFoundError: If conversation doesn't exist
            AuthorizationError: If user doesn't own the conversation
        """
        try:
            # Get conversation context for summary
            conversation_context = await self.memory.get_conversation_context(conversation_id)

            # Verify user authorization
            if conversation_context.user_id != user_id:
                raise AuthorizationError(f"User {user_id} not authorized for conversation {conversation_id}")

            # Generate conversation summary
            end_time = datetime.now(timezone.utc)

            # Calculate statistics
            user_messages = [msg for msg in conversation_context.messages if msg.role == MessageRole.USER]
            assistant_messages = [msg for msg in conversation_context.messages if msg.role == MessageRole.ASSISTANT]

            summary_stats = {
                'conversation_id': conversation_id,
                'user_id': user_id,
                'end_time': end_time.isoformat(),
                'total_messages': len(conversation_context.messages),
                'user_messages': len(user_messages),
                'assistant_messages': len(assistant_messages),
                'topic_focus': conversation_context.topic_focus,
                'active_documents': conversation_context.active_documents,
                'duration_minutes': self._calculate_conversation_duration(conversation_context),
                'summary_notes': summary_notes
            }

            # Update conversation metadata with end status
            await self.memory.update_conversation_metadata(
                conversation_id=conversation_id,
                metadata={
                    'ended_at': end_time.isoformat(),
                    'summary_stats': summary_stats
                }
            )

            logger.info(f"Ended conversation {conversation_id} with {len(conversation_context.messages)} messages")
            return summary_stats

        except (ConversationNotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error ending conversation: {str(e)}")
            raise ConversationError(f"Failed to end conversation: {str(e)}")

    async def search_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[Message]:
        """
        Search through user's conversation history.

        Args:
            user_id: ID of the user
            query: Search query
            limit: Maximum number of results

        Returns:
            List of relevant messages from conversations
        """
        try:
            return await self.memory.search_conversation_history(
                user_id=user_id,
                query=query,
                limit=limit
            )

        except Exception as e:
            logger.error(f"Error searching conversations: {str(e)}")
            raise ConversationError(f"Failed to search conversations: {str(e)}")

    async def _generate_regular_response(
        self,
        user_message: str,
        conversation_context: ConversationContext,
        question_type: QuestionType,
        user_documents: Optional[List[str]],
        processing_options: Optional[Dict[str, Any]]
    ) -> ChatResponse:
        """
        Generate a regular response using retrieval and generation.

        Args:
            user_message: User's message
            conversation_context: Current conversation context
            question_type: Classified question type
            user_documents: Optional document filter
            processing_options: Processing configuration

        Returns:
            Generated chat response
        """
        try:
            # Retrieve relevant context
            retrieval_result = await self.retriever.retrieve_context(
                query=user_message,
                conversation_history=conversation_context.messages if self.enable_context_memory else None,
                user_documents=user_documents or conversation_context.active_documents,
                question_type=question_type
            )

            # Generate response
            response = await self.generator.generate_response(
                user_query=user_message,
                retrieved_context=retrieval_result.chunks,
                conversation_history=conversation_context.messages if self.enable_context_memory else None,
                question_type=question_type,
                response_strategy=processing_options.get('response_strategy') if processing_options else None
            )

            # Add retrieval metadata
            response.metadata.update({
                'retrieval_time_ms': retrieval_result.search_time_ms,
                'total_chunks_found': retrieval_result.total_results,
                'query_enhancement': retrieval_result.query_enhancement
            })

            return response

        except (RetrievalError, ResponseGenerationError) as e:
            logger.error(f"Error in regular response generation: {str(e)}")
            # Return fallback response
            return ChatResponse(
                answer="I apologize, but I'm having trouble processing your request right now. Could you please try rephrasing your question?",
                sources=[],
                conversation_id="",
                response_id="",
                confidence_score=0.1,
                metadata={'error': str(e), 'fallback_response': True}
            )

    async def _handle_clarification_request(
        self,
        user_message: str,
        conversation_context: ConversationContext,
        user_documents: Optional[List[str]]
    ) -> ChatResponse:
        """
        Handle requests for clarification about previous responses.

        Args:
            user_message: User's clarification request
            conversation_context: Current conversation context
            user_documents: Optional document filter

        Returns:
            Clarification response
        """
        try:
            # Get the last assistant message
            assistant_messages = [msg for msg in conversation_context.messages if msg.role == MessageRole.ASSISTANT]

            if not assistant_messages:
                return ChatResponse(
                    answer="I don't have a previous response to clarify. Could you please ask a specific question?",
                    sources=[],
                    conversation_id="",
                    response_id="",
                    confidence_score=0.8
                )

            last_response = assistant_messages[-1]

            # Try to retrieve more context about the same topic
            retrieval_result = await self.retriever.retrieve_context(
                query=f"{user_message} {last_response.content[:100]}",  # Combine clarification request with previous response
                conversation_history=conversation_context.messages[-5:],  # Recent context
                user_documents=user_documents,
                question_type=QuestionType.EXPLANATION
            )

            # Generate clarification
            clarification_prompt = f"The user is asking for clarification about this previous response: '{last_response.content[:200]}...' Their clarification request is: '{user_message}'"

            response = await self.generator.generate_response(
                user_query=clarification_prompt,
                retrieved_context=retrieval_result.chunks,
                conversation_history=conversation_context.messages[-3:],  # Recent context
                question_type=QuestionType.EXPLANATION,
                response_strategy=None
            )

            return response

        except Exception as e:
            logger.warning(f"Error handling clarification request: {str(e)}")
            return ChatResponse(
                answer="I'd be happy to clarify! Could you please be more specific about what part you'd like me to explain further?",
                sources=[],
                conversation_id="",
                response_id="",
                confidence_score=0.6
            )

    async def _generate_conversation_summary(
        self,
        conversation_context: ConversationContext
    ) -> ChatResponse:
        """
        Generate a summary of the conversation so far.

        Args:
            conversation_context: Current conversation context

        Returns:
            Summary response
        """
        try:
            # Extract key points from conversation
            user_messages = [msg for msg in conversation_context.messages if msg.role == MessageRole.USER]
            assistant_messages = [msg for msg in conversation_context.messages if msg.role == MessageRole.ASSISTANT]

            if not user_messages:
                return ChatResponse(
                    answer="This conversation just started - there's nothing to summarize yet!",
                    sources=[],
                    conversation_id="",
                    response_id="",
                    confidence_score=0.9
                )

            # Build summary content
            topics_discussed = []
            if conversation_context.topic_focus:
                topics_discussed.append(conversation_context.topic_focus)

            summary_parts = [
                f"**Conversation Summary**",
                f"Topics discussed: {', '.join(topics_discussed) if topics_discussed else 'Various topics'}",
                f"Questions asked: {len(user_messages)}",
                f"Responses provided: {len(assistant_messages)}"
            ]

            # Add recent key points
            if len(user_messages) > 0:
                summary_parts.append("\n**Recent topics:**")
                for msg in user_messages[-3:]:  # Last 3 questions
                    preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
                    summary_parts.append(f"• {preview}")

            summary_content = "\n".join(summary_parts)

            return ChatResponse(
                answer=summary_content,
                sources=[],
                conversation_id="",
                response_id="",
                confidence_score=0.95,
                metadata={'summary_type': 'conversation_summary'}
            )

        except Exception as e:
            logger.warning(f"Error generating conversation summary: {str(e)}")
            return ChatResponse(
                answer="I'm having trouble generating a summary right now. The conversation has covered various topics related to your studies.",
                sources=[],
                conversation_id="",
                response_id="",
                confidence_score=0.5
            )

    def _detect_user_intent(
        self,
        user_message: str,
        conversation_history: List[Message]
    ) -> Optional[str]:
        """
        Detect user intent from message content and context.

        Args:
            user_message: User's message
            conversation_history: Recent conversation messages

        Returns:
            Detected intent or None
        """
        try:
            message_lower = user_message.lower()

            # Check for intent patterns
            for intent, patterns in self.intent_patterns.items():
                for pattern in patterns:
                    if pattern in message_lower:
                        logger.debug(f"Detected intent '{intent}' from pattern '{pattern}'")
                        return intent

            # Context-based intent detection
            if len(conversation_history) > 0:
                last_message = conversation_history[-1]

                # If user is asking very short questions after a detailed response, likely wants clarification
                if (len(user_message.split()) <= 3 and
                    last_message.role == MessageRole.ASSISTANT and
                    len(last_message.content) > 200):
                    return 'clarification'

                # If user mentions previous topics, might want related information
                if any(word in message_lower for word in ['previous', 'before', 'earlier', 'mentioned']):
                    return 'related_topics'

            return None

        except Exception as e:
            logger.warning(f"Intent detection failed: {str(e)}")
            return None

    def _generate_welcome_message(
        self,
        initial_context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Generate a welcome message for new conversations.

        Args:
            initial_context: Initial conversation context

        Returns:
            Welcome message or None
        """
        try:
            if not initial_context.get('send_welcome', True):
                return None

            welcome_parts = ["Hi! I'm StudyWise AI, your intelligent study assistant."]

            if initial_context.get('topic_focus'):
                welcome_parts.append(f"I see we'll be focusing on {initial_context['topic_focus']} today.")

            if initial_context.get('active_documents'):
                doc_count = len(initial_context['active_documents'])
                welcome_parts.append(f"I have access to {doc_count} document{'s' if doc_count > 1 else ''} to help answer your questions.")

            welcome_parts.append("Feel free to ask me anything about your study materials!")

            return " ".join(welcome_parts)

        except Exception as e:
            logger.warning(f"Welcome message generation failed: {str(e)}")
            return None

    def _build_conversation_context_string(
        self,
        messages: List[Message]
    ) -> str:
        """
        Build a context string from conversation messages.

        Args:
            messages: List of conversation messages

        Returns:
            Context string for use in prompts
        """
        try:
            if not messages:
                return ""

            # Get recent messages (last 5)
            recent_messages = messages[-5:]
            context_parts = []

            for message in recent_messages:
                if message.role in [MessageRole.USER, MessageRole.ASSISTANT]:
                    role_label = "Student" if message.role == MessageRole.USER else "Assistant"
                    content_preview = message.content[:150] + "..." if len(message.content) > 150 else message.content
                    context_parts.append(f"{role_label}: {content_preview}")

            return " | ".join(context_parts)

        except Exception as e:
            logger.warning(f"Context string building failed: {str(e)}")
            return ""

    async def _update_conversation_focus(
        self,
        conversation_context: ConversationContext,
        user_message: str,
        response: ChatResponse
    ) -> None:
        """
        Update conversation focus based on current interaction.

        Args:
            conversation_context: Current conversation context
            user_message: User's message
            response: Generated response
        """
        try:
            # Simple topic extraction from user message
            # This is a basic implementation - could be enhanced with NLP
            message_words = user_message.lower().split()

            # Look for key academic terms that might indicate topic focus
            academic_indicators = [
                'study', 'learn', 'understand', 'explain', 'definition',
                'concept', 'theory', 'principle', 'method', 'process'
            ]

            # If message contains academic indicators and no current focus, try to extract topic
            if (not conversation_context.topic_focus and
                any(indicator in message_words for indicator in academic_indicators) and
                len(message_words) > 3):

                # Simple topic extraction: look for capitalized words (potential topics)
                potential_topics = []
                words = user_message.split()
                for i, word in enumerate(words):
                    if (word[0].isupper() and
                        word.lower() not in ['i', 'what', 'how', 'why', 'when', 'where', 'can', 'could', 'would', 'should'] and
                        len(word) > 2):
                        potential_topics.append(word)

                if potential_topics:
                    new_focus = potential_topics[0]  # Take first potential topic
                    await self.update_conversation_focus(
                        conversation_context.conversation_id,
                        new_focus
                    )

        except Exception as e:
            logger.warning(f"Focus update failed: {str(e)}")

    def _calculate_conversation_duration(
        self,
        conversation_context: ConversationContext
    ) -> float:
        """
        Calculate conversation duration in minutes.

        Args:
            conversation_context: Conversation context

        Returns:
            Duration in minutes
        """
        try:
            if not conversation_context.messages:
                return 0.0

            first_message = conversation_context.messages[0]
            last_message = conversation_context.messages[-1]

            duration = last_message.timestamp - first_message.timestamp
            return duration.total_seconds() / 60.0

        except Exception as e:
            logger.warning(f"Duration calculation failed: {str(e)}")
            return 0.0


class ConversationError(Exception):
    """Raised when conversation operations fail."""
    pass
