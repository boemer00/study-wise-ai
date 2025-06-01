"""
Tests for voice AI compatibility (TTS/STT) and audio metadata support.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.study_modes.modes.traditional_mode import TraditionalMode
from src.study_modes.models.study_session import StudyPrompt, SessionResponse, PromptType


class TestTTSOptimization:
    """Test Text-to-Speech optimization features."""

    @pytest.fixture
    def traditional_mode(self):
        """TraditionalMode instance for testing TTS features."""
        return TraditionalMode(
            documents=['doc_1'],
            user_id='test-user',
            difficulty_level=3
        )

    @pytest.mark.asyncio
    async def test_tts_optimized_prompt_generation(self, traditional_mode):
        """Test that prompts are optimized for TTS delivery."""
        prompt = await traditional_mode.generate_initial_prompt(tts_optimized=True)

        # TTS-optimized prompts should have specific characteristics
        assert len(prompt.content) >= 50  # Sufficient content for natural speech
        assert len(prompt.content) <= 300  # Not too long for comfortable listening

        # Should avoid complex punctuation that doesn't translate well to speech
        complex_punctuation = ['...', '---', '***', '```']
        content_clean = any(punct in prompt.content for punct in complex_punctuation)
        assert not content_clean or len([p for p in complex_punctuation if p in prompt.content]) <= 1

        # Should use conversational language
        conversational_indicators = ['let\'s', 'we\'ll', 'you\'ll', 'we can', 'you might']
        has_conversational = any(indicator in prompt.content.lower() for indicator in conversational_indicators)
        assert has_conversational

    @pytest.mark.asyncio
    async def test_response_tts_formatting(self, traditional_mode):
        """Test that AI responses are formatted for TTS."""
        user_input = "What is machine learning?"

        response = await traditional_mode.process_user_response(
            user_input,
            tts_optimized=True
        )

        # TTS responses should be formatted appropriately
        assert response.ai_response is not None
        assert len(response.ai_response) >= 30  # Substantial response

        # Should avoid markdown formatting
        markdown_chars = ['#', '*', '`', '|', '[', ']']
        has_markdown = any(char in response.ai_response for char in markdown_chars)
        assert not has_markdown

        # Should use natural speech patterns
        assert '.' in response.ai_response  # Proper sentence structure
        assert response.ai_response.count('.') <= 5  # Not too many sentences for one response

    def test_audio_metadata_attachment(self, traditional_mode):
        """Test attachment of audio metadata to prompts and responses."""
        # Create prompt with audio metadata
        prompt = StudyPrompt(
            session_id="sess-123",
            prompt_type=PromptType.INITIAL,
            content="Welcome to your voice-enabled study session!",
            expected_concepts=["voice learning", "audio interaction"],
            difficulty_level=3,
            metadata={
                "voice_compatible": True,
                "speech_rate": "normal",
                "voice_gender": "neutral",
                "language": "en-US"
            },
            audio_file_path="/audio/prompts/prompt_123.mp3"
        )

        assert prompt.metadata["voice_compatible"] is True
        assert prompt.metadata["speech_rate"] == "normal"
        assert prompt.audio_file_path == "/audio/prompts/prompt_123.mp3"

        # Create response with audio metadata
        response = SessionResponse(
            session_id="sess-123",
            user_input="Tell me about neural networks",
            ai_response="Neural networks are computational models inspired by the brain.",
            concepts_identified=["neural networks", "computational models"],
            quality_score=0.8,
            metadata={
                "tts_duration_seconds": 5.2,
                "speech_clarity_score": 0.9,
                "voice_settings": {"speed": 1.0, "pitch": 0.0}
            },
            user_audio_path="/audio/user/user_input_123.wav",
            ai_audio_path="/audio/ai/ai_response_123.mp3"
        )

        assert response.metadata["tts_duration_seconds"] == 5.2
        assert response.user_audio_path == "/audio/user/user_input_123.wav"
        assert response.ai_audio_path == "/audio/ai/ai_response_123.mp3"

    @pytest.mark.asyncio
    async def test_voice_interaction_flow(self, traditional_mode):
        """Test complete voice interaction flow."""
        # Simulate voice-enabled session
        session_metadata = {
            "voice_enabled": True,
            "preferred_voice": "neural_voice_1",
            "speech_rate": 1.1,
            "audio_format": "mp3"
        }

        # Generate TTS-optimized initial prompt
        prompt = await traditional_mode.generate_initial_prompt(
            tts_optimized=True,
            voice_metadata=session_metadata
        )

        assert prompt.metadata.get("voice_compatible") is True

        # Process user response (simulating STT input)
        stt_input = "I would like to learn about machine learning algorithms"
        response = await traditional_mode.process_user_response(
            stt_input,
            tts_optimized=True,
            input_method="voice"
        )

        # Verify response is voice-optimized
        assert response.metadata.get("input_method") == "voice"
        assert len(response.ai_response.split('.')) <= 4  # Short sentences for TTS


class TestSTTInputHandling:
    """Test Speech-to-Text input handling and processing."""

    @pytest.fixture
    def traditional_mode(self):
        """TraditionalMode instance for testing STT features."""
        return TraditionalMode(
            documents=['doc_1'],
            user_id='test-user',
            difficulty_level=3
        )

    def test_stt_input_normalization(self, traditional_mode):
        """Test normalization of STT input text."""
        # STT often produces imperfect transcriptions
        stt_inputs = [
            "umm what is machine learning exactly",  # Filler words
            "What is machine learning?",  # Clean input
            "what is machine learning",  # No punctuation
            "What is machine learning question mark",  # Spoken punctuation
            "WHAT IS MACHINE LEARNING",  # All caps
            "what   is    machine    learning",  # Extra spaces
        ]

        for input_text in stt_inputs:
            normalized = traditional_mode.normalize_stt_input(input_text)

            # Should be properly capitalized
            assert normalized[0].isupper()

            # Should have proper punctuation
            assert normalized.endswith('.') or normalized.endswith('?')

            # Should remove filler words
            filler_words = ['umm', 'uh', 'like', 'you know']
            for filler in filler_words:
                assert filler not in normalized.lower()

            # Should normalize spacing
            assert '  ' not in normalized  # No double spaces

    def test_stt_confidence_handling(self, traditional_mode):
        """Test handling of STT confidence scores."""
        test_cases = [
            {"text": "What is machine learning?", "confidence": 0.95, "should_process": True},
            {"text": "What is machine learning?", "confidence": 0.75, "should_process": True},
            {"text": "What is machine learning?", "confidence": 0.45, "should_process": False},
            {"text": "Whats is mashine larning?", "confidence": 0.60, "should_process": False},  # Low confidence + errors
        ]

        for case in test_cases:
            should_process = traditional_mode.should_process_stt_input(
                case["text"],
                case["confidence"]
            )
            assert should_process == case["should_process"]

    def test_stt_error_correction(self, traditional_mode):
        """Test automatic correction of common STT errors."""
        error_corrections = [
            ("machine larning", "machine learning"),
            ("neural netwerk", "neural network"),
            ("deep larning", "deep learning"),
            ("artificial inteligence", "artificial intelligence"),
            ("algoritm", "algorithm"),
        ]

        for incorrect, correct in error_corrections:
            corrected = traditional_mode.correct_stt_errors(f"What is {incorrect}?")
            assert correct in corrected.lower()

    @pytest.mark.asyncio
    async def test_stt_context_understanding(self, traditional_mode):
        """Test understanding of voice input context and intent."""
        voice_inputs = [
            {
                "text": "Can you explain neural networks to me",
                "expected_intent": "explanation_request",
                "expected_concepts": ["neural networks"]
            },
            {
                "text": "I don't understand the previous concept",
                "expected_intent": "clarification_request",
                "expected_concepts": []
            },
            {
                "text": "Give me an example of machine learning",
                "expected_intent": "example_request",
                "expected_concepts": ["machine learning"]
            },
            {
                "text": "That makes sense now thanks",
                "expected_intent": "acknowledgment",
                "expected_concepts": []
            }
        ]

        for case in voice_inputs:
            analysis = await traditional_mode.analyze_voice_input_intent(case["text"])

            assert analysis["intent"] == case["expected_intent"]
            assert len(analysis["concepts"]) >= len(case["expected_concepts"])

    def test_spoken_punctuation_handling(self, traditional_mode):
        """Test handling of spoken punctuation marks."""
        spoken_punctuation_cases = [
            ("What is machine learning question mark", "What is machine learning?"),
            ("Neural networks comma like CNNs comma are powerful", "Neural networks, like CNNs, are powerful."),
            ("Deep learning period It uses neural networks", "Deep learning. It uses neural networks."),
            ("Machine learning exclamation mark It's amazing", "Machine learning! It's amazing."),
        ]

        for spoken, expected in spoken_punctuation_cases:
            converted = traditional_mode.convert_spoken_punctuation(spoken)
            assert converted == expected


class TestAudioMetadataSupport:
    """Test comprehensive audio metadata support throughout the system."""

    @pytest.fixture
    def traditional_mode(self):
        """TraditionalMode instance for testing audio metadata."""
        return TraditionalMode(
            documents=['doc_1'],
            user_id='test-user',
            difficulty_level=3
        )

    def test_audio_file_path_management(self, traditional_mode):
        """Test audio file path generation and management."""
        session_id = "sess-123"
        interaction_id = "int-456"

        # Test prompt audio path generation
        prompt_path = traditional_mode.generate_audio_file_path(
            session_id=session_id,
            interaction_id=interaction_id,
            audio_type="prompt",
            format="mp3"
        )

        assert session_id in prompt_path
        assert interaction_id in prompt_path
        assert prompt_path.endswith(".mp3")
        assert "prompt" in prompt_path

        # Test user audio path generation
        user_path = traditional_mode.generate_audio_file_path(
            session_id=session_id,
            interaction_id=interaction_id,
            audio_type="user_input",
            format="wav"
        )

        assert session_id in user_path
        assert interaction_id in user_path
        assert user_path.endswith(".wav")
        assert "user" in user_path

    def test_audio_metadata_serialization(self, traditional_mode):
        """Test serialization of audio metadata."""
        audio_metadata = {
            "duration_seconds": 4.5,
            "sample_rate": 22050,
            "channels": 1,
            "format": "mp3",
            "bit_rate": 128,
            "voice_settings": {
                "speed": 1.0,
                "pitch": 0.0,
                "voice_id": "neural_voice_1"
            },
            "generated_at": "2024-01-15T10:30:00Z",
            "file_size_bytes": 72000
        }

        # Create response with audio metadata
        response = SessionResponse(
            session_id="sess-123",
            user_input="Test audio input",
            ai_response="Test audio response",
            concepts_identified=["audio", "testing"],
            quality_score=0.8,
            metadata={"audio_metadata": audio_metadata},
            ai_audio_path="/audio/ai_response_123.mp3"
        )

        # Serialize and verify
        serialized = response.to_dict()
        assert "audio_metadata" in serialized["metadata"]
        assert serialized["metadata"]["audio_metadata"]["duration_seconds"] == 4.5
        assert serialized["ai_audio_path"] == "/audio/ai_response_123.mp3"

    @pytest.mark.asyncio
    async def test_audio_quality_assessment(self, traditional_mode):
        """Test audio quality assessment and optimization."""
        audio_samples = [
            {
                "metadata": {
                    "clarity_score": 0.95,
                    "noise_level": 0.05,
                    "speech_rate": 1.0,
                    "volume_consistency": 0.9
                },
                "expected_quality": "high"
            },
            {
                "metadata": {
                    "clarity_score": 0.75,
                    "noise_level": 0.20,
                    "speech_rate": 1.5,
                    "volume_consistency": 0.7
                },
                "expected_quality": "medium"
            },
            {
                "metadata": {
                    "clarity_score": 0.45,
                    "noise_level": 0.40,
                    "speech_rate": 2.0,
                    "volume_consistency": 0.5
                },
                "expected_quality": "low"
            }
        ]

        for sample in audio_samples:
            quality_assessment = await traditional_mode.assess_audio_quality(
                sample["metadata"]
            )

            assert quality_assessment["overall_quality"] == sample["expected_quality"]
            assert 0.0 <= quality_assessment["quality_score"] <= 1.0

    def test_voice_preference_management(self, traditional_mode):
        """Test management of user voice preferences."""
        voice_preferences = {
            "preferred_voice_id": "neural_voice_female_1",
            "speech_rate": 1.1,
            "pitch_adjustment": 0.0,
            "volume": 0.8,
            "language": "en-US",
            "accent": "neutral",
            "pause_duration": 0.5,
            "emphasis_style": "moderate"
        }

        # Set voice preferences
        traditional_mode.set_voice_preferences(voice_preferences)
        stored_prefs = traditional_mode.get_voice_preferences()

        assert stored_prefs["preferred_voice_id"] == "neural_voice_female_1"
        assert stored_prefs["speech_rate"] == 1.1
        assert stored_prefs["language"] == "en-US"

    @pytest.mark.asyncio
    async def test_adaptive_speech_rate(self, traditional_mode):
        """Test adaptive speech rate based on content complexity."""
        content_samples = [
            {
                "content": "Hello! Welcome to your study session.",
                "difficulty": 1,
                "expected_rate_range": (1.0, 1.2)  # Normal to slightly fast
            },
            {
                "content": "Neural networks utilize backpropagation algorithms to optimize weight parameters through gradient descent optimization.",
                "difficulty": 4,
                "expected_rate_range": (0.8, 1.0)  # Slower for complex content
            },
            {
                "content": "Machine learning is a subset of artificial intelligence that enables computers to learn from data.",
                "difficulty": 2,
                "expected_rate_range": (0.9, 1.1)  # Normal pace
            }
        ]

        for sample in content_samples:
            recommended_rate = await traditional_mode.calculate_adaptive_speech_rate(
                content=sample["content"],
                difficulty_level=sample["difficulty"],
                user_comprehension_score=0.7
            )

            min_rate, max_rate = sample["expected_rate_range"]
            assert min_rate <= recommended_rate <= max_rate


class TestVoiceSessionManagement:
    """Test voice-specific session management features."""

    @pytest.fixture
    def traditional_mode(self):
        """TraditionalMode instance for voice session testing."""
        return TraditionalMode(
            documents=['doc_1'],
            user_id='test-user',
            difficulty_level=3
        )

    @pytest.mark.asyncio
    async def test_voice_session_initialization(self, traditional_mode):
        """Test initialization of voice-enabled study sessions."""
        voice_session_config = {
            "voice_enabled": True,
            "auto_play_responses": True,
            "stt_enabled": True,
            "preferred_voice": "neural_voice_1",
            "background_music": False,
            "noise_reduction": True
        }

        session = await traditional_mode.initialize_voice_session(voice_session_config)

        assert session["voice_enabled"] is True
        assert session["stt_enabled"] is True
        assert "audio_session_id" in session
        assert "voice_settings" in session

    def test_voice_interaction_timing(self, traditional_mode):
        """Test timing management for voice interactions."""
        # Test response timing calculation
        user_input_length = 45  # characters
        expected_speaking_time = traditional_mode.calculate_speaking_time(user_input_length)

        # Average speaking rate is ~150 words per minute
        # Rough estimate: 5 characters per word, so ~30 words per minute per character
        assert 2.0 <= expected_speaking_time <= 8.0  # Reasonable range

        # Test pause management
        pause_duration = traditional_mode.calculate_optimal_pause(
            previous_response_length=200,
            user_comprehension_score=0.7,
            content_complexity=3
        )

        assert 0.5 <= pause_duration <= 3.0  # Reasonable pause range

    @pytest.mark.asyncio
    async def test_voice_error_handling(self, traditional_mode):
        """Test error handling in voice interactions."""
        error_scenarios = [
            {
                "error_type": "stt_low_confidence",
                "data": {"confidence": 0.3, "text": "unclear audio"},
                "expected_action": "request_repeat"
            },
            {
                "error_type": "tts_generation_failed",
                "data": {"text": "Response text", "error": "TTS service unavailable"},
                "expected_action": "fallback_to_text"
            },
            {
                "error_type": "audio_playback_failed",
                "data": {"audio_path": "/audio/response.mp3", "error": "File not found"},
                "expected_action": "regenerate_audio"
            }
        ]

        for scenario in error_scenarios:
            recovery_action = await traditional_mode.handle_voice_error(
                scenario["error_type"],
                scenario["data"]
            )

            assert recovery_action["action"] == scenario["expected_action"]
            assert "user_message" in recovery_action
            assert "retry_available" in recovery_action

    def test_audio_accessibility_features(self, traditional_mode):
        """Test audio accessibility features."""
        accessibility_settings = {
            "hearing_impaired_mode": True,
            "visual_feedback_enabled": True,
            "speech_to_text_display": True,
            "slow_speech_mode": True,
            "high_contrast_audio_cues": True
        }

        # Apply accessibility settings
        traditional_mode.configure_accessibility(accessibility_settings)

        # Test that settings are properly applied
        config = traditional_mode.get_accessibility_config()
        assert config["hearing_impaired_mode"] is True
        assert config["slow_speech_mode"] is True

        # Test slow speech rate for accessibility
        accessible_rate = traditional_mode.get_accessible_speech_rate()
        assert 0.6 <= accessible_rate <= 0.9  # Slower than normal rate

    @pytest.mark.asyncio
    async def test_multilingual_voice_support(self, traditional_mode):
        """Test multilingual voice support capabilities."""
        languages = [
            {"code": "en-US", "voice_id": "neural_voice_en_us_1"},
            {"code": "es-ES", "voice_id": "neural_voice_es_es_1"},
            {"code": "fr-FR", "voice_id": "neural_voice_fr_fr_1"},
            {"code": "de-DE", "voice_id": "neural_voice_de_de_1"},
        ]

        for lang in languages:
            # Test language-specific voice configuration
            voice_config = await traditional_mode.configure_language_voice(
                language_code=lang["code"],
                voice_id=lang["voice_id"]
            )

            assert voice_config["language"] == lang["code"]
            assert voice_config["voice_id"] == lang["voice_id"]
            assert "pronunciation_rules" in voice_config
            assert "accent_settings" in voice_config

    def test_voice_analytics_and_insights(self, traditional_mode):
        """Test voice interaction analytics and insights."""
        voice_session_data = {
            "total_interactions": 15,
            "voice_interactions": 12,
            "text_interactions": 3,
            "average_response_time": 3.5,
            "stt_accuracy_rate": 0.92,
            "user_speaking_pace": 1.2,
            "comprehension_indicators": {
                "requests_for_repetition": 2,
                "clarification_requests": 1,
                "positive_feedback": 8
            }
        }

        insights = traditional_mode.generate_voice_analytics(voice_session_data)

        assert "voice_engagement_score" in insights
        assert "stt_performance" in insights
        assert "recommended_adjustments" in insights
        assert insights["voice_engagement_score"] >= 0.0

        # High voice usage should result in high engagement score
        expected_engagement = voice_session_data["voice_interactions"] / voice_session_data["total_interactions"]
        assert insights["voice_engagement_score"] >= expected_engagement * 0.8
