"""
Abstract base class for study mode implementations.
"""

import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..models.study_session import StudyPrompt, SessionResponse


class BaseStudyMode(ABC):
    """
    Abstract base class for all study modes.

    This class defines the interface that all study mode implementations must follow,
    ensuring consistent behavior across different learning methodologies.
    """

    def __init__(self, documents: List[str], user_id: str, difficulty_level: int = 1):
        """
        Initialize study mode with user context.

        Args:
            documents: List of document IDs for this session
            user_id: User identifier for personalization
            difficulty_level: 1-5 scale for prompt difficulty
        """
        self.documents = documents
        self.user_id = user_id
        self.difficulty_level = difficulty_level
        self.session_context: Dict[str, Any] = {
            "interactions_count": 0,
            "concepts_covered": set(),
            "user_performance_scores": [],
            "difficulty_adjustments": [],
            "document_context": {}
        }

    @abstractmethod
    async def generate_initial_prompt(self) -> StudyPrompt:
        """
        Generate the first prompt to start the session.

        This method should analyze the user's documents and create an appropriate
        opening prompt based on the study mode's methodology.

        Returns:
            StudyPrompt: Initial prompt to begin the learning session

        Raises:
            ValueError: If documents are invalid or inaccessible
        """
        pass

    @abstractmethod
    async def process_user_response(self, response: str, current_prompt: StudyPrompt) -> SessionResponse:
        """
        Process user's response and generate next interaction.

        This is the core method that implements the study mode's learning logic.
        It should analyze the user's response and determine the next step in the
        learning process.

        Args:
            response: User's text response to the current prompt
            current_prompt: The prompt the user was responding to

        Returns:
            SessionResponse: AI feedback and next prompt (if any)

        Raises:
            ValueError: If response is invalid or cannot be processed
        """
        pass

    @abstractmethod
    async def evaluate_understanding(self, responses: List[str]) -> Dict[str, float]:
        """
        Evaluate user's understanding based on their responses.

        This method should analyze all responses in the session to assess
        the user's comprehension of different concepts.

        Args:
            responses: List of all user responses in the session

        Returns:
            Dict mapping concept names to understanding scores (0.0-1.0)
        """
        pass

    async def get_document_context(self, document_ids: List[str]) -> Dict[str, Any]:
        """
        Retrieve relevant context from documents for prompt generation.

        Args:
            document_ids: List of document IDs to analyze

        Returns:
            Dictionary containing extracted concepts, themes, and content
        """
        # Check if context is already cached
        cache_key = "_".join(sorted(document_ids))
        if cache_key in self.session_context["document_context"]:
            return self.session_context["document_context"][cache_key]

        # TODO: This would integrate with your existing document retrieval system
        # For now, we'll simulate document context extraction
        context = {
            "main_topics": [],
            "key_concepts": [],
            "document_summaries": {},
            "complexity_level": 1,
            "total_content_length": 0
        }

        # This would be replaced with actual document retrieval from your system
        try:
            # Simulate document analysis
            for doc_id in document_ids:
                # In real implementation, this would fetch from Weaviate/Supabase
                doc_summary = f"Summary of document {doc_id}"
                context["document_summaries"][doc_id] = doc_summary

                # Extract key concepts (would use NLP/AI in real implementation)
                concepts = [f"concept_{doc_id}_1", f"concept_{doc_id}_2"]
                context["key_concepts"].extend(concepts)

                # Estimate complexity
                context["complexity_level"] = max(context["complexity_level"],
                                                  min(5, len(concepts)))

            # Remove duplicates and cache
            context["key_concepts"] = list(set(context["key_concepts"]))
            self.session_context["document_context"][cache_key] = context

        except Exception as e:
            print(f"Warning: Could not retrieve document context: {e}")
            # Return minimal context to prevent failures
            context = {
                "main_topics": ["General topic"],
                "key_concepts": ["Basic concepts"],
                "document_summaries": {doc_id: f"Document {doc_id}" for doc_id in document_ids},
                "complexity_level": self.difficulty_level,
                "total_content_length": 1000
            }

        return context

    async def adjust_difficulty(self, user_performance: float) -> int:
        """
        Adjust difficulty level based on user performance.

        Args:
            user_performance: Performance score (0.0-1.0)

        Returns:
            New difficulty level (1-5)
        """
        current_level = self.difficulty_level

        # Track performance history
        self.session_context["user_performance_scores"].append(user_performance)

        # Only adjust after getting some performance data
        if len(self.session_context["user_performance_scores"]) < 3:
            return current_level

        # Calculate recent average performance
        recent_scores = self.session_context["user_performance_scores"][-3:]
        avg_performance = sum(recent_scores) / len(recent_scores)

        # Adjust difficulty based on performance
        if avg_performance > 0.8 and current_level < 5:
            new_level = min(5, current_level + 1)
            adjustment_reason = "High performance - increasing difficulty"
        elif avg_performance < 0.4 and current_level > 1:
            new_level = max(1, current_level - 1)
            adjustment_reason = "Low performance - decreasing difficulty"
        else:
            new_level = current_level
            adjustment_reason = "Performance adequate - maintaining level"

        # Log the adjustment
        if new_level != current_level:
            self.session_context["difficulty_adjustments"].append({
                "from_level": current_level,
                "to_level": new_level,
                "reason": adjustment_reason,
                "avg_performance": avg_performance
            })
            self.difficulty_level = new_level

        return new_level

    async def generate_session_summary(self, responses: List[str]) -> Dict[str, Any]:
        """
        Generate summary of the session for analytics.

        Args:
            responses: All user responses in the session

        Returns:
            Session summary with learning insights
        """
        understanding_scores = await self.evaluate_understanding(responses)

        summary = {
            "total_interactions": len(responses),
            "concepts_covered": list(self.session_context["concepts_covered"]),
            "understanding_scores": understanding_scores,
            "average_understanding": sum(understanding_scores.values()) / len(understanding_scores) if understanding_scores else 0.0,
            "difficulty_progression": {
                "initial_level": self.session_context.get("initial_difficulty", self.difficulty_level),
                "final_level": self.difficulty_level,
                "adjustments": self.session_context["difficulty_adjustments"]
            },
            "performance_trend": self.session_context["user_performance_scores"],
            "strengths": [],
            "areas_for_improvement": [],
            "recommendations": []
        }

        # Analyze strengths and weaknesses
        for concept, score in understanding_scores.items():
            if score >= 0.7:
                summary["strengths"].append(concept)
            elif score < 0.5:
                summary["areas_for_improvement"].append(concept)

        # Generate recommendations
        if summary["average_understanding"] < 0.5:
            summary["recommendations"].append("Consider reviewing fundamental concepts before proceeding")
            summary["recommendations"].append("Try using a lower difficulty level")
        elif summary["average_understanding"] > 0.8:
            summary["recommendations"].append("You're doing great! Consider increasing difficulty for more challenge")
            summary["recommendations"].append("Ready to explore advanced topics in this area")

        if len(summary["areas_for_improvement"]) > 0:
            summary["recommendations"].append(f"Focus additional study on: {', '.join(summary['areas_for_improvement'][:3])}")

        return summary

    def update_session_context(self, key: str, value: Any) -> None:
        """
        Update session context with new information.

        Args:
            key: Context key to update
            value: New value for the key
        """
        self.session_context[key] = value

    def add_covered_concept(self, concept: str) -> None:
        """
        Add a concept to the list of covered concepts.

        Args:
            concept: Concept name to add
        """
        self.session_context["concepts_covered"].add(concept)

    def get_interaction_count(self) -> int:
        """
        Get the number of interactions in this session.

        Returns:
            Number of interactions processed
        """
        return self.session_context["interactions_count"]

    def increment_interactions(self) -> None:
        """Increment the interaction count."""
        self.session_context["interactions_count"] += 1

    def get_covered_concepts(self) -> List[str]:
        """
        Get list of concepts covered in this session.

        Returns:
            List of concept names
        """
        return list(self.session_context["concepts_covered"])

    def validate_user_response(self, response: str) -> bool:
        """
        Validate user response for basic requirements.

        Args:
            response: User's response text

        Returns:
            True if response is valid, False otherwise
        """
        if not response or not response.strip():
            return False

        # Check minimum length (at least 10 characters)
        if len(response.strip()) < 10:
            return False

        # Check for reasonable maximum length (10,000 characters)
        if len(response) > 10000:
            return False

        return True

    def calculate_response_quality_score(self, response: str, expected_concepts: List[str]) -> float:
        """
        Calculate quality score for user response.

        Args:
            response: User's response text
            expected_concepts: Concepts that should be addressed

        Returns:
            Quality score from 0.0 to 1.0
        """
        if not self.validate_user_response(response):
            return 0.0

        score = 0.0
        response_lower = response.lower()

        # Length score (appropriate length gets full points)
        length = len(response.strip())
        if 50 <= length <= 500:
            length_score = 1.0
        elif length < 50:
            length_score = length / 50.0
        else:
            length_score = max(0.5, 1.0 - (length - 500) / 1000.0)

        score += length_score * 0.3

        # Concept coverage score
        if expected_concepts:
            covered_concepts = sum(1 for concept in expected_concepts
                                 if concept.lower() in response_lower)
            concept_score = covered_concepts / len(expected_concepts)
            score += concept_score * 0.5
        else:
            score += 0.5  # No specific concepts to check

        # Complexity/depth score (simple heuristic)
        sentences = response.count('.') + response.count('!') + response.count('?')
        complexity_indicators = ['because', 'therefore', 'however', 'although', 'furthermore']
        complexity_count = sum(1 for indicator in complexity_indicators
                             if indicator in response_lower)

        if sentences > 0 and complexity_count > 0:
            depth_score = min(1.0, (sentences * 0.2) + (complexity_count * 0.3))
        else:
            depth_score = 0.2

        score += depth_score * 0.2

        return min(1.0, score)
