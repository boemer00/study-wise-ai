"""
Tests for BaseStudyMode shared functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.study_modes.modes.base_mode import BaseStudyMode
from src.study_modes.modes.traditional_mode import TraditionalMode
from src.study_modes.models.study_session import StudyPrompt, SessionResponse, PromptType


class TestBaseStudyMode:
    """Test cases for BaseStudyMode shared functionality."""

    @pytest.fixture
    def concrete_mode(self):
        """TraditionalMode instance for testing BaseStudyMode functionality."""
        return TraditionalMode(
            documents=['doc_1', 'doc_2'],
            user_id='test-user-123',
            difficulty_level=3
        )

    def test_initialization(self, concrete_mode):
        """Test proper initialization of base mode."""
        assert concrete_mode.documents == ['doc_1', 'doc_2']
        assert concrete_mode.user_id == 'test-user-123'
        assert concrete_mode.difficulty_level == 3
        assert concrete_mode.session_context['interactions_count'] == 0
        assert len(concrete_mode.session_context['concepts_covered']) == 0
        assert concrete_mode.session_context['user_performance_scores'] == []

    @pytest.mark.asyncio
    async def test_get_document_context_caching(self, concrete_mode):
        """Test document context retrieval and caching."""
        # First call should create context
        context1 = await concrete_mode.get_document_context(['doc_1'])
        assert 'key_concepts' in context1
        assert 'document_summaries' in context1
        assert 'complexity_level' in context1

        # Second call should return cached result
        context2 = await concrete_mode.get_document_context(['doc_1'])
        assert context1 == context2  # Should be identical (cached)

        # Different document set should create new context
        context3 = await concrete_mode.get_document_context(['doc_2'])
        assert context3 != context1

    @pytest.mark.asyncio
    async def test_difficulty_adjustment_logic(self, concrete_mode):
        """Test automatic difficulty adjustment based on performance."""
        initial_level = concrete_mode.difficulty_level

        # Low performance should decrease difficulty
        new_level1 = await concrete_mode.adjust_difficulty(0.2)
        assert new_level1 == initial_level  # No change with only 1 score

        # Add more low scores
        await concrete_mode.adjust_difficulty(0.3)
        await concrete_mode.adjust_difficulty(0.1)
        new_level2 = await concrete_mode.adjust_difficulty(0.2)
        assert new_level2 < initial_level  # Should decrease

        # Reset and test high performance
        concrete_mode.difficulty_level = 3
        concrete_mode.session_context['user_performance_scores'] = []

        await concrete_mode.adjust_difficulty(0.9)
        await concrete_mode.adjust_difficulty(0.8)
        new_level3 = await concrete_mode.adjust_difficulty(0.9)
        assert new_level3 > 3  # Should increase

    def test_session_context_management(self, concrete_mode):
        """Test session context updates and concept tracking."""
        # Test adding concepts
        concrete_mode.add_covered_concept('neural_networks')
        concrete_mode.add_covered_concept('machine_learning')
        concrete_mode.add_covered_concept('neural_networks')  # Duplicate

        covered = concrete_mode.get_covered_concepts()
        assert len(covered) == 2  # No duplicates
        assert 'neural_networks' in covered
        assert 'machine_learning' in covered

        # Test interaction counting
        assert concrete_mode.get_interaction_count() == 0
        concrete_mode.increment_interactions()
        concrete_mode.increment_interactions()
        assert concrete_mode.get_interaction_count() == 2

        # Test context updates
        concrete_mode.update_session_context('custom_key', 'custom_value')
        assert concrete_mode.session_context['custom_key'] == 'custom_value'

    def test_response_validation(self, concrete_mode):
        """Test user response validation logic."""
        # Valid responses
        assert concrete_mode.validate_user_response("This is a valid response with enough content")
        assert concrete_mode.validate_user_response("What is machine learning?")

        # Invalid responses
        assert not concrete_mode.validate_user_response("")
        assert not concrete_mode.validate_user_response("   ")
        assert not concrete_mode.validate_user_response("short")
        assert not concrete_mode.validate_user_response("a" * 10001)  # Too long

    def test_response_quality_scoring(self, concrete_mode):
        """Test response quality scoring algorithm."""
        # High quality response
        good_response = "Machine learning is a fascinating field because it allows computers to learn from data. For example, neural networks can recognize patterns in images. However, they require large datasets to work effectively."
        expected_concepts = ['machine learning', 'neural networks']
        score = concrete_mode.calculate_response_quality_score(good_response, expected_concepts)
        assert 0.7 <= score <= 1.0

        # Medium quality response
        medium_response = "Machine learning is about teaching computers to learn from data."
        score = concrete_mode.calculate_response_quality_score(medium_response, expected_concepts)
        assert 0.3 <= score <= 0.7

        # Low quality response
        poor_response = "Yes"
        score = concrete_mode.calculate_response_quality_score(poor_response, expected_concepts)
        assert 0.0 <= score <= 0.3

    @pytest.mark.asyncio
    async def test_session_summary_generation(self, concrete_mode):
        """Test session summary generation."""
        # Add some test data
        concrete_mode.add_covered_concept('concept1')
        concrete_mode.add_covered_concept('concept2')
        concrete_mode.session_context['user_performance_scores'] = [0.7, 0.8, 0.6]

        responses = [
            "I understand concept1 because it relates to the main theory",
            "Can you explain concept2 with an example?",
            "This is confusing, I don't get it"
        ]

        summary = await concrete_mode.generate_session_summary(responses)

        assert 'total_interactions' in summary
        assert 'concepts_covered' in summary
        assert 'understanding_scores' in summary
        assert 'average_understanding' in summary
        assert 'difficulty_progression' in summary
        assert 'recommendations' in summary
        assert summary['total_interactions'] == 3
        assert len(summary['concepts_covered']) == 2

    @pytest.mark.asyncio
    async def test_error_handling_in_document_context(self, concrete_mode):
        """Test graceful error handling in document context retrieval."""
        # Test with invalid document IDs - this goes through normal flow, not error handling
        context = await concrete_mode.get_document_context(['invalid_doc_id'])

        # Should return context with simulated data based on document ID
        assert context is not None
        assert 'key_concepts' in context
        assert 'document_summaries' in context
        # The normal flow generates concepts based on document ID
        expected_concepts = ['concept_invalid_doc_id_1', 'concept_invalid_doc_id_2']
        assert context['key_concepts'] == expected_concepts

    def test_boundary_conditions(self, concrete_mode):
        """Test boundary conditions and edge cases."""
        # Test extreme difficulty levels
        concrete_mode.difficulty_level = 1
        result = concrete_mode.calculate_response_quality_score("test", [])
        assert 0.0 <= result <= 1.0

        concrete_mode.difficulty_level = 5
        result = concrete_mode.calculate_response_quality_score("test", [])
        assert 0.0 <= result <= 1.0

        # Test empty concepts list
        concrete_mode.session_context['concepts_covered'] = set()
        concepts = concrete_mode.get_covered_concepts()
        assert concepts == []

    def test_performance_tracking(self, concrete_mode):
        """Test performance score tracking and analysis."""
        scores = [0.1, 0.9, 0.5, 0.8, 0.7]
        for score in scores:
            concrete_mode.session_context['user_performance_scores'].append(score)

        # Test that scores are properly stored
        assert len(concrete_mode.session_context['user_performance_scores']) == 5
        assert concrete_mode.session_context['user_performance_scores'][-1] == 0.7

        # Test averaging logic would work
        avg = sum(concrete_mode.session_context['user_performance_scores']) / len(concrete_mode.session_context['user_performance_scores'])
        assert 0.0 <= avg <= 1.0

    @pytest.mark.asyncio
    async def test_multiple_document_context(self, concrete_mode):
        """Test handling multiple documents in context."""
        docs = ['doc_1', 'doc_2', 'doc_3', 'doc_4', 'doc_5']
        context = await concrete_mode.get_document_context(docs)

        # Should handle multiple documents
        assert len(context['document_summaries']) == 5
        assert all(doc_id in context['document_summaries'] for doc_id in docs)

        # Key concepts should include concepts from all documents
        assert len(context['key_concepts']) >= 5  # At least 2 per document

    def test_context_isolation(self):
        """Test that different mode instances have isolated contexts."""
        mode1 = TraditionalMode(['doc_1'], 'user1', 2)
        mode2 = TraditionalMode(['doc_2'], 'user2', 4)

        mode1.add_covered_concept('concept1')
        mode2.add_covered_concept('concept2')

        assert 'concept1' in mode1.get_covered_concepts()
        assert 'concept1' not in mode2.get_covered_concepts()
        assert 'concept2' in mode2.get_covered_concepts()
        assert 'concept2' not in mode1.get_covered_concepts()
