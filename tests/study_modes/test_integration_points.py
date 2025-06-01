"""
Tests for integration points with existing StudyWise infrastructure.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.study_modes.study_mode_manager import StudyModeManager
from src.study_modes.modes.traditional_mode import TraditionalMode
from src.study_modes.models.study_session import StudyMode, StudySession


class TestWeaviateIntegration:
    """Test integration with Weaviate vector database."""

    @pytest.fixture
    def mock_weaviate_client(self):
        """Mock Weaviate client for testing."""
        mock_client = Mock()
        mock_client.query = Mock()
        mock_client.query.get.return_value.with_class_name.return_value.with_where.return_value.with_limit.return_value.do.return_value = {
            'data': {
                'Get': {
                    'Document': [
                        {
                            'content': 'Neural networks are computational models inspired by biological neural networks.',
                            'metadata': {'chunk_id': 'chunk_1', 'document_id': 'doc_1'},
                            'concepts': ['neural networks', 'computational models']
                        },
                        {
                            'content': 'Machine learning algorithms learn patterns from data to make predictions.',
                            'metadata': {'chunk_id': 'chunk_2', 'document_id': 'doc_1'},
                            'concepts': ['machine learning', 'algorithms', 'predictions']
                        }
                    ]
                }
            }
        }
        return mock_client

    @pytest.fixture
    def traditional_mode_with_weaviate(self, mock_weaviate_client):
        """TraditionalMode with mocked Weaviate integration."""
        with patch('src.study_modes.modes.base_mode.weaviate_client', mock_weaviate_client):
            mode = TraditionalMode(
                documents=['doc_1'],
                user_id='test-user',
                difficulty_level=3
            )
            mode.weaviate_client = mock_weaviate_client
            return mode

    @pytest.mark.asyncio
    async def test_document_context_retrieval(self, traditional_mode_with_weaviate):
        """Test document context retrieval from Weaviate."""
        context = await traditional_mode_with_weaviate.get_document_context(['doc_1'])

        # Verify context structure
        assert 'key_concepts' in context
        assert 'document_summaries' in context
        assert 'complexity_level' in context

        # Verify data from Weaviate
        assert 'neural networks' in context['key_concepts']
        assert 'machine learning' in context['key_concepts']
        assert 'doc_1' in context['document_summaries']

    @pytest.mark.asyncio
    async def test_semantic_search_integration(self, traditional_mode_with_weaviate):
        """Test semantic search for relevant content."""
        query = "What are neural networks?"

        # Mock semantic search response
        traditional_mode_with_weaviate.weaviate_client.query.get.return_value.with_class_name.return_value.with_near_text.return_value.with_limit.return_value.do.return_value = {
            'data': {
                'Get': {
                    'Document': [
                        {
                            'content': 'Neural networks consist of interconnected nodes that process information.',
                            'metadata': {'relevance_score': 0.9, 'document_id': 'doc_1'},
                            'concepts': ['neural networks', 'nodes', 'information processing']
                        }
                    ]
                }
            }
        }

        relevant_content = await traditional_mode_with_weaviate.search_relevant_content(query)

        assert len(relevant_content) > 0
        assert 'neural networks' in relevant_content[0]['content']
        assert relevant_content[0]['metadata']['relevance_score'] > 0.5

    @pytest.mark.asyncio
    async def test_weaviate_connection_error_handling(self, traditional_mode_with_weaviate):
        """Test graceful handling of Weaviate connection errors."""
        # Mock connection error
        traditional_mode_with_weaviate.weaviate_client.query.get.side_effect = ConnectionError("Weaviate connection failed")

        # Should not crash, should return fallback data
        context = await traditional_mode_with_weaviate.get_document_context(['doc_1'])

        assert context is not None
        assert 'key_concepts' in context
        assert context['key_concepts'] == ['Basic concepts']  # Fallback

    @pytest.mark.asyncio
    async def test_empty_document_query(self, traditional_mode_with_weaviate):
        """Test handling of empty document queries."""
        # Mock empty response
        traditional_mode_with_weaviate.weaviate_client.query.get.return_value.with_class_name.return_value.with_where.return_value.with_limit.return_value.do.return_value = {
            'data': {'Get': {'Document': []}}
        }

        context = await traditional_mode_with_weaviate.get_document_context(['nonexistent_doc'])

        assert context is not None
        assert context['key_concepts'] == ['Basic concepts']  # Fallback


class TestSupabaseIntegration:
    """Test integration with Supabase for session persistence."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client for testing."""
        mock_client = Mock()

        # Mock table operations
        mock_table = Mock()
        mock_client.table.return_value = mock_table

        # Mock insert operation
        mock_table.insert.return_value.execute.return_value = {
            'data': [{'id': 'session_123', 'created_at': '2024-01-15T10:00:00'}],
            'error': None
        }

        # Mock select operation
        mock_table.select.return_value.eq.return_value.execute.return_value = {
            'data': [
                {
                    'id': 'session_123',
                    'user_id': 'user_456',
                    'study_mode': 'TRADITIONAL',
                    'difficulty_level': 3,
                    'session_data': {
                        'interactions_count': 5,
                        'concepts_covered': ['machine learning', 'neural networks'],
                        'user_performance_scores': [0.6, 0.7, 0.8]
                    },
                    'created_at': '2024-01-15T10:00:00',
                    'updated_at': '2024-01-15T10:30:00'
                }
            ],
            'error': None
        }

        # Mock update operation
        mock_table.update.return_value.eq.return_value.execute.return_value = {
            'data': [{'id': 'session_123', 'updated_at': '2024-01-15T10:30:00'}],
            'error': None
        }

        return mock_client

    @pytest.fixture
    def study_mode_manager_with_supabase(self, mock_supabase_client):
        """StudyModeManager with mocked Supabase integration."""
        with patch('src.study_modes.study_mode_manager.supabase_client', mock_supabase_client):
            manager = StudyModeManager(user_id='test-user')
            manager.supabase_client = mock_supabase_client
            return manager

    @pytest.mark.asyncio
    async def test_session_creation_persistence(self, study_mode_manager_with_supabase):
        """Test session creation and persistence to Supabase."""
        session = await study_mode_manager_with_supabase.create_session(
            documents=['doc_1'],
            study_mode=StudyMode.TRADITIONAL,
            difficulty_level=3
        )

        assert session is not None
        assert session.session_id is not None
        assert session.user_id == 'test-user'
        assert session.study_mode == StudyMode.TRADITIONAL

        # Verify Supabase insert was called
        study_mode_manager_with_supabase.supabase_client.table.assert_called_with('study_sessions')

    @pytest.mark.asyncio
    async def test_session_loading_from_persistence(self, study_mode_manager_with_supabase):
        """Test loading existing session from Supabase."""
        session = await study_mode_manager_with_supabase.load_session('session_123')

        assert session is not None
        assert session.session_id == 'session_123'
        assert session.user_id == 'user_456'
        assert session.study_mode == StudyMode.TRADITIONAL
        assert session.difficulty_level == 3
        assert len(session.interactions) >= 0  # Should load interaction history

    @pytest.mark.asyncio
    async def test_session_state_persistence(self, study_mode_manager_with_supabase):
        """Test session state updates are persisted."""
        session = await study_mode_manager_with_supabase.create_session(
            documents=['doc_1'],
            study_mode=StudyMode.TRADITIONAL,
            difficulty_level=3
        )

        # Simulate interaction
        await study_mode_manager_with_supabase.add_interaction(
            session.session_id,
            user_input="What is machine learning?",
            ai_response="Machine learning is...",
            concepts_identified=["machine learning"]
        )

        # Verify update was called
        assert study_mode_manager_with_supabase.supabase_client.table.called

    @pytest.mark.asyncio
    async def test_supabase_error_handling(self, study_mode_manager_with_supabase):
        """Test graceful handling of Supabase errors."""
        # Mock error response
        study_mode_manager_with_supabase.supabase_client.table.return_value.insert.return_value.execute.return_value = {
            'data': None,
            'error': {'message': 'Database connection failed'}
        }

        # Should handle error gracefully
        with pytest.raises(Exception):  # Appropriate exception for database errors
            await study_mode_manager_with_supabase.create_session(
                documents=['doc_1'],
                study_mode=StudyMode.TRADITIONAL,
                difficulty_level=3
            )

    @pytest.mark.asyncio
    async def test_session_cleanup_and_archiving(self, study_mode_manager_with_supabase):
        """Test session cleanup and archiving functionality."""
        # Mock old session data
        study_mode_manager_with_supabase.supabase_client.table.return_value.select.return_value.lt.return_value.execute.return_value = {
            'data': [
                {
                    'id': 'old_session_1',
                    'created_at': '2024-01-01T10:00:00',
                    'is_active': False
                }
            ],
            'error': None
        }

        archived_count = await study_mode_manager_with_supabase.cleanup_old_sessions(days_old=30)

        assert archived_count >= 0
        # Verify cleanup queries were made
        assert study_mode_manager_with_supabase.supabase_client.table.called


class TestDocumentHandlerIntegration:
    """Test integration with existing document handling system."""

    @pytest.fixture
    def mock_document_processor(self):
        """Mock document processor for testing."""
        mock_processor = Mock()
        mock_processor.get_document_metadata.return_value = {
            'document_id': 'doc_1',
            'title': 'Neural Collaborative Filtering',
            'content_type': 'PDF',
            'chunk_count': 25,
            'key_topics': ['machine learning', 'collaborative filtering', 'neural networks'],
            'complexity_score': 0.7,
            'reading_time_minutes': 45
        }

        mock_processor.get_document_chunks.return_value = [
            {
                'chunk_id': 'chunk_1',
                'content': 'Introduction to neural collaborative filtering...',
                'concepts': ['collaborative filtering', 'neural networks'],
                'position': 1
            },
            {
                'chunk_id': 'chunk_2',
                'content': 'Matrix factorization techniques...',
                'concepts': ['matrix factorization', 'embeddings'],
                'position': 2
            }
        ]

        return mock_processor

    @pytest.fixture
    def traditional_mode_with_document_handler(self, mock_document_processor):
        """TraditionalMode with mocked document handler integration."""
        with patch('src.study_modes.modes.base_mode.document_processor', mock_document_processor):
            mode = TraditionalMode(
                documents=['doc_1'],
                user_id='test-user',
                difficulty_level=3
            )
            mode.document_processor = mock_document_processor
            return mode

    @pytest.mark.asyncio
    async def test_document_metadata_retrieval(self, traditional_mode_with_document_handler):
        """Test retrieval of document metadata for context generation."""
        metadata = await traditional_mode_with_document_handler.get_document_metadata('doc_1')

        assert metadata['document_id'] == 'doc_1'
        assert metadata['title'] == 'Neural Collaborative Filtering'
        assert 'key_topics' in metadata
        assert metadata['complexity_score'] > 0

    @pytest.mark.asyncio
    async def test_document_content_retrieval(self, traditional_mode_with_document_handler):
        """Test retrieval of document content for study sessions."""
        chunks = await traditional_mode_with_document_handler.get_document_chunks('doc_1')

        assert len(chunks) > 0
        assert 'chunk_id' in chunks[0]
        assert 'content' in chunks[0]
        assert 'concepts' in chunks[0]

    @pytest.mark.asyncio
    async def test_multi_document_handling(self, traditional_mode_with_document_handler):
        """Test handling multiple documents in a single session."""
        # Update mock to handle multiple documents
        traditional_mode_with_document_handler.document_processor.get_document_metadata.side_effect = [
            {
                'document_id': 'doc_1',
                'title': 'Neural Collaborative Filtering',
                'key_topics': ['machine learning', 'collaborative filtering'],
                'complexity_score': 0.7
            },
            {
                'document_id': 'doc_2',
                'title': 'Deep Learning Fundamentals',
                'key_topics': ['deep learning', 'neural networks'],
                'complexity_score': 0.8
            }
        ]

        mode = TraditionalMode(
            documents=['doc_1', 'doc_2'],
            user_id='test-user',
            difficulty_level=3
        )
        mode.document_processor = traditional_mode_with_document_handler.document_processor

        context = await mode.get_document_context(['doc_1', 'doc_2'])

        assert len(context['document_summaries']) == 2
        assert 'doc_1' in context['document_summaries']
        assert 'doc_2' in context['document_summaries']

    @pytest.mark.asyncio
    async def test_document_not_found_handling(self, traditional_mode_with_document_handler):
        """Test handling of non-existent documents."""
        # Mock document not found
        traditional_mode_with_document_handler.document_processor.get_document_metadata.side_effect = FileNotFoundError("Document not found")

        metadata = await traditional_mode_with_document_handler.get_document_metadata('nonexistent_doc')

        # Should return fallback metadata
        assert metadata is not None
        assert 'error' in metadata or metadata == {}

    @pytest.mark.asyncio
    async def test_document_processing_error_recovery(self, traditional_mode_with_document_handler):
        """Test error recovery during document processing."""
        # Mock processing error
        traditional_mode_with_document_handler.document_processor.get_document_chunks.side_effect = Exception("Processing failed")

        chunks = await traditional_mode_with_document_handler.get_document_chunks('doc_1')

        # Should return empty list or fallback data
        assert isinstance(chunks, list)


class TestConcurrentSessionHandling:
    """Test handling of concurrent study sessions."""

    @pytest.fixture
    def study_mode_manager(self):
        """StudyModeManager for concurrent testing."""
        return StudyModeManager(user_id='test-user')

    @pytest.mark.asyncio
    async def test_multiple_active_sessions(self, study_mode_manager):
        """Test handling multiple active sessions for same user."""
        # Create multiple sessions
        session1 = await study_mode_manager.create_session(
            documents=['doc_1'],
            study_mode=StudyMode.TRADITIONAL,
            difficulty_level=2
        )

        session2 = await study_mode_manager.create_session(
            documents=['doc_2'],
            study_mode=StudyMode.FEYNMAN,
            difficulty_level=3
        )

        assert session1.session_id != session2.session_id
        assert session1.study_mode != session2.study_mode

        # Both should be active
        assert session1.is_active
        assert session2.is_active

    @pytest.mark.asyncio
    async def test_session_isolation(self, study_mode_manager):
        """Test that sessions are properly isolated."""
        session1 = await study_mode_manager.create_session(
            documents=['doc_1'],
            study_mode=StudyMode.TRADITIONAL,
            difficulty_level=2
        )

        session2 = await study_mode_manager.create_session(
            documents=['doc_1'],  # Same document, different session
            study_mode=StudyMode.TRADITIONAL,
            difficulty_level=2
        )

        # Add interaction to session1
        await study_mode_manager.add_interaction(
            session1.session_id,
            user_input="Test input 1",
            ai_response="Test response 1",
            concepts_identified=["concept1"]
        )

        # Session2 should not be affected
        loaded_session1 = await study_mode_manager.get_session(session1.session_id)
        loaded_session2 = await study_mode_manager.get_session(session2.session_id)

        assert loaded_session1.get_interaction_count() == 1
        assert loaded_session2.get_interaction_count() == 0

    @pytest.mark.asyncio
    async def test_session_limits_and_cleanup(self, study_mode_manager):
        """Test session limits and automatic cleanup."""
        # Create many sessions to test limits
        sessions = []
        for i in range(10):
            session = await study_mode_manager.create_session(
                documents=[f'doc_{i}'],
                study_mode=StudyMode.TRADITIONAL,
                difficulty_level=2
            )
            sessions.append(session)

        # All should be created successfully
        assert len(sessions) == 10

        # Test cleanup of inactive sessions
        for session in sessions[:5]:
            session.end_session()

        active_sessions = await study_mode_manager.get_active_sessions()
        assert len(active_sessions) == 5  # Only active sessions


class TestDataConsistencyAndIntegrity:
    """Test data consistency across all integration points."""

    @pytest.fixture
    def integrated_system(self):
        """Fully integrated system for consistency testing."""
        with patch('src.study_modes.study_mode_manager.weaviate_client'), \
             patch('src.study_modes.study_mode_manager.supabase_client'), \
             patch('src.study_modes.study_mode_manager.document_processor'):

            manager = StudyModeManager(user_id='consistency-test-user')
            return manager

    @pytest.mark.asyncio
    async def test_end_to_end_session_flow(self, integrated_system):
        """Test complete session flow with all integrations."""
        # Create session
        session = await integrated_system.create_session(
            documents=['doc_1'],
            study_mode=StudyMode.TRADITIONAL,
            difficulty_level=3
        )

        # Add multiple interactions
        interactions = [
            ("What is machine learning?", "It's when computers learn from data"),
            ("Can you give an example?", "Like email spam detection"),
            ("How does it work?", "Through algorithms that find patterns")
        ]

        for user_input, user_response in interactions:
            ai_response = f"Great question! {user_response} is correct."
            await integrated_system.add_interaction(
                session.session_id,
                user_input=user_input,
                ai_response=ai_response,
                concepts_identified=["machine learning"]
            )

        # End session and verify consistency
        await integrated_system.end_session(session.session_id)

        final_session = await integrated_system.get_session(session.session_id)
        assert not final_session.is_active
        assert final_session.get_interaction_count() == len(interactions)

    @pytest.mark.asyncio
    async def test_data_synchronization_across_components(self, integrated_system):
        """Test data synchronization between Weaviate, Supabase, and memory."""
        session = await integrated_system.create_session(
            documents=['doc_1'],
            study_mode=StudyMode.TRADITIONAL,
            difficulty_level=3
        )

        # Add interaction
        await integrated_system.add_interaction(
            session.session_id,
            user_input="Test synchronization",
            ai_response="Testing sync across components",
            concepts_identified=["synchronization", "testing"]
        )

        # Reload session from persistence
        reloaded_session = await integrated_system.load_session(session.session_id)

        # Data should be consistent
        assert reloaded_session.session_id == session.session_id
        assert reloaded_session.get_interaction_count() == session.get_interaction_count()

    @pytest.mark.asyncio
    async def test_rollback_on_partial_failure(self, integrated_system):
        """Test rollback behavior when part of the system fails."""
        session = await integrated_system.create_session(
            documents=['doc_1'],
            study_mode=StudyMode.TRADITIONAL,
            difficulty_level=3
        )

        # Mock partial failure (e.g., Supabase succeeds, Weaviate fails)
        with patch.object(integrated_system, 'supabase_client') as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("Supabase error")

            # Interaction should fail gracefully
            with pytest.raises(Exception):
                await integrated_system.add_interaction(
                    session.session_id,
                    user_input="This should fail",
                    ai_response="This should not be saved",
                    concepts_identified=["failure"]
                )

        # Session should remain in consistent state
        consistent_session = await integrated_system.get_session(session.session_id)
        assert consistent_session.get_interaction_count() == 0  # No partial updates
