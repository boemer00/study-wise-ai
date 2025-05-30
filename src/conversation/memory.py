"""
Conversation memory management for the Conversational RAG system.

This module handles storing, retrieving, and managing conversation history
and context for multi-turn interactions with the study assistant.
"""

import asyncio
import uuid
import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import logging

from .models import (
    Message,
    ConversationContext,
    ConversationSummary,
    MessageRole
)
from src.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Manages conversation memory and persistence.

    Handles storing conversation history, maintaining context windows,
    and providing efficient retrieval of relevant conversation history.
    """

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        max_context_messages: int = 20,
        context_window_tokens: int = 4000
    ) -> None:
        """
        Initialize conversation memory manager.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase service key
            max_context_messages: Maximum messages to keep in context
            context_window_tokens: Maximum tokens for context window
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.max_context_messages = max_context_messages
        self.context_window_tokens = context_window_tokens
        self.client = None

    async def _get_client(self):
        """Get or create Supabase client."""
        if self.client is None:
            self.client = get_supabase_client()
        return self.client

    async def create_conversation(
        self,
        user_id: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new conversation and return conversation ID.

        Args:
            user_id: ID of the user starting the conversation
            initial_context: Optional initial context metadata

        Returns:
            Unique conversation ID

        Raises:
            DatabaseError: If conversation creation fails
        """
        try:
            client = await self._get_client()
            conversation_id = str(uuid.uuid4())

            conversation_data = {
                'id': conversation_id,
                'user_id': user_id,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'topic_focus': initial_context.get('topic_focus') if initial_context else None,
                'active_documents': initial_context.get('active_documents', []) if initial_context else [],
                'metadata': initial_context or {}
            }

            result = client.table('conversations').insert(conversation_data).execute()

            if result.data:
                logger.info(f"Created conversation {conversation_id} for user {user_id}")
                return conversation_id
            else:
                raise DatabaseError("Failed to create conversation")

        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            raise DatabaseError(f"Failed to create conversation: {str(e)}")

    async def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a message to the conversation history.

        Args:
            conversation_id: ID of the conversation
            role: Role of the message sender
            content: Message content
            sources: Optional document sources referenced
            metadata: Optional message metadata

        Returns:
            Message ID

        Raises:
            ConversationNotFoundError: If conversation doesn't exist
            DatabaseError: If message storage fails
        """
        try:
            client = await self._get_client()
            message_id = str(uuid.uuid4())

            # Verify conversation exists
            conv_result = client.table('conversations').select('id').eq('id', conversation_id).execute()
            if not conv_result.data:
                raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

            message_data = {
                'message_id': message_id,
                'conversation_id': conversation_id,
                'role': role.value,
                'content': content,
                'sources': sources or [],
                'metadata': metadata or {},
                'created_at': datetime.now(timezone.utc).isoformat()
            }

            # Insert message
            result = client.table('messages').insert(message_data).execute()

            if result.data:
                # Update conversation timestamp
                client.table('conversations').update({
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }).eq('id', conversation_id).execute()

                logger.debug(f"Added message {message_id} to conversation {conversation_id}")
                return message_id
            else:
                raise DatabaseError("Failed to insert message")

        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error adding message: {str(e)}")
            raise DatabaseError(f"Failed to add message: {str(e)}")

    async def get_conversation_context(
        self,
        conversation_id: str
    ) -> ConversationContext:
        """
        Get current conversation context with recent messages.

        Args:
            conversation_id: ID of the conversation

        Returns:
            ConversationContext with recent messages and metadata

        Raises:
            ConversationNotFoundError: If conversation doesn't exist
        """
        try:
            client = await self._get_client()

            # Get conversation metadata
            conv_result = client.table('conversations').select('*').eq('id', conversation_id).execute()
            if not conv_result.data:
                raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

            conversation = conv_result.data[0]

            # Get recent messages
            messages_result = client.table('messages').select('*').eq(
                'conversation_id', conversation_id
            ).order('created_at', desc=False).limit(self.max_context_messages).execute()

            messages = []
            if messages_result.data:
                for msg_data in messages_result.data:
                    message = Message(
                        message_id=msg_data['message_id'],
                        role=MessageRole(msg_data['role']),
                        content=msg_data['content'],
                        timestamp=datetime.fromisoformat(msg_data['created_at']),
                        conversation_id=conversation_id,
                        sources=msg_data.get('sources', []),
                        metadata=msg_data.get('metadata', {})
                    )
                    messages.append(message)

            context = ConversationContext(
                conversation_id=conversation_id,
                user_id=conversation['user_id'],
                messages=messages,
                last_updated=datetime.fromisoformat(conversation['updated_at']),
                topic_focus=conversation.get('topic_focus'),
                active_documents=conversation.get('active_documents', [])
            )

            return context

        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting conversation context: {str(e)}")
            raise DatabaseError(f"Failed to get conversation context: {str(e)}")

    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """
        Get conversation message history.

        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages to return
            offset: Number of messages to skip

        Returns:
            List of messages in chronological order

        Raises:
            ConversationNotFoundError: If conversation doesn't exist
        """
        try:
            client = await self._get_client()

            # Verify conversation exists
            conv_result = client.table('conversations').select('id').eq('id', conversation_id).execute()
            if not conv_result.data:
                raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

            # Build query
            query = client.table('messages').select('*').eq('conversation_id', conversation_id).order('created_at', desc=False)

            if offset > 0:
                query = query.range(offset, offset + (limit or 1000) - 1)
            elif limit:
                query = query.limit(limit)

            result = query.execute()

            messages = []
            if result.data:
                for msg_data in result.data:
                    message = Message(
                        message_id=msg_data['message_id'],
                        role=MessageRole(msg_data['role']),
                        content=msg_data['content'],
                        timestamp=datetime.fromisoformat(msg_data['created_at']),
                        conversation_id=conversation_id,
                        sources=msg_data.get('sources', []),
                        metadata=msg_data.get('metadata', {})
                    )
                    messages.append(message)

            return messages

        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            raise DatabaseError(f"Failed to get conversation history: {str(e)}")

    async def update_conversation_metadata(
        self,
        conversation_id: str,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Update conversation metadata.

        Args:
            conversation_id: ID of the conversation
            metadata: Metadata to update

        Raises:
            ConversationNotFoundError: If conversation doesn't exist
        """
        try:
            client = await self._get_client()

            # Get existing conversation
            conv_result = client.table('conversations').select('*').eq('id', conversation_id).execute()
            if not conv_result.data:
                raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

            # Merge with existing metadata
            existing_metadata = conv_result.data[0].get('metadata', {})
            updated_metadata = {**existing_metadata, **metadata}

            # Update metadata and timestamp
            update_data = {
                'metadata': updated_metadata,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }

            # Update specific fields if provided
            if 'topic_focus' in metadata:
                update_data['topic_focus'] = metadata['topic_focus']
            if 'active_documents' in metadata:
                update_data['active_documents'] = metadata['active_documents']

            result = client.table('conversations').update(update_data).eq('id', conversation_id).execute()

            if result.data:
                logger.debug(f"Updated conversation {conversation_id} metadata")
            else:
                raise DatabaseError("Failed to update conversation metadata")

        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating conversation metadata: {str(e)}")
            raise DatabaseError(f"Failed to update conversation metadata: {str(e)}")

    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ConversationSummary]:
        """
        Get conversation summaries for a user.

        Args:
            user_id: ID of the user
            limit: Maximum number of conversations to return
            offset: Number of conversations to skip

        Returns:
            List of conversation summaries
        """
        try:
            client = await self._get_client()

            # Get user conversations with message counts
            query = client.table('conversations').select(
                'id, user_id, created_at, updated_at, topic_focus, active_documents, metadata'
            ).eq('user_id', user_id).order('updated_at', desc=True)

            if offset > 0:
                query = query.range(offset, offset + limit - 1)
            else:
                query = query.limit(limit)

            result = query.execute()

            summaries = []
            if result.data:
                for conv_data in result.data:
                    # Get message count for each conversation
                    msg_count_result = client.table('messages').select(
                        'id', count='exact'
                    ).eq('conversation_id', conv_data['id']).execute()

                    message_count = msg_count_result.count or 0

                    # Extract topics and documents from metadata and messages
                    topics_covered = []
                    documents_referenced = conv_data.get('active_documents', [])

                    if conv_data.get('topic_focus'):
                        topics_covered.append(conv_data['topic_focus'])

                    # Simple average response time calculation (placeholder)
                    avg_response_time_ms = 2000.0  # TODO: Calculate from actual response times

                    summary = ConversationSummary(
                        conversation_id=conv_data['id'],
                        user_id=conv_data['user_id'],
                        start_time=datetime.fromisoformat(conv_data['created_at']),
                        end_time=None,  # Mark as active for now
                        message_count=message_count,
                        topics_covered=topics_covered,
                        documents_referenced=documents_referenced,
                        avg_response_time_ms=avg_response_time_ms
                    )
                    summaries.append(summary)

            return summaries

        except Exception as e:
            logger.error(f"Error getting user conversations: {str(e)}")
            raise DatabaseError(f"Failed to get user conversations: {str(e)}")

    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a conversation and all its messages.

        Args:
            conversation_id: ID of the conversation to delete
            user_id: ID of the user (for authorization)

        Returns:
            True if deletion was successful

        Raises:
            ConversationNotFoundError: If conversation doesn't exist
            AuthorizationError: If user doesn't own the conversation
        """
        try:
            client = await self._get_client()

            # Verify conversation exists and user owns it
            conv_result = client.table('conversations').select('user_id').eq('id', conversation_id).execute()
            if not conv_result.data:
                raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

            if conv_result.data[0]['user_id'] != user_id:
                raise AuthorizationError(f"User {user_id} not authorized to delete conversation {conversation_id}")

            # Delete messages first (due to foreign key constraint)
            client.table('messages').delete().eq('conversation_id', conversation_id).execute()

            # Delete conversation
            result = client.table('conversations').delete().eq('id', conversation_id).execute()

            if result.data:
                logger.info(f"Deleted conversation {conversation_id} for user {user_id}")
                return True
            else:
                return False

        except (ConversationNotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error deleting conversation: {str(e)}")
            raise DatabaseError(f"Failed to delete conversation: {str(e)}")

    async def search_conversation_history(
        self,
        user_id: str,
        query: str,
        conversation_ids: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Message]:
        """
        Search through conversation history for relevant messages.

        Args:
            user_id: ID of the user
            query: Search query
            conversation_ids: Optional list of specific conversations to search
            limit: Maximum number of results

        Returns:
            List of relevant messages
        """
        try:
            client = await self._get_client()

            # Build search query - using simple text search for now
            # TODO: Implement semantic search with embeddings
            base_query = client.table('messages').select(
                '*, conversations!inner(user_id)'
            ).eq('conversations.user_id', user_id)

            # Add conversation filter if specified
            if conversation_ids:
                base_query = base_query.in_('conversation_id', conversation_ids)

            # Add text search (PostgreSQL full-text search)
            search_query = query.strip().lower()
            base_query = base_query.ilike('content', f'%{search_query}%')

            result = base_query.order('created_at', desc=True).limit(limit).execute()

            messages = []
            if result.data:
                for msg_data in result.data:
                    message = Message(
                        message_id=msg_data['message_id'],
                        role=MessageRole(msg_data['role']),
                        content=msg_data['content'],
                        timestamp=datetime.fromisoformat(msg_data['created_at']),
                        conversation_id=msg_data['conversation_id'],
                        sources=msg_data.get('sources', []),
                        metadata=msg_data.get('metadata', {})
                    )
                    messages.append(message)

            return messages

        except Exception as e:
            logger.error(f"Error searching conversation history: {str(e)}")
            raise DatabaseError(f"Failed to search conversation history: {str(e)}")

    def _format_context_window(
        self,
        messages: List[Message]
    ) -> str:
        """
        Format messages into a context window for LLM consumption.

        Args:
            messages: List of conversation messages

        Returns:
            Formatted context string
        """
        if not messages:
            return ""

        formatted_messages = []
        total_tokens = 0

        for message in reversed(messages):  # Start from most recent
            # Format message with role indicator
            role_prefix = {
                MessageRole.USER: "Human",
                MessageRole.ASSISTANT: "Assistant",
                MessageRole.SYSTEM: "System"
            }.get(message.role, "Unknown")

            formatted_msg = f"{role_prefix}: {message.content}"

            # Estimate tokens (rough approximation)
            msg_tokens = self._estimate_token_count(formatted_msg)

            if total_tokens + msg_tokens > self.context_window_tokens:
                break

            formatted_messages.append(formatted_msg)
            total_tokens += msg_tokens

        # Reverse to get chronological order
        formatted_messages.reverse()

        return "\n\n".join(formatted_messages)

    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation).

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters for English text
        # This is a simple heuristic; for production, use tiktoken library
        words = len(text.split())
        chars = len(text)

        # Use the more conservative estimate
        token_estimate = max(words, chars // 4)
        return int(token_estimate * 1.1)  # Add 10% buffer

    async def _cleanup_old_conversations(
        self,
        retention_days: int = 90
    ) -> int:
        """
        Clean up old conversations beyond retention period.

        Args:
            retention_days: Number of days to retain conversations

        Returns:
            Number of conversations cleaned up
        """
        try:
            client = await self._get_client()
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

            # Find old conversations
            old_convs_result = client.table('conversations').select('id').lt(
                'updated_at', cutoff_date.isoformat()
            ).execute()

            if not old_convs_result.data:
                return 0

            conversation_ids = [conv['id'] for conv in old_convs_result.data]

            # Delete messages first
            for conv_id in conversation_ids:
                client.table('messages').delete().eq('conversation_id', conv_id).execute()

            # Delete conversations
            client.table('conversations').delete().in_('id', conversation_ids).execute()

            logger.info(f"Cleaned up {len(conversation_ids)} old conversations")
            return len(conversation_ids)

        except Exception as e:
            logger.error(f"Error cleaning up conversations: {str(e)}")
            return 0


class ConversationNotFoundError(Exception):
    """Raised when a conversation cannot be found."""
    pass


class AuthorizationError(Exception):
    """Raised when user lacks permission for conversation access."""
    pass


class DatabaseError(Exception):
    """Raised when database operations fail."""
    pass
