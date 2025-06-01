"""
Core data models for study sessions and interactions.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Union


class StudyMode(Enum):
    """Available study modes for learning sessions."""
    TRADITIONAL = "traditional"
    FEYNMAN = "feynman"
    SOCRATIC = "socratic"
    DEBATE = "debate"


class PromptType(Enum):
    """Types of prompts that can be generated."""
    QUESTION = "question"
    EXPLANATION_REQUEST = "explanation_request"
    CHALLENGE = "challenge"
    CLARIFICATION = "clarification"
    SIMPLIFICATION = "simplification"
    ANALOGY_REQUEST = "analogy_request"


class SessionStage(Enum):
    """Current stage of a study session."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    TRANSITIONING = "transitioning"
    COMPLETED = "completed"
    PAUSED = "paused"


@dataclass
class StudyPrompt:
    """
    Represents a prompt/question in a study session.

    Attributes:
        prompt_id: Unique identifier for this prompt
        prompt_text: The actual text of the prompt/question
        prompt_type: Type of prompt for different interaction styles
        difficulty_level: 1-5 scale indicating prompt complexity
        related_documents: Document IDs relevant to this prompt
        expected_concepts: Key concepts the prompt aims to explore
        context: Additional context for prompt generation
        created_at: When the prompt was created
    """
    prompt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt_text: str = ""
    prompt_type: PromptType = PromptType.QUESTION
    difficulty_level: int = 1
    related_documents: List[str] = field(default_factory=list)
    expected_concepts: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SessionResponse:
    """
    Response from the AI system after processing user input.

    Attributes:
        response_id: Unique identifier for this response
        ai_message: The AI's response text
        next_prompt: Next prompt in the sequence (if any)
        session_stage: Current stage of the session
        progress_percentage: How far through the session (0-100)
        feedback: Specific feedback on user's response
        suggestions: List of suggestions for improvement
        metadata: Additional response metadata
        created_at: When the response was generated
    """
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ai_message: str = ""
    next_prompt: Optional[StudyPrompt] = None
    session_stage: SessionStage = SessionStage.ACTIVE
    progress_percentage: float = 0.0
    feedback: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class StudySession:
    """
    Represents a complete study mode session.

    Attributes:
        session_id: Unique session identifier
        user_id: User who owns this session
        study_mode: The learning methodology being used
        document_ids: Documents being studied in this session
        session_goals: Learning objectives for this session
        current_prompt: Current active prompt
        conversation_history: All prompts and responses in order
        session_stage: Current session stage
        difficulty_level: Current difficulty level (1-5)
        start_time: When the session began
        end_time: When the session ended (if completed)
        total_duration_seconds: Total session duration
        progress_percentage: Overall session progress (0-100)
        session_metadata: Additional session data
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    study_mode: StudyMode = StudyMode.TRADITIONAL
    document_ids: List[str] = field(default_factory=list)
    session_goals: List[str] = field(default_factory=list)
    current_prompt: Optional[StudyPrompt] = None
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    session_stage: SessionStage = SessionStage.INITIALIZING
    difficulty_level: int = 1
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    total_duration_seconds: int = 0
    progress_percentage: float = 0.0
    session_metadata: Dict[str, Any] = field(default_factory=dict)

    def add_interaction(self, prompt: StudyPrompt, user_response: str, ai_response: SessionResponse) -> None:
        """
        Add a new interaction to the session history.

        Args:
            prompt: The prompt that was presented
            user_response: User's response to the prompt
            ai_response: AI's response and next prompt
        """
        interaction = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": {
                "prompt_id": prompt.prompt_id,
                "prompt_text": prompt.prompt_text,
                "prompt_type": prompt.prompt_type.value,
                "difficulty_level": prompt.difficulty_level,
                "expected_concepts": prompt.expected_concepts
            },
            "user_response": user_response,
            "ai_response": {
                "response_id": ai_response.response_id,
                "ai_message": ai_response.ai_message,
                "feedback": ai_response.feedback,
                "suggestions": ai_response.suggestions,
                "progress_percentage": ai_response.progress_percentage
            }
        }
        self.conversation_history.append(interaction)

    def update_progress(self, new_percentage: float) -> None:
        """
        Update session progress percentage.

        Args:
            new_percentage: New progress value (0-100)
        """
        self.progress_percentage = max(0.0, min(100.0, new_percentage))

        # Update metadata with progress tracking
        if "progress_updates" not in self.session_metadata:
            self.session_metadata["progress_updates"] = []

        self.session_metadata["progress_updates"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "progress": self.progress_percentage
        })

    def calculate_duration(self) -> int:
        """
        Calculate current session duration in seconds.

        Returns:
            Duration in seconds since session start
        """
        if self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        else:
            duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()

        self.total_duration_seconds = int(duration)
        return self.total_duration_seconds

    def is_active(self) -> bool:
        """
        Check if session is currently active.

        Returns:
            True if session is in active state
        """
        return self.session_stage in [SessionStage.ACTIVE, SessionStage.TRANSITIONING]

    def get_interaction_count(self) -> int:
        """
        Get the number of interactions in this session.

        Returns:
            Number of interactions
        """
        return len(self.conversation_history)

    def get_last_user_response(self) -> Optional[str]:
        """
        Get the last user response in the session.

        Returns:
            Last user response text or None if no interactions
        """
        if not self.conversation_history:
            return None
        return self.conversation_history[-1].get("user_response")

    def get_covered_concepts(self) -> List[str]:
        """
        Get all concepts covered in this session.

        Returns:
            List of unique concepts discussed
        """
        concepts = set()
        for interaction in self.conversation_history:
            prompt_concepts = interaction.get("prompt", {}).get("expected_concepts", [])
            concepts.update(prompt_concepts)
        return list(concepts)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert session to dictionary for serialization.

        Returns:
            Dictionary representation of the session
        """
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "study_mode": self.study_mode.value,
            "document_ids": self.document_ids,
            "session_goals": self.session_goals,
            "current_prompt": {
                "prompt_id": self.current_prompt.prompt_id,
                "prompt_text": self.current_prompt.prompt_text,
                "prompt_type": self.current_prompt.prompt_type.value,
                "difficulty_level": self.current_prompt.difficulty_level,
                "expected_concepts": self.current_prompt.expected_concepts,
                "created_at": self.current_prompt.created_at.isoformat()
            } if self.current_prompt else None,
            "conversation_history": self.conversation_history,
            "session_stage": self.session_stage.value,
            "difficulty_level": self.difficulty_level,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration_seconds": self.calculate_duration(),
            "progress_percentage": self.progress_percentage,
            "session_metadata": self.session_metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StudySession':
        """
        Create session from dictionary representation.

        Args:
            data: Dictionary containing session data

        Returns:
            StudySession instance
        """
        session = cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            study_mode=StudyMode(data["study_mode"]),
            document_ids=data["document_ids"],
            session_goals=data["session_goals"],
            session_stage=SessionStage(data["session_stage"]),
            difficulty_level=data["difficulty_level"],
            start_time=datetime.fromisoformat(data["start_time"].replace('Z', '+00:00')),
            progress_percentage=data["progress_percentage"],
            session_metadata=data["session_metadata"]
        )

        # Restore conversation history
        session.conversation_history = data["conversation_history"]

        # Restore end time if present
        if data.get("end_time"):
            session.end_time = datetime.fromisoformat(data["end_time"].replace('Z', '+00:00'))

        # Restore current prompt if present
        if data.get("current_prompt"):
            prompt_data = data["current_prompt"]
            session.current_prompt = StudyPrompt(
                prompt_id=prompt_data["prompt_id"],
                prompt_text=prompt_data["prompt_text"],
                prompt_type=PromptType(prompt_data["prompt_type"]),
                difficulty_level=prompt_data["difficulty_level"],
                expected_concepts=prompt_data["expected_concepts"],
                created_at=datetime.fromisoformat(prompt_data["created_at"].replace('Z', '+00:00'))
            )

        return session
