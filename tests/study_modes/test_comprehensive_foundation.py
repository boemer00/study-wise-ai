"""
Comprehensive foundation tests for Study Modes implementation.
Tests only the actual implemented functionality to validate the core foundation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.study_modes.modes.traditional_mode import TraditionalMode
from src.study_modes.models.study_session import StudyPrompt, SessionResponse, PromptType, StudyMode, StudySession


class TestFoundationCore:
    """Test core foundation functionality that is actually implemented."""

    @pytest.fixture
    def traditional_mode(self):
        """TraditionalMode instance for testing."""
        return TraditionalMode(
            documents=['neural_collaborative_filtering.pdf'],
            user_id='test-user',
            difficulty_level=3
        )

    def test_mode_initialization(self, traditional_mode):
        """Test proper initialization of study modes."""
        assert traditional_mode.documents == ['neural_collaborative_filtering.pdf']
        assert traditional_mode.user_id == 'test-user'
        assert traditional_mode.difficulty_level == 3
        assert traditional_mode.session_context['interactions_count'] == 0
        assert len(traditional_mode.session_context['concepts_covered']) == 0

    @pytest.mark.asyncio
    async def test_initial_prompt_generation(self, traditional_mode):
        """Test initial prompt generation works correctly."""
        prompt = await traditional_mode.generate_initial_prompt()

        assert isinstance(prompt, StudyPrompt)
        assert prompt.prompt_text is not None
        assert len(prompt.prompt_text) > 50  # Substantial content
        assert prompt.prompt_type == PromptType.QUESTION
        assert prompt.difficulty_level == 3
        assert prompt.related_documents == ['neural_collaborative_filtering.pdf']

    @pytest.mark.asyncio
    async def test_user_response_processing(self, traditional_mode):
        """Test user response processing functionality."""
        # Generate initial prompt first
        initial_prompt = await traditional_mode.generate_initial_prompt()

        # Process a user response
        user_input = "What is machine learning and how does it work?"
        response = await traditional_mode.process_user_response(user_input, initial_prompt)

        assert isinstance(response, SessionResponse)
        assert response.ai_message is not None
        assert len(response.ai_message) > 30  # Substantial response
        assert response.session_stage is not None
        assert 0.0 <= response.progress_percentage <= 100.0

    @pytest.mark.asyncio
    async def test_understanding_evaluation(self, traditional_mode):
        """Test understanding evaluation with actual implementation."""
        responses = [
            "Machine learning is when computers learn from data to make predictions",
            "Neural networks are inspired by how the brain works with connected nodes",
            "I understand that algorithms can find patterns in data automatically"
        ]

        understanding_scores = await traditional_mode.evaluate_understanding(responses)

        assert isinstance(understanding_scores, dict)
        assert len(understanding_scores) > 0
        # All scores should be between 0 and 1
        for concept, score in understanding_scores.items():
            assert 0.0 <= score <= 1.0
            assert isinstance(concept, str)

    def test_document_context_retrieval(self, traditional_mode):
        """Test document context retrieval (synchronous mock version)."""
        # Test that the method exists and returns expected structure
        import asyncio
        context = asyncio.run(traditional_mode.get_document_context(['test_doc']))

        assert isinstance(context, dict)
        assert 'key_concepts' in context
        assert 'document_summaries' in context
        assert 'complexity_level' in context

    def test_response_validation(self, traditional_mode):
        """Test response validation logic."""
        # Valid responses
        assert traditional_mode.validate_user_response("This is a good detailed response about machine learning")
        assert traditional_mode.validate_user_response("What is deep learning?")

        # Invalid responses
        assert not traditional_mode.validate_user_response("")
        assert not traditional_mode.validate_user_response("   ")
        assert not traditional_mode.validate_user_response("yes")  # Too short

    def test_quality_scoring(self, traditional_mode):
        """Test response quality scoring."""
        good_response = "Machine learning is a powerful technique that allows computers to learn patterns from data and make predictions. For example, it can be used in email spam detection."
        expected_concepts = ['machine learning', 'data', 'predictions']

        score = traditional_mode.calculate_response_quality_score(good_response, expected_concepts)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be a reasonably good score

    def test_session_context_management(self, traditional_mode):
        """Test session context updates."""
        # Test concept tracking
        traditional_mode.add_covered_concept('neural_networks')
        traditional_mode.add_covered_concept('machine_learning')

        concepts = traditional_mode.get_covered_concepts()
        assert 'neural_networks' in concepts
        assert 'machine_learning' in concepts
        assert len(concepts) == 2

        # Test interaction counting
        assert traditional_mode.get_interaction_count() == 0
        traditional_mode.increment_interactions()
        assert traditional_mode.get_interaction_count() == 1

    def test_difficulty_adjustment(self, traditional_mode):
        """Test difficulty adjustment logic."""
        import asyncio

        # Add some performance scores
        traditional_mode.session_context['user_performance_scores'] = [0.8, 0.9, 0.85]

        new_level = asyncio.run(traditional_mode.adjust_difficulty(0.9))
        # Should increase difficulty for high performance
        assert new_level >= traditional_mode.difficulty_level

    @pytest.mark.asyncio
    async def test_session_summary_generation(self, traditional_mode):
        """Test session summary generation."""
        # Add some test data
        traditional_mode.add_covered_concept('machine_learning')
        traditional_mode.add_covered_concept('neural_networks')
        traditional_mode.session_context['user_performance_scores'] = [0.7, 0.8, 0.6]

        responses = [
            "I understand machine learning as computers learning from data",
            "Neural networks seem like artificial brain structures",
            "This is getting complex but I think I'm following"
        ]

        summary = await traditional_mode.generate_session_summary(responses)

        assert isinstance(summary, dict)
        assert 'total_interactions' in summary
        assert 'concepts_covered' in summary
        assert 'understanding_scores' in summary
        assert 'recommendations' in summary


class TestDataModelsIntegration:
    """Test integration of data models with core functionality."""

    def test_study_prompt_creation(self):
        """Test StudyPrompt model creation and validation."""
        prompt = StudyPrompt(
            prompt_text="What are your thoughts on neural networks?",
            prompt_type=PromptType.QUESTION,
            difficulty_level=3,
            expected_concepts=['neural networks', 'deep learning'],
            context={'voice_compatible': True}
        )

        assert prompt.prompt_text == "What are your thoughts on neural networks?"
        assert prompt.prompt_type == PromptType.QUESTION
        assert prompt.difficulty_level == 3
        assert 'neural networks' in prompt.expected_concepts
        assert prompt.context['voice_compatible'] is True

    def test_session_response_creation(self):
        """Test SessionResponse model creation."""
        response = SessionResponse(
            ai_message="Great question! Neural networks are computational models...",
            progress_percentage=45.0,
            feedback="Shows good understanding of basic concepts",
            suggestions=["Try exploring deep learning next", "Consider practical applications"]
        )

        assert "Neural networks" in response.ai_message
        assert response.progress_percentage == 45.0
        assert response.feedback is not None
        assert len(response.suggestions) == 2

    def test_study_session_creation(self):
        """Test StudySession model creation and interaction management."""
        session = StudySession(
            user_id="test-user",
            study_mode=StudyMode.TRADITIONAL,
            document_ids=["doc1", "doc2"],
            difficulty_level=3
        )

        # Create and add an interaction
        prompt = StudyPrompt(
            prompt_text="What is machine learning?",
            expected_concepts=["machine learning"]
        )
        response = SessionResponse(
            ai_message="Machine learning is...",
            progress_percentage=20.0
        )

        session.add_interaction(prompt, "User's response here", response)

        assert session.get_interaction_count() == 1
        assert len(session.conversation_history) == 1
        assert session.study_mode == StudyMode.TRADITIONAL


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""

    @pytest.fixture
    def traditional_mode(self):
        return TraditionalMode(['doc1'], 'user-test', 3)

    @pytest.mark.asyncio
    async def test_empty_documents_handling(self):
        """Test handling of empty document list."""
        with pytest.raises(ValueError):
            mode = TraditionalMode([], 'user-test', 3)
            await mode.generate_initial_prompt()

    @pytest.mark.asyncio
    async def test_invalid_user_response(self, traditional_mode):
        """Test handling of invalid user responses."""
        initial_prompt = await traditional_mode.generate_initial_prompt()

        # Test with empty response
        response = await traditional_mode.process_user_response("", initial_prompt)
        assert "more detail" in response.ai_message.lower()

        # Test with very short response
        response = await traditional_mode.process_user_response("yes", initial_prompt)
        assert "more detail" in response.ai_message.lower()

    def test_boundary_conditions(self, traditional_mode):
        """Test boundary conditions."""
        # Test extreme difficulty levels
        traditional_mode.difficulty_level = 1
        score = traditional_mode.calculate_response_quality_score("test response", [])
        assert 0.0 <= score <= 1.0

        traditional_mode.difficulty_level = 5
        score = traditional_mode.calculate_response_quality_score("test response", [])
        assert 0.0 <= score <= 1.0

    def test_context_isolation(self):
        """Test that different mode instances have isolated contexts."""
        mode1 = TraditionalMode(['doc1'], 'user1', 2)
        mode2 = TraditionalMode(['doc2'], 'user2', 4)

        mode1.add_covered_concept('concept1')
        mode2.add_covered_concept('concept2')

        assert 'concept1' in mode1.get_covered_concepts()
        assert 'concept1' not in mode2.get_covered_concepts()
        assert 'concept2' in mode2.get_covered_concepts()
        assert 'concept2' not in mode1.get_covered_concepts()


class TestVoiceCompatibility:
    """Test voice AI compatibility features that are actually implemented."""

    def test_audio_metadata_support(self):
        """Test that models support audio metadata."""
        # Test StudyPrompt with audio context
        prompt = StudyPrompt(
            prompt_text="Welcome to your voice study session!",
            context={
                "voice_compatible": True,
                "speech_rate": "normal",
                "tts_optimized": True
            }
        )

        assert prompt.context["voice_compatible"] is True
        assert prompt.context["speech_rate"] == "normal"

        # Test SessionResponse with audio metadata
        response = SessionResponse(
            ai_message="This response is optimized for text-to-speech",
            metadata={
                "tts_duration_estimate": 4.5,
                "speech_optimized": True,
                "voice_friendly": True
            }
        )

        assert response.metadata["speech_optimized"] is True
        assert response.metadata["tts_duration_estimate"] == 4.5

    def test_prompt_voice_optimization_context(self):
        """Test that prompts can include voice optimization context."""
        prompt = StudyPrompt(
            prompt_text="Let's explore machine learning together.",
            context={
                "voice_compatible": True,
                "conversational_tone": True,
                "pause_points": ["Let's explore", "machine learning", "together"],
                "estimated_speech_time": 3.2
            }
        )

        assert prompt.context["voice_compatible"] is True
        assert prompt.context["conversational_tone"] is True
        assert len(prompt.context["pause_points"]) == 3
