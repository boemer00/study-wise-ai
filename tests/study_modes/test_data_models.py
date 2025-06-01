"""
Tests for StudySession data models including edge cases and validation.
"""

import pytest
from datetime import datetime, timedelta
import json
from unittest.mock import patch
from src.study_modes.models.study_session import (
    StudyPrompt, SessionResponse, PromptType, StudyMode,
    StudySession, SessionStage
)


class TestStudyPrompt:
    """Test cases for StudyPrompt model."""

    def test_valid_prompt_creation(self):
        """Test creating a valid StudyPrompt."""
        prompt = StudyPrompt(
            prompt_text="Welcome to your study session!",
            prompt_type=PromptType.QUESTION,
            difficulty_level=3,
            expected_concepts=["concept1", "concept2"],
            context={"voice_compatible": True}
        )

        assert prompt.prompt_text == "Welcome to your study session!"
        assert prompt.prompt_type == PromptType.QUESTION
        assert prompt.difficulty_level == 3
        assert prompt.expected_concepts == ["concept1", "concept2"]
        assert prompt.context["voice_compatible"] is True
        assert prompt.prompt_id is not None

    def test_prompt_validation_difficulty_level(self):
        """Test difficulty level validation."""
        # Valid difficulty levels
        for level in [1, 2, 3, 4, 5]:
            prompt = StudyPrompt(
                prompt_text="Test prompt",
                difficulty_level=level
            )
            assert prompt.difficulty_level == level

        # Test default difficulty
        prompt = StudyPrompt(prompt_text="Test prompt")
        assert prompt.difficulty_level == 1

    def test_prompt_serialization_structure(self):
        """Test StudyPrompt data structure for serialization."""
        prompt = StudyPrompt(
            prompt_text="What do you think about this concept?",
            prompt_type=PromptType.EXPLANATION_REQUEST,
            difficulty_level=4,
            expected_concepts=["machine learning", "algorithms"],
            context={"requires_critical_thinking": True}
        )

        # Verify all required fields are present
        assert hasattr(prompt, 'prompt_id')
        assert hasattr(prompt, 'prompt_text')
        assert hasattr(prompt, 'prompt_type')
        assert hasattr(prompt, 'difficulty_level')
        assert hasattr(prompt, 'expected_concepts')
        assert hasattr(prompt, 'context')
        assert hasattr(prompt, 'created_at')

        # Verify data types
        assert isinstance(prompt.prompt_id, str)
        assert isinstance(prompt.prompt_text, str)
        assert isinstance(prompt.prompt_type, PromptType)
        assert isinstance(prompt.difficulty_level, int)
        assert isinstance(prompt.expected_concepts, list)
        assert isinstance(prompt.context, dict)
        assert isinstance(prompt.created_at, datetime)


class TestSessionResponse:
    """Test cases for SessionResponse model."""

    def test_valid_response_creation(self):
        """Test creating a valid SessionResponse."""
        response = SessionResponse(
            ai_message="Great insight! Let me expand on that...",
            feedback="Your understanding shows good grasp of concepts",
            suggestions=["Try exploring deeper examples", "Consider edge cases"],
            progress_percentage=65.5,
            metadata={"response_time_ms": 1500}
        )

        assert response.ai_message == "Great insight! Let me expand on that..."
        assert response.feedback == "Your understanding shows good grasp of concepts"
        assert response.suggestions == ["Try exploring deeper examples", "Consider edge cases"]
        assert response.progress_percentage == 65.5
        assert response.metadata["response_time_ms"] == 1500
        assert response.response_id is not None

    def test_response_progress_validation(self):
        """Test progress percentage validation."""
        # Valid progress values
        for progress in [0.0, 25.5, 50.0, 75.25, 100.0]:
            response = SessionResponse(
                ai_message="Test response",
                progress_percentage=progress
            )
            assert response.progress_percentage == progress

    def test_response_with_next_prompt(self):
        """Test SessionResponse with embedded next prompt."""
        next_prompt = StudyPrompt(
            prompt_text="Based on that, can you explain...",
            prompt_type=PromptType.CLARIFICATION,
            difficulty_level=2
        )

        response = SessionResponse(
            ai_message="Good answer! Now let's dig deeper.",
            next_prompt=next_prompt,
            session_stage=SessionStage.ACTIVE,
            progress_percentage=30.0
        )

        assert response.next_prompt == next_prompt
        assert response.session_stage == SessionStage.ACTIVE
        assert response.next_prompt.prompt_type == PromptType.CLARIFICATION

    def test_response_metadata_support(self):
        """Test extensive metadata support for responses."""
        metadata = {
            "tts_duration_seconds": 5.2,
            "speech_clarity_score": 0.9,
            "voice_settings": {"speed": 1.0, "pitch": 0.0},
            "user_engagement_indicators": ["active_listening", "follow_up_questions"],
            "difficulty_adjustment_needed": False
        }

        response = SessionResponse(
            ai_message="Complex response with metadata",
            metadata=metadata
        )

        assert response.metadata == metadata
        assert response.metadata["tts_duration_seconds"] == 5.2
        assert "voice_settings" in response.metadata


class TestStudySession:
    """Test cases for StudySession model."""

    def test_session_creation_and_initialization(self):
        """Test StudySession creation with proper initialization."""
        session = StudySession(
            user_id="user-456",
            study_mode=StudyMode.TRADITIONAL,
            document_ids=["doc1", "doc2"],
            difficulty_level=3,
            session_goals=["Understand concepts", "Apply knowledge"]
        )

        assert session.user_id == "user-456"
        assert session.study_mode == StudyMode.TRADITIONAL
        assert session.document_ids == ["doc1", "doc2"]
        assert session.difficulty_level == 3
        assert session.session_goals == ["Understand concepts", "Apply knowledge"]
        assert len(session.conversation_history) == 0
        assert session.session_stage == SessionStage.INITIALIZING
        assert session.is_active() == False  # Initializing is not active

    def test_session_interaction_management(self):
        """Test adding and managing interactions."""
        session = StudySession(
            user_id="user-test",
            study_mode=StudyMode.FEYNMAN,
            difficulty_level=2
        )

        # Create a prompt and response
        prompt = StudyPrompt(
            prompt_text="What is machine learning?",
            prompt_type=PromptType.QUESTION,
            expected_concepts=["machine learning", "data"]
        )

        response = SessionResponse(
            ai_message="That's a good start! Let me expand...",
            feedback="Shows basic understanding",
            progress_percentage=20.0
        )

        # Add interaction
        session.add_interaction(prompt, "It's when computers learn from data", response)

        assert len(session.conversation_history) == 1
        assert session.get_interaction_count() == 1

        interaction = session.conversation_history[0]
        assert interaction["user_response"] == "It's when computers learn from data"
        assert interaction["prompt"]["prompt_text"] == "What is machine learning?"
        assert interaction["ai_response"]["ai_message"] == "That's a good start! Let me expand..."

    def test_session_progress_tracking(self):
        """Test session progress calculation and tracking."""
        session = StudySession(
            user_id="user-progress",
            study_mode=StudyMode.SOCRATIC,
            difficulty_level=3
        )

        # Update progress multiple times
        session.update_progress(25.0)
        assert session.progress_percentage == 25.0

        session.update_progress(50.5)
        assert session.progress_percentage == 50.5

        session.update_progress(100.0)
        assert session.progress_percentage == 100.0

        # Check progress tracking in metadata
        assert "progress_updates" in session.session_metadata
        assert len(session.session_metadata["progress_updates"]) == 3

        # Test boundary validation
        session.update_progress(150.0)  # Over 100
        assert session.progress_percentage == 100.0

        session.update_progress(-10.0)  # Under 0
        assert session.progress_percentage == 0.0

    def test_session_concept_tracking(self):
        """Test concept tracking across interactions."""
        session = StudySession(
            user_id="user-concepts",
            study_mode=StudyMode.DEBATE,
            difficulty_level=4
        )

        # Add interactions with different concepts
        prompts_and_concepts = [
            ("What is machine learning?", ["machine learning", "algorithms"]),
            ("How do neural networks work?", ["neural networks", "algorithms"]),
            ("Explain deep learning", ["deep learning", "neural networks"])
        ]

        for prompt_text, concepts in prompts_and_concepts:
            prompt = StudyPrompt(
                prompt_text=prompt_text,
                expected_concepts=concepts
            )
            response = SessionResponse(ai_message="Good question!")
            session.add_interaction(prompt, f"Response to {prompt_text}", response)

        unique_concepts = session.get_covered_concepts()
        assert len(unique_concepts) == 4  # No duplicates
        assert "machine learning" in unique_concepts
        assert "algorithms" in unique_concepts
        assert "neural networks" in unique_concepts
        assert "deep learning" in unique_concepts

    def test_session_duration_calculation(self):
        """Test session duration calculation."""
        session = StudySession(
            user_id="user-duration",
            study_mode=StudyMode.TRADITIONAL,
            difficulty_level=2
        )

        # Test active session duration
        duration = session.calculate_duration()
        assert duration >= 0  # Should be positive or zero

        # Test completed session duration
        session.end_time = session.start_time + timedelta(minutes=30)
        duration = session.calculate_duration()
        assert duration == 1800  # 30 minutes = 1800 seconds

    def test_session_serialization_complete(self):
        """Test complete session serialization."""
        session = StudySession(
            user_id="user-serialize",
            study_mode=StudyMode.FEYNMAN,
            document_ids=["doc1", "doc2"],
            difficulty_level=5,
            session_goals=["Master concepts"]
        )

        # Add an interaction
        prompt = StudyPrompt(
            prompt_text="Explain this concept",
            expected_concepts=["explanation", "understanding"]
        )
        response = SessionResponse(
            ai_message="Good attempt! Let me add...",
            progress_percentage=40.0
        )
        session.add_interaction(prompt, "Here's my explanation...", response)

        # Set session to completed
        session.session_stage = SessionStage.COMPLETED
        session.end_time = session.start_time + timedelta(minutes=25)

        data = session.to_dict()

        assert data["user_id"] == "user-serialize"
        assert data["study_mode"] == "feynman"
        assert data["document_ids"] == ["doc1", "doc2"]
        assert data["difficulty_level"] == 5
        assert data["session_stage"] == "completed"
        assert len(data["conversation_history"]) == 1
        assert data["end_time"] is not None
        assert data["total_duration_seconds"] == 1500  # 25 minutes

    def test_session_deserialization(self):
        """Test session deserialization from stored data."""
        data = {
            "session_id": "sess-deserialize",
            "user_id": "user-deserialize",
            "study_mode": "socratic",
            "document_ids": ["doc1"],
            "session_goals": ["Learn effectively"],
            "conversation_history": [
                {
                    "timestamp": "2024-01-15T10:30:00+00:00",
                    "prompt": {
                        "prompt_id": "prompt-123",
                        "prompt_text": "Test prompt",
                        "prompt_type": "question",
                        "difficulty_level": 3,
                        "expected_concepts": ["test concept"]
                    },
                    "user_response": "Test response",
                    "ai_response": {
                        "response_id": "resp-123",
                        "ai_message": "Test AI response",
                        "feedback": "Good work",
                        "suggestions": ["Keep it up"],
                        "progress_percentage": 60.0
                    }
                }
            ],
            "session_stage": "active",
            "difficulty_level": 3,
            "start_time": "2024-01-15T10:00:00+00:00",
            "end_time": None,
            "progress_percentage": 60.0,
            "session_metadata": {"test_key": "test_value"}
        }

        session = StudySession.from_dict(data)

        assert session.session_id == "sess-deserialize"
        assert session.user_id == "user-deserialize"
        assert session.study_mode == StudyMode.SOCRATIC
        assert session.difficulty_level == 3
        assert len(session.conversation_history) == 1
        assert session.session_stage == SessionStage.ACTIVE
        assert session.progress_percentage == 60.0

    def test_session_state_management(self):
        """Test session state transitions."""
        session = StudySession(
            user_id="user-state",
            study_mode=StudyMode.TRADITIONAL
        )

        # Test initial state
        assert session.session_stage == SessionStage.INITIALIZING
        assert not session.is_active()

        # Test active state
        session.session_stage = SessionStage.ACTIVE
        assert session.is_active()

        # Test transitioning state
        session.session_stage = SessionStage.TRANSITIONING
        assert session.is_active()

        # Test completed state
        session.session_stage = SessionStage.COMPLETED
        assert not session.is_active()

        # Test paused state
        session.session_stage = SessionStage.PAUSED
        assert not session.is_active()

    def test_session_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test session with no interactions
        session = StudySession(
            user_id="user-empty",
            study_mode=StudyMode.TRADITIONAL,
            document_ids=[],
            difficulty_level=1
        )

        assert session.get_interaction_count() == 0
        assert session.get_covered_concepts() == []
        assert session.get_last_user_response() is None

        # Test session with maximum realistic interactions
        for i in range(50):  # Reasonable number of interactions
            prompt = StudyPrompt(
                prompt_text=f"Question {i}",
                expected_concepts=[f"concept{i}"]
            )
            response = SessionResponse(ai_message=f"Response {i}")
            session.add_interaction(prompt, f"User response {i}", response)

        assert session.get_interaction_count() == 50
        assert len(session.get_covered_concepts()) == 50  # All unique concepts


class TestSessionEnums:
    """Test cases for session-related enums."""

    def test_study_mode_enum(self):
        """Test StudyMode enum values."""
        assert StudyMode.TRADITIONAL.value == "traditional"
        assert StudyMode.FEYNMAN.value == "feynman"
        assert StudyMode.SOCRATIC.value == "socratic"
        assert StudyMode.DEBATE.value == "debate"

        # Test enum comparison
        assert StudyMode.TRADITIONAL != StudyMode.FEYNMAN
        assert StudyMode.SOCRATIC == StudyMode.SOCRATIC

    def test_prompt_type_enum(self):
        """Test PromptType enum values."""
        assert PromptType.QUESTION.value == "question"
        assert PromptType.EXPLANATION_REQUEST.value == "explanation_request"
        assert PromptType.CHALLENGE.value == "challenge"
        assert PromptType.CLARIFICATION.value == "clarification"

    def test_session_stage_enum(self):
        """Test SessionStage enum values."""
        assert SessionStage.INITIALIZING.value == "initializing"
        assert SessionStage.ACTIVE.value == "active"
        assert SessionStage.TRANSITIONING.value == "transitioning"
        assert SessionStage.COMPLETED.value == "completed"
        assert SessionStage.PAUSED.value == "paused"
