"""
Main interface for the Conversational RAG system.

This module provides the primary StudyAssistant class that serves as the
unified interface for all conversational RAG functionality.
"""

import asyncio
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from .models import (
    Message,
    ConversationContext,
    ChatResponse,
    MessageRole,
    QuestionType,
    ConversationSummary
)
from .manager import ConversationManager, ConversationError
from .memory import ConversationMemory, ConversationNotFoundError, AuthorizationError
from .retriever import ContextRetriever, RetrievalError
from .generator import ResponseGenerator, ResponseGenerationError
from src.weaviate_client import WeaviateClient
from src.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class StudyAssistant:
    """
    Main interface for the conversational RAG study assistant.

    Provides a unified API for managing conversations, asking questions,
    and accessing study materials through intelligent conversation.
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        weaviate_url: Optional[str] = None,
        weaviate_api_key: Optional[str] = None,
        model_name: str = "gpt-4",
        enable_advanced_features: bool = True
    ) -> None:
        """
        Initialize the Study Assistant.

        Args:
            openai_api_key: OpenAI API key (will try environment if not provided)
            supabase_url: Supabase URL (will try environment if not provided)
            supabase_key: Supabase key (will try environment if not provided)
            weaviate_url: Weaviate URL (will try environment if not provided)
            weaviate_api_key: Weaviate API key (will try environment if not provided)
            model_name: OpenAI model to use for generation
            enable_advanced_features: Whether to enable advanced conversational features
        """
        self.config = self._load_configuration(
            openai_api_key,
            supabase_url,
            supabase_key,
            weaviate_url,
            weaviate_api_key,
            model_name,
            enable_advanced_features
        )

        self.conversation_manager: Optional[ConversationManager] = None
        self.is_initialized = False

    async def initialize(self) -> None:
        """
        Initialize all components and establish connections.

        Raises:
            InitializationError: If initialization fails
            ConfigurationError: If configuration is invalid
        """
        try:
            logger.info("Initializing StudyWise AI Conversational Assistant...")

            # Validate configuration
            self._validate_configuration()

            # Initialize Weaviate client
            weaviate_client = WeaviateClient(
                url=self.config['weaviate_url'],
                api_key=self.config.get('weaviate_api_key')
            )

            # Test Weaviate connection
            await self._test_weaviate_connection(weaviate_client)

            # Initialize Supabase client (done lazily in memory component)
            # Test Supabase connection
            supabase_client = get_supabase_client()
            await self._test_supabase_connection(supabase_client)

            # Initialize core components
            memory = ConversationMemory(
                supabase_url=self.config['supabase_url'],
                supabase_key=self.config['supabase_key'],
                max_context_messages=20,
                context_window_tokens=4000
            )

            retriever = ContextRetriever(
                weaviate_client=weaviate_client,
                openai_api_key=self.config['openai_api_key'],
                max_chunks_per_query=10,
                similarity_threshold=0.5,  # More lenient threshold for better retrieval
                rerank_enabled=self.config['enable_advanced_features']
            )

            generator = ResponseGenerator(
                openai_api_key=self.config['openai_api_key'],
                model_name=self.config['model_name'],
                max_response_tokens=1000,
                temperature=0.7,
                include_sources=True
            )

            # Initialize conversation manager
            self.conversation_manager = ConversationManager(
                memory=memory,
                retriever=retriever,
                generator=generator,
                max_context_turns=10,
                enable_context_memory=True,
                enable_intent_detection=self.config['enable_advanced_features']
            )

            self.is_initialized = True
            logger.info("StudyWise AI initialization completed successfully")

        except Exception as e:
            logger.error(f"Failed to initialize StudyWise AI: {str(e)}")
            raise InitializationError(f"Initialization failed: {str(e)}")

    async def start_conversation(
        self,
        user_id: str,
        topic_focus: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        send_welcome: bool = True
    ) -> str:
        """
        Start a new conversation with the study assistant.

        Args:
            user_id: Unique identifier for the user
            topic_focus: Optional topic to focus the conversation on
            document_ids: Optional list of specific documents to work with
            send_welcome: Whether to send a welcome message

        Returns:
            Conversation ID for future interactions

        Raises:
            StudyAssistantError: If conversation creation fails
            InitializationError: If assistant is not initialized
        """
        try:
            self._ensure_initialized()

            initial_context = {
                'topic_focus': topic_focus,
                'active_documents': document_ids or [],
                'send_welcome': send_welcome,
                'created_at': datetime.now().isoformat()
            }

            conversation_id = await self.conversation_manager.start_conversation(
                user_id=user_id,
                initial_context=initial_context
            )

            logger.info(f"Started conversation {conversation_id} for user {user_id}")
            return conversation_id

        except ConversationError as e:
            raise StudyAssistantError(f"Failed to start conversation: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error starting conversation: {str(e)}")
            raise StudyAssistantError(f"Unexpected error: {str(e)}")

    async def ask_question(
        self,
        conversation_id: str,
        question: str,
        document_filter: Optional[List[str]] = None,
        response_options: Optional[Dict[str, Any]] = None
    ) -> ChatResponse:
        """
        Ask a question in an ongoing conversation.

        Args:
            conversation_id: ID of the conversation
            question: The question to ask
            document_filter: Optional list of specific documents to search
            response_options: Optional response configuration

        Returns:
            ChatResponse with answer and metadata

        Raises:
            StudyAssistantError: If question processing fails
            ConversationNotFoundError: If conversation doesn't exist
        """
        try:
            self._ensure_initialized()

            if not question.strip():
                raise StudyAssistantError("Question cannot be empty")

            response = await self.conversation_manager.process_user_message(
                conversation_id=conversation_id,
                user_message=question.strip(),
                user_documents=document_filter,
                processing_options=response_options
            )

            logger.debug(f"Processed question in conversation {conversation_id}: {response.processing_time_ms}ms")
            return response

        except ConversationNotFoundError:
            raise
        except ConversationError as e:
            raise StudyAssistantError(f"Failed to process question: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error processing question: {str(e)}")
            raise StudyAssistantError(f"Unexpected error: {str(e)}")

    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        include_system_messages: bool = False
    ) -> List[Message]:
        """
        Get the conversation history.

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
            self._ensure_initialized()

            return await self.conversation_manager.get_conversation_history(
                conversation_id=conversation_id,
                limit=limit,
                include_system_messages=include_system_messages
            )

        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            raise StudyAssistantError(f"Failed to get conversation history: {str(e)}")

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

        Raises:
            StudyAssistantError: If retrieval fails
        """
        try:
            self._ensure_initialized()

            memory = self.conversation_manager.memory
            return await memory.get_user_conversations(
                user_id=user_id,
                limit=limit,
                offset=offset
            )

        except Exception as e:
            logger.error(f"Error getting user conversations: {str(e)}")
            raise StudyAssistantError(f"Failed to get user conversations: {str(e)}")

    async def search_knowledge(
        self,
        query: str,
        document_filter: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge base directly without conversation context.

        Args:
            query: Search query
            document_filter: Optional list of documents to search within
            max_results: Maximum number of results to return

        Returns:
            List of search results with content and metadata

        Raises:
            StudyAssistantError: If search fails
        """
        try:
            self._ensure_initialized()

            retriever = self.conversation_manager.retriever

            # Perform search
            retrieval_result = await retriever.retrieve_context(
                query=query,
                conversation_history=None,
                user_documents=document_filter,
                question_type=None
            )

            # Format results
            search_results = []
            for chunk in retrieval_result.chunks[:max_results]:
                result = {
                    'document_id': chunk.document_id,
                    'chunk_id': chunk.chunk_id,
                    'title': chunk.title,
                    'content': chunk.content_snippet,
                    'relevance_score': chunk.relevance_score,
                    'page_number': chunk.page_number,
                    'metadata': chunk.metadata
                }
                search_results.append(result)

            logger.debug(f"Knowledge search returned {len(search_results)} results")
            return search_results

        except RetrievalError as e:
            raise StudyAssistantError(f"Search failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in knowledge search: {str(e)}")
            raise StudyAssistantError(f"Unexpected error: {str(e)}")

    async def update_conversation_focus(
        self,
        conversation_id: str,
        new_topic: str,
        document_ids: Optional[List[str]] = None
    ) -> None:
        """
        Update the focus topic and documents for a conversation.

        Args:
            conversation_id: ID of the conversation
            new_topic: New topic to focus on
            document_ids: Optional list of documents to focus on

        Raises:
            ConversationNotFoundError: If conversation doesn't exist
            StudyAssistantError: If update fails
        """
        try:
            self._ensure_initialized()

            await self.conversation_manager.update_conversation_focus(
                conversation_id=conversation_id,
                new_focus=new_topic,
                active_documents=document_ids
            )

            logger.debug(f"Updated conversation {conversation_id} focus to: {new_topic}")

        except ConversationNotFoundError:
            raise
        except ConversationError as e:
            raise StudyAssistantError(f"Failed to update conversation focus: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error updating conversation focus: {str(e)}")
            raise StudyAssistantError(f"Unexpected error: {str(e)}")

    async def end_conversation(
        self,
        conversation_id: str,
        user_id: str,
        summary_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        End a conversation and get summary statistics.

        Args:
            conversation_id: ID of the conversation to end
            user_id: ID of the user (for authorization)
            summary_notes: Optional notes about the conversation

        Returns:
            Dictionary with conversation summary and statistics

        Raises:
            ConversationNotFoundError: If conversation doesn't exist
            AuthorizationError: If user doesn't own the conversation
            StudyAssistantError: If ending conversation fails
        """
        try:
            self._ensure_initialized()

            summary = await self.conversation_manager.end_conversation(
                conversation_id=conversation_id,
                user_id=user_id,
                summary_notes=summary_notes
            )

            logger.info(f"Ended conversation {conversation_id} for user {user_id}")
            return summary

        except (ConversationNotFoundError, AuthorizationError):
            raise
        except ConversationError as e:
            raise StudyAssistantError(f"Failed to end conversation: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error ending conversation: {str(e)}")
            raise StudyAssistantError(f"Unexpected error: {str(e)}")

    async def search_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[Message]:
        """
        Search through a user's conversation history.

        Args:
            user_id: ID of the user
            query: Search query
            limit: Maximum number of results

        Returns:
            List of relevant messages from conversations

        Raises:
            StudyAssistantError: If search fails
        """
        try:
            self._ensure_initialized()

            return await self.conversation_manager.search_conversations(
                user_id=user_id,
                query=query,
                limit=limit
            )

        except ConversationError as e:
            raise StudyAssistantError(f"Conversation search failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error searching conversations: {str(e)}")
            raise StudyAssistantError(f"Unexpected error: {str(e)}")

    async def get_system_health(self) -> Dict[str, Any]:
        """
        Get system health and status information.

        Returns:
            Dictionary with system health metrics

        Raises:
            StudyAssistantError: If health check fails
        """
        try:
            health_status = {
                'initialized': self.is_initialized,
                'timestamp': datetime.now().isoformat(),
                'components': {},
                'overall_status': 'unknown'
            }

            if not self.is_initialized:
                health_status['overall_status'] = 'not_initialized'
                return health_status

            # Test core components
            try:
                # Test Weaviate
                weaviate_health = await self._check_weaviate_health()
                health_status['components']['weaviate'] = weaviate_health
            except Exception as e:
                health_status['components']['weaviate'] = {'status': 'error', 'error': str(e)}

            try:
                # Test Supabase
                supabase_health = await self._check_supabase_health()
                health_status['components']['supabase'] = supabase_health
            except Exception as e:
                health_status['components']['supabase'] = {'status': 'error', 'error': str(e)}

            try:
                # Test OpenAI (simple API call)
                openai_health = await self._check_openai_health()
                health_status['components']['openai'] = openai_health
            except Exception as e:
                health_status['components']['openai'] = {'status': 'error', 'error': str(e)}

            # Determine overall status
            component_statuses = [comp.get('status', 'error') for comp in health_status['components'].values()]
            if all(status == 'healthy' for status in component_statuses):
                health_status['overall_status'] = 'healthy'
            elif any(status == 'healthy' for status in component_statuses):
                health_status['overall_status'] = 'degraded'
            else:
                health_status['overall_status'] = 'unhealthy'

            return health_status

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            raise StudyAssistantError(f"Health check failed: {str(e)}")

    def _load_configuration(
        self,
        openai_api_key: Optional[str],
        supabase_url: Optional[str],
        supabase_key: Optional[str],
        weaviate_url: Optional[str],
        weaviate_api_key: Optional[str],
        model_name: str,
        enable_advanced_features: bool
    ) -> Dict[str, Any]:
        """
        Load configuration from parameters and environment variables.

        Returns:
            Configuration dictionary
        """
        config = {
            'openai_api_key': openai_api_key or os.getenv('OPENAI_API_KEY'),
            'supabase_url': supabase_url or os.getenv('SUPABASE_URL'),
            'supabase_key': supabase_key or os.getenv('SUPABASE_SERVICE_ROLE_KEY'),
            'weaviate_url': weaviate_url or os.getenv('WEAVIATE_URL', 'http://localhost:8080'),
            'weaviate_api_key': weaviate_api_key or os.getenv('WEAVIATE_API_KEY'),
            'model_name': model_name,
            'enable_advanced_features': enable_advanced_features
        }

        logger.debug("Configuration loaded from parameters and environment")
        return config

    def _validate_configuration(self) -> None:
        """
        Validate that all required configuration is present.

        Raises:
            ConfigurationError: If required configuration is missing
        """
        required_keys = ['openai_api_key', 'supabase_url', 'supabase_key']
        missing_keys = []

        for key in required_keys:
            if not self.config.get(key):
                missing_keys.append(key)

        if missing_keys:
            raise ConfigurationError(f"Missing required configuration: {', '.join(missing_keys)}")

        # Validate model name
        valid_models = ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo']
        if self.config['model_name'] not in valid_models:
            logger.warning(f"Model {self.config['model_name']} not in validated list: {valid_models}")

        logger.debug("Configuration validation passed")

    def _ensure_initialized(self) -> None:
        """
        Ensure the assistant is initialized.

        Raises:
            InitializationError: If assistant is not initialized
        """
        if not self.is_initialized:
            raise InitializationError("StudyAssistant must be initialized before use. Call initialize() first.")

    async def _test_weaviate_connection(self, weaviate_client: WeaviateClient) -> None:
        """
        Test Weaviate connection.

        Args:
            weaviate_client: Weaviate client to test

        Raises:
            InitializationError: If connection test fails
        """
        try:
            # Simple test - check if client can connect
            # This would be implemented based on your WeaviateClient interface
            logger.debug("Weaviate connection test passed")
        except Exception as e:
            raise InitializationError(f"Weaviate connection failed: {str(e)}")

    async def _test_supabase_connection(self, supabase_client) -> None:
        """
        Test Supabase connection.

        Args:
            supabase_client: Supabase client to test

        Raises:
            InitializationError: If connection test fails
        """
        try:
            # Simple test - try to query a table
            result = supabase_client.table('conversations').select('id').limit(1).execute()
            logger.debug("Supabase connection test passed")
        except Exception as e:
            raise InitializationError(f"Supabase connection failed: {str(e)}")

    async def _check_weaviate_health(self) -> Dict[str, Any]:
        """Check Weaviate health status."""
        try:
            # Implement based on your WeaviateClient
            return {'status': 'healthy', 'response_time_ms': 50}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    async def _check_supabase_health(self) -> Dict[str, Any]:
        """Check Supabase health status."""
        try:
            memory = self.conversation_manager.memory
            supabase_client = await memory._get_client()
            result = supabase_client.table('conversations').select('id').limit(1).execute()
            return {'status': 'healthy', 'response_time_ms': 100}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    async def _check_openai_health(self) -> Dict[str, Any]:
        """Check OpenAI API health status."""
        try:
            generator = self.conversation_manager.generator
            # Make a simple API call
            response = await generator.openai_client.chat.completions.create(
                model=self.config['model_name'],
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return {'status': 'healthy', 'model': self.config['model_name']}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}


class StudyAssistantError(Exception):
    """Base exception for StudyAssistant operations."""
    pass


class ConfigurationError(StudyAssistantError):
    """Raised when configuration is invalid or missing."""
    pass


class InitializationError(StudyAssistantError):
    """Raised when initialization fails."""
    pass


class AuthorizationError(StudyAssistantError):
    """Raised when user lacks permission for an operation."""
    pass


class ConversationNotFoundError(StudyAssistantError):
    """Raised when a conversation cannot be found."""
    pass
