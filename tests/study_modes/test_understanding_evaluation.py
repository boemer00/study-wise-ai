"""
Tests for understanding evaluation and concept tracking consistency.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.study_modes.modes.base_mode import BaseStudyMode
from src.study_modes.modes.traditional_mode import TraditionalMode
from src.study_modes.models.analytics import ConceptUnderstanding, LearningInsights


class TestConceptExtraction:
    """Test concept extraction algorithms used across all study modes."""

    @pytest.fixture
    def traditional_mode(self):
        """TraditionalMode instance for testing concept extraction."""
        return TraditionalMode(
            documents=['neural_collaborative_filtering.pdf'],
            user_id='test-user',
            difficulty_level=3
        )

    def test_concept_extraction_from_responses(self, traditional_mode):
        """Test concept extraction from user responses."""
        test_cases = [
            {
                "response": "Machine learning uses algorithms to find patterns in data, especially neural networks which can handle complex relationships.",
                "expected_concepts": ["machine learning", "algorithms", "neural networks", "data patterns"],
                "min_concepts": 3
            },
            {
                "response": "Collaborative filtering is a recommendation technique that uses user behavior to predict preferences. Matrix factorization helps reduce dimensionality.",
                "expected_concepts": ["collaborative filtering", "recommendation", "matrix factorization"],
                "min_concepts": 2
            },
            {
                "response": "Deep learning architectures like CNNs and RNNs have revolutionized computer vision and natural language processing.",
                "expected_concepts": ["deep learning", "CNNs", "RNNs", "computer vision", "natural language processing"],
                "min_concepts": 4
            }
        ]

        for case in test_cases:
            concepts = traditional_mode.extract_concepts_from_response(case["response"])
            assert len(concepts) >= case["min_concepts"]

            # Check if key expected concepts are found
            found_concepts = [c.lower() for c in concepts]
            expected_found = sum(1 for exp in case["expected_concepts"] if exp.lower() in " ".join(found_concepts))
            assert expected_found >= case["min_concepts"] // 2  # At least half should be found

    def test_concept_extraction_edge_cases(self, traditional_mode):
        """Test concept extraction with edge cases."""
        edge_cases = [
            ("", []),  # Empty response
            ("Yes", []),  # Too short
            ("I don't know", []),  # Non-technical
            ("The quick brown fox jumps over the lazy dog", []),  # No technical concepts
            ("AI ML DL CNN RNN", ["AI", "ML", "DL", "CNN", "RNN"])  # Acronyms only
        ]

        for response, expected_behavior in edge_cases:
            concepts = traditional_mode.extract_concepts_from_response(response)
            if expected_behavior == []:
                assert len(concepts) <= 1  # Should extract very few or no concepts
            else:
                assert len(concepts) >= len(expected_behavior) // 2  # Should find some acronyms

    def test_concept_normalization(self, traditional_mode):
        """Test concept normalization and deduplication."""
        response = "Machine Learning and machine learning are the same as ML. Neural networks and neural nets are similar concepts."
        concepts = traditional_mode.extract_concepts_from_response(response)

        # Convert to lowercase for comparison
        normalized_concepts = [c.lower() for c in concepts]

        # Should not have duplicates when normalized
        assert len(normalized_concepts) == len(set(normalized_concepts))

        # Should recognize variations
        assert any("machine learning" in c.lower() or "ml" in c.lower() for c in concepts)
        assert any("neural" in c.lower() for c in concepts)

    @pytest.mark.asyncio
    async def test_concept_understanding_evaluation(self, traditional_mode):
        """Test understanding evaluation based on concept usage."""
        # Test cases with different levels of understanding
        test_interactions = [
            {
                "user_response": "Neural networks are like the human brain, they have layers that process information and learn patterns from data through backpropagation.",
                "expected_understanding_level": "high",
                "concepts": ["neural networks", "backpropagation", "pattern recognition"]
            },
            {
                "user_response": "Machine learning is when computers learn from data to make predictions.",
                "expected_understanding_level": "medium",
                "concepts": ["machine learning", "data", "predictions"]
            },
            {
                "user_response": "I think neural networks are just computer programs that do AI stuff.",
                "expected_understanding_level": "low",
                "concepts": ["neural networks", "AI"]
            }
        ]

        for interaction in test_interactions:
            understanding = await traditional_mode.evaluate_concept_understanding(
                interaction["user_response"],
                interaction["concepts"]
            )

            # Verify understanding object structure
            assert hasattr(understanding, 'concept_name')
            assert hasattr(understanding, 'understanding_level')
            assert hasattr(understanding, 'confidence_score')
            assert hasattr(understanding, 'evidence_phrases')

            # Verify understanding levels match expectations
            if interaction["expected_understanding_level"] == "high":
                assert understanding.understanding_level >= 0.7
            elif interaction["expected_understanding_level"] == "medium":
                assert 0.3 <= understanding.understanding_level <= 0.7
            else:  # low
                assert understanding.understanding_level <= 0.4


class TestProgressConsistency:
    """Test progress calculation consistency across sessions."""

    @pytest.fixture
    def mode_with_history(self):
        """Mode instance with interaction history."""
        mode = TraditionalMode(['doc1'], 'user-test', 3)

        # Add mock interaction history
        mode.session_context['user_performance_scores'] = [0.2, 0.4, 0.6, 0.8, 0.7]
        mode.session_context['concepts_covered'] = {
            'machine learning', 'neural networks', 'algorithms', 'data science'
        }
        mode.session_context['interactions_count'] = 5

        return mode

    def test_progress_calculation_consistency(self, mode_with_history):
        """Test that progress calculations are consistent."""
        # Multiple calls should return the same result
        progress1 = mode_with_history.calculate_session_progress()
        progress2 = mode_with_history.calculate_session_progress()
        progress3 = mode_with_history.calculate_session_progress()

        assert progress1 == progress2 == progress3
        assert 0.0 <= progress1 <= 1.0

    def test_progress_incremental_updates(self, mode_with_history):
        """Test that progress updates incrementally and correctly."""
        initial_progress = mode_with_history.calculate_session_progress()

        # Add a high-quality interaction
        mode_with_history.session_context['user_performance_scores'].append(0.9)
        mode_with_history.session_context['interactions_count'] += 1
        new_progress = mode_with_history.calculate_session_progress()

        assert new_progress >= initial_progress  # Should improve or stay same

        # Add a low-quality interaction
        mode_with_history.session_context['user_performance_scores'].append(0.1)
        mode_with_history.session_context['interactions_count'] += 1
        final_progress = mode_with_history.calculate_session_progress()

        # Progress should reflect the overall average
        expected_avg = sum(mode_with_history.session_context['user_performance_scores']) / len(mode_with_history.session_context['user_performance_scores'])
        assert abs(final_progress - expected_avg) < 0.1

    def test_concept_mastery_tracking(self, mode_with_history):
        """Test concept mastery progression tracking."""
        # Test concept mastery evaluation
        concepts = mode_with_history.get_covered_concepts()
        assert len(concepts) == 4
        assert 'machine learning' in concepts
        assert 'neural networks' in concepts

        # Add new concept
        mode_with_history.add_covered_concept('deep learning')
        updated_concepts = mode_with_history.get_covered_concepts()
        assert len(updated_concepts) == 5
        assert 'deep learning' in updated_concepts

        # Adding duplicate should not increase count
        mode_with_history.add_covered_concept('machine learning')
        final_concepts = mode_with_history.get_covered_concepts()
        assert len(final_concepts) == 5  # Should still be 5


class TestCrossSessionConsistency:
    """Test consistency across different sessions and study modes."""

    def test_concept_extraction_consistency_across_modes(self):
        """Test that concept extraction works consistently across different study modes."""
        # This would test Feynman, Socratic, and Debate modes when implemented
        # For now, we test the base functionality that all modes will inherit

        traditional_mode = TraditionalMode(['doc1'], 'user1', 3)

        test_response = "Machine learning algorithms like neural networks use gradient descent to optimize loss functions."

        concepts = traditional_mode.extract_concepts_from_response(test_response)

        # All modes should extract similar core concepts
        concept_text = ' '.join(concepts).lower()
        assert 'machine learning' in concept_text or 'ml' in concept_text
        assert 'neural' in concept_text
        assert 'gradient' in concept_text or 'optimization' in concept_text

    def test_difficulty_adjustment_consistency(self):
        """Test difficulty adjustment is consistent across sessions."""
        mode1 = TraditionalMode(['doc1'], 'user1', 3)
        mode2 = TraditionalMode(['doc1'], 'user1', 3)

        # Same performance should lead to same difficulty adjustments
        performance_scores = [0.2, 0.3, 0.1, 0.4]

        for score in performance_scores:
            mode1.session_context['user_performance_scores'].append(score)
            mode2.session_context['user_performance_scores'].append(score)

        # Both should adjust difficulty the same way
        new_level1 = mode1.calculate_suggested_difficulty()
        new_level2 = mode2.calculate_suggested_difficulty()

        assert new_level1 == new_level2

    @pytest.mark.asyncio
    async def test_understanding_evaluation_consistency(self):
        """Test understanding evaluation consistency."""
        mode1 = TraditionalMode(['doc1'], 'user1', 3)
        mode2 = TraditionalMode(['doc1'], 'user1', 3)

        test_response = "Neural networks are computational models inspired by biological neural networks. They consist of interconnected nodes that process information."
        test_concepts = ["neural networks", "computational models", "nodes"]

        # Both modes should evaluate understanding similarly
        understanding1 = await mode1.evaluate_concept_understanding(test_response, test_concepts)
        understanding2 = await mode2.evaluate_concept_understanding(test_response, test_concepts)

        # Should be very similar (allowing for small floating point differences)
        assert abs(understanding1.understanding_level - understanding2.understanding_level) < 0.1
        assert abs(understanding1.confidence_score - understanding2.confidence_score) < 0.1


class TestAnalyticsDataConsistency:
    """Test analytics data consistency and accuracy."""

    @pytest.fixture
    def analytics_mode(self):
        """Mode with analytics data for testing."""
        mode = TraditionalMode(['doc1'], 'user-analytics', 3)

        # Add realistic interaction data
        interactions = [
            ("What is machine learning?", "It's when computers learn from data", 0.6),
            ("Can you give an example?", "Like spam email detection using neural networks", 0.8),
            ("How does backpropagation work?", "It adjusts weights by calculating gradients backwards through the network", 0.9),
            ("What about overfitting?", "When models memorize training data instead of learning patterns", 0.7),
            ("Any prevention techniques?", "Cross-validation, regularization, and dropout can help", 0.8)
        ]

        for prompt, response, score in interactions:
            mode.session_context['user_performance_scores'].append(score)
            concepts = mode.extract_concepts_from_response(response)
            for concept in concepts:
                mode.add_covered_concept(concept)

        mode.session_context['interactions_count'] = len(interactions)
        return mode

    def test_learning_insights_generation(self, analytics_mode):
        """Test learning insights generation accuracy."""
        insights = analytics_mode.generate_learning_insights()

        # Verify insights structure
        assert hasattr(insights, 'total_study_time')
        assert hasattr(insights, 'concepts_mastered')
        assert hasattr(insights, 'average_understanding_score')
        assert hasattr(insights, 'areas_for_improvement')
        assert hasattr(insights, 'recommended_next_topics')

        # Verify data accuracy
        assert insights.average_understanding_score > 0.6  # Should reflect good performance
        assert len(insights.concepts_mastered) >= 3  # Should have identified several concepts
        assert len(insights.recommended_next_topics) >= 2  # Should suggest follow-up topics

    def test_spaced_repetition_scheduling(self, analytics_mode):
        """Test spaced repetition scheduling consistency."""
        concepts = analytics_mode.get_covered_concepts()

        for concept in concepts:
            # Test concept understanding object creation
            concept_understanding = ConceptUnderstanding(
                concept_name=concept,
                understanding_level=0.7,
                confidence_score=0.8,
                last_reviewed=analytics_mode.session_context.get('created_at'),
                review_history=[0.5, 0.6, 0.7]
            )

            # Test next review calculation
            next_review = concept_understanding.calculate_next_review_date()
            assert next_review is not None

            # Test difficulty calculation
            difficulty = concept_understanding.calculate_concept_difficulty()
            assert 0.0 <= difficulty <= 1.0

    def test_performance_trend_analysis(self, analytics_mode):
        """Test performance trend analysis."""
        scores = analytics_mode.session_context['user_performance_scores']

        # Test trend calculation
        trend = analytics_mode.calculate_performance_trend()

        # With scores [0.6, 0.8, 0.9, 0.7, 0.8], trend should be positive overall
        assert trend > 0  # Overall improving trend

        # Test moving average calculation
        moving_avg = analytics_mode.calculate_moving_average_performance(window=3)
        assert len(moving_avg) <= len(scores)
        assert all(0.0 <= avg <= 1.0 for avg in moving_avg)

    def test_recommendation_engine_consistency(self, analytics_mode):
        """Test recommendation engine consistency."""
        # Generate recommendations multiple times
        recommendations1 = analytics_mode.generate_study_recommendations()
        recommendations2 = analytics_mode.generate_study_recommendations()

        # Should be consistent (deterministic based on current state)
        assert len(recommendations1) == len(recommendations2)

        # Should include relevant recommendation types
        rec_types = [rec.get('type') for rec in recommendations1]
        assert 'concept_review' in rec_types or 'next_topic' in rec_types
        assert 'difficulty_adjustment' in rec_types or 'study_method' in rec_types

    @pytest.mark.asyncio
    async def test_session_summary_accuracy(self, analytics_mode):
        """Test session summary generation accuracy."""
        mock_responses = [
            "Machine learning helps computers learn from data automatically",
            "Neural networks use backpropagation to adjust their weights",
            "Overfitting occurs when models memorize instead of generalizing",
            "Regularization techniques help prevent overfitting",
            "Cross-validation helps evaluate model performance reliably"
        ]

        summary = await analytics_mode.generate_session_summary(mock_responses)

        # Verify summary completeness
        assert summary['total_interactions'] == len(mock_responses)
        assert len(summary['concepts_covered']) >= 3
        assert 0.0 <= summary['average_understanding'] <= 1.0
        assert 'recommendations' in summary
        assert len(summary['recommendations']) >= 1

        # Verify summary reflects actual performance
        expected_avg = sum(analytics_mode.session_context['user_performance_scores']) / len(analytics_mode.session_context['user_performance_scores'])
        assert abs(summary['average_understanding'] - expected_avg) < 0.1


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling in understanding evaluation."""

    def test_malformed_response_handling(self):
        """Test handling of malformed or problematic responses."""
        mode = TraditionalMode(['doc1'], 'user-test', 3)

        problematic_responses = [
            None,
            "",
            "   ",
            "\n\n\n",
            "🤖🚀✨" * 100,  # Emoji spam
            "a" * 10000,  # Extremely long
            "SELECT * FROM users; DROP TABLE students;",  # SQL injection attempt
            "<script>alert('xss')</script>",  # XSS attempt
        ]

        for response in problematic_responses:
            try:
                # Should not crash
                if response is not None:
                    concepts = mode.extract_concepts_from_response(response)
                    assert isinstance(concepts, list)
                    score = mode.calculate_response_quality_score(response, [])
                    assert 0.0 <= score <= 1.0
            except ValueError as e:
                # ValueError is acceptable for clearly invalid input
                assert "validation" in str(e).lower() or "invalid" in str(e).lower()

    @pytest.mark.asyncio
    async def test_concept_understanding_with_no_context(self):
        """Test concept understanding evaluation with missing context."""
        mode = TraditionalMode(['doc1'], 'user-test', 3)

        # Test with empty concepts list
        understanding = await mode.evaluate_concept_understanding(
            "This is a response about machine learning",
            []
        )

        assert understanding is not None
        assert hasattr(understanding, 'understanding_level')
        assert 0.0 <= understanding.understanding_level <= 1.0

    def test_performance_calculation_edge_cases(self):
        """Test performance calculations with edge case data."""
        mode = TraditionalMode(['doc1'], 'user-test', 3)

        # Test with no performance scores
        assert mode.calculate_session_progress() == 0.0

        # Test with single score
        mode.session_context['user_performance_scores'] = [0.5]
        assert mode.calculate_session_progress() == 0.5

        # Test with extreme scores
        mode.session_context['user_performance_scores'] = [0.0, 1.0, 0.0, 1.0]
        progress = mode.calculate_session_progress()
        assert progress == 0.5  # Should average correctly

        # Test with all same scores
        mode.session_context['user_performance_scores'] = [0.7] * 10
        assert mode.calculate_session_progress() == 0.7
