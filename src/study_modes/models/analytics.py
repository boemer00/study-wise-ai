"""
Learning analytics and insights data models.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from .study_session import StudyMode


@dataclass
class ConceptUnderstanding:
    """
    Represents understanding level for a specific concept.

    Attributes:
        concept_name: Name of the concept
        understanding_score: 0.0-1.0 score indicating mastery level
        study_mode: Which study mode was used to learn this concept
        document_source: Which document the concept came from
        learning_sessions: Number of sessions spent on this concept
        last_practiced: When this concept was last reviewed
        confidence_trend: List of recent confidence scores
        weak_areas: Specific aspects that need improvement
    """
    concept_name: str = ""
    understanding_score: float = 0.0
    study_mode: StudyMode = StudyMode.TRADITIONAL
    document_source: str = ""
    learning_sessions: int = 0
    last_practiced: Optional[datetime] = None
    confidence_trend: List[float] = field(default_factory=list)
    weak_areas: List[str] = field(default_factory=list)

    def update_understanding(self, new_score: float) -> None:
        """
        Update understanding score and trend.

        Args:
            new_score: New understanding score (0.0-1.0)
        """
        self.understanding_score = max(0.0, min(1.0, new_score))
        self.confidence_trend.append(self.understanding_score)
        self.last_practiced = datetime.now(timezone.utc)

        # Keep only last 10 scores for trend analysis
        if len(self.confidence_trend) > 10:
            self.confidence_trend = self.confidence_trend[-10:]

    def is_improving(self) -> bool:
        """
        Check if understanding is improving based on recent trend.

        Returns:
            True if trend shows improvement
        """
        if len(self.confidence_trend) < 3:
            return False

        recent_scores = self.confidence_trend[-3:]
        return recent_scores[-1] > recent_scores[0]

    def needs_review(self, days_threshold: int = 7) -> bool:
        """
        Check if concept needs review based on last practice time.

        Args:
            days_threshold: Days since last practice to trigger review

        Returns:
            True if needs review
        """
        if not self.last_practiced:
            return True

        days_since_practice = (datetime.now(timezone.utc) - self.last_practiced).days

        # Higher understanding requires less frequent review
        review_interval = int(days_threshold * (1 + self.understanding_score))
        return days_since_practice >= review_interval


@dataclass
class StudyModePreference:
    """
    Tracks user preferences and effectiveness for different study modes.

    Attributes:
        study_mode: The study mode being analyzed
        usage_count: Number of times user has used this mode
        average_understanding_improvement: Average improvement per session
        preferred_difficulty_level: User's preferred difficulty (1-5)
        session_completion_rate: Percentage of completed sessions
        average_session_duration: Average time spent in this mode
        effectiveness_score: Overall effectiveness rating (0.0-1.0)
        user_feedback_score: User's subjective rating of this mode
    """
    study_mode: StudyMode = StudyMode.TRADITIONAL
    usage_count: int = 0
    average_understanding_improvement: float = 0.0
    preferred_difficulty_level: int = 1
    session_completion_rate: float = 0.0
    average_session_duration: int = 0
    effectiveness_score: float = 0.0
    user_feedback_score: Optional[float] = None

    def update_from_session(self, session_duration: int, understanding_improvement: float, completed: bool) -> None:
        """
        Update preferences based on a new session.

        Args:
            session_duration: Duration of the session in seconds
            understanding_improvement: Improvement in understanding (0.0-1.0)
            completed: Whether the session was completed
        """
        # Update usage count
        self.usage_count += 1

        # Update average understanding improvement
        if self.usage_count == 1:
            self.average_understanding_improvement = understanding_improvement
        else:
            self.average_understanding_improvement = (
                (self.average_understanding_improvement * (self.usage_count - 1) + understanding_improvement)
                / self.usage_count
            )

        # Update average session duration
        if self.usage_count == 1:
            self.average_session_duration = session_duration
        else:
            self.average_session_duration = int(
                (self.average_session_duration * (self.usage_count - 1) + session_duration)
                / self.usage_count
            )

        # Update completion rate
        completed_sessions = int(self.session_completion_rate * (self.usage_count - 1) / 100)
        if completed:
            completed_sessions += 1
        self.session_completion_rate = (completed_sessions / self.usage_count) * 100

        # Calculate effectiveness score (combination of improvement and completion)
        self.effectiveness_score = (
            self.average_understanding_improvement * 0.7 +
            (self.session_completion_rate / 100) * 0.3
        )

    def get_recommendation_strength(self) -> str:
        """
        Get recommendation strength for this study mode.

        Returns:
            Recommendation level: "highly_recommended", "recommended", "neutral", "not_recommended"
        """
        if self.effectiveness_score >= 0.8:
            return "highly_recommended"
        elif self.effectiveness_score >= 0.6:
            return "recommended"
        elif self.effectiveness_score >= 0.4:
            return "neutral"
        else:
            return "not_recommended"


@dataclass
class LearningInsights:
    """
    Comprehensive learning insights and recommendations for a user.

    Attributes:
        user_id: User these insights belong to
        analysis_period_days: Number of days of data analyzed
        total_study_sessions: Total sessions completed
        total_study_time_hours: Total time spent studying
        strong_concepts: Concepts the user has mastered
        weak_concepts: Concepts needing improvement
        preferred_study_mode: Most effective study mode for this user
        study_mode_preferences: Detailed breakdown by mode
        recommended_review_concepts: Concepts due for review
        suggested_difficulty_adjustment: Recommended difficulty changes
        learning_velocity: Rate of concept mastery (concepts/week)
        consistency_score: How consistently user studies (0.0-1.0)
        upcoming_focus_areas: What to study next
        personalized_tips: Customized learning recommendations
        generated_at: When these insights were created
    """
    user_id: str = ""
    analysis_period_days: int = 30
    total_study_sessions: int = 0
    total_study_time_hours: float = 0.0
    strong_concepts: List[ConceptUnderstanding] = field(default_factory=list)
    weak_concepts: List[ConceptUnderstanding] = field(default_factory=list)
    preferred_study_mode: StudyMode = StudyMode.TRADITIONAL
    study_mode_preferences: List[StudyModePreference] = field(default_factory=list)
    recommended_review_concepts: List[str] = field(default_factory=list)
    suggested_difficulty_adjustment: Dict[StudyMode, int] = field(default_factory=dict)
    learning_velocity: float = 0.0
    consistency_score: float = 0.0
    upcoming_focus_areas: List[str] = field(default_factory=list)
    personalized_tips: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def get_weakest_concepts(self, limit: int = 5) -> List[ConceptUnderstanding]:
        """
        Get the concepts that need the most improvement.

        Args:
            limit: Maximum number of concepts to return

        Returns:
            List of concepts ordered by improvement need
        """
        # Sort all concepts by understanding score (ascending)
        all_concepts = self.strong_concepts + self.weak_concepts
        weakest = sorted(all_concepts, key=lambda c: c.understanding_score)

        # Filter for concepts with low scores (< 0.6)
        weak_concepts = [c for c in weakest if c.understanding_score < 0.6]

        return weak_concepts[:limit]

    def get_ready_for_review(self) -> List[ConceptUnderstanding]:
        """
        Get concepts that are ready for spaced repetition review.

        Returns:
            List of concepts due for review
        """
        all_concepts = self.strong_concepts + self.weak_concepts
        return [c for c in all_concepts if c.needs_review()]

    def calculate_overall_progress(self) -> float:
        """
        Calculate overall learning progress score.

        Returns:
            Progress score from 0.0 to 1.0
        """
        if not self.strong_concepts and not self.weak_concepts:
            return 0.0

        all_concepts = self.strong_concepts + self.weak_concepts
        if not all_concepts:
            return 0.0

        # Calculate average understanding across all concepts
        total_understanding = sum(c.understanding_score for c in all_concepts)
        average_understanding = total_understanding / len(all_concepts)

        # Factor in consistency and learning velocity
        consistency_factor = self.consistency_score
        velocity_factor = min(1.0, self.learning_velocity / 2.0)  # Normalize velocity

        # Weighted combination
        progress = (
            average_understanding * 0.6 +
            consistency_factor * 0.2 +
            velocity_factor * 0.2
        )

        return min(1.0, max(0.0, progress))

    def generate_personalized_tips(self) -> List[str]:
        """
        Generate personalized learning tips based on user data.

        Returns:
            List of personalized recommendations
        """
        tips = []

        # Consistency tips
        if self.consistency_score < 0.5:
            tips.append("Try to study regularly - even 15 minutes daily is better than long irregular sessions.")

        # Study mode recommendations
        best_mode = self.get_most_effective_study_mode()
        if best_mode != StudyMode.TRADITIONAL:
            tips.append(f"You seem to learn best with {best_mode.value} mode. Consider using it more often.")

        # Difficulty adjustment tips
        if self.needs_difficulty_increase():
            tips.append("You're mastering concepts quickly! Try increasing the difficulty level for more challenge.")
        elif self.needs_difficulty_decrease():
            tips.append("Consider lowering the difficulty level to build stronger foundations.")

        # Review tips
        review_concepts = self.get_ready_for_review()
        if review_concepts:
            tips.append(f"Review these concepts: {', '.join([c.concept_name for c in review_concepts[:3]])}")

        # Weak area focus
        weak_concepts = self.get_weakest_concepts(3)
        if weak_concepts:
            tips.append(f"Focus extra attention on: {', '.join([c.concept_name for c in weak_concepts])}")

        self.personalized_tips = tips
        return tips

    def get_most_effective_study_mode(self) -> StudyMode:
        """
        Get the most effective study mode for this user.

        Returns:
            StudyMode with highest effectiveness score
        """
        if not self.study_mode_preferences:
            return StudyMode.TRADITIONAL

        best_mode = max(self.study_mode_preferences, key=lambda p: p.effectiveness_score)
        return best_mode.study_mode

    def needs_difficulty_increase(self) -> bool:
        """
        Check if user would benefit from increased difficulty.

        Returns:
            True if difficulty should be increased
        """
        # High understanding scores and fast learning velocity suggest need for more challenge
        avg_understanding = self.calculate_overall_progress()
        return avg_understanding > 0.8 and self.learning_velocity > 3.0

    def needs_difficulty_decrease(self) -> bool:
        """
        Check if user would benefit from decreased difficulty.

        Returns:
            True if difficulty should be decreased
        """
        # Low understanding scores and slow velocity suggest need for easier content
        avg_understanding = self.calculate_overall_progress()
        return avg_understanding < 0.4 and self.learning_velocity < 0.5

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert insights to dictionary for serialization.

        Returns:
            Dictionary representation of insights
        """
        return {
            "user_id": self.user_id,
            "analysis_period_days": self.analysis_period_days,
            "total_study_sessions": self.total_study_sessions,
            "total_study_time_hours": self.total_study_time_hours,
            "overall_progress": self.calculate_overall_progress(),
            "preferred_study_mode": self.preferred_study_mode.value,
            "learning_velocity": self.learning_velocity,
            "consistency_score": self.consistency_score,
            "weak_concepts": [
                {
                    "name": c.concept_name,
                    "score": c.understanding_score,
                    "needs_review": c.needs_review(),
                    "improving": c.is_improving()
                }
                for c in self.get_weakest_concepts()
            ],
            "ready_for_review": [c.concept_name for c in self.get_ready_for_review()],
            "personalized_tips": self.generate_personalized_tips(),
            "study_mode_effectiveness": [
                {
                    "mode": p.study_mode.value,
                    "effectiveness_score": p.effectiveness_score,
                    "usage_count": p.usage_count,
                    "recommendation": p.get_recommendation_strength()
                }
                for p in self.study_mode_preferences
            ],
            "generated_at": self.generated_at.isoformat()
        }
